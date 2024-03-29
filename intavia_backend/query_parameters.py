import copy
import dataclasses
from enum import Enum
import json
from typing import Any
import typing
from fastapi import Query
from pydantic import BaseModel, HttpUrl, NonNegativeInt, PositiveInt
from dateutil.parser import *
import datetime
import base64
import hashlib


class DatasetsEnum(str, Enum):
    APIS = "https://apis.acdh.oeaw.ac.at/data"
    BSampo = "http://ldf.fi/nbf/data"
    BNet = "http://data.biographynet.nl/"
    SBI = "http://www.intavia.eu/sbi"


class GenderqueryEnum(str, Enum):
    male = "male"
    female = "female"
    unknown = "unknown"


class EntityTypesEnum(str, Enum):
    person = "person"
    group = "group"

    def get_rdf_uri(self) -> str:
        map = {"person": "idmcore:Person_Proxy", "group": "idmcore:Group"}
        return map[self.name]


@dataclasses.dataclass(kw_only=True)
class Base:

    pass


@dataclasses.dataclass(kw_only=True)
class QueryBase:
    page: PositiveInt = Query(default=1, gte=1)
    limit: int = Query(default=50, le=1000, gte=1)
    _offset: int = Query(default=0, include_in_schema=False)


@dataclasses.dataclass(kw_only=True)
class Search_Base:
    q: str = Query(default=None, max_length=200, description="Searches across labels of all entity proxies")
    occupation: str = Query(default=None, max_length=200, description="Searches the labels of the Occupations")
    gender: GenderqueryEnum = Query(default=None, description="Filters Persons according to gender")
    gender_id: HttpUrl = Query(
        default=None, description="Filters Persons according to gender. Uses URIs rather than the enum."
    )
    bornBefore: str | datetime.datetime = Query(
        default=None, description="Filters for Persons born before a certain date"
    )
    bornAfter: str | datetime.datetime = Query(
        default=None, description="Filters for Persons born after a certain date"
    )
    diedAfter: str | datetime.datetime = Query(
        default=None, description="Filters for Persons died after a certain date"
    )
    diedBefore: str | datetime.datetime = Query(
        default=None, description="Filters for Persons died before a certain date"
    )
    occupations_id: typing.List[HttpUrl] | None = Query(
        default=None, description="filters for persons with occupations using URIs"
    )
    relatedPlace: str = Query(default=None, description="Filter for places related to the searched entity")
    relatedPlaces_id: typing.List[HttpUrl] = Query(
        default=None, description="Filter for places related to the searched entity using URIs"
    )

    def __post_init__(self):
        if hasattr(self, "page"):
            self._offset = (self.page - 1) * self.limit
        if self.bornBefore is not None:
            self.__setattr__("bornBefore", parse(self.bornBefore).strftime("%Y-%m-%dT00:00:00"))
        if self.bornAfter is not None:
            self.__setattr__("bornAfter", parse(self.bornAfter).strftime("%Y-%m-%dT00:00:00"))
        if self.diedBefore is not None:
            self.__setattr__("diedBefore", parse(self.diedBefore).strftime("%Y-%m-%dT00:00:00"))
        if self.diedAfter is not None:
            self.__setattr__("diedAfter", parse(self.diedAfter).strftime("%Y-%m-%dT00:00:00"))


@dataclasses.dataclass(kw_only=True)
class Search(Search_Base, QueryBase, Base):
    datasets: list[DatasetsEnum] = Query(
        description="Select datasets to limit query to",
        default=[DatasetsEnum.APIS, DatasetsEnum.BSampo, DatasetsEnum.BNet, DatasetsEnum.SBI],
    )
    kind: list[EntityTypesEnum] = Query(default=None, description="Limit Query to entity type.")
    includeEvents: bool = Query(default=False, description="Whether to include data on events")


@dataclasses.dataclass(kw_only=True)
class SearchVocabs(QueryBase, Base):
    q: str = Query(default=None, description="Query for a label in the Vocabulary")


@dataclasses.dataclass(kw_only=True)
class Entity_Retrieve(QueryBase, Base):
    ids: typing.List[HttpUrl] = Query(description="List of IDs to retrieve.")
    includeEvents: bool = Query(default=False, description="Whether to include data on events")


@dataclasses.dataclass(kw_only=True)
class StatisticsBase(Search_Base, Base):
    bins: PositiveInt = 10


class ReconTypeEnum(str, Enum):
    Person = "Person"
    Group = "Group"
    Place = "Place"

    def get_rdf_uri(self) -> str:
        map = {
            "Person": "<http://www.intavia.eu/idm-core/Provided_Person>",
            "Group": "<http://www.cidoc-crm.org/cidoc-crm/E74_Group>",
            "Place": "<http://www.cidoc-crm.org/cidoc-crm/E53_Place>",
        }
        return map[self.name]


@dataclasses.dataclass(kw_only=True)
class ReconQuery(Base):
    query: str
    limit: int
    type: ReconTypeEnum = Query(default=ReconTypeEnum.Person, description="Filter for returned entity type.")


@dataclasses.dataclass(kw_only=True)
class ReconQueries(Base):
    queries: list[ReconQuery]


@dataclasses.dataclass(kw_only=True)
class ReconQueryBatch(Base):
    queries: ReconQueries
