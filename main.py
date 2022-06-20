from fastapi import FastAPI, Query
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

app = FastAPI()

sparql = SPARQLWrapper(os.environ.get("SPARQL_ENDPOINT"))
sparql.setReturnFormat(JSON)
sparql.setHTTPAuth("BASIC")
sparql.setCredentials(user=os.environ.get("SPARQL_USER"), passwd=os.environ.get("SPARQL_PASSWORD"))

jinja_env = Environment(loader=FileSystemLoader('sparql/'), autoescape=False)

cache_client = Client(('localhost', 11211), serde=serde.pickle_serde)

@app.get("/")
async def root():
    return {"message": "Hello World"}

config = {
    'person_v1': {
        'id': '?person$anchor',
        'label': {
            'default': '?entityLabel'
        },
        'relations':
            {
                'id': '?event$anchor'
            } 
    }
}


@app.get("/api/entities/search", response_model=PaginatedResponseEntities)
async def query_persons(q: str | None = Query(default=None, max_length=200), limit : int = Query(default=50, le=1000, gt=0), page : int = Query(default=1, gt=0)):
    res = cache_client.get(q)
    if res is not None:
        tm_template = os.path.getmtime(r'sparql/person_v1.sparql')
        if tm_template > res['time'].timestamp():
            res = None
        else:
            res = res['data']
    if res is None:
        query_template = jinja_env.get_template('person_v1.sparql').render(q=q)
        sparql.setQuery(query_template)
        res = sparql.queryAndConvert()
        rq, proto, opt = pre_process({'proto': config['person_v1']})
        res = convert_sparql_result(res, proto, {"is_json_ld": False, "langTag": "show", "voc": "PROTO"})
        cache_client.set(q, {'time': datetime.datetime.now(), 'data': res})
    t1 = PaginatedResponseEntities(**{'page': 1, 'count': len(res), 'pages': len(res)/limit, 'results': res[:50]}) 
    return t1
