#!/usr/bin/env python3
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime

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
CONCURRENCY = 50
# ---------------------------------------------


def now_str():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def clean_paren_spaces(s: str) -> str:
    # remove any spaces immediately after "(" or before ")"
    return s.replace("( ", "(").replace(" )", ")")


def parse_infobox(html, title, url):
    soup = BeautifulSoup(html, "html.parser")
    fish = {"name": title, "url": url}
    missing = []

    inf = soup.find("div", class_="infobox")
    if not inf:
        return fish, ["infobox_missing"]

    # basic rows
    datarows = inf.find_all("div", class_="infobox-datarow")

    for row in datarows:
        heading = row.find("p", class_="data-heading")
        content = row.find("p", class_="data-content") or row.find("ul", class_="data-content")
        if not heading or not content:
            continue
        key = heading.get_text(strip=True).lower()
        val = content.get_text(" ", strip=True)
        val = clean_paren_spaces(val)
        fish[key] = val

    # C$/kg
    ckg = inf.find("p", class_="data-heading", string=lambda s: s and "C$/kg" in s)
    if ckg:
        node = ckg.find_next("p", class_="data-content")
        if node:
            fish["value_per_kg_base"] = clean_paren_spaces(node.get_text(strip=True))

    # tabber weights & values
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
                v = content.get_text(strip=True)
                v = clean_paren_spaces(v).replace("kg", "").replace("C$", "").strip()
                fish[h] = v

    return fish, missing


async def fetch_fish(session, title):
    url_title = title.replace(" ", "_")
    url = f"{BASE_URL}/wiki/{url_title}"

    try:
        async with session.get(url, headers=HEADERS, timeout=20) as resp:
            html = await resp.text()
    except Exception:
        return title, {"name": title, "url": url}, ["http_error"]

    if resp.status != 200:
        return title, {"name": title, "url": url}, [f"http_{resp.status}"]

    fish, missing = parse_infobox(html, title, url)
    return title, fish, missing


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


async def scrape_all(limit=None):
    async with aiohttp.ClientSession() as session:
        titles = await get_all_titles(session)
        if limit:
            titles = titles[:limit]
        total = len(titles)
        results = {}
        log_lines = []
        sem = asyncio.Semaphore(CONCURRENCY)
        start = time.time()

        async def sem_task(idx, t):
            async with sem:
                title, fish, missing = await fetch_fish(session, t)
                elapsed = time.time() - start
                done = idx
                remain = total - done
                rate = done / elapsed if elapsed > 0 else 0
                eta = remain / rate if rate > 0 else float('inf')
                print(f"[{now_str()}] [{done}/{total}] {title} — missing: {missing} | {rate:.1f} items/s | ETA: {eta/60:.1f} min")
                key = title.lower().replace(" ", "_").replace("'", "")
                results[key] = fish
                log_lines.append(f"[{done}/{total}] {title} — missing: {missing}")

        tasks = [asyncio.create_task(sem_task(i+1, t)) for i, t in enumerate(titles)]
        await asyncio.gather(*tasks)

    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    print(f"\n[{now_str()}] Saved {len(results)} → {OUTPUT_FILE}")


if __name__ == "__main__":
    import aiohttp
    asyncio.run(scrape_all(limit=None))  
