import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

# ─────────────────────────────────────────────
# HEADERS — pretend to be a real browser
# ─────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,ne;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ─────────────────────────────────────────────
# SOURCES TO TRY (in order of preference)
# ─────────────────────────────────────────────
SOURCES = [
    "https://www.onlinekhabar.com/election-result",
    "https://www.setopati.com/election/result",
    "https://kathmandupost.com/election-results",
    "https://election.ekantipur.com",
]

# ─────────────────────────────────────────────
# DEFAULT DATA (last known good results)
# Used as fallback if scraping fails
# ─────────────────────────────────────────────
DEFAULT_DATA = {
    "parties": {
        "rsp":  {"name": "RSP",           "won": 2,  "leading": 69, "total": 71,  "color": "#e74c3c"},
        "nc":   {"name": "Nepali Congress","won": 1,  "leading": 9,  "total": 10,  "color": "#27ae60"},
        "uml":  {"name": "CPN-UML",        "won": 0,  "leading": 5,  "total": 5,   "color": "#e67e22"},
        "ncp":  {"name": "NCP Maoist",     "won": 0,  "leading": 4,  "total": 4,   "color": "#8e44ad"},
    },
    "hotseats": {
        "jhapa5":   {"const": "Jhapa-5",    "c1": "Balen Shah",      "p1": "RSP",      "v1": 17396, "c2": "KP Sharma Oli",   "p2": "UML",     "v2": 6087,  "lead": 11309},
        "chitwan3": {"const": "Chitwan-3",  "c1": "Sobita Gautam",   "p1": "RSP",      "v1": 4941,  "c2": "Renu Dahal",      "p2": "Maoist",  "v2": 2958,  "lead": 1983},
        "sarlahi4": {"const": "Sarlahi-4",  "c1": "Amresh Kr. Singh","p1": "RSP",      "v1": 1908,  "c2": "Gagan Thapa",     "p2": "NC",      "v2": 536,   "lead": 1372},
        "chitwan2": {"const": "Chitwan-2",  "c1": "Rabi Lamichhane", "p1": "RSP",      "v1": 6700,  "c2": "Asmin Ghimire",   "p2": "UML",     "v2": 2329,  "lead": 4371},
        "rukumE":   {"const": "Rukum East", "c1": "Prachanda",       "p1": "Maoist",   "v1": 1415,  "c2": "Lilamani Gautam", "p2": "UML",     "v2": 431,   "lead": 984},
    },
    "summary": "RSP is leading with a historic wave nationally. Balen Shah leads KP Oli by over 11,000 votes in Jhapa-5. Counting is ongoing across all 165 constituencies.",
    "ticker": "RSP leading 69+ seats nationally | Balen leads KP Oli by 11,000+ in Jhapa-5 | Sobita ahead of Renu Dahal in Chitwan-3",
    "source": "Last known data (auto-update pending)",
    "lastUpdated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    "countingComplete": False,
}


def safe_int(text):
    """Extract first integer from a string."""
    if not text:
        return 0
    nums = re.findall(r'\d[\d,]*', str(text).replace(',', ''))
    return int(nums[0]) if nums else 0


