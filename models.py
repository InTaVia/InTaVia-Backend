from copy import deepcopy
from dataclasses import dataclass
from distutils.command.config import config
from inspect import getmro
import re
from tkinter import W
import typing
from xmlrpc.client import Boolean
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    NonNegativeInt,
    PositiveInt,
    ValidationError,
    constr,
)
from pydantic.dataclasses import dataclass
from pydantic.utils import GetterDict
from pydantic.fields import ModelField
from enum import Enum
from geojson_pydantic import Polygon, Point
from typing import Any, Callable, Union
import datetime

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


class InTaViaConfig:
    validate_assignment = True


class InTaViaModelBaseClass(BaseModel):
    def flatten_rdf_data(self, data: dict) -> list:
        """Flatten the RDF data to a list of dicts. Stores it also in the object.

        Args:
            data (dict): The RDF data

        Returns:
            list: A list of dicts
        """
        flattened_data = []
        for ent in data["results"]:
            d_res = {}
            for k, v in ent.items():
                if isinstance(v, dict):
                    if "value" in v:
                        if "datatype" in v:
                            if v["datatype"] == "http://www.w3.org/2001/XMLSchema#dateTime":
                                v["value"] = datetime.datetime.fromisoformat(v["value"].replace("Z", "+00:00"))
                            elif v["datatype"] == "http://www.w3.org/2001/XMLSchema#integer":
                                v["value"] = int(v["value"])
                            elif v["datatype"] == "http://www.w3.org/2001/XMLSchema#boolean":
                                v["value"] = bool(v["value"])
                            elif v["datatype"] == "http://www.w3.org/2001/XMLSchema#float":
                                v["value"] = float(v["value"])
                        d_res[k] = v["value"]
                    else:
                        d_res[k] = v
                else:
                    d_res[k] = v
            flattened_data.append(d_res)
        return flattened_data

    @staticmethod
    def filter_sparql(
        data: list | dict,
        filters: typing.List[typing.Tuple[str, str]] | None = None,
        list_of_keys: typing.List[str] = None,
        anchor: str | None = None,
        additional_values: typing.List[str] | None = None,
    ) -> typing.List[dict] | None:
        """filters sparql result for key value pairs

        Args:
            data (list): array of results from sparql endpoint (python object converted from json return)
            filter (typing.List[tuple]): list of tuples containing key / value pair to filter on
            list_of_keys (typing.List[str], optional): list of keys to return. Defaults to None.
            additional_values (typing.List[str], optional): list of additional values to return. Defaults to None.

        Returns:
            typing.List[dict] | None: list of dictionaries containing keys and values
        """
        if isinstance(data, dict):
            data = [data]
        if additional_values is None:
            additional_values = []
        if filters is not None:
            while len(filters) > 0 and len(data) > 0:
                f1 = filters.pop(0)
                data_res = list(filter(lambda x: (x[f1[0]] == f1[1]), data))
            data = data_res
        if len(data) == 0:
            return None
        res = []
        if list_of_keys is not None:
            data = [{k: v for k, v in d.items() if k in list_of_keys} for d in data]
        if anchor is not None:
            lst_unique_vals = set([x[anchor] for x in data])
            res_fin_anchor = []
            for item in lst_unique_vals:
                add_vals = []
                res1 = {}
                for i2 in list(filter(lambda d: d[anchor] == item, data)):
                    add_vals_dict = deepcopy(i2)
                    for k, v in i2.items():
                        if k in additional_values or k == anchor:
                            if k not in res1:
                                res1[k] = v
                            else:
                                if isinstance(res1[k], str):
                                    if v != res1[k]:
                                        res1[k] = [res1[k], v]
                                elif isinstance(res1[k], int):
                                    if v != res1[k]:
                                        res1[k] = [res1[k], v]
                                elif isinstance(res1[k], float):
                                    if v != res1[k]:
                                        res1[k] = [res1[k], v]
                                elif v not in res1[k]:
                                    res1[k].append(v)
                            # del add_vals_dict[k]
                    add_vals.append(add_vals_dict)
                res1["results"] = add_vals
                res_fin_anchor.append(res1)
            return res_fin_anchor
        return data

    def get_anchor_element_from_field(self, field: ModelField) -> typing.Tuple[str, ModelField] | None:
        for f_name, f_class in field.type_.__fields__.items():
            f_conf = f_class.field_info.extra.get("rdfconfig", object())
            if getattr(f_conf, "anchor", False):
                if getattr(f_conf, "path", False):
                    f_name = getattr(f_conf, "path")
                return f_name, f_class
        return None

    def get_rdf_variables_from_field(self, field: ModelField) -> typing.List[str]:
        res = []
        for f_name, f_class in field.type_.__fields__.items():
            f_conf = f_class.field_info.extra.get("rdfconfig", object())
            if hasattr(f_conf, "path"):
                res.append(f_conf.path)
            else:
                res.append(f_name)
        return res

    def map_fields_data(self, data: dict) -> dict:
        res = {}
        for k, v in data.items():
            if k == "results":
                res[k] = v
                continue
            for field_names, field in self.__fields__.items():
                if field.__module__ == "models":
                    res[k] = v
                    continue
                if getattr(field.field_info.extra.get("rdfconfig"), "callback_function", False):
                    v = getattr(field.field_info.extra.get("rdfconfig"), "callback_function")(v)
                f_conf = field.field_info.extra.get("rdfconfig", object())
                if hasattr(f_conf, "path"):
                    if f_conf.path == k:
                        res[field_names] = v
                else:
                    if field_names == k:
                        res[field_names] = v
        return res

    def create_data_from_rdf(self, data: list, fields: dict | None = None) -> dict | None:
        """creates data from rdf data

        Args:
            data (list): data from rdf
            fields (dict): fields to create (defaults to all fields defined in class)
        """
        if fields is None:
            fields = self.__fields__
        for field, field_class in fields.items():
            if field_class.type_.__module__ == "models":
                anch_f = self.get_anchor_element_from_field(field=field_class)
                f_fields = self.get_rdf_variables_from_field(field=field_class)
                if anch_f is not None:
                    anch_f = anch_f[0]
                rdf_data = self.filter_sparql(data=data, anchor=anch_f, list_of_keys=f_fields)
                print("test")
            else:
                pass
        anchor = False
        field_serialize = []
        data_fin = []
        for field in [item for item in fields]:
            f1 = fields[field]
            if getattr(f1.field_info.extra.get("rdfconfig", object()), "anchor", False):
                if anchor:
                    raise ValueError("Only one anchor field allowed")
                anchor = fields[field]
            if f1.type_.__module__ == "models":
                field_serialize.append(f1)
            # if f1.type_ in [str, int, float]:
            #     pass
        if not anchor:
            raise ValidationError(
                f"Every single object needs one configured anchor element: {self.__class__.__name__} does not have one."
            )
        anchor_path = getattr(anchor.field_info.extra.get("rdfconfig"), "path")
        for d in data:
            pass
        print(" ...")

    def __init__(__pydantic_self__, **data: Any) -> None:
        data = __pydantic_self__.map_fields_data(data=data)
        for field in __pydantic_self__.__fields__.values():
            if field.type_.__module__ == "models":
                anch_f = __pydantic_self__.get_anchor_element_from_field(field=field)
                f_fields = __pydantic_self__.get_rdf_variables_from_field(field=field)
                if anch_f is not None:
                    anch_f = anch_f[0]
                rdf_data = __pydantic_self__.filter_sparql(data=data["results"], anchor=anch_f, list_of_keys=f_fields)
                if rdf_data is not None:
                    if isinstance(rdf_data, list) and field.outer_type_ == list:
                        data[field.name] = [field.type_(**item) for item in rdf_data]
                    elif isinstance(rdf_data, list) and field.outer_type_ != list:
                        data[field.name] = field.type_(**rdf_data[0])
                    else:
                        data[field.name] = field.type_(**rdf_data)
                    print("init")
        super().__init__(**data)


