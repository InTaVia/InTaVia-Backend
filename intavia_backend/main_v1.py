import datetime
import aioredis
from tkinter import W
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi_versioning import VersionedFastAPI, version, versioned_api_route
from .models_v1 import (
    PaginatedResponseEntities,
    PaginatedResponseOccupations,
    ReconResponse,
    StatisticsBins,
    StatisticsOccupationReturn,
)
import math
import os
from jinja2 import Environment, FileSystemLoader
import os.path
from .conversion import convert_sparql_result
from .query_parameters import Entity_Retrieve, ReconQueryBatch, Search, SearchVocabs, StatisticsBase
import sentry_sdk
from dataclasses import asdict
import dateutil

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from .intavia_cache import cache
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


RECON_MAX_BATCH_SIZE = 50


@router.get(
    "/recon",
    tags=["Reconciliation"],
)
async def recon_manifest():
    return {
        "versions": ["0.1"],
        "name": "InTaVia",
        "identifierSpace": "http://www.intavia.eu/idm-core/",
        "schemaSpace": "http://www.intavia.eu/idm-core/Provided_Item",
        "batchSize": RECON_MAX_BATCH_SIZE,
        "defaultTypes": [
            {"id": "Person", "name": "Person"},
            {"id": "Group", "name": "Group"},
            {"id": "Place", "name": "Place"},
        ],
    }


@router.post(
    "/recon/reconcile",
    response_model=ReconResponse,
    response_model_exclude_none=True,
    tags=["Reconciliation"],
    description="Endpoint that implements the reconciliation aPI specification.",
)
async def recon(payload: ReconQueryBatch = Depends()):
    if len(payload.queries.queries) > RECON_MAX_BATCH_SIZE:
        raise HTTPException(status_code=413, detail="Maximum batch size is " + str(RECON_MAX_BATCH_SIZE))
    results = []
    response = {"results": results}
    for reconQuery in payload.queries.queries:
        if reconQuery.type.get_rdf_uri() in ["<http://www.intavia.eu/idm-core/Provided_Person>"]:
            res = get_query_from_triplestore(reconQuery, "recon_provided_person_v1_1.sparql")
        else:
            res = get_query_from_triplestore(reconQuery, "recon_crm_v1_1.sparql")
        batch_results = []
        for r in res:
            batch_results.append({"id": r["id"], "name": r["label"], "score": r["score"]})
        results.append({"candidates": batch_results})
    print(response)
    return response
