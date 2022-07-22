from tkinter import W
from fastapi import Depends, FastAPI, Query
from pydantic import HttpUrl
from models import PaginatedResponseEntities, PaginatedResponseOccupations, PersonFull, GroupFull, PlaceFull, StatisticsBins
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
from query_parameters import Search, SearchVocabs, StatisticsBirth
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from dataclasses import asdict
import dateutil


app = FastAPI(
    docs_url="/",
    title="InTaVia IDM-Json Backend",
    description="Development version of the InTaVia backend.",
    version="0.1.0"
)

sentry_sdk.init(
    dsn="https://a1253a59c2564963a8f126208f03a655@sentry.acdh-dev.oeaw.ac.at/9",

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production,
    traces_sample_rate=1.0,
)

#app.add_middleware(SentryAsgiMiddleware)

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
    sparql.setCredentials(user=os.environ.get("SPARQL_USER"), passwd=os.environ.get("SPARQL_PASSWORD"))

jinja_env = Environment(loader=FileSystemLoader('sparql/'), autoescape=False)

cache_client = Client(('localhost', 11211), serde=serde.pickle_serde)

def get_query_from_cache(search: Search, sparql_template: str): 
    res = cache_client.get(search.get_cache_str())
    if res is not None:
        tm_template = os.path.getmtime(f"sparql/{sparql_template}")
        if tm_template > res['time'].timestamp():
            res = None
        else:
            res = res['data']
    if res is None:
        query_template = jinja_env.get_template(sparql_template).render(**asdict(search))
        sparql.setQuery(query_template)
        res = sparql.queryAndConvert()
        rq, proto, opt = pre_process({'proto': config[sparql_template]})
        res = convert_sparql_result(res, proto, {"is_json_ld": False, "langTag": "show", "voc": "PROTO"})
        cache_client.set(search.get_cache_str(), {'time': datetime.datetime.now(), 'data': res})
    return res


def calculate_date_range(start, end, intv):
    diff = (end  - start ) / intv
    for i in range(intv):
        yield (start + diff * i)
    yield end




config = {
    'search_v2.sparql': {
        'id': '?person$anchor',
        'kind': '?entityTypeLabel',
        '_linkedIds': "?linkedIds$list",
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
    }
}


@app.get("/api/entities/search", 
response_model=PaginatedResponseEntities,
response_model_exclude_none=True, 
tags=["Query endpoints"],
description="Endpoint that allows to query and retrieve entities including \
    the node history. Depending on the objects found the return object is \
        different.")
async def query_entities(search: Search = Depends()):
    res = get_query_from_cache(search, "search_v2.sparql")
    start = (search.page*search.limit)-search.limit
    end = start + search.limit
    return {'page': search.page, 'count': len(res), 'pages': math.ceil(len(res)/search.limit), 'results': res[start:end]}


@app.get("/api/voabularies/occupations/search", 
response_model=PaginatedResponseOccupations,
response_model_exclude_none=True, 
tags=["Vocabularies"],
description="Endpoint that allows to query and retrieve entities including \
    the node history. Depending on the objects found the return object is \
        different.")
async def query_occupations(search: SearchVocabs = Depends()):
    res = get_query_from_cache(search, "occupation_v1.sparql")
    start = (search.page*search.limit)-search.limit
    end = start + search.limit
    return {'page': search.page, 'count': len(res), 'pages': math.ceil(len(res)/search.limit), 'results': res[start:end]}


@app.get(
    "/api/statistics/birth/search",
    response_model=StatisticsBins,
    tags=["Statistics"],
    description="Endpoint that returns counts in bins for date of births"
)
async def statistics_birth(search: StatisticsBirth = Depends()):
    res = get_query_from_cache(search, "statistics_birthdate_v1.sparql")
    for idx, v in enumerate(res):
        res[idx]["date"] = dateutil.parser.parse(res[idx]["date"])
    if len(res) > search.bins:
        bins_config = calculate_date_range(res[0]["date"], res[-1]["date"], search.bins)
        bins = []
        for date in bins_config:
            if len(res) == 0:
                bins.append(
                    {
                        'label': date.strftime("%Y-%m-%d"),
                        'count': 0
                    }
                )
                continue
            count = 0
            if res[0]["date"] <= date:
                d1 = res.pop(0)
            else:
                d1 = False
            while d1:
                count += d1["count"]
                d1 = False
                if len(res) > 0:
                    if res[0]["date"] <= date:
                        d1 = res.pop(0)
            bins.append(
                {
                    'label': date.strftime("%Y-%m-%d"),
                    'count': count
                }
            )
    else:
        bins = [{'label': x["date"].strftime("%Y-%m-%d"), "count": x["count"]} for x in res]         

    return {'bins': bins}


@app.get("/api/entities/id", 
response_model=PaginatedResponseEntities,
response_model_exclude_none=True, 
tags=["Enities endpoints"],
description="Endpoint that allows to retrive an entity by id.")
async def retrieve_entity(id: HttpUrl):
    res = get_query_from_cache(id, "get_entity_v1.sparql")
    return res 