class InTaViaModelBaseClassBak(BaseModel):
    @staticmethod
    def filter_sparql(
        data: list | dict,
        filters: typing.List[typing.Tuple[str, str]] | None = None,
        list_of_keys: typing.List[str] = None,
        anchor: str | None = None,
    ) -> typing.List[dict] | None:
        """filters sparql result for key value pairs

        Args:
            data (list): array of results from sparql endpoint (python object converted from json return)
            filter (typing.List[tuple]): list of tuples containing key / value pair to filter on
            list_of_keys (typing.List[str], optional): list of keys to return. Defaults to None.

        Returns:
            typing.List[dict] | None: list of dictionaries containing keys and values
        """
        if isinstance(data, dict):
            data = [data]
        if filters is not None:
            while len(filters) > 0 and len(data) > 0:
                f1 = filters.pop(0)
                data = list(filter(lambda x: (x[f1[0]]["value"] == f1[1]), data))
        if len(data) == 0:
            return None
        res = []
        for item in data:
            d1 = dict()
            for key, value in item.items():
                if list_of_keys is None or key in list_of_keys:
                    d1[key] = value["value"]
            res.append(d1)
        if anchor is not None:
            lst_unique_vals = set([x[anchor] for x in res])
            res_fin_anchor = []
            for item in lst_unique_vals:
                res1 = {}
                for i2 in list(filter(lambda d: d[anchor] == item, res)):
                    for k, v in i2.items():
                        if k not in res1:
                            res1[k] = v
                        else:
                            if isinstance(res1[k], str):
                                if v != res1[k]:
                                    res1[k] = [res1[k], v]
                            elif v not in res1[k]:
                                res1[k].append(v)
                res_fin_anchor.append(res1)
            return res_fin_anchor
        return res

    def get_anchor_element_from_field(self, field: ModelField) -> ModelField | None:
        for f_name, f_class in field.type_.__fields__.items():
            f_conf = f_class.field_info.extra.get("rdfconfig", object())
            if getattr(f_conf, "anchor", False):
                return f_name, f_class
        return None

    def filter_data_for_related_field(self, data: any, field: str) -> any:
        pass

    def get_rdf_variables_from_field(self, field: ModelField) -> typing.List[str]:
        res = []
        for f_name, f_class in field.type_.__fields__.items():
            f_conf = f_class.field_info.extra.get("rdfconfig", object())
            if hasattr(f_conf, "path"):
                res.append(f_conf.path)
            else:
                res.append(f_name)
        return res

    def create_data_from_rdf(self, data: list, fields: dict | None = None) -> dict | None:
        """creates data from rdf data

        Args:
            data (list): data from rdf
            fields (dict): fields to create (defaults to all fields defined in class)
        """
        if fields is None:
            fields = self.__fields__
        # fields_parent = []
        # for key, value in fields.items():
        #     for cls in getmro(self.__class__)[2:]:
        #         if cls.__module__ != 'models':
        #             continue
        #         if key in cls.__fields__:
        #             fields_parent.append(key)
        #             break
        for field, field_class in fields.items():
            if field_class.type_.__module__ == "models":
                anch_f = self.get_anchor_element_from_field(field=field_class)
                f_fields = self.get_rdf_variables_from_field(field=field_class)
                if anch_f is not None:
                    anch_f = anch_f[0]
                rdf_data = self.filter_sparql(data=data, anchor=anch_f, list_of_keys=f_fields)
                print("test")
            else:
                pass
        anchor = False
        field_serialize = []
        data_fin = []
        for field in [item for item in fields]:
            f1 = fields[field]
            if getattr(f1.field_info.extra.get("rdfconfig", object()), "anchor", False):
                if anchor:
                    raise ValueError("Only one anchor field allowed")
                anchor = fields[field]
            if f1.type_.__module__ == "models":
                field_serialize.append(f1)
            # if f1.type_ in [str, int, float]:
            #     pass
        if not anchor:
            raise ValidationError(
                f"Every single object needs one configured anchor element: {self.__class__.__name__} does not have one."
            )
        anchor_path = getattr(anchor.field_info.extra.get("rdfconfig"), "path")
        for d in data:
            pass
        print(" ...")

    # def __init__(__pydantic_self__, **data: Any) -> None:
    #     __pydantic_self__.create_data_from_rdf(data)
    #     super().__init__(**data)


