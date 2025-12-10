import pandas as pd
from tqdm import tqdm
from SPARQLWrapper import SPARQLWrapper, JSON
import urllib.parse
import time

*# -------------------------------------------------*
*# 1️⃣  Your original DataFrame (replace with your own source)*
*# -------------------------------------------------*
*# Example data – you can load from CSV, DB, etc.*
authors = [
  "Elinor Ostrom",
  "J. R. R. Tolkien",
  "John Kennedy Toole",
  "Antoine de Saint-Exupéry",
  "Marta Rojals",
  "Haruki Murakami"
]

df = pd.DataFrame({"author_name": authors})

*# -------------------------------------------------*
*# 2️⃣  Helper: build a SPARQL query for ONE name*
*# -------------------------------------------------*
def build_query(name: str) -> str:
  """
  Returns a SPARQL query that looks for a Wikidata entity whose
  rdfs:label matches *exactly* the supplied name (English language).
  It then pulls gender, country of birth, ethnicity and sexual orientation.
  """
  escaped = urllib.parse.quote(name)  *# safe for inclusion in the query string*
  query = f"""
  SELECT ?person ?personLabel ?genderLabel ?birthCountryLabel ?ethnicityLabel ?orientationLabel WHERE {{
    # Find the entity with the exact English label
    ?person rdfs:label "{name}"@en .
    OPTIONAL {{ ?person wdt:P21 ?gender . SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}
    
    # Country of birth: place of birth (P19) → country (P17)
    OPTIONAL {{
      ?person wdt:P19 ?birthPlace .
      ?birthPlace wdt:P17 ?birthCountry .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}

    OPTIONAL {{ ?person wdt:P172 ?ethnicity . SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}
    OPTIONAL {{ ?person wdt:P91 ?orientation . SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}

    # Pull human‑readable labels
    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
  }}
  LIMIT 1
  """
  return query

*# -------------------------------------------------*
*# 3️⃣  Function: run a query and parse results*
*# -------------------------------------------------*
sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
sparql.setReturnFormat(JSON)

def query_wikidata(name: str):
  """Returns a dict with the four fields (or None if not found)."""
  q = build_query(name)
  sparql.setQuery(q)
  try:
      ret = sparql.query().convert()
  except Exception as e:
      print(f"⚠️  Query failed for '{name}': {e}")
      return {"gender": None,
              "birth_country": None,
              "ethnicity": None,
              "sexual_orientation": None}

  *# If there are no bindings, return Nones*
  if not ret["results"]["bindings"]:
      return {"gender": None,
              "birth_country": None,
              "ethnicity": None,
              "sexual_orientation": None}

  b = ret["results"]["bindings"][0]   *# we limited to 1 result*
  def _val(key):
      return b[key]["value"] if key in b else None

  return {
      "gender": _val("genderLabel"),
      "birth_country": _val("birthCountryLabel"),
      "ethnicity": _val("ethnicityLabel"),
      "sexual_orientation": _val("orientationLabel")
  }

*# -------------------------------------------------*
*# 4️⃣  Loop over the DataFrame, fill new columns*
*# -------------------------------------------------*
*# Prepare empty columns*
df["gender"] = None
df["birth_country"] = None
df["ethnicity"] = None
df["sexual_orientation"] = None

for idx, row in tqdm(df.iterrows(), total=len(df), desc="Fetching Wikidata"):
  name = row["author_name"]
  info = query_wikidata(name)

  *# Assign results back into the DataFrame*
  df.at[idx, "gender"] = info["gender"]
  df.at[idx, "birth_country"] = info["birth_country"]
  df.at[idx, "ethnicity"] = info["ethnicity"]
  df.at[idx, "sexual_orientation"] = info["sexual_orientation"]

  *# Be polite to the public endpoint – short pause*
  time.sleep(0.2)   *# 5 requests per second max is recommended*

*# -------------------------------------------------*
*# 5️⃣  Result preview*
*# -------------------------------------------------*
print("\n=== Enriched DataFrame ===")
print(df.head())