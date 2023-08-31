from dataclasses import asdict
import datetime
import math
import dateutil
from fastapi import APIRouter, Depends, HTTPException
from .intavia_cache import cache
import requests

from fastapi_versioning import version, versioned_api_route
from intavia_backend.models_v2 import (
    Biography,
    Entity,
    Event,
    MediaResource,
    PaginatedResponseBiography,
    PaginatedResponseEntities,
    PaginatedResponseEvents,
    PaginatedResponseMedia,
    PaginatedResponseVocabularyEntries,
    StatisticsBins,
    StatisticsOccupationPrelim,
    StatisticsOccupationPrelimList,
    StatisticsOccupationReturn,
    StatsEntityType,
    VocabularyEntry,
)
from intavia_backend.query_parameters_v2 import (
    Base,
    Entity_Retrieve,
    QueryBase,
    RequestID,
    Search,
    Search_Base,
    SearchEventKindVocab,
    SearchEvents,
    SearchOccupationsStats,
    SearchVocabs,
    StatisticsBase,
    StatisticsBinsQuery,
)
from .utils import create_bins_from_range, flatten_rdf_data, get_query_from_triplestore_v2, toggle_urls_encoding

router = APIRouter(route_class=versioned_api_route(2, 0))


def create_bins_occupations(res):
    res = StatisticsOccupationPrelimList(**{"results": res})
    data = res.dict()["results"]
    data_fin = {"id": "root", "label": "root", "count": 0, "children": []}
    data_second = []
    for idx, occ in enumerate(data):
        if occ["broader"] is None:
            if isinstance(occ["label"], list):
                occ["label"] = " / ".join(occ["label"])
            elif ">>" in occ["label"]:
                occ["label"] = occ["label"].split(" >> ")[-1]
            if data_fin["children"] is None:
                data_fin["children"] = []
            data_fin["children"].append(
                {"id": occ["id"], "label": occ["label"], "count": occ["count"], "children": None}
            )
        else:
            data_second.append(occ)
    while len(data_second) > 0:
        for idx, occ in enumerate(data_second):
            for child in data_fin["children"]:
                if child["id"] == occ["broader"][0]["id"]:
                    if isinstance(occ["label"], list):
                        occ["label"] = " / ".join(occ["label"])
                    elif ">>" in occ["label"]:
                        occ["label"] = occ["label"].split(" >> ")[-1]
                    if child["children"] is None:
                        child["children"] = []
                    child["children"].append({"id": occ["id"], "label": occ["label"], "count": occ["count"]})
                    data_second.pop(idx)
                    break
    return data_fin


@router.get(
    "/api/events/search",
    response_model=PaginatedResponseEvents,
    response_model_exclude_none=True,
    tags=["Events endpoints"],
    description="Endpoint that allows to query and retrieve entities including \
    the node history. Depending on the objects found the return object is \
        different.",
)
@cache()
async def query_events(search: SearchEvents = Depends()):
    res = get_query_from_triplestore_v2(search, "search_events_v2_1.sparql")
    res = flatten_rdf_data(res)
    pages = math.ceil(int(res[0]["count"]) / search.limit) if len(res) > 0 else 0
    count = int(res[0]["count"]) if len(res) > 0 else 0
    return {"page": search.page, "count": count, "pages": pages, "results": res}


@router.post(
    "/api/events/retrieve",
    response_model=PaginatedResponseEvents,
    response_model_exclude_none=True,
    tags=["Events endpoints"],
    description="Endpoint that allows to bulk retrieve events when IDs are known.",
)
@cache()
async def bulk_retrieve_events(
    ids: RequestID,
    query: QueryBase = Depends(),
):
    query_dict = asdict(query)
    query_dict["ids"] = ids.id
    res = get_query_from_triplestore_v2(query_dict, "bulk_retrieve_events_v2_1.sparql")
    res = flatten_rdf_data(res)
    pages = math.ceil(int(res[0]["count"]) / query.limit) if len(res) > 0 else 0
    count = int(res[0]["count"]) if len(res) > 0 else 0
    return {"page": query.page, "count": count, "pages": pages, "results": res}


