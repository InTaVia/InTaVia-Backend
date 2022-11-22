import datetime
from enum import Enum
import typing
from geojson_pydantic import Point, Polygon

from pydantic import BaseModel, Field, HttpUrl, NonNegativeInt, PositiveInt
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


class VocabsRelation(RDFUtilsModelBaseClass):
    kind: EnumVocabsRelation = EnumVocabsRelation.sameas


class InternationalizedLabel(RDFUtilsModelBaseClass):
    """Used to provide internationalized labels"""

    default: str = Field(..., rdfconfig=FieldConfigurationRDF(path="entityLabel", anchor=True))
    en: typing.Optional[str]
    de: str | None = None
    fi: str | None = None
    si: str | None = None
    du: str | None = None


class GroupType(RDFUtilsModelBaseClass):
    """sets the type of Groups (Organizations)"""

    id: str
    label: InternationalizedLabel


class EntityEventKind(RDFUtilsModelBaseClass):

    id: str
    label: InternationalizedLabel


class Occupation(RDFUtilsModelBaseClass):
    id: str
    label: InternationalizedLabel


class OccupationRelation(VocabsRelation):
    occupation: Occupation | None = None


class OccupationFull(Occupation):
    relations: list[OccupationRelation] | None = None


class MediaKind(RDFUtilsModelBaseClass):
    id: str
    label: EnumMediaKind = EnumMediaKind.biographytext


class HistoricalEventType(RDFUtilsModelBaseClass):
    id: str
    label: InternationalizedLabel


class EntityRelationRole(RDFUtilsModelBaseClass):
    id: str
    label: InternationalizedLabel | None = None


class MediaResource(RDFUtilsModelBaseClass):
    id: str
    attribution: str
    url: HttpUrl
    kind: MediaKind
    description: str | None = None


class Source(RDFUtilsModelBaseClass):
    citation: str = Field(..., rdfconfig=FieldConfigurationRDF(path="person", callback_function=get_source_mapping))


class LinkedIdProvider(RDFUtilsModelBaseClass):
    label: str
    baseUrl: HttpUrl


class LinkedId(RDFUtilsModelBaseClass):
    id: str
    provider: LinkedIdProvider | None = None
    _str_idprovider: str

    # def __init__(__pydantic_self__, **data: Any) -> None:
    #     test = False
    #     if "_str_idprovider" in data:
    #         # Test for query params and remove them
    #         if re.search(r"\?[^/]+$", data["_str_idprovider"]):
    #             data["_str_idprovider"] = "/".join(data["_str_idprovider"].split("/")[:-1])
    #         for k, v in linked_id_providers.items():
    #             if v["baseUrl"] in data["_str_idprovider"]:
    #                 test = True
    #                 match = re.search(v["regex_id"], data["_str_idprovider"])
    #                 if match:
    #                     data["id"] = match.group(1)
    #                     data["provider"] = LinkedIdProvider(**v)
    #                     break
    #                 else:
    #                     data["id"] = data["_str_idprovider"]
    #         if not test:
    #             data["id"] = data["_str_idprovider"]
    #     super().__init__(**data)


class EntityBase(RDFUtilsModelBaseClass):
    id: str = Field(..., rdfconfig=FieldConfigurationRDF(path="person", anchor=True))
    label: InternationalizedLabel | None = None
    # FIXME: For the moment we determine that via the URI, needs to be fixed when provenance is in place
    source: Source | None = None
    linkedIds: list[LinkedId] | None = None
    _linkedIds: list[HttpUrl] | None = None
    alternativeLabels: list[InternationalizedLabel] | None = None
    description: str | None = None
    media: list[MediaResource] | None = None
    relations: list["EntityEventRelation"] | None = None

    # def __init__(__pydantic_self__, **data: Any) -> None:
    #     #__pydantic_self__.create_data_from_rdf(data)
    #     if "label" in data:
    #         if isinstance(data["label"], list):
    #             label = data["label"].pop()
    #             data["alternativeLabels"] = data["label"]
    #             data["label"] = label
    #     if "_linkedIds" in data:
    #         data["linkedIds"] = [LinkedId(_str_idprovider=x)
    #                              for x in data["_linkedIds"]]
    #     for key, value in source_mapping.items():
    #         if key in data["id"]:
    #             data["source"] = Source(citation=value)
    #     super().__init__(**data)


