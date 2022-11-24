import math
from fastapi import APIRouter, Depends

from fastapi_versioning import version, versioned_api_route
from intavia_backend.models_v2 import Entity, FakeList
from intavia_backend.query_parameters import Entity_Retrieve
from .utils import flatten_rdf_data, get_query_from_triplestore_v2, toggle_urls_encoding

router = APIRouter(route_class=versioned_api_route(2, 0))


@router.get(
    "/api/entity/{entity_id}",
    response_model=Entity,
    response_model_exclude_none=True,
    tags=["Entyties endpoints"],
    description="Endpoint that allows to retrive an entity by id.",
)
async def retrieve_entity_v2(entity_id: str):
    res = get_query_from_triplestore_v2({"entity_id": toggle_urls_encoding(entity_id)}, "get_entity_v2_1.sparql")
    # res = FakeList(**{"results": flatten_rdf_data(res)})
    return {"_results": flatten_rdf_data(res)}
