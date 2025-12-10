import requests
import time
import pandas as pd
from typing import Optional, Dict

WIKIDATA_SEARCH_URL = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "dslabs-wikidata-query/1.0 (contact: youremail@example.com)"}

def get_wikidata_qid(name: str, language: str = "en", max_retries: int = 2) -> Optional[str]:
    params = {
        "action": "wbsearchentities",
        "format": "json",
        "language": language,
        "search": name,
        "type": "item",
        "limit": 1
    }
    for attempt in range(max_retries + 1):
        resp = requests.get(WIKIDATA_SEARCH_URL, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("search"):
                return data["search"][0].get("id")
            return None
        else:
            time.sleep(1 + attempt)
    return None

def get_wikidata_props(qid: str) -> Dict[str, Optional[str]]:
    # SPARQL: optional gender (P21), ethnicity (P172), sexual orientation (P91),
    # place of birth (P19) -> place wdt:P17 country.
    q = f"""
    SELECT ?genderLabel ?countryLabel ?ethnicityLabel ?sexOrientLabel WHERE {{
      OPTIONAL {{ wd:{qid} wdt:P21 ?gender. }}
      OPTIONAL {{ wd:{qid} wdt:P19 ?place. ?place wdt:P17 ?country. }}
      OPTIONAL {{ wd:{qid} wdt:P172 ?ethnicity. }}
      OPTIONAL {{ wd:{qid} wdt:P91 ?sexOrient. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 1
    """
    resp = requests.get(WIKIDATA_SPARQL_URL, params={"query": q, "format": "json"}, headers=HEADERS, timeout=60)
    if resp.status_code != 200:
        return {"gender": None, "country_of_birth": None, "ethnicity": None, "sexual_orientation": None}
    results = resp.json().get("results", {}).get("bindings", [])
    if not results:
        return {"gender": None, "country_of_birth": None, "ethnicity": None, "sexual_orientation": None}
    row = results[0]
    def get_label(key):
        v = row.get(key)
        return v.get("value") if v else None
    return {
        "gender": get_label("genderLabel"),
        "country_of_birth": get_label("countryLabel"),
        "ethnicity": get_label("ethnicityLabel"),
        "sexual_orientation": get_label("sexOrientLabel")
    }

def get_author_wikidata_info(names, pause_seconds: float = 0.5):
    """Query Wikidata for a list/iterable of author names. Returns DataFrame with columns:
       author_name, qid, gender, country_of_birth, ethnicity, sexual_orientation
    """
    records = []
    seen = {}
    for name in pd.Index(names).unique():
        if pd.isna(name) or str(name).strip() == "":
            records.append({
                "author_name": name,
                "qid": None,
                "gender": None,
                "country_of_birth": None,
                "ethnicity": None,
                "sexual_orientation": None
            })
            continue
        if name in seen:
            records.append({"author_name": name, **seen[name]})
            continue
        # 1) search for qid
        qid = get_wikidata_qid(name)
        if qid is None:
            rec = {"qid": None, "gender": None, "country_of_birth": None, "ethnicity": None, "sexual_orientation": None}
            seen[name] = rec
            records.append({"author_name": name, **rec})
            time.sleep(pause_seconds)
            continue
        # 2) fetch properties
        props = get_wikidata_props(qid)
        rec = {"qid": qid, **props}
        seen[name] = rec
        records.append({"author_name": name, **rec})
        time.sleep(pause_seconds)
    return pd.DataFrame.from_records(records)

# Example usage:
# assumes `df` already exists and has a column `author_name`
mapping_df = get_author_wikidata_info(df['author_text'])
# Merge mapping back into original df (left join)
df_augmented = df.merge(mapping_df, on="author_text", how="left")

# Keep only requested new columns (if you prefer)
# df_augmented = df_augmented.assign(
#     gender = df_augmented['gender'],
#     country_of_birth = df_augmented['country_of_birth'],
#     ethnicity = df_augmented['ethnicity'],
#     sexual_orientation = df_augmented['sexual_orientation']
# )

df_augmented