@router.get(
    "/api/events/{event_id}",
    response_model=Event,
    response_model_exclude_none=True,
    tags=["Events endpoints"],
    description="Endpoint that allows to retrive any event by id.",
)
@cache()
async def retrieve_event_v2(event_id: str, query: Base = Depends()):
    try:
        event_id = toggle_urls_encoding(event_id)
    except:
        raise HTTPException(status_code=404, detail="Item not found")
    query_dict = asdict(query)
    query_dict["event_id"] = event_id
    res = get_query_from_triplestore_v2(query_dict, "get_event_v2_1.sparql")
    # res = FakeList(**{"results": flatten_rdf_data(res)})
    if len(res) == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"_results": flatten_rdf_data(res)}


@router.get(
    "/api/entities/search",
    response_model=PaginatedResponseEntities,
    response_model_exclude_none=True,
    tags=["Entities endpoints"],
    description="Endpoint that allows to query and retrieve entities including \
    the node history. Depending on the objects found the return object is \
        different.",
)
@cache()
async def query_entities(search: Search = Depends()):
    res = get_query_from_triplestore_v2(search, "search_v2_1.sparql")
    res = flatten_rdf_data(res)
    pages = math.ceil(int(res[0]["count"]) / search.limit) if len(res) > 0 else 0
    count = int(res[0]["count"]) if len(res) > 0 else 0
    return {"page": search.page, "count": count, "pages": pages, "results": res}


@router.post(
    "/api/entities/retrieve",
    response_model=PaginatedResponseEntities,
    response_model_exclude_none=True,
    tags=["Entities endpoints"],
    description="Endpoint that allows to bulk retrieve entities when IDs are known.",
)
@cache()
async def bulk_retrieve_entities(
    ids: RequestID,
    query: QueryBase = Depends(),
):
    query_dict = asdict(query)
    query_dict["ids"] = ids.id
    res = get_query_from_triplestore_v2(query_dict, "bulk_retrieve_entities_v2_1.sparql")
    res = flatten_rdf_data(res)
    pages = math.ceil(int(res[0]["count"]) / query.limit) if len(res) > 0 else 0
    count = int(res[0]["count"]) if len(res) > 0 else 0
    return {"page": query.page, "count": count, "pages": pages, "results": res}


@router.get(
    "/api/entities/{entity_id}",
    response_model=Entity,
    response_model_exclude_none=True,
    tags=["Entities endpoints"],
    description="Endpoint that allows to retrive an entity by id.",
)
@cache()
async def retrieve_entity_v2(entity_id: str, query: Base = Depends()):
    try:
        entity_id = toggle_urls_encoding(entity_id)
    except:
        raise HTTPException(status_code=404, detail="Item not found")
    query_dict = asdict(query)
    query_dict["entity_id"] = entity_id
    res = get_query_from_triplestore_v2(query_dict, "get_entity_v2_1.sparql")
    # res = FakeList(**{"results": flatten_rdf_data(res)})
    if len(res) == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"_results": flatten_rdf_data(res)}


@router.post(
    "/api/media/retrieve",
    response_model=PaginatedResponseMedia,
    response_model_exclude_none=True,
    tags=["Entities endpoints"],
    description="Endpoint that allows to bulk retrieve media objects when IDs are known.",
)
@cache()
async def bulk_retrieve_media_objects(
    ids: RequestID,
    query: QueryBase = Depends(),
):
    query_dict = asdict(query)
    query_dict["ids"] = ids.id
    # res = get_query_from_triplestore_v2(query_dict, "bulk_retrieve_entities_v2_1.sparql")
    # res = flatten_rdf_data(res)
    res = []
    for url in ids.id:
        id = toggle_urls_encoding(url)
        res.append({"id": id, "url": url})
    pages = math.ceil(len(res) / query.limit) if len(res) > 0 else 0
    count = len(res)
    return {"page": query.page, "count": count, "pages": pages, "results": res}


