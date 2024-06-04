# type: ignore
# flake8: noqa
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
import pandas as pd
import altair as alt

df = pd.read_csv("data/bookwyrm-export.csv")

df.head()
#
#
#
#
#
#
#
#
#

df = df.filter()

alt.Chart(df).mark_bar().encode(
    x='count()',
    y=alt.Y('author_text').sort('-x').title('Author')
).properties(
  title='Top Authors'
)
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
# pip install sparqlwrapper
# https://rdflib.github.io/sparqlwrapper/

import sys
from SPARQLWrapper import SPARQLWrapper, JSON

endpoint_url = "https://query.wikidata.org/sparql"

query = """SELECT DISTINCT ?item ?itemLabel ?sex_or_gender ?sex_or_genderLabel ?date_of_birth ?date_of_death ?occupation ?occupationLabel WHERE {
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE]". }
  {
    SELECT DISTINCT ?item WHERE {
      ?item p:P31 ?statement0.
      ?statement0 (ps:P31/(wdt:P279*)) wd:Q5.
      ?item p:P2561 ?statement1.
      ?statement1 ps:P2561 _:anyValueP2561.
    }
    LIMIT 10
  }
  OPTIONAL { ?item wdt:P21 ?sex_or_gender. }
  OPTIONAL { ?item wdt:P569 ?date_of_birth. }
  OPTIONAL { ?item wdt:P570 ?date_of_death. }
  OPTIONAL { ?item wdt:P106 ?occupation. }
}"""


def get_results(endpoint_url, query):
    user_agent = "WDQS-example Python/%s.%s" % (sys.version_info[0], sys.version_info[1])
    # TODO adjust user agent; see https://w.wiki/CX6
    sparql = SPARQLWrapper(endpoint_url, agent=user_agent)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()


results = get_results(endpoint_url, query)

for result in results["results"]["bindings"]:
    print(result)

#
#
#
from SPARQLWrapper import SPARQLWrapper, JSON

NAME_FRAGMENT = "Andreotti"

QUERY = f"""
SELECT DISTINCT ?uri 
WHERE {{ 
   ?uri a foaf:Person. 
   ?uri ?p ?person_full_name. 
   FILTER(?p IN(dbo:birthName,dbp:birthName ,dbp:fullname,dbp:name)). 
   ?uri rdfs:label ?person_name . 
   ?person_name bif:contains "{NAME_FRAGMENT}" .  
   FILTER(langMatches(lang(?person_full_name), "en")) .
}} 
LIMIT 100
"""

# Specify the DBPedia endpoint
#sparql = SPARQLWrapper("http://dbpedia.org/sparql")
#sparql.setQuery(QUERY)
#sparql.setReturnFormat(JSON)

# Run the query
result = sparql.query().convert()

# The return data contains "bindings" (a list of dictionaries)
for link in result["results"]["bindings"]:
    # We want the "value" attribute of the "comment" field
    print(link["uri"]["value"])
#
#
#
#
from SPARQLWrapper import SPARQLWrapper, JSON

def get_wikidata_info(selected_author="Haruki Murakami"):
    # SPARQL query with a parameter for the selected_author
    query = """
    SELECT ?human ?humanLabel ?dob ?gender ?wikidataUrl
    WHERE {
      ?human rdfs:label ?label.
      ?human wdt:P31 wd:Q5;  # Instance of human
             wdt:P569 ?dob;  # Date of birth
             wdt:P21 ?gender;  # Gender
             wdt:P31 wd:Q5.  # Ensure the entity is a human

      FILTER(LANG(?label) = "en" && STR(?label) = STR(?selected_author))

      BIND(wd:Q42 AS ?wikidataUrl)  # Replace Q42 with the actual QID of the specified label
      SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    }
    """

    # Create a SPARQLWrapper object and set the endpoint
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setQuery(query)

    # Set the parameters
    sparql.setParams({
        "selected_author": selected_author
    })

    # Define the request headers
    sparql.addCustomHttpHeader("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    # Set the result format to JSON
    sparql.setReturnFormat(JSON)

    # Execute the query and parse the results
    results = sparql.query().convert()

    # Print the results
    for result in results['results']['bindings']:
        print(result['humanLabel']['value'])
        print("Date of Birth:", result['dob']['value'])
        print("Gender:", result['gender']['value'])
        print("Wikidata URL:", result['wikidataUrl']['value'])
        print()

# Example usage
selected_author = "Haruki Murakami"  # Change this to the label you want to query
get_wikidata_info(selected_author)

#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
