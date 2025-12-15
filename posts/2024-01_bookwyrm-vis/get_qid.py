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


#%% Get properties ----
import requests
import time
import pandas as pd
from typing import Dict, Optional

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "dslabs-wikidata-query/1.0 (contact: youremail@example.com)"}

def get_props_for_qid(qid: str, retries: int = 2, timeout: int = 60) -> Dict[str, Optional[str]]:
    if qid is None or (isinstance(qid, float) and pd.isna(qid)) or str(qid).strip() == "":
        return {
            "country_of_birth": None,
            "gender": None,
            "country_of_citizenship": None,
            "ethnicity": None,
            "sexual_orientation": None,
            "date_of_birth": None,
            "date_of_death": None
        }

    q = f"""
    SELECT ?genderLabel ?countryLabel ?countryCitizenshipLabel ?ethnicityLabel ?sexOrientLabel ?dob ?dod WHERE {{
      OPTIONAL {{ wd:{qid} wdt:P21 ?gender. }}
      OPTIONAL {{ wd:{qid} wdt:P19 ?place. ?place wdt:P17 ?country. }}
      OPTIONAL {{ wd:{qid} wdt:P27 ?countryCitizenship. }}
      OPTIONAL {{ wd:{qid} wdt:P172 ?ethnicity. }}
      OPTIONAL {{ wd:{qid} wdt:P91 ?sexOrient. }}
      OPTIONAL {{ wd:{qid} wdt:P569 ?dob. }}
      OPTIONAL {{ wd:{qid} wdt:P570 ?dod. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 1
    """

    attempt = 0
    while True:
        try:
            resp = requests.get(WIKIDATA_SPARQL_URL, params={"query": q, "format": "json"}, headers=HEADERS, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                bindings = data.get("results", {}).get("bindings", [])
                if not bindings:
                    return {
                        "country_of_birth": None,
                        "gender": None,
                        "country_of_citizenship": None,
                        "ethnicity": None,
                        "sexual_orientation": None,
                        "date_of_birth": None,
                        "date_of_death": None
                    }
                row = bindings[0]
                def _get(key):
                    v = row.get(key)
                    return v.get("value") if v else None
                return {
                    "country_of_birth": _get("countryLabel"),
                    "gender": _get("genderLabel"),
                    "country_of_citizenship": _get("countryCitizenshipLabel"),
                    "ethnicity": _get("ethnicityLabel"),
                    "sexual_orientation": _get("sexOrientLabel"),
                    "date_of_birth": _get("dob"),
                    "date_of_death": _get("dod")
                }
            elif resp.status_code in (429, 503):
                # rate limited or service unavailable: back off and retry
                attempt += 1
                if attempt > retries:
                    return {k: None for k in ["country_of_birth","gender","country_of_citizenship","ethnicity","sexual_orientation","date_of_birth","date_of_death"]}
                time.sleep(2 ** attempt)
                continue
            else:
                resp.raise_for_status()
        except (requests.RequestException, ValueError):
            attempt += 1
            if attempt > retries:
                return {k: None for k in ["country_of_birth","gender","country_of_citizenship","ethnicity","sexual_orientation","date_of_birth","date_of_death"]}
            time.sleep(1 + attempt)

def crate_wikidata_properties_df(qid_df: pd.DataFrame, qid_col: str = "qid", author_col: str = "author_text", pause_seconds: float = 0.5) -> pd.DataFrame:
    """
    Given a dataframe with columns `author_text` and `qid`, query Wikidata for each qid
    and return a new dataframe with the following columns:
      - author_text
      - qid
      - country_of_birth
      - gender
      - country_of_citizenship
      - ethnicity
      - sexual_orientation
      - date_of_birth
      - date_of_death

    The function preserves the order of rows in `qid_df`. If `qid` is missing or invalid,
    property values will be None.
    """
    required_cols = [author_col, qid_col]
    for c in required_cols:
        if c not in qid_df.columns:
            raise KeyError(f"Column {c!r} not found in qid_df")

    records = []
    for _, row in qid_df.iterrows():
        author = row[author_col]
        qid = row[qid_col]
        props = get_props_for_qid(qid)
        # be polite to the wikidata servers
        time.sleep(pause_seconds)
        record = {"author_text": author, "qid": qid}
        record.update(props)
        records.append(record)

    return pd.DataFrame.from_records(records)

# Example usage:
result_df = crate_wikidata_properties_df(qid_df.head(), qid_col='qid', author_col='author_text', pause_seconds=0.6)
# result_df  # DataFrame with requested properties

#%% Get properties, option 2 ---

import requests
import time
import pandas as pd
from typing import Dict, Iterable, List, Optional

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "dslabs-wikidata-query/1.0 (contact: youremail@example.com)"}

