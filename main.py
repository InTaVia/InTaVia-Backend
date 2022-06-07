from fastapi import FastAPI, Query
from models import PersonFull

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/persons/",  response_model=PersonFull)
async def query_persons(q: str | None = Query(default=None, max_length=200)):
    return {}
