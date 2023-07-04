import base64
import datetime
from enum import Enum
import os
import re
import typing
from geojson_pydantic import Point, Polygon
from pydantic import BaseModel, Field, HttpUrl, NonNegativeInt, PositiveInt
from rdf_fastapi_utils.models import FieldConfigurationRDF, RDFUtilsModelBaseClass

BASE_URL = os.getenv("BASE_URL", "http://intavia-backend.acdh-dev.oeaw.ac.at")

source_mapping = {
    "intavia.eu/apis/personproxy": "Austrian Biographical Dictionary",
    "data.biographynet.nl": "BiographyNET",
    "intavia.eu/personproxy/bs": "Biography Sampo",
}

linked_id_providers = {
    "gnd": {
        "label": "Gemeinsame Normdatei (GND)",
        "baseUrl": "https://d-nb.info/gnd",
        "regex_id": r"/([^/]+)$",
    },
    "APIS": {
        "label": "Österreichische Biographische Lexikon, APIS",
        "baseUrl": "https://apis.acdh.oeaw.ac.at",
        "regex_id": "([0-9]+)/?$",
    },
    "wikidata": {
        "label": "Wikidata",
        "baseUrl": "http://www.wikidata.org/entity",
        "regex_id": ".+?(Q[^\.]+)",
    },
    "biographysampo": {
        "label": "BiographySampo",
        "baseUrl": "http://ldf.fi/nbf/",
        "regex_id": "nbf/([^\.]+)",
    },
}


def get_source_mapping(source):
    for key, value in source_mapping.items():
        if key in source:
            return value
    return None


def pp_label(field, item, data):
    if isinstance(item, list):
        return item[0]
    else:
        return item


def pp_id_provider(field, item, data):
    """function that uses sameas links and regexes to generate
    linkedId objects

    Args:
        field (class): field class instance
        item (list): list of IDs extracted from the sparql query
        data (dict): complete data

    Returns:
        list: list of dicts describing the linkedIds
    """

    res = []
    if isinstance(item, str):
        item = [item]
    for it in item:
        data = {}
        test = False
        # Test for query params and remove them
        if re.search(r"\?[^/]+$", it["id"]):
            it = "/".join(it["id"].split("/")[:-1])
        else:
            it = it["id"]
        for k, v in linked_id_providers.items():
            if v["baseUrl"] in it:
                test = True
                match = re.search(v["regex_id"], it)
                if match:
                    data["id"] = match.group(1)
                    data["provider"] = LinkedIdProvider(**v)
                    break
                else:
                    data["id"] = it
        if not test:
            data["id"] = it
        res.append(data)
    return res


def pp_label_str(field, item, data):
    if isinstance(item, str):
        return {"default": item}
    else:
        return item


def pp_label_list(field, item, data):
    if isinstance(item, list):
        return [{"default": i} for i in item]
    else:
        return item


def convert_date_to_iso8601(field, item, data):
    if isinstance(item, datetime.datetime):
        return item.isoformat().split("T")[0]
    else:
        return item


def pp_gender_to_label(field, item, data):
    if "Male" in item["gender"] and "genderLabel" not in item:
        item["genderLabel"] = "male"
    if "Female" in item["gender"] and "genderLabel" not in item:
        item["genderLabel"] = "female"
    return item


def pp_lat_long(field, item, data):
    if isinstance(item, str):
        item = [
            item,
        ]
    for it in item:
        if it.startswith("Point"):
            lst_item = it.split(" ")
            item = Point(coordinates=[lst_item[2], lst_item[3]])
    return item


def pp_source(field, item, data):
    for source, citation in source_mapping.items():
        if source in item["citation"]:
            return {"citation": citation}


def pp_base64(data):
    if data is None:
        return None
    if isinstance(data, list):
        return [base64.urlsafe_b64encode(item2.encode("utf-8")).decode("utf-8") for item2 in data]
    return base64.urlsafe_b64encode(data.encode("utf-8")).decode("utf-8")


def pp_base64_to_list(data):
    if data is None:
        return None
    if isinstance(data, list):
        return [base64.urlsafe_b64encode(item2.encode("utf-8")).decode("utf-8") for item2 in data]
    return [base64.urlsafe_b64encode(data.encode("utf-8")).decode("utf-8")]


class EnumVocabsRelation(str, Enum):
    broader = "broader"
    narrower = "narrower"
    sameas = "same-as"


class EnumMediaObjectKind(str, Enum):
    image = "image"
    audio = "audio"
    video = "video"