@router.get(
    "/api/media/{media_id}",
    response_model=MediaResource,
    response_model_exclude_none=True,
    tags=["Entities endpoints"],
    description="Endpoint that allows to retrive a media object by id.",
)
@cache()
async def retrieve_media(media_id: str, query: Base = Depends()):
    try:
        media_id_url = toggle_urls_encoding(media_id)
    except:
        raise HTTPException(status_code=404, detail="Item not found")
    # query_dict = asdict(query)
    # query_dict["media_id"] = media_id
    # res = get_query_from_triplestore_v2(query_dict, "get_entity_v2_1.sparql")
    # res = FakeList(**{"results": flatten_rdf_data(res)})
    # if len(res) == 0:
    #    raise HTTPException(status_code=404, detail="Item not found")
    return {"id": media_id, "url": media_id_url}


@router.post(
    "/api/biography/retrieve",
    response_model=PaginatedResponseBiography,
    response_model_exclude_none=True,
    tags=["Entities endpoints"],
    description="Endpoint that allows to bulk retrieve biography objects when IDs are known.",
)
@cache()
async def bulk_retrieve_biography_objects(
    ids: RequestID,
    query: QueryBase = Depends(),
):
    query_dict = asdict(query)
    query_dict["ids"] = ids.id
    res = get_query_from_triplestore_v2(query_dict, "bulk_retrieve_biographies_v2_1.sparql")
    res = flatten_rdf_data(res)
    fin = []
    for r in res:
        r_fin = {"id": toggle_urls_encoding(r["bioID"])}
        if "bioText" in r:
            r1 = requests.get(r["bioText"])
            if r1.status_code == 200:
                r_fin["text"] = r1.json()["text"]
        if "bioAbstract" in res[0]:
            r2 = requests.get(r["bioAbstract"])
            if r2.status_code == 200:
                r_fin["abstract"] = r2.json()["text"]
        fin.append(r_fin)
    pages = math.ceil(len(res) / query.limit) if len(res) > 0 else 0
    count = len(res)
    return {"page": query.page, "count": count, "pages": pages, "results": fin}


@router.get(
    "/api/biography/{biography_id}",
    response_model=Biography,
    response_model_exclude_none=True,
    tags=["Entities endpoints"],
    description="Endpoint that allows to retrive a biography object by id.",
)
@cache()
async def retrieve_biography(biography_id: str, query: Base = Depends()):
    try:
        biography_id_decoded = toggle_urls_encoding(biography_id)
    except:
        raise HTTPException(status_code=404, detail="Item not found")
    query_dict = asdict(query)
    query_dict["bioID"] = biography_id_decoded
    res = get_query_from_triplestore_v2(query_dict, "get_biography_v2_1.sparql")
    # res = FakeList(**{"results": flatten_rdf_data(res)})
    if len(res) == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    fin = {"id": biography_id}
    if "bioText" in res[0]:
        r1 = requests.get(res[0]["bioText"]["value"])
        if r1.status_code == 200:
            fin["text"] = r1.json()["text"]
    if "bioAbstract" in res[0]:
        r2 = requests.get(res[0]["bioAbstract"]["value"])
        if r2.status_code == 200:
            fin["abstract"] = r2.json()["text"]
    return fin


@router.get(
    "/api/vocabularies/occupations/search",
    response_model=PaginatedResponseVocabularyEntries,
    response_model_exclude_none=True,
    tags=["Vocabulary endpoints"],
    description="Endpoint that allows to query and retrieve occupation concepts.",
)
@cache()
async def query_occupations(search: SearchVocabs = Depends()):
    res = get_query_from_triplestore_v2(search, "occupation_v2_1.sparql")
    res = flatten_rdf_data(res)
    pages = math.ceil(int(res[0]["count"]) / search.limit) if len(res) > 0 else 0
    count = int(res[0]["count"]) if len(res) > 0 else 0
    return {"page": search.page, "count": count, "pages": pages, "results": res}


@router.get(
    "/api/vocabularies/occupations/{occupation_id}",
    response_model=VocabularyEntry,
    response_model_exclude_none=True,
    tags=["Vocabulary endpoints"],
    description="Endpoint that allows to retrive any occupation by id.",
)
@cache()
async def retrieve_occupation_v2(occupation_id: str, query: Base = Depends()):
    # res = FakeList(**{"results": flatten_rdf_data(res)})
    try:
        occupation_id = toggle_urls_encoding(occupation_id)
    except:
        raise HTTPException(status_code=404, detail="Item not found")
    query_dict = asdict(query)
    query_dict["occupation_id"] = occupation_id
    res = get_query_from_triplestore_v2({"occupation_id": occupation_id}, "occupation_retrieve_v2_1.sparql")
    # res = FakeList(**{"results": flatten_rdf_data(res)})
    if len(res) == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"_results": flatten_rdf_data(res)}


