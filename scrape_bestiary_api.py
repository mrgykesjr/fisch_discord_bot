#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import json
import os
import time

BASE_URL = "https://fisch.fandom.com"
CATEGORY = "Category:Bestiary"
OUTPUT_FILE = "fisch_bestiary_full.json"
LOG_FILE = "fisch_bestiary_scrape_log.txt"

def get_all_titles():
    session = requests.Session()
    url = BASE_URL + "/api.php"
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": CATEGORY,
        "cmnamespace": "0",
        "cmlimit": "500",
        "format": "json"
    }
    titles = []
    while True:
        resp = session.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        members = data.get("query", {}).get("categorymembers", [])
        for m in members:
            t = m.get("title")
            if t:
                titles.append(t)
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
        params["cmcontinue"] = cont
        time.sleep(0.2)
    return titles

def parse_fish(title: str):
    url = BASE_URL + "/wiki/" + title.replace(" ", "_")
    resp = requests.get(url)
    if resp.status_code != 200:
        return None, ["http_fail"]
    soup = BeautifulSoup(resp.text, "html.parser")

    fish = {"name": title}
    missing = []

    inf = soup.find("aside", class_="portable-infobox")
    if not inf:
        missing.append("infobox_missing")
        return fish, missing

    def get_simple_field(src):
        node = inf.find(attrs={"data-source": src})
        if node:
            val = node.find(class_="pi-data-value")
            if val:
                return val.get_text(strip=True)
            else:
                return node.get_text(strip=True)
        return None

    # Simple fields
    for src, key in [("rarity", "rarity"), ("location", "location"), ("bait", "bait")]:
        v = get_simple_field(src)
        if v:
            fish[key] = v
        else:
            missing.append(src)

    # Time / weather / season
    # The horizontal-group table has table → tr + td with data-source attributes
    for ds in ("time", "weather", "season"):
        td = inf.find("td", attrs={"data-source": ds})
        if td:
            fish[ds] = td.get_text(strip=True)
        else:
            # if no td, maybe default — but we'll log missing
            missing.append(ds)

    # Weights: lowest_kg, average_kg, highest_kg
    for src, key in [("lowest_kg", "min_weight"), ("average_kg", "avg_weight"), ("highest_kg", "max_weight")]:
        td = inf.find("td", attrs={"data-source": src})
        if td:
            fish[key] = td.get_text(strip=True).replace(",", "")
        else:
            missing.append(src)

    # Base value (average C$) and per-kg if present
    td_base = inf.find("td", attrs={"data-source": "average_C"})
    if td_base:
        fish["base_value_c"] = td_base.get_text(strip=True).replace(",", "")
    else:
        missing.append("average_C")

    td_perkg = inf.find("td", attrs={"data-source": "C_kg"})
    if td_perkg:
        fish["value_per_kg_base"] = td_perkg.get_text(strip=True)

    return fish, missing

def scrape_all(limit=None):
    titles = get_all_titles()
    print(f"Found {len(titles)} fish titles.")
    results = {}
    log_lines = []
    for idx, title in enumerate(titles, start=1):
        if limit is not None and idx > limit:
            break
        fish, missing = parse_fish(title)
        key = title.lower().replace(" ", "_").replace("'", "")
        results[key] = fish
        log_lines.append(f"[{idx}/{len(titles)}] {title} — missing: {missing}")
        print(log_lines[-1])
        time.sleep(0.3)

    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    print(f"Saved {len(results)} entries to {OUTPUT_FILE}, log in {LOG_FILE}")

if __name__ == "__main__":
    scrape_all(limit=None)   # change to limit=None to fetch all
