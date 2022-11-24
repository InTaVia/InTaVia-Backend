import datetime
import aioredis
from tkinter import W
from fastapi import APIRouter, Depends, FastAPI
from fastapi_versioning import VersionedFastAPI, version, versioned_api_route
from .models_v1 import (
    PaginatedResponseEntities,
    PaginatedResponseOccupations,
    StatisticsBins,
    StatisticsOccupationReturn,
)
import math
import os
from jinja2 import Environment, FileSystemLoader
import os.path
from .conversion import convert_sparql_result
from .query_parameters import Entity_Retrieve, Search, SearchVocabs, StatisticsBase
import sentry_sdk
from dataclasses import asdict
import dateutil

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from .main_v2 import router as router_v2
from .utils import get_query_from_triplestore


router = APIRouter(route_class=versioned_api_route(1, 0))
tags_metadata = [
    {"name": "Query endpoints", "description": "Endpoints used to query and filter the InTaVia Knowledgegraph"}
]


def create_bins_from_range(start, end, intv):
    bins = list(calculate_date_range(start, end, intv))
    bins_fin = []
    for i in range(0, intv):
        bins_fin.append(
            {
                "values": (bins[i], bins[i + 1]),
                "label": f"{bins[i].strftime('%Y')} - {bins[i+1].strftime('%Y')}",
                "count": 0,
            }
        )
    return bins_fin


def calculate_date_range(start, end, intv):
    diff = (end - start) / intv
    for i in range(intv):
        yield (start + diff * i)
    yield end


@router.get(
    "/api/entities/search",
    response_model=PaginatedResponseEntities,
    response_model_exclude_none=True,
    tags=["Query endpoints"],
    description="Endpoint that allows to query and retrieve entities including \
    the node history. Depending on the objects found the return object is \
        different.",
)
async def query_entities(search: Search = Depends()):
    res = get_query_from_triplestore(search, "search_v3.sparql")
    pages = math.ceil(int(res[0]["count"]) / search.limit) if len(res) > 0 else 0
    count = int(res[0]["count"]) if len(res) > 0 else 0
    return {"page": search.page, "count": count, "pages": pages, "results": flatten_rdf_data(res)}


@router.get(
    "/api/vocabularies/occupations/search",
    response_model=PaginatedResponseOccupations,
    response_model_exclude_none=True,
    tags=["Vocabularies"],
    description="Endpoint that allows to query and retrieve entities including \
    the node history. Depending on the objects found the return object is \
        different.",
)
@cache()
async def query_occupations(search: SearchVocabs = Depends()):
    res = get_query_from_triplestore(search, "occupation_v1.sparql")
    start = (search.page * search.limit) - search.limit
    end = start + search.limit
    return {"page": search.page, "count": len(res), "pages": math.ceil(len(res) / search.limit), "results": res}


@router.get(
    "/api/statistics/birth/search",
    response_model=StatisticsBins,
    tags=["Statistics"],
    description="Endpoint that returns counts in bins for date of births",
)
@cache()
async def statistics_birth(search: StatisticsBase = Depends()):
    res = get_query_from_triplestore(search, "statistics_birthdate_v1.sparql")
    for idx, v in enumerate(res):
        res[idx]["date"] = dateutil.parser.parse(res[idx]["date"][:10])
    bins = create_bins_from_range(res[0]["date"], res[-1]["date"], search.bins)
    for idx, b in enumerate(bins):
        for date in res:
            if b["values"][0] <= date["date"] <= b["values"][1]:
                b["count"] += date["count"]
        bins[idx] = b
    return {"bins": bins}


@router.get(
    "/api/statistics/death/search",
    response_model=StatisticsBins,
    tags=["Statistics"],
    description="Endpoint that returns counts in bins for date of deaths",
)
@cache()
async def statistics_death(search: StatisticsBase = Depends()):
    res = get_query_from_triplestore(search, "statistics_deathdate_v1.sparql")
    for idx, v in enumerate(res):
        res[idx]["date"] = dateutil.parser.parse(res[idx]["date"][:10])
    bins = create_bins_from_range(res[0]["date"], res[-1]["date"], search.bins)
    for idx, b in enumerate(bins):
        for date in res:
            if b["values"][0] <= date["date"] <= b["values"][1]:
                b["count"] += date["count"]
        bins[idx] = b
    return {"bins": bins}


@router.get(
    "/api/statistics/occupations/search",
    response_model=StatisticsOccupationReturn,
    tags=["Statistics"],
    description="Endpoint that returns counts of the occupations",
)
@cache()
async def statistics_occupations(search: StatisticsBase = Depends()):
    res = get_query_from_triplestore(search, "statistics_occupation_v1.sparql")
    data = res
    data_fin = {"id": "root", "label": "root", "count": 0, "children": []}
    data_second = []
    for idx, occ in enumerate(data):
        if "broader" not in occ:
            if isinstance(occ["label"], list):
                occ["label"] = " / ".join(occ["label"])
            elif ">>" in occ["label"]:
                occ["label"] = occ["label"].split(" >> ")[-1]
            data_fin["children"].append({"id": occ["id"], "label": occ["label"], "count": occ["count"], "children": []})
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
                    child["children"].append({"id": occ["id"], "label": occ["label"], "count": occ["count"]})
                    data_second.pop(idx)
                    break
    return {"tree": data_fin}


@router.get(
    "/api/entities/id",
    response_model=PaginatedResponseEntities,
    response_model_exclude_none=True,
    tags=["Enities endpoints"],
    description="Endpoint that allows to retrive an entity by id.",
)
@cache()
async def retrieve_entity(search: Entity_Retrieve = Depends()):
    res = get_query_from_triplestore(search, "get_entity_v1.sparql", "search_v3.sparql")
    pages = math.ceil(int(res[0]["_count"]) / search.limit) if len(res) > 0 else 0
    count = int(res[0]["_count"]) if len(res) > 0 else 0
    return {"page": search.page, "count": count, "pages": pages, "results": res}
