from fastapi import FastAPI, Query
from models import PersonFull, GroupFull, PlaceFull
from typing import Union
import os
from SPARQLWrapper import SPARQLWrapper, JSON
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
        'id$anchor': 'id',
        'relations': [
            {
                'id$anchor': 'event.id'
            }
        ]
    }
}

@app.get("/api/entities/search", response_model=Union[PersonFull, GroupFull, PlaceFull])
async def query_persons(q: str | None = Query(default=None, max_length=200)):
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
        cache_client.set(q, {'time': datetime.datetime.now(), 'data': res})
    r2 = convert_sparql_result(res, config['person_v1']) 
    return {}
