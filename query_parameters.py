from enum import Enum
import json
from typing import Any
import typing
from fastapi import Query
from pydantic import BaseModel, HttpUrl, NonNegativeInt, PositiveInt
from dateutil.parser import *
import datetime
from dataclasses import dataclass, asdict


class GenderqueryEnum(str, Enum):
    male = "male"
    female = "female"
    unknown = "unknown"


class EntityTypesEnum(str, Enum):
    person = "person"
    group = "group"

    def get_rdf_uri(self) -> str:
        map = {
            "person": "idmcore:Person_Proxy",
            "group": "crm:E74_Group"
        }
        return map[self.name]


@dataclass(kw_only=True)
class QueryBase:
    page: PositiveInt = Query(default=1, gte=1)
    limit: int = Query(default=50, le=1000, gte=1)

    def get_cache_str(self):
        d1 = asdict(self)
        d1.pop("page", None)
        d1.pop("limit", None)
        return str(hash(json.dumps(d1, sort_keys=True)))

@dataclass(kw_only=True)
class Search(QueryBase):
    q: str = Query(default=None,
                   max_length=200,
                   description="Searches across labels of all entity proxies")
    entityType: EntityTypesEnum = Query(default=None, description="Limit Query to entity type.")
    includeEvents: bool = Query(default=False, description="Whether to include data on events")
    occupation: str = Query(default=None,
    max_length=200,
    description="Searches the labels of the Occupations")
    gender: GenderqueryEnum = Query(default=None, description="Filters Persons according to gender")
    bornBefore: str|datetime.datetime = Query(default=None, description="Filters for Persons born before a certain date")
    bornAfter: str|datetime.datetime = Query(default=None, description="Filters for Persons born after a certain date")
    diedAfter: str|datetime.datetime = Query(default=None, description="Filters for Persons died after a certain date")
    diedBefore: str|datetime.datetime = Query(default=None, description="Filters for Persons died before a certain date")
    occupations_id: typing.List[HttpUrl]|None = Query(default=None, description="filters for persons with occupations using URIs")

    def __post_init__(self):
        if self.bornBefore is not None:
            self.__setattr__('bornBefore', parse(self.bornBefore).strftime('%Y-%m-%dT00:00:00'))
        if self.bornAfter is not None:
            self.__setattr__('bornAfter', parse(self.bornAfter).strftime('%Y-%m-%dT00:00:00'))
        if self.diedBefore is not None:
            self.__setattr__('diedBefore', parse(self.diedBefore).strftime('%Y-%m-%dT00:00:00'))
        if self.diedAfter is not None:
            self.__setattr__('diedAfter', parse(self.diedAfter).strftime('%Y-%m-%dT00:00:00'))

@dataclass(kw_only=True)
class SearchVocabs(QueryBase):
    q: str = Query(default = None, description="Query for a label in the Vocabulary")