class EntityType(str, Enum):
    Person = "person"
    Place = "place"
    Group = "group"
    CulturalHeritageObject = "cultural-heritage-object"
    HistoricalEvent = "historical-event"

    def __str__(self):
        return self.value

    def get_rdf_uri(self) -> str:
        map = {
            "person": "idmcore:Person_Proxy",
            "group": "idmcore:Group",
            "place": "crm:E53_Place",
            "cultural-heritage-object": "idm:CHO_Proxy",
            "historical-event": "idmcore:HistoricalEvent_Proxy",
        }
        return map[self.value]


class IntaViaBackendBaseModel(RDFUtilsModelBaseClass):
    errors: typing.List[str] | None = None

    class Config:
        RDF_utils_catch_errors = True
        RDF_utils_error_field_name = "errors"
        RDF_utils_move_errors_to_top = True


class LinkedIdProvider(BaseModel):
    label: str
    baseUrl: HttpUrl


class LinkedId(BaseModel):
    id: str
    provider: LinkedIdProvider | None = None


class InternationalizedLabel(IntaViaBackendBaseModel):
    """Used to provide internationalized labels"""

    default: str
    en: typing.Optional[str]
    de: str | None = None
    fi: str | None = None
    si: str | None = None
    du: str | None = None

    def __init__(__pydantic_self__, **data: typing.Any) -> None:
        super().__init__(**data)


class MediaResource(BaseModel):
    """Object for representing media resources"""

    id: str
    label: InternationalizedLabel | None = None
    description: str | None = None
    attribution: str | None = None
    url: HttpUrl
    # TODO: Should be an actual vocabulary.
    # kind: MediaKind;
    kind: EnumMediaObjectKind = EnumMediaObjectKind.image


class Biography(BaseModel):
    """Object for representing biographies"""

    id: str
    title: str | None = None
    abstract: str | None = None
    text: str
    citation: str | None = None


class GenderType(IntaViaBackendBaseModel):
    id: str = Field(..., rdfconfig=FieldConfigurationRDF(path="gender", anchor=True))
    label: InternationalizedLabel = Field(
        None, rdfconfig=FieldConfigurationRDF(path="genderLabel", default_dict_key="default")
    )


class EntityEventRelation(IntaViaBackendBaseModel):
    event: str = Field(..., rdfconfig=FieldConfigurationRDF(path="event", anchor=True, encode_function=pp_base64))
    role: str = Field(..., rdfconfig=FieldConfigurationRDF(path="role_type", encode_function=pp_base64))


class Occupation(IntaViaBackendBaseModel):
    id: str = Field(..., rdfconfig=FieldConfigurationRDF(path="occupation", anchor=True, encode_function=pp_base64))
    label: InternationalizedLabel = Field(
        None, rdfconfig=FieldConfigurationRDF(path="occupationLabel", default_dict_key="default")
    )


class Source(BaseModel):
    citation: str


class Entity(IntaViaBackendBaseModel):
    id: str = Field(
        ...,
        rdfconfig=FieldConfigurationRDF(path="entity", anchor=True, encode_function=pp_base64),
    )
    label: InternationalizedLabel | None = Field(
        None, rdfconfig=FieldConfigurationRDF(path="entityLabel", default_dict_key="default")
    )
    kind: EntityType = Field(EntityType.Person, rdfconfig=FieldConfigurationRDF(path="entityTypeLabel"))
    # FIXME: For the moment we determine that via the URI, needs to be fixed when provenance is in place
    source: Source | None = Field(
        None, rdfconfig=FieldConfigurationRDF(callback_function=pp_source, path="source", default_dict_key="citation")
    )

    linkedIds: list[LinkedId] | None = Field(
        None, rdfconfig=FieldConfigurationRDF(callback_function=pp_id_provider, path="linkedIds", default_dict_key="id")
    )
    # _linkedIds: list[HttpUrl] | None = None
    gender: GenderType | None = Field(
        None, rdfconfig=FieldConfigurationRDF(callback_function=pp_gender_to_label, path="gender")
    )
    occupations: typing.List[Occupation] | None = None
    alternativeLabels: list[InternationalizedLabel] | None = Field(
        None, rdfconfig=FieldConfigurationRDF(path="entityLabel", default_dict_key="default")
    )
    description: str | None = None
    media: list[str] | None = Field(
        None, rdfconfig=FieldConfigurationRDF(path="mediaObject", encode_function=pp_base64_to_list)
    )
    biographies: list[str] | None = Field(
        None, rdfconfig=FieldConfigurationRDF(path="biographyObject", encode_function=pp_base64_to_list)
    )
    geometry: typing.Union[Polygon, Point] | None = Field(
        None, rdfconfig=FieldConfigurationRDF(path="geometry", callback_function=pp_lat_long, bypass_data_mapping=True)
    )
    relations: list[EntityEventRelation] = []


