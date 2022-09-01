import aioredis
from tkinter import W
from fastapi import Depends, FastAPI, Query
from pydantic import HttpUrl
from models import PaginatedResponseEntities, PaginatedResponseOccupations, PersonFull, GroupFull, PlaceFull, StatisticsBins, StatisticsOccupation, StatisticsOccupationReturn
from typing import Union
import math
import os
from SPARQLWrapper import SPARQLWrapper, JSON
from SPARQLTransformer import pre_process
from jinja2 import Environment, FileSystemLoader
from pymemcache.client.base import Client
from pymemcache import serde
import os.path
import datetime
from conversion import convert_sparql_result
from query_parameters import Entity_Retrieve, Search, SearchVocabs, StatisticsBase
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from dataclasses import asdict
import dateutil
from fastapi.middleware.cors import CORSMiddleware

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache


app = FastAPI(
    docs_url="/",
    title="InTaVia IDM-Json Backend",
    description="Development version of the InTaVia backend.",
    version="0.1.0"
)

origins = [
    "http://localhost:3000",
    "https://intavia.acdh-dev.oeaw.ac.at",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
sentry_sdk.init(
    dsn="https://a1253a59c2564963a8f126208f03a655@sentry.acdh-dev.oeaw.ac.at/9",

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production,
    traces_sample_rate=1.0,
)

# app.add_middleware(SentryAsgiMiddleware)

tags_metadata = [
    {
        "name": "Query endpoints",
        "description": "Endpoints used to query and filter the InTaVia Knowledgegraph"
    }
]

sparql_endpoint = os.environ.get("SPARQL_ENDPOINT")
sparql = SPARQLWrapper(sparql_endpoint)
sparql.setReturnFormat(JSON)
if not sparql_endpoint.startswith("http://127.0.0.1:8080"):
    sparql.setHTTPAuth("BASIC")
    sparql.setCredentials(user=os.environ.get(
        "SPARQL_USER"), passwd=os.environ.get("SPARQL_PASSWORD"))

jinja_env = Environment(loader=FileSystemLoader('sparql/'), autoescape=False)

#cache_client = Client(('localhost', 11211), serde=serde.pickle_serde)


def get_query_from_triplestore(search: Search, sparql_template: str, proto_config: str | None = None):
    #res = cache_client.get(search.get_cache_str(sparql_template))
    res = None
    if res is not None:
        tm_template = os.path.getmtime(f"sparql/{sparql_template}")
        if tm_template > res['time'].timestamp():
            res = None
        else:
            res = res['data']
    if res is None:
        query_template = jinja_env.get_template(
            sparql_template).render(**asdict(search))
        sparql.setQuery(query_template)
        res = sparql.queryAndConvert()
        rq, proto, opt = pre_process(
            {'proto': config[sparql_template] if proto_config is None else config[proto_config]})
        res = convert_sparql_result(
            res, proto, {"is_json_ld": False, "langTag": "hide", "voc": "PROTO"})
        cache_key = search.get_cache_str(sparql_template)
        #res_cache_set = cache_client.set(cache_key, {
        #                 'time': datetime.datetime.now(), 'data': res})
    return res


def create_bins_from_range(start, end, intv):
    bins = list(calculate_date_range(start, end, intv))
    bins_fin = []
    for i in range(0, intv):
        bins_fin.append({
            "values": (bins[i], bins[i+1]),
            "label": f"{bins[i].strftime('%Y')} - {bins[i+1].strftime('%Y')}",
            "count": 0
        })
    return bins_fin


def calculate_date_range(start, end, intv):
    diff = (end - start) / intv
    for i in range(intv):
        yield (start + diff * i)
    yield end


config = {
    'search_v3.sparql': {
        'id': '?person$anchor',
        'kind': '?entityTypeLabel',
        '_linkedIds': "?linkedIds$list",
        '_count': '?count',
        'gender': {
            'id': '?gender',
            'label': {'default': '?genderLabel'}},
        'occupations': {
            'id': '?occupation$anchor$list',
            'label': {'default': '?occupationLabel'}},
        'label': {
            'default': '?entityLabel'
        },
        'events':
            {
                'id': '?event$anchor$list',
                'label': {
                    'default': '?eventLabel'
                },
                'startDate': '?start',
                'endDate': '?end',
                '_source_entity_role': {
                    'id': '?role',
                    'label': {
                        'default': '?roleLabel'
                    }
                },
                'place': {
                    'id': '?evPlace',
                    '_lat_long': '?evPlaceLatLong',
                    'label': {
                        'default': '?evPlaceLabel'
                    },
                },
                'relations': {
                    'id': '?entity2$anchor$list',
                    'kind': '?entity2TypeLabel',
                    'label': {
                        'default': '?entity2Label'
                    },
                    'role': {
                        'id': '?role2$anchor',
                        'label': {
                            "default": '?roleLabel2'
                        }
                    }
                }
        }
    },
    'occupation_v1.sparql': {
        'id': '?occupation$anchor',
        'label': {
            'default': '?occupationLabel'
        },
        'relations': {
            '_id': '?broader$anchor$list',
            'kind': '?kindBroader',
            'occupation': {
                'id': '?broader',
                'label': {
                    'default': '?broaderLabel'
                }

            }
        }
    },
    'statistics_birthdate_v1.sparql': {
        'date': '?date$anchor',
        'count': '?count'
    },
    'statistics_deathdate_v1.sparql': {
        'date': '?date$anchor',
        'count': '?count'
    },
    'statistics_occupation_v1.sparql': {
        'id': '?occupation$anchor',
        'label': '?occupationLabel',
        'broader': {
            'id': '?broader$anchor',
            'label': '?broaderLabel'
        },
        'count': '?count'
    }
}


@app.get("/api/entities/search",
         response_model=PaginatedResponseEntities,
         response_model_exclude_none=True,
         tags=["Query endpoints"],
         description="Endpoint that allows to query and retrieve entities including \
    the node history. Depending on the objects found the return object is \
        different.")
@cache()
async def query_entities(search: Search = Depends()):
    res = get_query_from_triplestore(search, "search_v3.sparql")
    start = (search.page*search.limit)-search.limit
    end = start + search.limit
    return {'page': search.page, 'count': int(res[0]["_count"] if len(res) > 0 else 0), 'pages': math.ceil(int(res[0]["_count"])/search.limit if len(res) > 0 else 0), 'results': res}


@app.get("/api/vocabularies/occupations/search",
         response_model=PaginatedResponseOccupations,
         response_model_exclude_none=True,
         tags=["Vocabularies"],
         description="Endpoint that allows to query and retrieve entities including \
    the node history. Depending on the objects found the return object is \
        different.")
async def query_occupations(search: SearchVocabs = Depends()):
    res = get_query_from_triplestore(search, "occupation_v1.sparql")
    start = (search.page*search.limit)-search.limit
    end = start + search.limit
    return {'page': search.page, 'count': len(res), 'pages': math.ceil(len(res)/search.limit), 'results': res[start:end]}


@app.get(
    "/api/statistics/birth/search",
    response_model=StatisticsBins,
    tags=["Statistics"],
    description="Endpoint that returns counts in bins for date of births"
)
async def statistics_birth(search: StatisticsBase = Depends()):
    res = get_query_from_triplestore(search, "statistics_birthdate_v1.sparql")
    for idx, v in enumerate(res):
        res[idx]["date"] = dateutil.parser.parse(res[idx]["date"])
    bins = create_bins_from_range(res[0]["date"], res[-1]["date"], search.bins)
    for idx, b in enumerate(bins):
        for date in res:
            if b["values"][0] <= date["date"] <= b["values"][1]:
                b["count"] += date["count"]
        bins[idx] = b
    return {'bins': bins}


@app.get(
    "/api/statistics/death/search",
    response_model=StatisticsBins,
    tags=["Statistics"],
    description="Endpoint that returns counts in bins for date of deaths"
)
async def statistics_death(search: StatisticsBase = Depends()):
    res = get_query_from_triplestore(search, "statistics_deathdate_v1.sparql")
    for idx, v in enumerate(res):
        res[idx]["date"] = dateutil.parser.parse(res[idx]["date"])
    bins = create_bins_from_range(res[0]["date"], res[-1]["date"], search.bins)
    for idx, b in enumerate(bins):
        for date in res:
            if b["values"][0] <= date["date"] <= b["values"][1]:
                b["count"] += date["count"]
        bins[idx] = b
    return {'bins': bins}


@app.get(
    "/api/statistics/occupations/search",
    response_model=StatisticsOccupationReturn,
    tags=["Statistics"],
    description="Endpoint that returns counts of the occupations"
)
async def statistics_occupations(search: StatisticsBase = Depends()):
    res = get_query_from_triplestore(search, "statistics_occupation_v1.sparql")
    data = res
    data_fin = {'id': "root", 'label': "root", 'count': 0, 'children': []}
    data_second = []
    for idx, occ in enumerate(data):
        if "broader" not in occ:
            if isinstance(occ["label"], list):
                occ["label"] = " / ".join(occ["label"])
            elif ">>" in occ["label"]:
                occ["label"] = occ["label"].split(" >> ")[-1]
            data_fin["children"].append({'id': occ["id"], 'label': occ["label"], 'count': occ["count"], "children": []})
        else:
            data_second.append(occ)
    while len(data_second) > 0:
        for idx, occ in enumerate(data_second):
            for child in data_fin["children"]:
                if child["id"] == occ["broader"]["id"]:
                    if isinstance(occ["label"], list):
                        occ["label"] = " / ".join(occ["label"])
                    elif ">>" in occ["label"]:
                        occ["label"] = occ["label"].split(" >> ")[-1]
                    child["children"].append({'id': occ["id"], 'label': occ["label"], 'count': occ["count"]})
                    data_second.pop(idx)
                    break   
    return {"tree": data_fin}


@app.get("/api/entities/id",
         response_model=PaginatedResponseEntities,
         response_model_exclude_none=True,
         tags=["Enities endpoints"],
         description="Endpoint that allows to retrive an entity by id.")
async def retrieve_entity(id: Entity_Retrieve = Depends()):
    res = get_query_from_triplestore(id, "get_entity_v1.sparql", "search_v2.sparql")
    return {"page": 1, "count": len(res), "pages": 1, "results": res}


@app.on_event("startup")
async def startup():
    redis =  aioredis.from_url("redis://localhost", encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
