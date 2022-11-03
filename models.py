from copy import deepcopy
from dataclasses import dataclass
from distutils.command.config import config
import re
import typing
from xmlrpc.client import Boolean
from pydantic import BaseModel, HttpUrl, NonNegativeInt, PositiveInt, ValidationError
from pydantic.dataclasses import dataclass
from pydantic.utils import GetterDict
from enum import Enum
from geojson_pydantic import Polygon, Point
from typing import Any, Union
import datetime

source_mapping = {
    "intavia.eu/apis/personproxy": "Austrian Biographical Dictionary",
    "data.biographynet.nl": "BiographyNET",
    "intavia.eu/personproxy/bs": "Biography Sampo"

}

linked_id_providers = {
    "gnd": {
        "label": "Gemeinsame Normdatei (GND)",
        "baseUrl": "https://d-nb.info/gnd",
        "regex_id": r"/([^/]+)$"
    },
    "APIS": {
        "label": "Österreichische Biographische Lexikon, APIS",
        "baseUrl": "https://apis.acdh.oeaw.ac.at",
        "regex_id": "([0-9]+)/?$"
    },
    "wikidata": {
        "label": "Wikidata",
        "baseUrl": "http://www.wikidata.org/entity",
        "regex_id": ".+?(Q[^\.]+)"
    },
    "biographysampo": {
        "label": "BiographySampo",
        "baseUrl": "http://ldf.fi/nbf/",
        "regex_id": "nbf/([^\.]+)"
    }
}


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

    def __init__(__pydantic_self__, **data: Any) -> None:
        super().__init__(**data)


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


class Occupation(BaseModel):
    id: str
    label: InternationalizedLabel


class OccupationRelation(VocabsRelation):
    occupation: Occupation | None = None


class OccupationFull(Occupation):
    relations: list[OccupationRelation] | None = None


class MediaKind(BaseModel):
    id: str
    label: EnumMediaKind = EnumMediaKind.biographytext


class HistoricalEventType(BaseModel):
    id: str
    label: InternationalizedLabel


class EntityRelationRole(BaseModel):
    id: str
    label: InternationalizedLabel | None = None


class MediaResource(BaseModel):
    id: str
    attribution: str
    url: HttpUrl
    kind: MediaKind
    description: str | None = None


class Source(BaseModel):
    citation: str


class LinkedIdProvider(BaseModel):
    label: str
    baseUrl: HttpUrl


class LinkedId(BaseModel):
    id: str
    provider: LinkedIdProvider | None = None
    _str_idprovider: str

    def __init__(__pydantic_self__, **data: Any) -> None:
        test = False
        if "_str_idprovider" in data:
            # Test for query params and remove them
            if re.search(r"\?[^/]+$", data["_str_idprovider"]):
                data["_str_idprovider"] = "/".join(data["_str_idprovider"].split("/")[:-1])
            for k, v in linked_id_providers.items():
                if v["baseUrl"] in data["_str_idprovider"]:
                    test = True
                    match = re.search(
                        v["regex_id"], data["_str_idprovider"])
                    if match:
                        data["id"] = match.group(1)
                        data["provider"] = LinkedIdProvider(**v)
                        break
                    else:
                        data["id"] = data["_str_idprovider"] 
            if not test:
                data["id"] = data["_str_idprovider"]
        super().__init__(**data)


class EntityBase(BaseModel):
    id: str
    label: InternationalizedLabel | None = None
    # FIXME: For the moment we determine that via the URI, needs to be fixed when provenance is in place
    source: Source | None = None
    linkedIds: list[LinkedId] | None = None
    _linkedIds: list[HttpUrl] | None = None
    alternativeLabels: list[InternationalizedLabel] | None = None
    description: str | None = None
    media: list[MediaResource] | None = None
    # relations: list["EntityEventRelation"] | None = None

    def __init__(__pydantic_self__, **data: Any) -> None:
        if "label" in data:
            if isinstance(data["label"], list):
                label = data["label"].pop()
                data["alternativeLabels"] = data["label"]
                data["label"] = label
        if "_linkedIds" in data:
            data["linkedIds"] = [LinkedId(_str_idprovider=x)
                                 for x in data["_linkedIds"]]
        for key, value in source_mapping.items():
            if key in data["id"]:
                data["source"] = Source(citation=value)
        super().__init__(**data)


class GenderType(BaseModel):
    id: str
    label: InternationalizedLabel


class Person(EntityBase):
    kind = "person"
    gender: GenderType | None = None
    occupations: typing.List[Occupation] | None = None

    def __init__(__pydantic_self__, **data: Any) -> None:
        if "gender" in data:    # FIXME: This should be fixed in the data, by adding a label to the gender type
            if "label" not in data["gender"]:
                data["gender"]["label"] = {"default": data["gender"]["id"].split("/")[-1]}
        super().__init__(**data)


class Place(EntityBase):
    kind = "place"
    _lat_long: str | None = None
    geometry: Union[Polygon, Point] | None = None

    def __init__(pydantic_self__, **data: Any) -> None:
        if "_lat_long" in data:
            coordinates = []
            for x in data["_lat_long"].split(" "):
                try:
                    coordinates.append(float(x.strip()))
                except:
                    pass
            # FIXME: We are still using inconsistent formatting for ccordinates
            data["geometry"] = Point(coordinates=coordinates[::-1])
        super().__init__(**data)


class Group(EntityBase):
    kind = "group"
    type: GroupType | None = None


