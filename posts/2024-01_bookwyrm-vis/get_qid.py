import requests
import time
import pandas as pd
from typing import Iterable, List, Optional, Dict, Set

WIKIDATA_SEARCH_URL = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "dslabs-wikidata-query/1.0 (contact: youremail@example.com)"}

PREF_OCC_WRITER = "Q36180"     # writer
PREF_OCC_NOVELIST = "Q6625963" # novelist
HUMAN_Q = "Q5"

def wbsearch_candidates(name: str, language: str = "en", limit: int = 5, timeout: int = 30) -> List[str]:
    """
    Given a name string, return a list of candidate QIDs from Wikidata search.
    """
    if name is None or (isinstance(name, float) and pd.isna(name)) or str(name).strip() == "":
        return []
    params = {
        "action": "wbsearchentities",
        "format": "json",
        "language": language,
        "search": name,
        "type": "item",
        "limit": limit
    }
    resp = requests.get(WIKIDATA_SEARCH_URL, params=params, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return [item["id"] for item in data.get("search", []) if "id" in item]

def query_human_occupations_for_qids(qids: Iterable[str], timeout: int = 60) -> Dict[str, Set[str]]:
    """
    Given an iterable of QIDs (e.g. ['Q123','Q456']), return a mapping
    qid -> set of occupation QIDs for items that are humans (P31 = Q5).

    Items that are not humans will NOT appear in the mapping.
    """
    qid_list = [q for q in qids]
    if not qid_list:
        return {}
    values = " ".join(f"wd:{q}" for q in qid_list)
    sparql = f"""
    SELECT ?item ?occ WHERE {{
      VALUES ?item {{ {values} }}
      ?item wdt:P31 wd:{HUMAN_Q}.
      OPTIONAL {{ ?item wdt:P106 ?occ. }}
    }}
    """
    resp = requests.get(WIKIDATA_SPARQL_URL, params={"query": sparql, "format": "json"}, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    results = resp.json().get("results", {}).get("bindings", [])
    mapping: Dict[str, Set[str]] = {}
    for row in results:
        item_url = row["item"]["value"]
        qid = item_url.rsplit("/", 1)[-1]
        occ_val = row.get("occ")
        occ_qid = None
        if occ_val:
            occ_qid = occ_val["value"].rsplit("/", 1)[-1]
        mapping.setdefault(qid, set())
        if occ_qid:
            mapping[qid].add(occ_qid)
    return mapping

def choose_preferred_qid(candidates: List[str], human_occ_map: Dict[str, Set[str]]) -> Optional[str]:
    """
    Given candidate IDs (in search order) and a mapping of human QIDs to their occupation sets,
    return a single preferred qid or None.
    Preference order:
      1) first candidate that is human and has occupation writer (Q36180)
      2) first candidate that is human and has occupation novelist (Q6625963)
      3) first candidate that is human (any occupation)
      4) else None
    """
    # 1) writer
    for q in candidates:
        occs = human_occ_map.get(q)
        if occs and PREF_OCC_WRITER in occs:
            return q
    # 2) novelist
    for q in candidates:
        occs = human_occ_map.get(q)
        if occs and PREF_OCC_NOVELIST in occs:
            return q
    # 3) any human
    for q in candidates:
        if q in human_occ_map:
            return q
    return None

def resolve_name_to_qid(name: str, pause_seconds: float = 0.5) -> Optional[str]:
    """
    Resolve a single name to a preferred QID following the rules described.
    """
    candidates = wbsearch_candidates(name)
    if not candidates:
        return None
    # Query occupations for all candidates at once and restrict to humans
    human_occ_map = query_human_occupations_for_qids(candidates)
    chosen = choose_preferred_qid(candidates, human_occ_map)
    time.sleep(pause_seconds)
    return chosen

def resolve_names_to_qids(names: Iterable[str], pause_seconds: float = 0.5) -> pd.DataFrame:
    """
    Resolve an iterable of names to QIDs. Returns DataFrame with columns:
      - author_text: the original name
      - qid: chosen QID or None
    Maintains the order of first appearance of unique names in `names`.
    """
    seen = {}
    records = []
    for name in pd.Index(list(names)):
        if pd.isna(name) or str(name).strip() == "":
            records.append({"author_text": name, "qid": None})
            continue
        if name in seen:
            records.append({"author_text": name, "qid": seen[name]})
            continue
        qid = resolve_name_to_qid(name, pause_seconds=pause_seconds)
        seen[name] = qid
        records.append({"author_text": name, "qid": qid})
    return pd.DataFrame.from_records(records)

# Example usage:
names_series = ['Mike Parker', 'J.K. Rowling', 'Mark Fisher', 'Mark Graham', 'Unknown Author', None, '']
qid_df = resolve_names_to_qids(names_series, pause_seconds=0.5)
qid_df