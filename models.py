import typing
from pydantic import BaseModel, HttpUrl
from enum import Enum
from geojson_pydantic import Polygon, Point
from typing import Union
import datetime


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
    en: str | None = None
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
    source: Source
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
    group_type: GroupType | None = None


class CulturalHeritageObject(EntityBase):
    kind = "cultural-heritage-object"


class HistoricalEvent(EntityBase):
    kind = "historical-event"
    historical_event_type: HistoricalEventType | None = None


class EntityEventRelation(BaseModel):
    id: str
    entity: Union[Person, Place, Group, CulturalHeritageObject, HistoricalEvent]
    role: EntityRelationRole
    source: Source


class EntityEvent(BaseModel):
    id: str
    label: InternationalizedLabel
    source: Source
    kind: EntityEventKind | None = None
    date: typing.Tuple[datetime.date, datetime.date] | None = None
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
