import requests
import csv
import time
import os
import re
import argparse
import random
from datetime import datetime

BASE_URL = "https://www.sreality.cz/api/cs/v2/estates"

PARAMS = {
    "category_main_cb": 1,
    "category_type_cb": 2,
    "locality_region_id": 10,
    "per_page": 20,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8",
    "Referer": "https://www.sreality.cz/",
}

OUTPUT_DIR = "data"

ATTRIBUTE_MAP = {
    "size_m2": ["Užitná ploch", "Užitná plocha", "Celková plocha", "Plocha", "Obytná plocha"],
    "floor": ["Podlaží"],
    "building_type": ["Stavba", "Typ budovy"],
    "condition": ["Stav objektu", "Stav"],
    "furnished": ["Vybavení", "Vybaveno"],
    "elevator": ["Výtah"],
    "balcony": ["Balkón", "Balkon"],
    "terrace": ["Terasa"],
    "energy_rating": ["Energetická náročnost budovy", "PENB"],
    "ownership": ["Vlastnictví"],
    "parking": ["Parkování"],
    "cellar": ["Sklep"],
    "loggia": ["Lodžie", "Lodžia"],
    "heating": ["Topení"],
    "apartment_type": ["Typ bytu"],
    "note_about_price": ["Poznámka k ceně"],
}

CSV_COLUMNS = [
    "scrape_date", "hash_id", "name", "locality", "district", "neighborhood",
    "price_czk", "size_m2", "rooms", "floor", "building_type", "condition",
    "furnished", "elevator", "balcony", "terrace", "energy_rating",
    "ownership", "parking", "cellar", "loggia", "heating", "apartment_type",
    "note_about_price",
]

def load_existing_ids():
    existing_ids = set()
    if not os.path.exists(OUTPUT_DIR):
        return existing_ids

    for filename in os.listdir(OUTPUT_DIR):
        if filename.startswith("sreality_") and filename.endswith(".csv"):
            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    hash_id = row.get("hash_id", "")
                    if hash_id:
                        existing_ids.add(str(hash_id))

    return existing_ids

def get_listing_ids(page):
    params = {**PARAMS, "page": page}

    try:
        response = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()

        listings = []
        for estate in data.get("_embedded", {}).get("estates", []):
            hash_id = estate.get("hash_id")
            if hash_id:
                basic_info = {
                    "name": estate.get("name", ""),
                    "locality": estate.get("locality", ""),
                    "price": estate.get("price", None),
                    "price_czk": estate.get("price_czk", {}).get("value_raw", None),
                }
                listings.append((hash_id, basic_info))

        return listings

    except requests.exceptions.RequestException as e:
        print(f"  Warning: Error fetching page {page}: {e}")
        return []


def extract_attribute(items, possible_names):
    for name in possible_names:
        for item in items:
            if item.get("name") == name:
                value = item.get("value")
                if isinstance(value, list):
                    return ", ".join(
                        str(v.get("value", v) if isinstance(v, dict) else v) for v in value
                    )
                return str(value) if value is not None else ""
    return ""


def extract_rooms_from_name(name):
    match = re.search(r'(\d\+(?:kk|1|2|3))', str(name), re.IGNORECASE)
    if match:
        return match.group(1)

    if "atypick" in str(name).lower():
        return "atypicky"

    return ""


def extract_size_from_name(name):
    match = re.search(r'(\d+)\s*m[²2]', str(name))
    if match:
        return match.group(1)
    return ""


def parse_district(locality_text):
    match = re.search(r'Praha\s+(\d+)', str(locality_text))
    if match:
        return f"Praha {match.group(1)}"
    return ""


def parse_neighborhood(locality_text):
    match = re.search(r'Praha\s+\d+\s*-\s*(.+)', str(locality_text))
    if match:
        return match.group(1).strip()
    return ""


def get_listing_detail(hash_id):
    url = f"{BASE_URL}/{hash_id}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])

        detail = {}

        for csv_col, possible_names in ATTRIBUTE_MAP.items():
            detail[csv_col] = extract_attribute(items, possible_names)

        return detail

    except requests.exceptions.RequestException as e:
        print(f"  Warning: Error fetching detail {hash_id}: {e}")
        return {}


