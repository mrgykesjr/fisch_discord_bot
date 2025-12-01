import requests
from bs4 import BeautifulSoup
import json
import re
import os

WIKI_URL = "https://fisch.fandom.com/wiki/Enchantments"
TARGET_PATH = os.path.join("data", "enchants.json")

CATEGORIES = {
    "Regular Enchantments": "regular",
    "Exalted Enchantments": "exalted",
    "Cosmic Enchantments": "cosmic",
    "Twisted Enchantments": "twisted",
    "Song of the Deep Enchantments": "song_of_the_deep"
}

_SPLIT_REGEX = re.compile(r'\s*(?<!\d)([.,])\s+')

def clean(s: str) -> str:
    return " ".join(s.strip().split())

def split_effects(text: str):
    parts = []
    last = 0
    for m in _SPLIT_REGEX.finditer(text):
        idx = m.start(1)
        part = text[last:idx]
        part = clean(part)
        if part:
            parts.append(part)
        last = m.end()
    tail = clean(text[last:])
    if tail:
        parts.append(tail)
    return parts

def parse_table(table, category_key):
    result = {}
    rows = table.find_all("tr")[1:]
    for row in rows:
        cols = row.find_all(["td","th"])
        if len(cols) < 2:
            continue

        name = clean(cols[0].get_text(separator=" ").strip())
        key = name.lower().replace(" ", "_")

        effect_td = cols[1]
        lis = effect_td.find_all("li")
        if lis:
            effects = [clean(li.get_text()) for li in lis]
        else:
            raw = clean(effect_td.get_text(separator="\n").strip())
            effects = split_effects(raw) if raw else []

        tips = []
        if len(cols) >= 3:
            tips_td = cols[2]
            ul = tips_td.find("ul")
            if ul:
                tips = [clean(li.get_text()) for li in ul.find_all("li")]
            else:
                raw_tips = tips_td.get_text(separator="\n").strip()
                tips = [clean(line) for line in raw_tips.split("\n") if clean(line)]

        result[key] = {
            "name": name,
            "category": category_key,
            "effect": effects,
            "tips": tips
        }
    return result

def scrape_all_enchants():
    resp = requests.get(WIKI_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    all_enchants = {}
    for header_text, cat_key in CATEGORIES.items():
        header = soup.find(lambda tag: tag.name in ["h2","h3","h4"] and header_text in tag.get_text())
        if not header:
            continue
        table = header.find_next("table")
        if table:
            parsed = parse_table(table, cat_key)
            all_enchants.update(parsed)
    return all_enchants

def load_existing(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    print("Scraping wiki for enchants…")
    scraped = scrape_all_enchants()
    print(f"Scraped {len(scraped)} enchant entries.")

    existing = load_existing(TARGET_PATH)
    print(f"Loaded {len(existing)} existing enchant entries.")

    # Merge: scraped overwrites existing for same key
    merged = {**existing, **scraped}

    save_json(merged, TARGET_PATH)
    print("enchants.json updated — total entries:", len(merged))
