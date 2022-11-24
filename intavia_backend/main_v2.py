import math
from fastapi import APIRouter, Depends

from fastapi_versioning import version, versioned_api_route
from intavia_backend.models_v2 import Entity, PaginatedResponseEntities
from intavia_backend.query_parameters_v2 import Entity_Retrieve, Search
from .utils import flatten_rdf_data, get_query_from_triplestore_v2, toggle_urls_encoding

router = APIRouter(route_class=versioned_api_route(2, 0))


@router.get(
    "/api/entity/{entity_id}",
    response_model=Entity,
    response_model_exclude_none=True,
    tags=["Entities endpoints"],
    description="Endpoint that allows to retrive an entity by id.",
)
async def retrieve_entity_v2(entity_id: str):
    res = get_query_from_triplestore_v2({"entity_id": toggle_urls_encoding(entity_id)}, "get_entity_v2_1.sparql")
    # res = FakeList(**{"results": flatten_rdf_data(res)})
    return {"_results": flatten_rdf_data(res)}


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
    res = get_query_from_triplestore_v2(search, "search_v2_1.sparql")
    res = flatten_rdf_data(res)
    pages = math.ceil(int(res[0]["count"]) / search.limit) if len(res) > 0 else 0
    count = int(res[0]["count"]) if len(res) > 0 else 0
    return {"page": search.page, "count": count, "pages": pages, "results": res}
