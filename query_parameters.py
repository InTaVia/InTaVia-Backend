import json
from fastapi import Query
from pydantic import BaseModel, HttpUrl, NonNegativeInt, PositiveInt


class QueryBase(BaseModel):
    page: PositiveInt = Query(default=1, gte=1)
    limit: int = Query(default=50, le=1000, gte=1)

    def get_cache_str(self):
        return str(hash(json.dumps(self.dict(exclude={"page", "limit"}), sort_keys=True)))


class Search(QueryBase):
    q: str = Query(default=None,
                   max_length=200,
                   description="Searches across labels of all entity proxies")
