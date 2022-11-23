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


def get_entity_class(field, data):
    # res = []
    # for ent in data[0]["results"]:  # FIXME: this needs a generic approach, data should be filtered before
    #     if ent["entityTypeLabel"] == "person":
    #         res.append(PersonFull(**ent))
    #     elif ent["entityTypeLabel"] == "place":
    #         res.append(PlaceFull(**ent))
    #     elif ent["entityTypeLabel"] == "organization":
    #         res.append(GroupFull(**ent))
    # return res
    return PersonFull

class ID(RDFUtilsModelBaseClass):
    

class InternationalizedLabel(RDFUtilsModelBaseClass):
    """Used to provide internationalized labels"""

    default: str = Field(..., rdfconfig=FieldConfigurationRDF(path="entityLabel", anchor=True))
    en: typing.Optional[str]
    de: str | None = None
    fi: str | None = None
    si: str | None = None
    du: str | None = None


class EntityBase(RDFUtilsModelBaseClass):
    id: str = Field(..., rdfconfig=FieldConfigurationRDF(path="person", anchor=True))
    label: InternationalizedLabel | None = None
    # FIXME: For the moment we determine that via the URI, needs to be fixed when provenance is in place
    source: Source | None = None
    linkedIds: list[LinkedId] | None = None
    # _linkedIds: list[HttpUrl] | None = None
    alternativeLabels: list[InternationalizedLabel] | None = None
    description: str | None = None
    media: list[MediaResource] | None = None
    events: list["Event"] | None = None


class Event(RDFUtilsModelBaseClass):
