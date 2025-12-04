#!/usr/bin/env python3
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import os
import re

BASE_URL = "https://fischipedia.org"
ROD_LIST_URL = BASE_URL + "/wiki/Fishing_Rods"
OUTPUT_FILE = "data/rods.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())

async def fetch_html(session, url):
    async with session.get(url, headers=HEADERS, timeout=20) as resp:
        return await resp.text()

async def get_rod_names(session):
    html = await fetch_html(session, ROD_LIST_URL)
    soup = BeautifulSoup(html, "html.parser")
    rods = []
    for table in soup.find_all("table"):
        ths = table.find_all("th")
        headers = [clean(th.get_text()) for th in ths]
        low = [h.lower() for h in headers]
        if not ("name" in low and ("cost" in low or "price" in low or "obtained from" in low)):
            continue
        for tr in table.find_all("tr")[1:]:
            a = tr.find("a", href=True)
            if not a:
                continue
            href = a["href"]
            if not href.startswith("/wiki/"):
                continue
            raw = href.replace("/wiki/", "")
            if ":" in raw:
                continue
            name = raw.replace("_", " ")
            rods.append(name)
    return sorted(set(rods))

def extract_enchants(soup):
    enchants = []
    # find the div that signals the “Enchanting” section
    # from your HTML snippet: class includes "enchanting" or style has "--enchanting-highlight-color"
    enchanting_div = soup.find("div", class_=lambda c: c and ("enchanting" in c.lower() or "enchanting-themed" in c.lower()))
    if not enchanting_div:
        return enchants

    # within that div, look for all <li> under <ul>
    for ul in enchanting_div.find_all("ul"):
        for li in ul.find_all("li"):
            text = clean(li.get_text(" ", strip=True))
            if text:
                enchants.append(text)
    return enchants

def parse_rod_page(soup, name):
    rod = {"name": name, "url": f"{BASE_URL}/wiki/{name.replace(' ','_')}"}

    inf = soup.find("div", class_="infobox")
    if inf:
        for row in inf.find_all("div", class_="infobox-datarow"):
            heading = row.find("p", class_="data-heading")
            content = row.find("p", class_="data-content")
            if not heading or not content:
                continue
            key = clean(heading.get_text(" ", strip=True)).lower()
            val = clean(content.get_text(" ", strip=True))
            rod[key] = val

    ench = extract_enchants(soup)
    if ench:
        rod["recommended_enchants"] = ench

    return rod

async def fetch_rod(session, name):
    url = f"{BASE_URL}/wiki/{name.replace(' ', '_')}"
    try:
        html = await fetch_html(session, url)
    except Exception as e:
        print(f"[ERROR] fetch {name}: {e}")
        return None
    soup = BeautifulSoup(html, "html.parser")
    return parse_rod_page(soup, name)

async def scrape_all():
    async with aiohttp.ClientSession() as session:
        rod_names = await get_rod_names(session)
        print("Found rod names:", rod_names[:10], "... total:", len(rod_names))
        tasks = [fetch_rod(session, n) for n in rod_names]
        results = await asyncio.gather(*tasks)

    rods = {r["name"]: r for r in results if r}
    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(rods, f, indent=2, ensure_ascii=False)
    print("Saved", len(rods), "rods →", OUTPUT_FILE)

if __name__ == "__main__":
    asyncio.run(scrape_all())
