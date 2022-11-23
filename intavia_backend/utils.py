from dataclasses import asdict
import os
from SPARQLWrapper import SPARQLWrapper, JSON
from intavia_backend.query_parameters import Search
from jinja2 import Environment, FileSystemLoader
from .conversion import convert_sparql_result
from SPARQLTransformer import pre_process

config = {
    "search_v3.sparql": {
        "id": "?person$anchor",
        "kind": "?entityTypeLabel",
        "_linkedIds": "?linkedIds$list",
        "count": "?count",
        "gender": {"id": "?gender", "label": {"default": "?genderLabel"}},
        "occupations": {"id": "?occupation$anchor$list", "label": {"default": "?occupationLabel"}},
        "label": {"default": "?entityLabel"},
        "events": {
            "id": "?event$anchor$list",
            "label": {"default": "?eventLabel"},
            "startDate": "?start",
            "endDate": "?end",
            "_source_entity_role": {"id": "?role", "label": {"default": "?roleLabel"}},
            "place": {
                "id": "?evPlace$anchor",
                "_lat_long": "?evPlaceLatLong",
                "label": {"default": "?evPlaceLabel"},
            },
            "relations": {
                "id": "?entity2$anchor$list",
                "kind": "?entity2TypeLabel",
                "label": {"default": "?entity2Label"},
                "role": {"id": "?role2$anchor", "label": {"default": "?roleLabel2"}},
            },
        },
    },
    "occupation_v1.sparql": {
        "id": "?occupation$anchor",
        "label": {"default": "?occupationLabel"},
        "relations": {
            "_id": "?broader$anchor$list",
            "kind": "?kindBroader",
            "occupation": {"id": "?broader", "label": {"default": "?broaderLabel"}},
        },
    },
    "statistics_birthdate_v1.sparql": {"date": "?date$anchor", "count": "?count"},
    "statistics_deathdate_v1.sparql": {"date": "?date$anchor", "count": "?count"},
    "statistics_occupation_v1.sparql": {
        "id": "?occupation$anchor",
        "label": "?occupationLabel",
        "broader": {"id": "?broader$anchor", "label": "?broaderLabel"},
        "count": "?count",
    },
}

jinja_env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "sparql")), autoescape=False)
sparql_endpoint = os.environ.get("SPARQL_ENDPOINT")
sparql = SPARQLWrapper(sparql_endpoint)
sparql.setReturnFormat(JSON)
if not sparql_endpoint.startswith("http://127.0.0.1:8080"):
    sparql.setHTTPAuth("BASIC")
    sparql.setCredentials(user=os.environ.get("SPARQL_USER"), passwd=os.environ.get("SPARQL_PASSWORD"))


def get_query_from_triplestore(search: Search, sparql_template: str, proto_config: str | None = None):
    query_template = jinja_env.get_template(sparql_template).render(**asdict(search))
    sparql.setQuery(query_template)
    res = sparql.queryAndConvert()
    rq, proto, opt = pre_process({"proto": config[sparql_template] if proto_config is None else config[proto_config]})
    res = convert_sparql_result(res, proto, {"is_json_ld": False, "langTag": "hide", "voc": "PROTO"})
    return res
