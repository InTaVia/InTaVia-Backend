import dataclasses
from enum import Enum
import typing
from fastapi import Query
from pydantic import BaseModel, HttpUrl, PositiveInt
from dateutil.parser import parse
import datetime
import base64
from .models_v2 import EntityType


def toggle_urls_encoding(url):
    """Toggles the encoding of the url.

    Args:
        url (str): The url

    Returns:
        str: The encoded/decoded url
    """
    if "/v2/api" in url:
        return base64.urlsafe_b64decode(url.split("/")[-1].encode("utf-8")).decode(
            "utf-8"
        )
    elif "/" in url:
        return base64.urlsafe_b64encode(url.encode("utf-8")).decode("utf-8")
    else:
        return base64.urlsafe_b64decode(url.encode("utf-8")).decode("utf-8")


class DatasetsEnum(str, Enum):
    APIS = "http://apis.acdh.oeaw.ac.at/data/v5"
    BSampo = "http://ldf.fi/nbf/data"
    BNet = "http://data.biographynet.nl"
    SBI = "http://www.intavia.eu/sbi"
    CHO_test = "http://data.acdh.oeaw.ac.at/intavia/cho/v6"
    CHO_test2 = "http://data.acdh.oeaw.ac.at/intavia/cho/v1"
    EDM_test = "http://edm-enrich2023-06-14.intavia.eu"


class GenderqueryEnum(str, Enum):
    male = "male"
    female = "female"
    unknown = "unknown"


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
class Base:
    datasets: list[DatasetsEnum] = Query(
        description="Select datasets to limit query to",
        default=[
            DatasetsEnum.APIS,
            DatasetsEnum.BSampo,
            DatasetsEnum.SBI,
            DatasetsEnum.CHO_test,
            DatasetsEnum.BNet,
        ],
    )


@dataclasses.dataclass(kw_only=True)
class QueryBase(Base):
    page: PositiveInt = Query(default=1, gte=1)
    limit: int = Query(default=50, le=1000, gte=1)
    _offset: int = Query(default=0, include_in_schema=False)

    def __post_init__(self):
        if hasattr(self, "page"):
            self._offset = (self.page - 1) * self.limit


@dataclasses.dataclass(kw_only=True)
class SearchEventsBase:
    q: str = Query(
        default=None,
        max_length=200,
        description="Searches across labels of all events. When not using quotes, the query will be wildcarded. When using quotes, \
            the query will be exact. Keep in mind that the wildcards will be added right and left of the query (wildcards are not added per token).",
    )
    related_entities: str = Query(
        default=None, max_length=200, description="Searches labels of related entities"
    )
    related_entities_id: typing.List[str] = Query(
        default=None, description="Searches related entities using IDs"
    )
    role: str = Query(
        default=None, max_length=200, description="Searches labels of roles"
    )
    role_id: typing.List[str] = Query(
        default=None, description="Searches roles using IDs"
    )
    event_kind: str = Query(
        default=None, max_length=200, description="Searches labels of event kinds"
    )
    event_kind_id: typing.List[str] = Query(
        default=None, description="Searches event kinds using IDs"
    )

    def __post_init__(self):
        super().__post_init__()
        if self.related_entities_id is not None:
            self.__setattr__(
                "related_entities_id",
                [toggle_urls_encoding(x) for x in self.related_entities_id],
            )
        if self.role_id is not None:
            self.__setattr__("role_id", [toggle_urls_encoding(x) for x in self.role_id])
        if self.event_kind_id is not None:
            self.__setattr__(
                "event_kind_id", [toggle_urls_encoding(x) for x in self.event_kind_id]
            )
        if self.q is not None:
            if not self.q.startswith('"') and not self.q.endswith('"'):
                self.__setattr__("q", f"*{self.q}*")
            else:
                self.__setattr__("q", self.q[1:-1])


