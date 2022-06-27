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

app = FastAPI()

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


@app.get("/")
async def root():
    return {"message": "Hello World"}

config = {
    'person_v1': {
        'id': '?person$anchor',
        'gender': '?genderLabel',
        'label': {
            'default': '?entityLabel'
        },
        'events':
            {
                'id': '?event$anchor',
                'startDate': '?start',
                'endDate': '?end',
                'relations$list': {
                    'id': '?entity2$anchor',
                    'label': {
                        'default': '?entity2Label'
                    }
                }
            } 
    }
}


@app.get("/api/entities/search", response_model=PaginatedResponseEntities)
async def query_persons(search: Search = Depends()):
    res = get_query_from_cache(search, "person_v1.sparql")
    start = (search.page*search.limit)-search.limit
    end = start + search.limit
    t1 = PaginatedResponseEntities.from_orm({'page': search.page, 'count': len(res), 'pages': len(res)/search.limit, 'results': res[start:end]}) 
    return t1