class GenderType(RDFUtilsModelBaseClass):
    id: str = Field(..., rdfconfig=FieldConfigurationRDF(path="gender"))
    label: InternationalizedLabel


class Person(EntityBase):
    kind = "person"
    gender: GenderType | None = None
    occupations: typing.List[Occupation] | None = None

    # def __init__(__pydantic_self__, **data: Any) -> None:
    #     if "gender" in data:    # FIXME: This should be fixed in the data, by adding a label to the gender type
    #         if "label" not in data["gender"]:
    #             data["gender"]["label"] = {
    #                 "default": data["gender"]["id"].split("/")[-1]}
    #     super().__init__(**data)


class Place(EntityBase):
    kind = "place"
    _lat_long: str | None = None
    geometry: typing.Union[Polygon, Point] | None = None

    # def __init__(pydantic_self__, **data: Any) -> None:
    #     if "_lat_long" in data:
    #         coordinates = []
    #         for x in data["_lat_long"].split(" "):
    #             try:
    #                 coordinates.append(float(x.strip()))
    #             except:
    #                 pass
    #         # FIXME: We are still using inconsistent formatting for ccordinates
    #         data["geometry"] = Point(coordinates=coordinates[::-1])
    #     super().__init__(**data)


class Group(EntityBase):
    kind = "group"
    type: GroupType | None = None


class CulturalHeritageObject(EntityBase):
    kind = "cultural-heritage-object"


class HistoricalEvent(EntityBase):
    kind = "historical-event"
    type: HistoricalEventType | None = None


class EntityEventRelation(RDFUtilsModelBaseClass):
    id: str
    label: InternationalizedLabel | None = None
    entity: typing.Union[Person, Place, Group, CulturalHeritageObject, HistoricalEvent] | None = None
    role: EntityRelationRole | None = None
    source: Source | None = None

    # def __init__(__pydantic_self__, **data: Any) -> None:
    #     # if "label" in data:
    #     if isinstance(data["label"], list):
    #         data["label"] = data["label"][0]
    #     # data["label"] = data["label"][0]
    #     if not "entity" in data:
    #         if "kind" in data:
    #             if data["kind"] == "person":
    #                 data["entity"] = Person(**data)
    #             elif data["kind"] == "group":
    #                 data["entity"] = Group(**data)
    #             elif data["kind"] == "place":
    #                 data["entity"] = Place(**data)
    #     super().__init__(**data)


class EntityEvent(RDFUtilsModelBaseClass):
    id: str
    label: InternationalizedLabel | None = None
    source: Source | None = None
    _source_entity_role: EntityRelationRole | None = None
    _self_added: bool = False
    kind: EntityEventKind | None = None
    startDate: str | None = None
    endDate: str | None = None
    place: Place | None = None
    relations: typing.List[EntityEventRelation] | None = None


class PersonFull(Person):
    test: str = "test"
    events: typing.List["EntityEvent"] | None = None

    # def __init__(__pydantic_self__, **data: Any) -> None:
    #     if "events" in data:
    #         for c, ev in enumerate(data["events"]):
    #             ev_self = deepcopy(data)
    #             del ev_self["events"]
    #             if "occupation" in ev_self:
    #                 del ev_self["occupation"]
    #             if "_source_entity_role" in ev:
    #                 ev_self["role"] = ev["_source_entity_role"]
    #             if not "relations" in data["events"][c]:
    #                 data["events"][c]["relations"] = []
    #             if ev_self["id"] not in [x["id"] for x in data["events"][c]["relations"]]:
    #                 data["events"][c]["relations"].insert(0, EntityEventRelation(**ev_self))
    #                 data["events"][c]["_self_added"] = True
    #     super().__init__(**data)


class PlaceFull(Place):
    events: typing.List["EntityEvent"] | None = None


class GroupFull(Group):
    events: typing.List["EntityEvent"] | None = None