class Event(IntaViaBackendBaseModel):
    id: str = Field(
        ...,
        rdfconfig=FieldConfigurationRDF(path="event", anchor=True, encode_function=pp_base64),
    )
    label: InternationalizedLabel | None = Field(
        None, rdfconfig=FieldConfigurationRDF(path="event_label", default_dict_key="default")
    )
    kind: str | None = Field(None, rdfconfig=FieldConfigurationRDF(path="event_type", encode_function=pp_base64))
    # source: Source | None = None
    # kind: EntityEventKind | None = None
    startDate: str | None = Field(
        None, rdfconfig=FieldConfigurationRDF(path="begin", callback_function=convert_date_to_iso8601)
    )
    endDate: str | None = Field(
        None, rdfconfig=FieldConfigurationRDF(path="end", callback_function=convert_date_to_iso8601)
    )
    # place: Place | None = None
    relations: typing.List["EventEntityRelation"] = []


class EventEntityRelation(IntaViaBackendBaseModel):
    role: str | None = Field(
        ...,
        rdfconfig=FieldConfigurationRDF(path="role_type", encode_function=pp_base64),
    )
    entity: str = Field(..., rdfconfig=FieldConfigurationRDF(path="entity", encode_function=pp_base64, anchor=True))


class VocabularyRelation(IntaViaBackendBaseModel):
    relation_type: EnumVocabsRelation = Field(
        EnumVocabsRelation.broader, rdfconfig=FieldConfigurationRDF(path="relation_type")
    )
    related_vocabulary: str = Field(
        ..., rdfconfig=FieldConfigurationRDF(path="related_vocabulary", anchor=True, encode_function=pp_base64)
    )


class VocabularyEntry(IntaViaBackendBaseModel):
    id: str = Field(..., rdfconfig=FieldConfigurationRDF(path="vocabulary", anchor=True, encode_function=pp_base64))
    label: InternationalizedLabel | None = Field(
        None, rdfconfig=FieldConfigurationRDF(path="vocabulary_label", default_dict_key="default")
    )
    related: typing.List["VocabularyRelation"] | None


class PaginatedResponseBase(IntaViaBackendBaseModel):
    count: NonNegativeInt = 0
    page: NonNegativeInt = 0
    pages: NonNegativeInt = 0


class PaginatedResponseEntities(PaginatedResponseBase):
    results: typing.List[Entity] = Field([], rdfconfig=FieldConfigurationRDF(path="results"))

    class Config(PaginatedResponseBase.Config):
        sort_key = {"original key": "entity", "object list": "results"}


class PaginatedResponseMedia(PaginatedResponseBase):
    results: typing.List[MediaResource] = []


class PaginatedResponseBiography(PaginatedResponseBase):
    results: typing.List[Biography] = []


class PaginatedResponseEvents(PaginatedResponseBase):
    results: typing.List[Event] = Field([], rdfconfig=FieldConfigurationRDF(path="results"))


class PaginatedResponseVocabularyEntries(PaginatedResponseBase):
    results: typing.List[VocabularyEntry] = Field([], rdfconfig=FieldConfigurationRDF(path="results"))


class StatisticsOccupationPrelimBroader(IntaViaBackendBaseModel):
    id: str = Field(..., rdfconfig=FieldConfigurationRDF(path="broaderUri", anchor=True, encode_function=pp_base64))
    label: str | None = Field(None, rdfconfig=FieldConfigurationRDF(path="broaderLabel"))


class StatisticsOccupationPrelim(IntaViaBackendBaseModel):
    id: str = Field(..., rdfconfig=FieldConfigurationRDF(path="occupation", anchor=True, encode_function=pp_base64))
    label: str = Field(..., rdfconfig=FieldConfigurationRDF(path="occupationLabel"))
    count: int = Field(..., rdfconfig=FieldConfigurationRDF(path="count"))
    broader: list[StatisticsOccupationPrelimBroader] | None = None


class StatisticsOccupationPrelimList(IntaViaBackendBaseModel):
    results: list[StatisticsOccupationPrelim] = Field([], rdfconfig=FieldConfigurationRDF(path="results"))


class StatisticsOccupation(BaseModel):
    id: str
    label: str
    count: int = 0
    children: typing.List["StatisticsOccupation"] | None = None


class StatisticsOccupationReturn(BaseModel):
    tree: StatisticsOccupation


class Bin(BaseModel):
    label: str
    count: int
    values: typing.Tuple[
        typing.Union[int, float, datetime.datetime], typing.Union[int, float, datetime.datetime]
    ] | None = None
    order: PositiveInt | None = None


class StatisticsBins(BaseModel):
    bins: list[Bin]


EntityEventRelation.update_forward_refs()
Event.update_forward_refs()
Entity.update_forward_refs()
VocabularyEntry.update_forward_refs()
VocabularyRelation.update_forward_refs()