@router.post(
    "/api/vocabularies/occupations/retrieve",
    response_model=PaginatedResponseVocabularyEntries,
    response_model_exclude_none=True,
    tags=["Vocabulary endpoints"],
    description="Endpoint that allows to bulk retrieve occupations when IDs are known.",
)
@cache()
async def bulk_retrieve_voc_occupations(
    ids: RequestID,
    query: QueryBase = Depends(),
):
    query_dict = asdict(query)
    query_dict["ids"] = ids.id
    res = get_query_from_triplestore_v2(query_dict, "bulk_retrieve_occupations_v2_1.sparql")
    res = flatten_rdf_data(res)
    pages = math.ceil(int(res[0]["count"]) / query.limit) if len(res) > 0 else 0
    count = int(res[0]["count"]) if len(res) > 0 else 0
    return {"page": query.page, "count": count, "pages": pages, "results": res}


@router.get(
    "/api/vocabularies/roles/search",
    response_model=PaginatedResponseVocabularyEntries,
    response_model_exclude_none=True,
    tags=["Vocabulary endpoints"],
    description="Endpoint that allows to query and retrieve event roles.",
)
@cache()
async def query_event_roles(search: SearchVocabs = Depends()):
    res = get_query_from_triplestore_v2(search, "event_role_v2_1.sparql")
    res = flatten_rdf_data(res)
    pages = math.ceil(int(res[0]["count"]) / search.limit) if len(res) > 0 else 0
    count = int(res[0]["count"]) if len(res) > 0 else 0
    return {"page": search.page, "count": count, "pages": pages, "results": res}


@router.get(
    "/api/vocabularies/roles/{event_role_id}",
    response_model=VocabularyEntry,
    response_model_exclude_none=True,
    tags=["Vocabulary endpoints"],
    description="Endpoint that allows to retrive any roles by id.",
)
@cache()
async def retrieve_event_role_v2(event_role_id: str, query: Base = Depends()):
    try:
        event_role_id = toggle_urls_encoding(event_role_id)
    except:
        raise HTTPException(status_code=404, detail="Item not found")
    if event_role_id == "http://www.cidoc-crm.org/cidoc-crm/P7_took_place_at":
        return {"_results": [{"vocabulary": event_role_id, "vocabulary_label": "took place at"}]}
    query_dict = asdict(query)
    query_dict["event_role_id"] = event_role_id
    res = get_query_from_triplestore_v2(query_dict, "event_role_retrieve_v2_1.sparql")
    # res = FakeList(**{"results": flatten_rdf_data(res)})
    if len(res) == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    # res = FakeList(**{"results": flatten_rdf_data(res)})
    return {"_results": flatten_rdf_data(res)}


@router.post(
    "/api/vocabularies/roles/retrieve",
    response_model=PaginatedResponseVocabularyEntries,
    response_model_exclude_none=True,
    tags=["Vocabulary endpoints"],
    description="Endpoint that allows to bulk retrieve event roles when IDs are known.",
)
@cache()
async def bulk_retrieve_voc_event_roles(
    ids: RequestID,
    query: QueryBase = Depends(),
):
    query_dict = asdict(query)
    query_dict["ids"] = ids.id
    res = get_query_from_triplestore_v2(query_dict, "bulk_retrieve_event_role_v2_1.sparql")
    res = flatten_rdf_data(res)
    pages = math.ceil(int(res[0]["count"]) / query.limit) if len(res) > 0 else 0
    count = int(res[0]["count"]) if len(res) > 0 else 0
    return {"page": query.page, "count": count, "pages": pages, "results": res}


