from copy import deepcopy
from dataclasses import dataclass
from distutils.command.config import config
import re
import typing
from xmlrpc.client import Boolean
from pydantic import BaseModel, Field, HttpUrl, NonNegativeInt, PositiveInt, ValidationError, constr
from pydantic.dataclasses import dataclass
from pydantic.utils import GetterDict
from enum import Enum
from geojson_pydantic import Polygon, Point
from typing import Any, Union
import datetime


class FieldConfigurationRDF(BaseModel):
    path: constr(regex="^[a-zA-Z0-9\.]+$")
    anchor: Boolean = False


class InTaViaBaseModel(BaseModel):

    def create_data_from_json(self, data):
        pass

    def __init__(__pydantic_self__, **data: Any) -> None:
        __pydantic_self__.create_data_from_json(data)
        super().__init__(**data)

class IntTestModel(InTaViaBaseModel):
    id: int = Field(rdfconfig=FieldConfigurationRDF(path="test.test2"))

IntTestModel(**{"id": "1"})