class FieldConfigurationRDF(BaseModel):
    path: constr(regex="^[a-zA-Z0-9\.]+$")
    anchor: Boolean = False
    default_value: Boolean = False
    callback_function: Callable | None = None


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

    # def __init__(__pydantic_self__, **data: Any) -> None:
    #     super().__init__(**data)


class InternationalizedLabel(InTaViaModelBaseClass):
    """Used to provide internationalized labels"""

    default: str = Field(..., rdfconfig=FieldConfigurationRDF(path="entityLabel", anchor=True))
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


class Source(InTaViaModelBaseClass):
    citation: str = Field(..., rdfconfig=FieldConfigurationRDF(path="person", callback_function=get_source_mapping))


class LinkedIdProvider(BaseModel):
    label: str
    baseUrl: HttpUrl


class LinkedId(BaseModel):
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


class EntityBase(InTaViaModelBaseClass):
    id: str = Field(..., rdfconfig=FieldConfigurationRDF(path="person", anchor=True))
    label: InternationalizedLabel | None = None
    # FIXME: For the moment we determine that via the URI, needs to be fixed when provenance is in place
    source: Source | None = None
    # linkedIds: list[LinkedId] | None = None
    # _linkedIds: list[HttpUrl] | None = None
    # alternativeLabels: list[InternationalizedLabel] | None = None
    # description: str | None = None
    # media: list[MediaResource] | None = None
    # relations: list["EntityEventRelation"] | None = None

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