@router.get(
    "/api/vocabularies/event_kinds/search",
    response_model=PaginatedResponseVocabularyEntries,
    response_model_exclude_none=True,
    tags=["Vocabulary endpoints"],
    description="Endpoint that allows to query and retrieve event kinds.",
)
@cache()
async def query_event_kind(search: SearchEventKindVocab = Depends()):
    res = get_query_from_triplestore_v2(search, "event_kind_v2_1.sparql")
    res = flatten_rdf_data(res)
    pages = math.ceil(int(res[0]["count"]) / search.limit) if len(res) > 0 else 0
    count = int(res[0]["count"]) if len(res) > 0 else 0
    return {"page": search.page, "count": count, "pages": pages, "results": res}


@router.get(
    "/api/vocabularies/event_kinds/{event_kind_id}",
    response_model=VocabularyEntry,
    response_model_exclude_none=True,
    tags=["Vocabulary endpoints"],
    description="Endpoint that allows to retrive any event kinds by id.",
)
@cache()
async def retrieve_event_kind_v2(event_kind_id: str, query: Base = Depends()):
    try:
        event_kind_id = toggle_urls_encoding(event_kind_id)
    except:
        raise HTTPException(status_code=404, detail="Item not found")
    query_dict = asdict(query)
    query_dict["event_kind_id"] = event_kind_id
    res = get_query_from_triplestore_v2(query_dict, "event_kind_retrieve_v2_1.sparql")
    # res = FakeList(**{"results": flatten_rdf_data(res)})
    if len(res) == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"_results": flatten_rdf_data(res)}


@router.post(
    "/api/vocabularies/event_kinds/retrieve",
    response_model=PaginatedResponseVocabularyEntries,
    response_model_exclude_none=True,
    tags=["Vocabulary endpoints"],
    description="Endpoint that allows to bulk retrieve event kinds when IDs are known.",
)
@cache()
async def bulk_retrieve_voc_event_kinds(
    ids: RequestID,
    query: QueryBase = Depends(),
):
    query_dict = asdict(query)
    query_dict["ids"] = ids.id
    res = get_query_from_triplestore_v2(query_dict, "bulk_retrieve_event_kind_v2_1.sparql")
    res = flatten_rdf_data(res)
    pages = math.ceil(int(res[0]["count"]) / query.limit) if len(res) > 0 else 0
    count = int(res[0]["count"]) if len(res) > 0 else 0
    return {"page": query.page, "count": count, "pages": pages, "results": res}


@router.get(
    "/api/statistics/occupations/search",
    response_model=StatisticsOccupationReturn,
    response_model_exclude_none=True,
    tags=["Statistics"],
    description="Endpoint that returns counts of the occupations",
)
@cache()
async def statistics_occupations(search: SearchOccupationsStats = Depends()):
    res = get_query_from_triplestore_v2(search, "statistics_occupation_v2_1.sparql")
    res = flatten_rdf_data(res)
    data_fin = create_bins_occupations(res)
    return {"tree": data_fin}


@router.post(
    "/api/statistics/occupations/bulk",
    response_model=StatisticsOccupationReturn,
    response_model_exclude_none=True,
    tags=["Statistics"],
    description="Endpoint that returns counts of the occupations for known IDs",
)
@cache()
async def statistics_occupations_bulk(ids: RequestID):
    res = get_query_from_triplestore_v2({"ids": ids.id}, "statistics_occupation_v2_1.sparql")
    res = flatten_rdf_data(res)
    data_fin = create_bins_occupations(res)
    return {"tree": data_fin}


@router.get(
    "/api/statistics/death_dates/search",
    response_model=StatisticsBins,
    response_model_exclude_none=True,
    tags=["Statistics"],
    description="Endpoint that returns counts in bins for date of deaths",
)
@cache()
async def statistics_death(search: StatisticsBase = Depends()):
    res = get_query_from_triplestore_v2(search, "statistics_deathdate_v2_1.sparql")
    res = flatten_rdf_data(res)
    for idx, v in enumerate(res):
        if not isinstance(res[idx]["date"], datetime.datetime):
            res[idx]["date"] = dateutil.parser.parse(res[idx]["date"][:10])
    bins = create_bins_from_range(res[0]["date"], res[-1]["date"], search.bins)
    for idx, b in enumerate(bins):
        for date in res:
            if b["values"][0] <= date["date"] <= b["values"][1]:
                b["count"] += date["count"]
        bins[idx] = b
    return {"bins": bins}