def save_to_csv(listings, filepath, append=False):
    mode = "a" if append else "w"
    write_header = not append or not os.path.exists(filepath)

    with open(filepath, mode, newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        for listing in listings:
            writer.writerow(listing)


def print_progress(current, total, prefix=""):
    bar_length = 30
    filled = int(bar_length * current / total) if total > 0 else 0
    bar = "#" * filled + "-" * (bar_length - filled)
    percent = (current / total * 100) if total > 0 else 0
    print(f"\r   {prefix} [{bar}] {current}/{total} ({percent:.0f}%)", end="", flush=True)

def scrape_sreality(max_pages, output_file):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if output_file is None:
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(OUTPUT_DIR, f"sreality_prague_rent_{date_str}.csv")
    else:
        output_file = os.path.join(OUTPUT_DIR, output_file)

    all_ids = []

    for page in range(1, max_pages + 1):
        listings = get_listing_ids(page)
        if not listings:
            print(f"\nNo more listings found at page {page}. Stopping.")
            break
        all_ids.extend(listings)
        print_progress(page, max_pages, "Pages")
        time.sleep(random.uniform(0.5, 1.5))

    print(f"\nFound {len(all_ids)} listings\n")

    if not all_ids:
        print("No listings found. Check your internet connection.")
        return

    existing_ids = load_existing_ids()
    if existing_ids:
        before = len(all_ids)
        all_ids = [(h, b) for h, b in all_ids if str(h) not in existing_ids]
        skipped = before - len(all_ids)
        print(f"Found {len(existing_ids)} previously scraped listings.")
        print(f"Skipping {skipped} duplicates, {len(all_ids)} new listings to fetch.\n")

    if not all_ids:
        print("No new listings to scrape.")
        return

    all_listings = []
    total = len(all_ids)

    for i, (hash_id, basic_info) in enumerate(all_ids, 1):
        detail = get_listing_detail(hash_id)

        if not detail:
            print_progress(i, total, "Listings")
            continue

        name = basic_info.get("name", "")
        locality = basic_info.get("locality", "")

        listing = {
            "scrape_date": datetime.now().strftime("%Y-%m-%d"),
            "hash_id": hash_id,
            "name": name,
            "locality": locality,
            "district": parse_district(locality),
            "neighborhood": parse_neighborhood(locality),
            "price_czk": basic_info.get("price", None) or basic_info.get("price_czk", None),
            "rooms": extract_rooms_from_name(name),
        }

        api_size = detail.get("size_m2", "")
        if api_size:
            listing["size_m2"] = api_size
        else:
            listing["size_m2"] = extract_size_from_name(name)

        for csv_col in ATTRIBUTE_MAP:
            if csv_col not in listing:
                listing[csv_col] = detail.get(csv_col, "")

        all_listings.append(listing)
        print_progress(i, total, "Listings")
        time.sleep(random.uniform(0.3, 1.0))

    save_to_csv(all_listings, output_file)


def merge_data_files():
    csv_files = [os.path.join(OUTPUT_DIR, f)for f in os.listdir(OUTPUT_DIR)if f.startswith("sreality_") and f.endswith(".csv") and f != "sreality_combined.csv"]

    if not csv_files:
        print("  No data files found in data/ directory.")
        return

    all_rows = []
    seen_ids = set()

    for filepath in csv_files:
        count = 0
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                hash_id = row.get("hash_id", "")
                if hash_id not in seen_ids:
                    seen_ids.add(hash_id)
                    all_rows.append(row)
                count += 1
        print(f"   {os.path.basename(filepath)}: {count} records")

    output = os.path.join(OUTPUT_DIR, "sreality_combined.csv")
    save_to_csv(all_rows, output)

    print(f"\nMerged: {len(all_rows)} unique listings")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Prague apartment rentals from Sreality.cz")
    parser.add_argument("--pages", type=int, default=30,help="Number of pages to scrape (20 listings per page). Default: 30")
    parser.add_argument("--output", type=str, default=None,help="Output CSV filename. Default: auto-generated with date")
    parser.add_argument("--merge", action="store_true",help="Merge all existing data files into one combined CSV")
    parser.add_argument("--debug", action="store_true",help="Debug mode: fetch listings and show all available attributes")
    parser.add_argument("--count", type=int, default=3,help="Number of listings to check in debug mode. Default: 3")

    args = parser.parse_args()

    if args.merge:
        merge_data_files()
    else:
        scrape_sreality(max_pages=args.pages, output_file=args.output)