class GenderType(BaseModel):
    id: str
    label: InternationalizedLabel


class Person(EntityBase):
    kind = "person"
    # gender: GenderType | None = None
    # occupations: typing.List[Occupation] | None = None

    # def __init__(__pydantic_self__, **data: Any) -> None:
    #     if "gender" in data:    # FIXME: This should be fixed in the data, by adding a label to the gender type
    #         if "label" not in data["gender"]:
    #             data["gender"]["label"] = {
    #                 "default": data["gender"]["id"].split("/")[-1]}
    #     super().__init__(**data)


class Place(EntityBase):
    kind = "place"
    _lat_long: str | None = None
    geometry: Union[Polygon, Point] | None = None

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
    entity: Union[Person, Place, Group, CulturalHeritageObject, HistoricalEvent] | None = None
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


class EntityEvent(BaseModel):
    id: str
    label: InternationalizedLabel | None = None
    source: Source | None = None
    # _source_entity_role: EntityRelationRole | None = None
    # _self_added: Boolean = False
    # kind: EntityEventKind | None = None
    # startDate: str | None = None
    # endDate: str | None = None
    # place: Place | None = None
    # relations: typing.List[EntityEventRelation] | None = None


class PersonFull(Person):
    event: str = "test"
    # events: typing.List["EntityEvent"] | None = None

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


class PaginatedResponseBase(InTaViaModelBaseClass):
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
    results: typing.List[Union[PersonFull, PlaceFull, GroupFull]] = Field(..., path="person", description="tetst")
    errors: typing.List[ValidationErrorModel] | None = None

    def __init__(self, **data: Any) -> None:
        # self.create_data_from_rdf(data)
        data_flattened = self.flatten_rdf_data(data)
        res = []
        data_person = self.filter_sparql(
            data=data_flattened,
            filters=[
                ("entityTypeLabel", "person"),
            ],
            anchor="person",
        )
        errors = []
        for person in data_person:
            try:
                res.append(PersonFull(**person))
            except ValidationError as e:
                errors.append({"id": person["person"], "error": str(e)})

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