@router.post(
    "/api/statistics/death_dates/bulk",
    response_model=StatisticsBins,
    response_model_exclude_none=True,
    tags=["Statistics"],
    description="Endpoint that returns counts in bins for date of death of known IDs",
)
@cache()
async def statistics_death_bulk(ids: RequestID, search: StatisticsBinsQuery = Depends()):
    res = get_query_from_triplestore_v2({"ids": ids.id}, "statistics_deathdate_v2_1.sparql")
    if len(res) == 0:
        raise HTTPException(status_code=404, detail="Items not found")
    res = flatten_rdf_data(res)
    for idx, v in enumerate(res):
        if not isinstance(res[idx]["date"], datetime.datetime):
            res[idx]["date"] = dateutil.parser.parse(res[idx]["date"][:10])
    bins = create_bins_from_range(res[0]["date"], res[-1]["date"], search.bins)
    for idx, b in enumerate(bins):
        for date in res:
            if b["values"][0] <= date["date"] <= b["values"][1]:
                b["count"] += date["count"]
        bins[idx] = b
    return {"bins": bins}


@router.get(
    "/api/statistics/birth_dates/search",
    response_model=StatisticsBins,
    response_model_exclude_none=True,
    tags=["Statistics"],
    description="Endpoint that returns counts in bins for date of birth",
)
@cache()
async def statistics_birth(search: StatisticsBase = Depends()):
    res = get_query_from_triplestore_v2(search, "statistics_birthdate_v2_1.sparql")
    res = flatten_rdf_data(res)
    for idx, v in enumerate(res):
        if not isinstance(res[idx]["date"], datetime.datetime):
            res[idx]["date"] = dateutil.parser.parse(res[idx]["date"][:10])
    bins = create_bins_from_range(res[0]["date"], res[-1]["date"], search.bins)
    for idx, b in enumerate(bins):
        for date in res:
            if b["values"][0] <= date["date"] <= b["values"][1]:
                b["count"] += date["count"]
        bins[idx] = b
    return {"bins": bins}


@router.post(
    "/api/statistics/birth_dates/bulk",
    response_model=StatisticsBins,
    response_model_exclude_none=True,
    tags=["Statistics"],
    description="Endpoint that returns counts in bins for date of birth of known IDs",
)
@cache()
async def statistics_birth_bulk(ids: RequestID, search: StatisticsBinsQuery = Depends()):
    res = get_query_from_triplestore_v2({"ids": ids.id}, "statistics_birthdate_v2_1.sparql")
    if len(res) == 0:
        raise HTTPException(status_code=404, detail="Items not found")
    res = flatten_rdf_data(res)
    for idx, v in enumerate(res):
        if not isinstance(res[idx]["date"], datetime.datetime):
            res[idx]["date"] = dateutil.parser.parse(res[idx]["date"][:10])
    bins = create_bins_from_range(res[0]["date"], res[-1]["date"], search.bins)
    for idx, b in enumerate(bins):
        for date in res:
            if b["values"][0] <= date["date"] <= b["values"][1]:
                b["count"] += date["count"]
        bins[idx] = b
    return {"bins": bins}


@router.get(
    "/api/statistics/entity_types/search",
    response_model=StatsEntityType,
    response_model_exclude_none=True,
    tags=["Statistics"],
    description="Endpoint that returns counts of entity types",
)
@cache()
async def statistics_entity_type(search: Search = Depends()):
    res = get_query_from_triplestore_v2(search, "statistics_entity_types_v2_1.sparql")
    res = flatten_rdf_data(res)
    res_fin = {}
    for ent in res:
        res_fin[ent["entityTypeLabel"]] = ent["count"]
    return res_fin


@router.post(
    "/api/statistics/entity_types/bulk",
    response_model=StatsEntityType,
    response_model_exclude_none=True,
    tags=["Statistics"],
    description="Endpoint that returns counts of entity types",
)
@cache()
async def statistics_entity_type_bulk(ids: RequestID):
    res = get_query_from_triplestore_v2({"ids": ids.id}, "statistics_entity_types_v2_1.sparql")
    res = flatten_rdf_data(res)
    res_fin = {}
    for ent in res:
        res_fin[ent["entityTypeLabel"]] = ent["count"]
    return res_fin