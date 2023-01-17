from dataclasses import asdict
import math
from fastapi import APIRouter, Depends, HTTPException

from fastapi_versioning import version, versioned_api_route
from intavia_backend.models_v2 import (
    Entity,
    Event,
    PaginatedResponseEntities,
    PaginatedResponseEvents,
    PaginatedResponseVocabularyEntries,
    VocabularyEntry,
)
from intavia_backend.query_parameters_v2 import (
    Entity_Retrieve,
    QueryBase,
    RequestID,
    Search,
    SearchEvents,
    SearchVocabs,
)
from .utils import flatten_rdf_data, get_query_from_triplestore_v2, toggle_urls_encoding

router = APIRouter(route_class=versioned_api_route(2, 0))


@router.get(
    "/api/event/search",
    response_model=PaginatedResponseEvents,
    response_model_exclude_none=True,
    tags=["Events endpoints"],
    description="Endpoint that allows to query and retrieve entities including \
    the node history. Depending on the objects found the return object is \
        different.",
)
async def query_events(search: SearchEvents = Depends()):
    res = get_query_from_triplestore_v2(search, "search_events_v2_1.sparql")
    res = flatten_rdf_data(res)
    pages = math.ceil(int(res[0]["count"]) / search.limit) if len(res) > 0 else 0
    count = int(res[0]["count"]) if len(res) > 0 else 0
    return {"page": search.page, "count": count, "pages": pages, "results": res}


@router.post(
    "/api/event/retrieve",
    response_model=PaginatedResponseEvents,
    response_model_exclude_none=True,
    tags=["Events endpoints"],
    description="Endpoint that allows to bulk retrieve events when IDs are known.",
)
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
    "/api/event/{event_id}",
    response_model=Event,
    response_model_exclude_none=True,
    tags=["Events endpoints"],
    description="Endpoint that allows to retrive any event by id.",
)
async def retrieve_event_v2(event_id: str):
    try:
        event_id = toggle_urls_encoding(event_id)
    except:
        raise HTTPException(status_code=404, detail="Item not found")
    res = get_query_from_triplestore_v2({"event_id": event_id}, "get_entity_v2_1.sparql")
    # res = FakeList(**{"results": flatten_rdf_data(res)})
    if len(res) == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"_results": flatten_rdf_data(res)}


@router.get(
    "/api/entity/{entity_id}",
    response_model=Entity,
    response_model_exclude_none=True,
    tags=["Entities endpoints"],
    description="Endpoint that allows to retrive an entity by id.",
)
async def retrieve_entity_v2(entity_id: str):
    try:
        entity_id = toggle_urls_encoding(entity_id)
    except:
        raise HTTPException(status_code=404, detail="Item not found")
    res = get_query_from_triplestore_v2({"entity_id": entity_id}, "get_entity_v2_1.sparql")
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
    "/api/vocabularies/occupations/search",
    response_model=PaginatedResponseVocabularyEntries,
    response_model_exclude_none=True,
    tags=["Vocabulary endpoints"],
    description="Endpoint that allows to query and retrieve occupation concepts.",
)
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
async def retrieve_occupation_v2(occupation_id: str):
    # res = FakeList(**{"results": flatten_rdf_data(res)})
    try:
        occupation_id = toggle_urls_encoding(occupation_id)
    except:
        raise HTTPException(status_code=404, detail="Item not found")
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
    "/api/vocabularies/role/search",
    response_model=PaginatedResponseVocabularyEntries,
    response_model_exclude_none=True,
    tags=["Vocabulary endpoints"],
    description="Endpoint that allows to query and retrieve event roles.",
)
async def query_event_roles(search: SearchVocabs = Depends()):
    res = get_query_from_triplestore_v2(search, "event_role_v2_1.sparql")
    res = flatten_rdf_data(res)
    pages = math.ceil(int(res[0]["count"]) / search.limit) if len(res) > 0 else 0
    count = int(res[0]["count"]) if len(res) > 0 else 0
    return {"page": search.page, "count": count, "pages": pages, "results": res}


@router.get(
    "/api/vocabularies/role/{event_role_id}",
    response_model=VocabularyEntry,
    response_model_exclude_none=True,
    tags=["Vocabulary endpoints"],
    description="Endpoint that allows to retrive any roles by id.",
)
async def retrieve_event_role_v2(event_role_id: str):
    try:
        event_role_id = toggle_urls_encoding(event_role_id)
    except:
        raise HTTPException(status_code=404, detail="Item not found")
    if event_role_id == "http://www.cidoc-crm.org/cidoc-crm/P7_took_place_at":
        return {"_results": [{"vocabulary": event_role_id, "vocabulary_label": "took place at"}]}
    res = get_query_from_triplestore_v2({"event_role_id": event_role_id}, "event_role_retrieve_v2_1.sparql")
    # res = FakeList(**{"results": flatten_rdf_data(res)})
    if len(res) == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    # res = FakeList(**{"results": flatten_rdf_data(res)})
    return {"_results": flatten_rdf_data(res)}


@router.post(
    "/api/vocabularies/role/retrieve",
    response_model=PaginatedResponseVocabularyEntries,
    response_model_exclude_none=True,
    tags=["Vocabulary endpoints"],
    description="Endpoint that allows to bulk retrieve event roles when IDs are known.",
)
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
    "/api/vocabularies/event_kind/search",
    response_model=PaginatedResponseVocabularyEntries,
    response_model_exclude_none=True,
    tags=["Vocabulary endpoints"],
    description="Endpoint that allows to query and retrieve event kinds.",
)
async def query_event_kind(search: SearchVocabs = Depends()):
    res = get_query_from_triplestore_v2(search, "event_kind_v2_1.sparql")
    res = flatten_rdf_data(res)
    pages = math.ceil(int(res[0]["count"]) / search.limit) if len(res) > 0 else 0
    count = int(res[0]["count"]) if len(res) > 0 else 0
    return {"page": search.page, "count": count, "pages": pages, "results": res}


@router.get(
    "/api/vocabularies/event_kind/{event_kind_id}",
    response_model=VocabularyEntry,
    response_model_exclude_none=True,
    tags=["Vocabulary endpoints"],
    description="Endpoint that allows to retrive any event kinds by id.",
)
async def retrieve_event_kind_v2(event_kind_id: str):
    try:
        event_kind_id = toggle_urls_encoding(event_kind_id)
    except:
        raise HTTPException(status_code=404, detail="Item not found")
    res = get_query_from_triplestore_v2({"event_kind_id": event_kind_id}, "event_kind_retrieve_v2_1.sparql")
    # res = FakeList(**{"results": flatten_rdf_data(res)})
    if len(res) == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"_results": flatten_rdf_data(res)}


@router.post(
    "/api/vocabularies/event_kind/retrieve",
    response_model=PaginatedResponseVocabularyEntries,
    response_model_exclude_none=True,
    tags=["Vocabulary endpoints"],
    description="Endpoint that allows to bulk retrieve event kinds when IDs are known.",
)
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