class CulturalHeritageObjectFull(CulturalHeritageObject):
    events: typing.List["EntityEvent"] | None = None


class HistoricalEventFull(HistoricalEvent):
    events: typing.List["EntityEvent"] | None = None


class PaginatedResponseBase(RDFUtilsModelBaseClass):
    count: NonNegativeInt = 0
    page: NonNegativeInt = 0
    pages: NonNegativeInt = 0


class ValidationErrorModel(RDFUtilsModelBaseClass):
    id: str
    error: str


class PaginatedResponseEntities(PaginatedResponseBase):
    results: list[typing.Union["PersonFull", "PlaceFull"]] = Field(
        ..., rdfconfig=FieldConfigurationRDF(serialization_class_callback=get_entity_class)
    )
    # errors: typing.List[ValidationErrorModel] | None = None

    # def __init__(self, **data: Any) -> None:
    #     super().__init__(**data)

    #     # self.create_data_from_rdf(data)
    #     data_flattened = self.flatten_rdf_data(data)
    #     res = []
    #     data_person = self.filter_sparql(
    #         data=data_flattened,
    #         filters=[
    #             ("entityTypeLabel", "person"),
    #         ],
    #         anchor="person",
    #     )
    #     errors = []
    #     for person in data_person:
    #         try:
    #             res.append(PersonFull(**person).dict())
    #         except ValidationError as e:
    #             errors.append({"id": person["person"], "error": str(e)})

    # for ent in data["results"]:
    #     if ent["kind"] == "person":
    #         try:
    #             res.append(PersonFull(**ent))
    #         except ValidationError as e:
    #             errors.append({"id": ent["id"], "error": str(e)})
    #     elif ent["kind"] == "group":
    #         try:
    #             res.append(GroupFull(**ent))
    #         except ValidationError as e:
    #             errors.append({"id": ent["id"], "error": str(e)})
    #     elif ent["kind"] == "place":
    #         try:
    #             res.append(PlaceFull(**ent))
    #         except ValidationError as e:
    #             errors.append({"id": ent["id"], "error": str(e)})
    # data["results"] = res
    # if len(errors) > 0:
    #     data["errors"] = errors
    # super().__init__(**data)
    # self.results = res


PaginatedResponseEntities.update_forward_refs()
PlaceFull.update_forward_refs()
PersonFull.update_forward_refs()
EntityEvent.update_forward_refs()
GroupFull.update_forward_refs()
CulturalHeritageObjectFull.update_forward_refs()
HistoricalEventFull.update_forward_refs()
Place.update_forward_refs()
Person.update_forward_refs()
Group.update_forward_refs()
CulturalHeritageObject.update_forward_refs()
HistoricalEvent.update_forward_refs()


class PaginatedResponseOccupations(PaginatedResponseBase):
    results: typing.List[OccupationFull]
    errors: typing.List[ValidationErrorModel] | None = None

    # def __init__(__pydantic_self__, **data: Any) -> None:
    #     res = []
    #     errors = []
    #     for occupation in data["results"]:
    #         try:
    #             res.append(OccupationFull(**occupation))
    #         except ValidationError as e:
    #             errors.append({"id": occupation["id"], "error": str(e)})
    #     if len(errors) > 0:
    #         data["errors"] = errors
    #     super().__init__(**data)
    #     __pydantic_self__.results = res

    # class Config:
    #     orm_mode = True
    #     getter_dict = PaginatedResponseGetterDict


class Bin(RDFUtilsModelBaseClass):
    label: str
    count: int
    values: typing.Tuple[
        typing.Union[int, float, datetime.datetime], typing.Union[int, float, datetime.datetime]
    ] | None = None
    order: PositiveInt | None = None


class StatisticsBins(RDFUtilsModelBaseClass):
    bins: list[Bin]


class StatisticsOccupation(RDFUtilsModelBaseClass):
    id: str
    label: str
    count: int = 0
    children: typing.List["StatisticsOccupation"] | None = None


class StatisticsOccupationReturn(RDFUtilsModelBaseClass):
    tree: StatisticsOccupation