def fetch_page(url, timeout=15):
    """Fetch a URL and return BeautifulSoup, or None on failure."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  ✗ Failed to fetch {url}: {e}")
        return None


# ─────────────────────────────────────────────
# PARSER: OnlineKhabar election result page
# ─────────────────────────────────────────────
def parse_onlinekhabar(soup):
    data = DEFAULT_DATA.copy()
    data["parties"] = {k: v.copy() for k, v in DEFAULT_DATA["parties"].items()}

    try:
        # OnlineKhabar typically has a summary table with party totals
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cols = [td.get_text(strip=True) for td in row.find_all(["td","th"])]
                if not cols:
                    continue
                text = " ".join(cols).lower()

                # Match party rows
                if "swatantra" in text or "rsp" in text:
                    nums = [safe_int(c) for c in cols if re.search(r'\d', c)]
                    if len(nums) >= 2:
                        data["parties"]["rsp"]["won"] = nums[0]
                        data["parties"]["rsp"]["leading"] = nums[1] if len(nums) > 1 else 0
                        data["parties"]["rsp"]["total"] = nums[0] + (nums[1] if len(nums) > 1 else 0)

                elif "congress" in text and "nepali" in text:
                    nums = [safe_int(c) for c in cols if re.search(r'\d', c)]
                    if len(nums) >= 2:
                        data["parties"]["nc"]["won"] = nums[0]
                        data["parties"]["nc"]["leading"] = nums[1] if len(nums) > 1 else 0
                        data["parties"]["nc"]["total"] = nums[0] + (nums[1] if len(nums) > 1 else 0)

                elif "uml" in text or ("communist" in text and "maoist" not in text):
                    nums = [safe_int(c) for c in cols if re.search(r'\d', c)]
                    if len(nums) >= 2:
                        data["parties"]["uml"]["won"] = nums[0]
                        data["parties"]["uml"]["leading"] = nums[1] if len(nums) > 1 else 0
                        data["parties"]["uml"]["total"] = nums[0] + (nums[1] if len(nums) > 1 else 0)

                elif "maoist" in text or "prachanda" in text:
                    nums = [safe_int(c) for c in cols if re.search(r'\d', c)]
                    if len(nums) >= 2:
                        data["parties"]["ncp"]["won"] = nums[0]
                        data["parties"]["ncp"]["leading"] = nums[1] if len(nums) > 1 else 0
                        data["parties"]["ncp"]["total"] = nums[0] + (nums[1] if len(nums) > 1 else 0)

        # Try to find hot seat data
        page_text = soup.get_text()
        parse_hotseat_text(page_text, data)

        data["source"] = "onlinekhabar.com"
        data["lastUpdated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        print("  ✓ Parsed OnlineKhabar successfully")
        return data

    except Exception as e:
        print(f"  ✗ Parse error: {e}")
        return None


# ─────────────────────────────────────────────
# PARSER: Generic — looks for numbers near names
# ─────────────────────────────────────────────
def parse_generic(soup, source_name):
    data = DEFAULT_DATA.copy()
    data["parties"] = {k: v.copy() for k, v in DEFAULT_DATA["parties"].items()}
    data["hotseats"] = {k: v.copy() for k, v in DEFAULT_DATA["hotseats"].items()}

    page_text = soup.get_text(separator="\n")
    lines = page_text.split("\n")

    # ── Party totals ──
    for i, line in enumerate(lines):
        ll = line.lower().strip()
        context = " ".join(lines[max(0,i-2):i+3]).lower()

        # Grab all numbers near party mentions
        nums_in_context = [safe_int(x) for x in re.findall(r'\d[\d,]*', context) if safe_int(x) > 0]

        if ("swatantra" in ll or ("rsp" in ll and "result" not in ll)):
            if nums_in_context:
                data["parties"]["rsp"]["total"] = max(nums_in_context)

        if "nepali congress" in ll or ("congress" in ll and "india" not in ll):
            if nums_in_context:
                data["parties"]["nc"]["total"] = max(nums_in_context)

        if "uml" in ll or ("एमाले" in ll):
            if nums_in_context:
                data["parties"]["uml"]["total"] = max(nums_in_context)

        if "maoist" in ll or "माओवादी" in ll:
            if nums_in_context:
                data["parties"]["ncp"]["total"] = max(nums_in_context)

    # ── Hot seats ──
    parse_hotseat_text(page_text, data)

    data["source"] = source_name
    data["lastUpdated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    print(f"  ✓ Parsed {source_name} generically")
    return data


def parse_hotseat_text(text, data):
    """Extract hot seat vote counts from raw page text."""
    lines = text.split("\n")

    for i, line in enumerate(lines):
        ll = line.lower()
        context_block = " ".join(lines[max(0,i-3):i+4])
        nums = [safe_int(x) for x in re.findall(r'\d[\d,]*', context_block) if safe_int(x) > 100]

        if "balen" in ll or "बालेन" in ll:
            if nums:
                data["hotseats"]["jhapa5"]["v1"] = max(nums)

        if ("kp oli" in ll or "केपी ओली" in ll or "sharma oli" in ll):
            if nums:
                data["hotseats"]["jhapa5"]["v2"] = max(nums)

        if "sobita" in ll or "सोबिता" in ll:
            if nums:
                data["hotseats"]["chitwan3"]["v1"] = max(nums)

        if "renu dahal" in ll or "रेनु दाहाल" in ll:
            if nums:
                data["hotseats"]["chitwan3"]["v2"] = max(nums)

        if "amresh" in ll or "अमरेश" in ll:
            if nums:
                data["hotseats"]["sarlahi4"]["v1"] = max(nums)

        if "gagan thapa" in ll or "गगन थापा" in ll:
            if nums:
                data["hotseats"]["sarlahi4"]["v2"] = max(nums)

        if "rabi lamichhane" in ll or "रबि लामिछाने" in ll:
            if nums:
                data["hotseats"]["chitwan2"]["v1"] = max(nums)

        if "prachanda" in ll or "प्रचण्ड" in ll:
            if nums:
                data["hotseats"]["rukumE"]["v1"] = max(nums)

    # Recalculate leads
    for key, hs in data["hotseats"].items():
        hs["lead"] = hs["v1"] - hs["v2"]


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print(f"\n{'='*50}")
    print(f"Nepal Election Fetcher — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}")

    result_data = None

    for url in SOURCES:
        print(f"\n→ Trying: {url}")
        soup = fetch_page(url)
        if not soup:
            continue

        if "onlinekhabar" in url:
            result_data = parse_onlinekhabar(soup)
        else:
            domain = url.split("/")[2].replace("www.", "")
            result_data = parse_generic(soup, domain)

        if result_data:
            break

    if not result_data:
        print("\n⚠ All sources failed — using default fallback data")
        result_data = DEFAULT_DATA.copy()
        result_data["source"] = "fallback (all sources unreachable)"
        result_data["lastUpdated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Build summary line
    p = result_data["parties"]
    result_data["summary"] = (
        f"RSP leading with {p['rsp']['total']} seats (won: {p['rsp']['won']}, leading: {p['rsp']['leading']}). "
        f"Nepali Congress at {p['nc']['total']} seats. "
        f"CPN-UML at {p['uml']['total']} seats. "
        f"NCP Maoist at {p['ncp']['total']} seats. "
        f"Counting ongoing across 165 constituencies. "
        f"Balen Shah leading KP Oli by {result_data['hotseats']['jhapa5']['lead']:,} votes in Jhapa-5."
    )

    result_data["ticker"] = (
        f"RSP total {p['rsp']['total']} seats | "
        f"Balen leads KP Oli by {result_data['hotseats']['jhapa5']['lead']:,} in Jhapa-5 | "
        f"Sobita leads Renu Dahal by {result_data['hotseats']['chitwan3']['lead']:,} in Chitwan-3 | "
        f"Rabi Lamichhane leads by {result_data['hotseats']['chitwan2']['lead']:,} in Chitwan-2"
    )

    # Save
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ data.json saved successfully!")
    print(f"   RSP: {p['rsp']['total']} | NC: {p['nc']['total']} | UML: {p['uml']['total']} | NCP: {p['ncp']['total']}")
    print(f"   Source: {result_data['source']}")
    print(f"   Updated: {result_data['lastUpdated']}\n")


if __name__ == "__main__":
    main()
