import math
from fastapi import APIRouter, Depends

from fastapi_versioning import version, versioned_api_route
from intavia_backend.models_v1 import PaginatedResponseEntities
from intavia_backend.query_parameters import Entity_Retrieve
from .utils import flatten_rdf_data, get_query_from_triplestore_v2

router = APIRouter(route_class=versioned_api_route(2, 0))


@router.get(
    "/api/entities/id",
    response_model=PaginatedResponseEntities,
    response_model_exclude_none=True,
    tags=["Enities endpoints"],
    description="Endpoint that allows to retrive an entity by id.",
)
async def retrieve_entity_v2(search: Entity_Retrieve = Depends()):
    res = get_query_from_triplestore_v2(search, "get_entity_v1.sparql")
    pages = math.ceil(int(res[0]["_count"]) / search.limit) if len(res) > 0 else 0
    count = int(res[0]["_count"]) if len(res) > 0 else 0
    return {"page": search.page, "count": count, "pages": pages, "results": flatten_rdf_data(res)}
