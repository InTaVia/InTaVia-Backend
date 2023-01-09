import base64
import datetime
from enum import Enum
import os
import typing
from pydantic import Field, HttpUrl, NonNegativeInt
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


def pp_base64(data):
    if data is None:
        return None
    if isinstance(data, list):
        return [base64.urlsafe_b64encode(item2.encode("utf-8")).decode("utf-8") for item2 in data]
    return base64.urlsafe_b64encode(data.encode("utf-8")).decode("utf-8")


class EnumVocabsRelation(str, Enum):
    broader = "broader"
    narrower = "narrower"
    sameas = "same-as"


class EntityType(str, Enum):
    person = "person"
    place = "place"
    group = "group"
    CulturalHeritageObject = "CulturalHeritageObject"
    HistoricalEvent = "HistoricalEvent"


class InternationalizedLabel(RDFUtilsModelBaseClass):
    """Used to provide internationalized labels"""

    default: str
    en: typing.Optional[str]
    de: str | None = None
    fi: str | None = None
    si: str | None = None
    du: str | None = None

    def __init__(__pydantic_self__, **data: typing.Any) -> None:
        super().__init__(**data)


class Entity(RDFUtilsModelBaseClass):
    id: str = Field(
        ...,
        rdfconfig=FieldConfigurationRDF(path="entity", anchor=True, encode_function=pp_base64),
    )
    label: InternationalizedLabel | None = Field(
        None, rdfconfig=FieldConfigurationRDF(path="entityLabel", default_dict_key="default")
    )
    type: EntityType = Field(EntityType.person, rdfconfig=FieldConfigurationRDF(path="entityTypeLabel"))
    # FIXME: For the moment we determine that via the URI, needs to be fixed when provenance is in place
    # source: Source | None = None
    # linkedIds: list[LinkedId] | None = None
    # _linkedIds: list[HttpUrl] | None = None
    alternativeLabels: list[InternationalizedLabel] | None = Field(
        None, rdfconfig=FieldConfigurationRDF(path="entityLabel", default_dict_key="default")
    )
    description: str | None = None
    # media: list[MediaResource] | None = None
    events: list | None = Field(None, rdfconfig=FieldConfigurationRDF(path="event", encode_function=pp_base64))


class Event(RDFUtilsModelBaseClass):
    id: str = Field(
        ...,
        rdfconfig=FieldConfigurationRDF(path="event", anchor=True, encode_function=pp_base64),
    )
    label: InternationalizedLabel | None = Field(
        None, rdfconfig=FieldConfigurationRDF(path="event_label", default_dict_key="default")
    )
    # source: Source | None = None
    # kind: EntityEventKind | None = None
    startDate: str | None = Field(
        None, rdfconfig=FieldConfigurationRDF(path="begin", callback_function=convert_date_to_iso8601)
    )
    endDate: str | None = Field(
        None, rdfconfig=FieldConfigurationRDF(path="end", callback_function=convert_date_to_iso8601)
    )
    # place: Place | None = None
    relations: typing.List["EntityEventRelation"] | None


class EntityEventRelation(RDFUtilsModelBaseClass):
    id: str = Field(..., rdfconfig=FieldConfigurationRDF(path="role", anchor=True))
    label: InternationalizedLabel | None = Field(
        None, rdfconfig=FieldConfigurationRDF(path="role_label", default_dict_key="default")
    )
    kind: HttpUrl | None = Field(
        None,
        rdfconfig=FieldConfigurationRDF(
            path="role_type",
        ),
    )
    entity: str = Field(..., rdfconfig=FieldConfigurationRDF(path="entity", encode_function=pp_base64))


class VocabularyRelation(RDFUtilsModelBaseClass):
    relation_type: EnumVocabsRelation = Field(
        EnumVocabsRelation.broader, rdfconfig=FieldConfigurationRDF(path="relation_type")
    )
    related_vocabulary: str = Field(
        ..., rdfconfig=FieldConfigurationRDF(path="related_vocabulary", anchor=True, encode_function=pp_base64)
    )


class VocabularyEntry(RDFUtilsModelBaseClass):
    id: str = Field(..., rdfconfig=FieldConfigurationRDF(path="vocabulary", anchor=True, encode_function=pp_base64))
    label: InternationalizedLabel | None = Field(
        None, rdfconfig=FieldConfigurationRDF(path="vocabulary_label", default_dict_key="default")
    )
    related: typing.List["VocabularyRelation"] | None


class PaginatedResponseBase(RDFUtilsModelBaseClass):
    count: NonNegativeInt = 0
    page: NonNegativeInt = 0
    pages: NonNegativeInt = 0


class PaginatedResponseEntities(PaginatedResponseBase):
    results: typing.List[Entity] = Field([], rdfconfig=FieldConfigurationRDF(path="results"))


class PaginatedResponseVocabularyEntries(PaginatedResponseBase):
    results: typing.List[VocabularyEntry] = Field([], rdfconfig=FieldConfigurationRDF(path="results"))


EntityEventRelation.update_forward_refs()
Event.update_forward_refs()
Entity.update_forward_refs()
VocabularyEntry.update_forward_refs()
VocabularyRelation.update_forward_refs()