def _query_props_for_qids_batch(qids: List[str], retries: int = 2, timeout: int = 60) -> Dict[str, Dict[str, Optional[str]]]:
    """
    Query Wikidata for a batch of QIDs and return mapping qid -> property dict.
    Uses GROUP_CONCAT to aggregate multi-valued properties with '|' separator.
    Returns keys: country_of_birth, gender, country_of_citizenship, ethnicity,
    sexual_orientation, date_of_birth, date_of_death (dates as ISO strings).
    """
    if not qids:
        return {}

    # prepare VALUES list
    values = " ".join(f"wd:{q}" for q in qids)
    sparql = f"""
    SELECT ?item
           (GROUP_CONCAT(DISTINCT ?genderLabel; separator="|") AS ?gender)
           (GROUP_CONCAT(DISTINCT ?countryLabel; separator="|") AS ?country_of_birth)
           (GROUP_CONCAT(DISTINCT ?countryCitizenshipLabel; separator="|") AS ?country_of_citizenship)
           (GROUP_CONCAT(DISTINCT ?ethnicityLabel; separator="|") AS ?ethnicity)
           (GROUP_CONCAT(DISTINCT ?sexOrientLabel; separator="|") AS ?sexual_orientation)
           (SAMPLE(?dob) AS ?date_of_birth)
           (SAMPLE(?dod) AS ?date_of_death)
    WHERE {{
      VALUES ?item {{ {values} }}
      OPTIONAL {{ ?item wdt:P21 ?gender. }}
      OPTIONAL {{ ?item wdt:P19 ?place. ?place wdt:P17 ?country. }}
      OPTIONAL {{ ?item wdt:P27 ?countryCitizenship. }}
      OPTIONAL {{ ?item wdt:P172 ?ethnicity. }}
      OPTIONAL {{ ?item wdt:P91 ?sexOrient. }}
      OPTIONAL {{ ?item wdt:P569 ?dob. }}
      OPTIONAL {{ ?item wdt:P570 ?dod. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    GROUP BY ?item
    """
    attempt = 0
    while True:
        try:
            resp = requests.get(WIKIDATA_SPARQL_URL, params={"query": sparql, "format": "json"}, headers=HEADERS, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                rows = data.get("results", {}).get("bindings", [])
                out: Dict[str, Dict[str, Optional[str]]] = {}
                for r in rows:
                    item_url = r["item"]["value"]
                    qid = item_url.rsplit("/", 1)[-1]
                    def _val(k):
                        v = r.get(k)
                        return v["value"] if v else None
                    out[qid] = {
                        "country_of_birth": _val("country_of_birth"),
                        "gender": _val("gender"),
                        "country_of_citizenship": _val("country_of_citizenship"),
                        "ethnicity": _val("ethnicity"),
                        "sexual_orientation": _val("sexual_orientation"),
                        "date_of_birth": _val("date_of_birth"),
                        "date_of_death": _val("date_of_death")
                    }
                # ensure all requested qids are present in mapping (missing => None)
                for q in qids:
                    out.setdefault(q, {
                        "country_of_birth": None,
                        "gender": None,
                        "country_of_citizenship": None,
                        "ethnicity": None,
                        "sexual_orientation": None,
                        "date_of_birth": None,
                        "date_of_death": None
                    })
                return out
            elif resp.status_code in (429, 503):
                attempt += 1
                if attempt > retries:
                    break
                time.sleep(2 ** attempt)
                continue
            else:
                resp.raise_for_status()
        except requests.RequestException:
            attempt += 1
            if attempt > retries:
                break
            time.sleep(1 + attempt)

    # On failure, return None for all
    return {q: { "country_of_birth": None, "gender": None, "country_of_citizenship": None,
                 "ethnicity": None, "sexual_orientation": None, "date_of_birth": None, "date_of_death": None }
            for q in qids}

def fetch_wikidata_properties_for_qid_df_batch(
    qid_df: pd.DataFrame,
    qid_col: str = "qid",
    author_col: str = "author_text",
    batch_size: int = 40,
    pause_between_batches: float = 1.0
) -> pd.DataFrame:
    """
    Given a dataframe `qid_df` with columns `author_text` and `qid`, query Wikidata in batches
    and return a dataframe with columns:
      author_text, qid, country_of_birth, gender, country_of_citizenship,
      ethnicity, sexual_orientation, date_of_birth (datetime), date_of_death (datetime)
    Multi-valued label fields are returned as '|' separated strings (or None).
    Dates are parsed to pandas datetime (or NaT if missing/unparseable).
    """
    for col in (qid_col, author_col):
        if col not in qid_df.columns:
            raise KeyError(f"Column {col!r} not found in qid_df")

    # preserve original order
    qid_series = qid_df[qid_col].astype(object)
    unique_qids = [str(q) for q in pd.Series(qid_series.dropna().unique()) if str(q).strip() != "nan" and str(q).strip() != ""]
    # chunk
    mappings: Dict[str, Dict[str, Optional[str]]] = {}
    for i in range(0, len(unique_qids), batch_size):
        batch = unique_qids[i:i+batch_size]
        batch_map = _query_props_for_qids_batch(batch)
        mappings.update(batch_map)
        time.sleep(pause_between_batches)

    records = []
    for _, row in qid_df.iterrows():
        author = row.get(author_col)
        qid = row.get(qid_col)
        if pd.isna(qid) or qid is None or str(qid).strip() == "":
            rec = {
                "author_text": author,
                "qid": None,
                "country_of_birth": None,
                "gender": None,
                "country_of_citizenship": None,
                "ethnicity": None,
                "sexual_orientation": None,
                "date_of_birth": pd.NaT,
                "date_of_death": pd.NaT
            }
            records.append(rec)
            continue
        qid_str = str(qid)
        props = mappings.get(qid_str, {
            "country_of_birth": None, "gender": None, "country_of_citizenship": None,
            "ethnicity": None, "sexual_orientation": None, "date_of_birth": None, "date_of_death": None
        })
        # parse dates
        dob = pd.to_datetime(props.get("date_of_birth"), errors="coerce")
        dod = pd.to_datetime(props.get("date_of_death"), errors="coerce")
        rec = {
            "author_text": author,
            "qid": qid_str,
            "country_of_birth": props.get("country_of_birth"),
            "gender": props.get("gender"),
            "country_of_citizenship": props.get("country_of_citizenship"),
            "ethnicity": props.get("ethnicity"),
            "sexual_orientation": props.get("sexual_orientation"),
            "date_of_birth": dob,
            "date_of_death": dod
        }
        records.append(rec)

    return pd.DataFrame.from_records(records)

# Example usage:
# result_df = fetch_wikidata_properties_for_qid_df_batch(qid_df, qid_col='qid', author_col='author_text', batch_size=40, pause_between_batches=1.0)
# result_df  # contains requested properties with dates as datetimes