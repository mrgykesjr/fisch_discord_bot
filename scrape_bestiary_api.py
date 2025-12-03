#!/usr/bin/env python3
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import os
import time

# ---------------------------------------------
# CONFIG
# ---------------------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

BASE_URL = "https://fischipedia.org"
FISH_LIST_URL = BASE_URL + "/wiki/Fish"
OUTPUT_FILE = "data/bestiary.json"
LOG_FILE = "fischipedia_scrape_log.txt"

CONCURRENCY = 50  # adjust if needed


# ---------------------------------------------
# GET ALL FISH TITLES
# ---------------------------------------------
async def get_all_titles(session):
    async with session.get(FISH_LIST_URL, headers=HEADERS) as resp:
        text = await resp.text()

    soup = BeautifulSoup(text, "html.parser")
    titles = []

    for link in soup.select("a[href^='/wiki/']"):
        href = link.get("href", "")
        if not href.startswith("/wiki/"):
            continue

        raw = href.replace("/wiki/", "")

        if ":" in raw:
            continue
        if raw.lower() in ("main_page", "fish"):
            continue
        if "%" in raw:
            continue

        titles.append(raw.replace("_", " "))

    return sorted(set(titles))


# ---------------------------------------------
# PARSE INFOBOX
# ---------------------------------------------
def parse_infobox(html, title, url):
    soup = BeautifulSoup(html, "html.parser")
    fish = {"name": title, "url": url}
    missing = []

    inf = soup.find("div", class_="infobox")
    if not inf:
        return fish, ["infobox_missing"]

    datarows = inf.find_all("div", class_="infobox-datarow")

    for row in datarows:
        heading = row.find("p", class_="data-heading")
        content = row.find(class_="data-content")

        if not heading or not content:
            continue

        key = heading.get_text(strip=True).lower()
        val = content.get_text(" ", strip=True)

        key_map = {
            "rarity": "rarity",
            "location": "location",
            "weather": "weather",
            "time": "time",
            "season": "season",
            "bait": "bait",
            "sources": "sources",
            "resilience": "resilience",
        }

        if key in key_map:
            fish[key_map[key]] = val

    # C$/kg
    ckg = inf.find("p", class_="data-heading", string=lambda s: s and "C$/kg" in s)
    if ckg:
        node = ckg.find_next("p", class_="data-content")
        if node:
            fish["value_per_kg_base"] = node.get_text(strip=True)

    # TABBER
    tabber = inf.find("div", class_="tabber")
    if tabber:
        panels = tabber.find_all("article", class_="tabber__panel")

        for p in panels:
            rows = p.find_all("div", class_="infobox-datarow")

            for r in rows:
                heading = r.find("p", class_="data-heading")
                content = r.find("p", class_="data-content")

                if not heading or not content:
                    continue

                h = heading.get_text(strip=True).lower()
                v = content.get_text(strip=True).replace("kg", "").replace("C$", "").strip()

                if "min. kg" in h: fish["min_weight"] = v
                if "avg. kg" in h: fish["avg_weight"] = v
                if "base kg" in h: fish["base_weight"] = v
                if "max. kg" in h: fish["max_weight"] = v
                if "true min. kg" in h: fish["true_min_weight"] = v
                if "true max. kg" in h: fish["true_max_weight"] = v

                if "min. c$" in h: fish["min_value_c"] = v
                if "avg. c$" in h: fish["avg_value_c"] = v
                if "base c$" in h: fish["base_value_c"] = v
                if "max. c$" in h: fish["max_value_c"] = v
                if "true min. c$" in h: fish["true_min_value_c"] = v
                if "true max. c$" in h: fish["true_max_value_c"] = v

    return fish, missing


# ---------------------------------------------
# FETCH A SINGLE PAGE (ASYNC)
# ---------------------------------------------
async def fetch_fish(session, title):
    url_title = title.replace(" ", "_")
    url = f"{BASE_URL}/wiki/{url_title}"

    try:
        async with session.get(url, headers=HEADERS, timeout=20) as resp:
            html = await resp.text()
    except:
        return title, {"name": title, "url": url}, ["http_error"]

    if resp.status != 200:
        return title, {"name": title, "url": url}, [f"http_{resp.status}"]

    fish, missing = parse_infobox(html, title, url)
    return title, fish, missing


# ---------------------------------------------
# MAIN SCRAPER
# ---------------------------------------------
async def scrape_all(limit=None):
    async with aiohttp.ClientSession() as session:
        titles = await get_all_titles(session)

        if limit:
            titles = titles[:limit]

        tasks = []
        sem = asyncio.Semaphore(CONCURRENCY)

        async def sem_task(t):
            async with sem:
                return await fetch_fish(session, t)

        for t in titles:
            tasks.append(asyncio.create_task(sem_task(t)))

        results_raw = await asyncio.gather(*tasks)

    results = {}
    log_lines = []

    total = len(results_raw)

    for idx, (title, fish, missing) in enumerate(results_raw, start=1):
        key = title.lower().replace(" ", "_").replace("'", "")
        results[key] = fish

        line = f"[{idx}/{total}] {title} — missing: {missing}"
        print(line)
        log_lines.append(line)

    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    print(f"\nSaved {len(results)} → {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(scrape_all(limit=None))  # remove limit later
