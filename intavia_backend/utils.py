import base64
from dataclasses import asdict
import datetime
import os
from urllib.parse import quote, unquote
from SPARQLWrapper import SPARQLWrapper, JSON
from intavia_backend.query_parameters import Search
from intavia_backend.query_parameters_v2 import Search as SearchV2
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
    "recon_provided_person_v1_1.sparql": {"id": "?id", "score": "?score", "label": "?label"},
    "recon_crm_v1_1.sparql": {"id": "?id", "score": "?score", "label": "?label"},
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


def get_query_from_triplestore_v2(search: Search, sparql_template: str):
    """creates the query from the template and the search parameters and returns the json
       from the triplestore. This is v2 and doesnt need the proto config anymore

    Args:
        search (Search): _description_
        sparql_template (str): _description_

    Returns:
        _type_: _description_
    """
    if isinstance(search, Search) or isinstance(search, SearchV2):
        search = asdict(search)
    query_template = jinja_env.get_template(sparql_template).render(**search)
    sparql.setQuery(query_template)
    res = sparql.queryAndConvert()
    return res["results"]["bindings"]


def flatten_rdf_data(data: dict) -> list:
    """Flatten the RDF data to a list of dicts.

    Args:
        data (dict): The RDF data

    Returns:
        list: A list of dicts
    """
    flattened_data = []
    for ent in data:
        d_res = {}
        for k, v in ent.items():
            if isinstance(v, dict):
                if "value" in v:
                    if "datatype" in v:
                        if v["datatype"] == "http://www.w3.org/2001/XMLSchema#dateTime":
                            v["value"] = datetime.datetime.fromisoformat(str(v["value"]).replace("Z", "+00:00"))
                        elif v["datatype"] == "http://www.w3.org/2001/XMLSchema#integer":
                            v["value"] = int(v["value"])
                        elif v["datatype"] == "http://www.w3.org/2001/XMLSchema#boolean":
                            v["value"] = bool(v["value"])
                        elif v["datatype"] == "http://www.w3.org/2001/XMLSchema#float":
                            v["value"] = float(v["value"])
                    d_res[k] = v["value"]
                else:
                    d_res[k] = v
            else:
                d_res[k] = v
        flattened_data.append(d_res)
    return flattened_data


def toggle_urls_encoding(url):
    """Toggles the encoding of the url.

    Args:
        url (str): The url

    Returns:
        str: The encoded/decoded url
    """
    if "/" in url:
        return base64.urlsafe_b64encode(url.encode("utf-8")).decode("utf-8")
    else:
        return base64.urlsafe_b64decode(url.encode("utf-8")).decode("utf-8")
