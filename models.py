from dataclasses import dataclass
from distutils.command.config import config
import typing
from pydantic import BaseModel, HttpUrl, NonNegativeInt, PositiveInt
from pydantic.dataclasses import dataclass
from pydantic.utils import GetterDict
from enum import Enum
from geojson_pydantic import Polygon, Point
from typing import Any, Union
import datetime


class InTaViaConfig:
    validate_assignment = True


class EnumVocabsRelation(str, Enum):
    broader = "broader"
    narrower = "narrower"
    sameas = "same-as"


class EnumMediaKind(str, Enum):
    biographytext = "biography-text"
    image = "image"
    landingpage = "landing-page"
    text = "text"
    video = "video"


class VocabsRelation(BaseModel):
    kind: EnumVocabsRelation = EnumVocabsRelation.sameas


class InternationalizedLabel(BaseModel):
    """Used to provide internationalized labels"""

    default: str
    en: typing.Optional[str]
    de: str | None = None
    fi: str | None = None
    si: str | None = None
    du: str | None = None


class GroupType(BaseModel):
    """sets the type of Groups (Organizations)"""

    id: str
    label: InternationalizedLabel


class EntityEventKind(BaseModel):

    id: str
    label: InternationalizedLabel


class OccupationRelation(VocabsRelation):
    relation: "Occupation"


class Occupation(BaseModel):

    id: str
    label: InternationalizedLabel
    relation: list[OccupationRelation]


class MediaKind(BaseModel):
    id: str
    label: EnumMediaKind = EnumMediaKind.biographytext


class HistoricalEventType(BaseModel):
    id: str
    label: InternationalizedLabel


class EntityRelationRole(BaseModel):
    id: str
    label: InternationalizedLabel


class MediaResource(BaseModel):
    id: str
    attribution: str
    url: HttpUrl
    kind: MediaKind
    description: str | None = None


class Source(BaseModel):
    citation: str


class EntityBase(BaseModel):
    id: str
    label: InternationalizedLabel
    source: Source | None = None
    linkedIds: list[HttpUrl] | None = None
    alternativeLabels: list[InternationalizedLabel] | None = None
    description: str | None = None
    media: list[MediaResource] | None = None
    # relations: list["EntityEventRelation"] | None = None


class Person(EntityBase):
    kind = "person"
    gender: str | None = None


class Place(EntityBase):
    kind = "place"
    coordinates: Union[Polygon, Point] | None = None


class Group(EntityBase):
    kind = "group"
    type: GroupType | None = None


class CulturalHeritageObject(EntityBase):
    kind = "cultural-heritage-object"


class HistoricalEvent(EntityBase):
    kind = "historical-event"
    type: HistoricalEventType | None = None


class EntityEventRelation(BaseModel):
    id: str
    label: str | None = None
    entity: Union[Person, Place, Group, CulturalHeritageObject, HistoricalEvent] | None = None
    role: EntityRelationRole | None = None
    source: Source | None = None


class EntityEvent(BaseModel):
    id: str
    label: InternationalizedLabel | None = None
    source: Source
    kind: EntityEventKind | None = None
    startDate: str | None = None
    endDate: str | None = None
    place: Place | None = None
    relations: typing.List[EntityEventRelation]


class PersonFull(Person):
    relations: typing.List["EntityEventRelation"] | None = None


class PlaceFull(Place):
    relations: typing.List["EntityEventRelation"] | None = None


class GroupFull(Group):
    relations: typing.List["EntityEventRelation"] | None = None


class CulturalHeritageObjectFull(CulturalHeritageObject):
    relations: typing.List["EntityEventRelation"] | None = None


class HistoricalEventFull(HistoricalEvent):
    relations: typing.List["EntityEventRelation"] | None = None


class PaginatedResponseBase(BaseModel):
    count: NonNegativeInt = 0
    page: NonNegativeInt = 0
    pages: NonNegativeInt = 0

class PaginatedResponseGetterDict(GetterDict):

    def get(self, key: str, default: Any) -> Any:
        if key == "results":
            res = []
            print("test")
            for ent in self._obj["results"]:
                if ent["kind"] == "person":
                    res.append(PersonFull(**ent))
                elif ent["kind"] == "group":
                    res.append(GroupFull(**ent)) 
                elif ent["kind"] == "place":
                    res.append(PlaceFull(**ent))
            return res
        else:
            return self._obj.get(key, default)


class PaginatedResponseEntities(PaginatedResponseBase):
    results: typing.List[Union[PersonFull, PlaceFull, GroupFull]]

    def dict(self, *args, **kwargs) -> 'DictStrAny':
        _ignored = kwargs.pop('exclude_none')
        return super().dict(*args, exclude_none=True, **kwargs)
    
    class Config:
        orm_mode = True
        getter_dict = PaginatedResponseGetterDict