@dataclasses.dataclass(kw_only=True)
class Search_Base:
    q: str = Query(
        default=None,
        max_length=200,
        description="Searches across labels of all entity proxies. When not using quotes, the query will be wildcarded. When using quotes, \
            the query will be exact. Keep in mind that the wildcards will be added right and left of the query (wildcards are not added per token).",
    )
    occupation: str = Query(
        default=None,
        max_length=200,
        description="Searches the labels of the Occupations",
    )
    gender: GenderqueryEnum = Query(
        default=None, description="Filters Persons according to gender"
    )
    gender_id: HttpUrl = Query(
        default=None,
        description="Filters Persons according to gender. Uses URIs rather than the enum.",
    )
    born_before: str | datetime.datetime = Query(
        default=None, description="Filters for Persons born before a certain date"
    )
    born_after: str | datetime.datetime = Query(
        default=None, description="Filters for Persons born after a certain date"
    )
    died_after: str | datetime.datetime = Query(
        default=None, description="Filters for Persons died after a certain date"
    )
    died_before: str | datetime.datetime = Query(
        default=None, description="Filters for Persons died before a certain date"
    )
    occupations_id: typing.List[str] | None = Query(
        default=None, description="filters for persons with occupations using IDs"
    )
    related_entity: str = Query(
        default=None, description="Filter for entities related to the searched entity"
    )
    related_entities_id: typing.List[str] = Query(
        default=None,
        description="Filter for entities related to the searched entity using URIs",
    )
    event_role: str = Query(
        default=None,
        description="Filter for event roles related to the searched entity",
    )
    event_roles_id: typing.List[str] = Query(
        default=None,
        description="Filter for event roles related to the searched entity using IDs",
    )

    def __post_init__(self):
        super().__post_init__()
        if self.born_before is not None:
            self.__setattr__(
                "born_before", parse(self.born_before).strftime("%Y-%m-%dT00:00:00")
            )
        if self.born_after is not None:
            self.__setattr__(
                "born_after", parse(self.born_after).strftime("%Y-%m-%dT00:00:00")
            )
        if self.died_before is not None:
            self.__setattr__(
                "died_before", parse(self.died_before).strftime("%Y-%m-%dT00:00:00")
            )
        if self.died_after is not None:
            self.__setattr__(
                "died_after", parse(self.died_after).strftime("%Y-%m-%dT00:00:00")
            )
        if self.occupations_id is not None:
            self.__setattr__(
                "occupations_id", [toggle_urls_encoding(x) for x in self.occupations_id]
            )
        if self.related_entities_id is not None:
            self.__setattr__(
                "related_entities_id",
                [toggle_urls_encoding(x) for x in self.related_entities_id],
            )
        if self.event_roles_id is not None:
            self.__setattr__(
                "event_roles_id", [toggle_urls_encoding(x) for x in self.event_roles_id]
            )
        if self.q is not None:
            if not self.q.startswith('"') and not self.q.endswith('"'):
                self.__setattr__("q", f"*{self.q}*")
            else:
                self.__setattr__("q", self.q[1:-1])


@dataclasses.dataclass(kw_only=True)
class ReconQuery(Base):
    query: str
    limit: int
    type: ReconTypeEnum = Query(
        default=ReconTypeEnum.Person, description="Filter for returned entity type."
    )


@dataclasses.dataclass(kw_only=True)
class ReconQueries(Base):
    queries: list[ReconQuery]


@dataclasses.dataclass(kw_only=True)
class ReconQueryBatch(Base):
    queries: ReconQueries


@dataclasses.dataclass(kw_only=True)
class Search(Search_Base, QueryBase):
    kind: list[EntityType] = Query(
        default=None, description="Limit Query to entity type."
    )


@dataclasses.dataclass(kw_only=True)
class SearchOccupationsStats(Search_Base, QueryBase):
    pass


@dataclasses.dataclass(kw_only=True)
class SearchEvents(SearchEventsBase, QueryBase):
    pass

@dataclasses.dataclass(kw_only=True)
class SearchEventKindVocab(QueryBase):
    q: str = Query(
        default=None,
        description="Query for a label in the Vocabulary. Matching is done on substring level.",
    )

@dataclasses.dataclass(kw_only=True)
class SearchVocabs(QueryBase):
    q: str = Query(
        default=None,
        description="Query for a label in the Vocabulary. When not using quotes, the query will be wildcarded. When using quotes, \
            the query will be exact. Keep in mind that the wildcards will be added right and left of the query (wildcards are not added per token).",
    )

    def __post_init__(self):
        super().__post_init__()
        if self.q is not None:
            if not self.q.startswith('"') and not self.q.endswith('"'):
                self.__setattr__("q", f"*{self.q}*")
            else:
                self.__setattr__("q", self.q[1:-1])


@dataclasses.dataclass(kw_only=True)
class Entity_Retrieve(QueryBase):
    ids: typing.List[HttpUrl] = Query(description="List of IDs to retrieve.")


@dataclasses.dataclass(kw_only=True)
class StatisticsBinsQuery(Base):
    bins: PositiveInt = 10


@dataclasses.dataclass(kw_only=True)
class StatisticsBase(Search_Base, StatisticsBinsQuery):
    pass


# Models for JSON body


class RequestID(BaseModel):
    id: list[str]

    def __init__(__pydantic_self__, **data: typing.Any) -> None:
        data["id"] = [toggle_urls_encoding(item) for item in data["id"]]
        super().__init__(**data)
