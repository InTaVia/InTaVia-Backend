from enum import Enum
import typing
from pydantic import Field
from rdf_fastapi_utils.models import FieldConfigurationRDF, RDFUtilsModelBaseClass


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


class EntityType(str, Enum):
    person = "person"
    place = "place"
    group = "group"
    CulturalHeritageObject = "CulturalHeritageObject"
    HistoricalEvent = "HistoricalEvent"


class InternationalizedLabel(RDFUtilsModelBaseClass):
    """Used to provide internationalized labels"""

    default: str = Field(..., rdfconfig=FieldConfigurationRDF(path="entityLabel", anchor=True))
    en: typing.Optional[str]
    de: str | None = None
    fi: str | None = None
    si: str | None = None
    du: str | None = None


class Entity(RDFUtilsModelBaseClass):
    id: str = Field(..., rdfconfig=FieldConfigurationRDF(path="entity", anchor=True))
    # label: InternationalizedLabel | None = None
    type: EntityType = Field(EntityType.person, rdfconfig=FieldConfigurationRDF(path="entityTypeLabel"))
    # FIXME: For the moment we determine that via the URI, needs to be fixed when provenance is in place
    # source: Source | None = None
    # linkedIds: list[LinkedId] | None = None
    # _linkedIds: list[HttpUrl] | None = None
    # alternativeLabels: list[InternationalizedLabel] | None = None
    description: str | None = None
    # media: list[MediaResource] | None = None
    events: list | None = Field(None, rdfconfig=FieldConfigurationRDF(path="event"))


class FakeList(RDFUtilsModelBaseClass):
    results: list[Entity] = Field(..., rdfconfig=FieldConfigurationRDF(path="results"))
