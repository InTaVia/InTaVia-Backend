from fastapi import Depends, FastAPI, Query
from models import PaginatedResponseEntities, PersonFull, GroupFull, PlaceFull
from typing import Union
import os
from SPARQLWrapper import SPARQLWrapper, JSON
from SPARQLTransformer import pre_process
from jinja2 import Environment, FileSystemLoader
from pymemcache.client.base import Client
from pymemcache import serde
import os.path
import datetime
from conversion import convert_sparql_result
from query_parameters import Search

app = FastAPI(
    docs_url="/",
    title="InTaVia IDM-Json Backend",
    description="Development version of the InTaVia backend.",
    version="0.1.0"
)

tags_metadata = [
    {
        "name": "Query endpoints",
        "description": "Endpoints used to query and filter the InTaVia Knowledgegraph"
    }
]

sparql = SPARQLWrapper(os.environ.get("SPARQL_ENDPOINT"))
sparql.setReturnFormat(JSON)
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
        query_template = jinja_env.get_template(sparql_template).render(**search.dict())
        sparql.setQuery(query_template)
        res = sparql.queryAndConvert()
        rq, proto, opt = pre_process({'proto': config['person_v1']})
        res = convert_sparql_result(res, proto, {"is_json_ld": False, "langTag": "show", "voc": "PROTO"})
        cache_client.set(search.get_cache_str(), {'time': datetime.datetime.now(), 'data': res})
    return res


config = {
    'person_v1': {
        'id': '?person$anchor',
        'kind': '?entityTypeLabel',
        'gender': '?genderLabel',
        'label': {
            'default': '?entityLabel'
        },
        'events':
            {
                'id': '?event$anchor$list',
                'startDate': '?start',
                'endDate': '?end',
                'relations': {
                    'id': '?entity2$anchor$list',
                    'kind': '?entity2TypeLabel',
                    'label': {
                        'default': '?entity2Label'
                    },
                    'role': {
                        'id': '?role2',
                        'label': '?roleLabel2'
                    }
                }
            } 
    }
}


@app.get("/api/entities/search", 
response_model=PaginatedResponseEntities, 
tags=["Query endpoints"],
description="Endpoint that allows to query and retrieve entities including \
    the node history. Depending on the objects found the return object is \
        different.")
async def query_entities(search: Search = Depends()):
    res = get_query_from_cache(search, "search_v1.sparql")
    start = (search.page*search.limit)-search.limit
    end = start + search.limit
    t1 = PaginatedResponseEntities.from_orm({'page': search.page, 'count': len(res), 'pages': len(res)/search.limit, 'results': res[start:end]}) 
    return t1