class CulturalHeritageObject(EntityBase):
    kind = "cultural-heritage-object"


class HistoricalEvent(EntityBase):
    kind = "historical-event"
    type: HistoricalEventType | None = None


class EntityEventRelationGetter(GetterDict):

    def get(self, key: Any, default: Any = None) -> Any:
        if key == "entity":
            ent = self._obj["entity"]
            if ent["kind"] == "person":
                return Person(**ent)
            elif ent["kind"] == "group":
                return Group(**ent)
            elif ent["kind"] == "place":
                return Place(**ent)
        else:
            return self._obj.get(key, default)


class EntityEventRelation(BaseModel):
    id: str
    label: InternationalizedLabel | None = None
    entity: Union[Person, Place, Group,
                  CulturalHeritageObject, HistoricalEvent] | None = None
    role: EntityRelationRole | None = None
    source: Source | None = None

    def __init__(__pydantic_self__, **data: Any) -> None:
        # if "label" in data:
        if isinstance(data["label"], list):
            data["label"] = data["label"][0]
        #data["label"] = data["label"][0]
        if not "entity" in data:
            if "kind" in data:
                if data["kind"] == "person":
                    data["entity"] = Person(**data)
                elif data["kind"] == "group":
                    data["entity"] = Group(**data)
                elif data["kind"] == "place":
                    data["entity"] = Place(**data)
        super().__init__(**data)
        print('test')


class EntityEvent(BaseModel):
    id: str
    label: InternationalizedLabel | None = None
    source: Source | None = None
    _source_entity_role: EntityRelationRole | None = None
    _self_added: Boolean = False
    kind: EntityEventKind | None = None
    startDate: str | None = None
    endDate: str | None = None
    place: Place | None = None
    relations: typing.List[EntityEventRelation] | None = None


class PersonFull(Person):
    events: typing.List["EntityEvent"] | None = None

    def __init__(__pydantic_self__, **data: Any) -> None:
        if "events" in data:
            for c, ev in enumerate(data["events"]):
                ev_self = deepcopy(data)
                del ev_self["events"]
                if "occupation" in ev_self:
                    del ev_self["occupation"]
                if "_source_entity_role" in ev:
                    ev_self["role"] = ev["_source_entity_role"]
                if not "relations" in data["events"][c]:
                    data["events"][c]["relations"] = []
                if ev_self["id"] not in [x["id"] for x in data["events"][c]["relations"]]:
                    data["events"][c]["relations"].insert(
                        0, EntityEventRelation(**ev_self))
                    data["events"][c]["_self_added"] = True
        super().__init__(**data)


class PlaceFull(Place):
    events: typing.List["EntityEvent"] | None = None


class GroupFull(Group):
    events: typing.List["EntityEvent"] | None = None


class CulturalHeritageObjectFull(CulturalHeritageObject):
    events: typing.List["EntityEvent"] | None = None


class HistoricalEventFull(HistoricalEvent):
    events: typing.List["EntityEvent"] | None = None


class PaginatedResponseBase(BaseModel):
    count: NonNegativeInt = 0
    page: NonNegativeInt = 0
    pages: NonNegativeInt = 0

    def __init__(__pydantic_self__, **data: Any) -> None:
        super().__init__(**data)


class ValidationErrorModel(BaseModel):
    id: str
    error: str


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
    errors: typing.List[ValidationErrorModel] | None = None

    def __init__(self, **data: Any) -> None:
        res = []
        errors = []
        for ent in data["results"]:
            if ent["kind"] == "person":
                try:
                    res.append(PersonFull(**ent))
                except ValidationError as e:
                    errors.append({"id": ent["id"], "error": str(e)})
            elif ent["kind"] == "group":
                try:
                    res.append(GroupFull(**ent))
                except ValidationError as e:
                    errors.append({"id": ent["id"], "error": str(e)})
            elif ent["kind"] == "place":
                try:
                    res.append(PlaceFull(**ent))
                except ValidationError as e:
                    errors.append({"id": ent["id"], "error": str(e)})
        data["results"] = res
        if len(errors) > 0:
            data["errors"] = errors
        super().__init__(**data)
        self.results = res


class PaginatedResponseOccupations(PaginatedResponseBase):
    results: typing.List[OccupationFull]
    errors: typing.List[ValidationErrorModel] | None = None

    def __init__(__pydantic_self__, **data: Any) -> None:
        res = []
        errors = []
        for occupation in data["results"]:
            try:
                res.append(OccupationFull(**occupation))
            except ValidationError as e:
                errors.append({"id": occupation["id"], "error": str(e)})
        if len(errors) > 0:
            data["errors"] = errors
        super().__init__(**data)
        __pydantic_self__.results = res

    # class Config:
    #     orm_mode = True
    #     getter_dict = PaginatedResponseGetterDict


class Bin(BaseModel):
    label: str
    count: int
    values: typing.Tuple[Union[int, float, datetime.datetime], Union[int, float, datetime.datetime]] | None = None
    order: PositiveInt | None = None


class StatisticsBins(BaseModel):
    bins: list[Bin]


class StatisticsOccupation(BaseModel):
    id: str
    label: str
    count: int = 0
    children: typing.List["StatisticsOccupation"] | None = None


class StatisticsOccupationReturn(BaseModel):
    tree: StatisticsOccupation

class ReconSuggestResultReturn(BaseModel):
    id: str
    name: str

class ReconSuggestReturn(BaseModel):
    result: list[ReconSuggestResultReturn]


