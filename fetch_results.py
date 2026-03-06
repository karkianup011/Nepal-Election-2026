import requests
import json
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, */*",
    "Referer": "https://nepalvotes.live/",
    "Origin": "https://nepalvotes.live",
}

CONSTITUENCIES_URL = "https://nepalvotes.live/constituencies.json"
PARTIES_URL        = "https://nepalvotes.live/pr_parties.json"

def normalize_party(name):
    if not name: return "Others"
    n = name.lower()
    if "swatantra" in n or "rsp" in n:                          return "RSP"
    if "nepali congress" in n or n == "nc":                     return "NC"
    if "uml" in n or "एमाले" in n or ("communist" in n and "maoist" not in n): return "UML"
    if "maoist" in n or "माओवादी" in n:                        return "Maoist"
    if "rpm" in n or "rpp" in n or "rastriya prajatantra" in n: return "RPM"
    return "Others"

def party_color(key):
    return {"RSP":"#e74c3c","NC":"#27ae60","UML":"#e67e22",
            "Maoist":"#8e44ad","RPM":"#2980b9"}.get(key, "#6a8fad")

def fetch_json(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  Failed {url}: {e}")
        return None

def main():
    print(f"\n{'='*55}")
    print(f"Nepal Election Fetcher — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Source: nepalvotes.live (ECN official data)")
    print(f"{'='*55}")

    print("\n-> Fetching constituencies.json ...")
    raw_const = fetch_json(CONSTITUENCIES_URL)
    print("-> Fetching pr_parties.json ...")
    raw_parties = fetch_json(PARTIES_URL)

    if not raw_const:
        print("Could not fetch constituencies — aborting")
        return

    constituencies = []
    party_counts = {k:{"won":0,"leading":0} for k in ["RSP","NC","UML","Maoist","RPM","Others"]}

    items = raw_const if isinstance(raw_const, list) else raw_const.get("constituencies", raw_const.get("data", []))

    for item in items:
        try:
            cands = item.get("candidates", item.get("results", item.get("votes", [])))
            cands_sorted = sorted(cands, key=lambda x: int(x.get("votes", x.get("vote_count", 0))), reverse=True)

            c1 = cands_sorted[0] if len(cands_sorted) > 0 else {}
            c2 = cands_sorted[1] if len(cands_sorted) > 1 else {}

            name1  = c1.get("name", c1.get("candidate_name", ""))
            party1 = c1.get("party", c1.get("party_name", c1.get("party_short", "")))
            votes1 = int(c1.get("votes", c1.get("vote_count", 0)))
            name2  = c2.get("name", c2.get("candidate_name", ""))
            party2 = c2.get("party", c2.get("party_name", c2.get("party_short", "")))
            votes2 = int(c2.get("votes", c2.get("vote_count", 0)))

            pkey1 = normalize_party(party1)
            won   = item.get("status","").lower() in ("won","declared","result declared")
            prov  = item.get("province", item.get("province_name", ""))
            dist  = item.get("district", item.get("district_name", ""))
            cname = item.get("name", item.get("constituency_name", ""))
            cid   = item.get("id", item.get("constituency_id", 0))

            constituencies.append({"id":cid,"prov":prov,"dist":dist,"name":cname,
                                    "c1":name1,"p1":party1,"v1":votes1,
                                    "c2":name2,"p2":party2,"v2":votes2,"won":won})

            if pkey1 in party_counts:
                if won: party_counts[pkey1]["won"] += 1
                else:   party_counts[pkey1]["leading"] += 1
        except Exception as e:
            print(f"  Parse error: {e}")
            continue

    print(f"\nParsed {len(constituencies)} constituencies")

    parties = {}
    for k, v in party_counts.items():
        parties[k.lower()] = {"name":k,"won":v["won"],"leading":v["leading"],
                               "total":v["won"]+v["leading"],"color":party_color(k)}

    if raw_parties:
        plist = raw_parties if isinstance(raw_parties, list) else raw_parties.get("parties", [])
        for p in plist:
            pname = p.get("name", p.get("party_name",""))
            key   = normalize_party(pname).lower()
            if key in parties:
                parties[key]["won"]     = int(p.get("won", p.get("seats_won", parties[key]["won"])))
                parties[key]["leading"] = int(p.get("leading", p.get("seats_leading", parties[key]["leading"])))
                parties[key]["total"]   = parties[key]["won"] + parties[key]["leading"]

    rsp = parties.get("rsp",{}); nc = parties.get("nc",{})
    uml = parties.get("uml",{}); mao = parties.get("maoist",{})

    summary = (f"RSP leading with {rsp.get('total',0)} seats (won: {rsp.get('won',0)}, leading: {rsp.get('leading',0)}). "
               f"Nepali Congress at {nc.get('total',0)} seats. CPN-UML at {uml.get('total',0)} seats. "
               f"NCP Maoist at {mao.get('total',0)} seats. Data from ECN via nepalvotes.live.")

    ticker = (f"RSP {rsp.get('total',0)} seats | NC {nc.get('total',0)} | "
              f"UML {uml.get('total',0)} | Maoist {mao.get('total',0)} | Live ECN data")

    output = {"lastUpdated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
              "source": "nepalvotes.live (ECN official data)",
              "countingComplete": False,
              "summary": summary, "ticker": ticker,
              "parties": parties, "constituencies": constituencies}

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"data.json saved with {len(constituencies)} constituencies!")
    print(f"RSP:{rsp.get('total',0)} | NC:{nc.get('total',0)} | UML:{uml.get('total',0)} | Maoist:{mao.get('total',0)}")

if __name__ == "__main__":
    main()
