from typing import Any
from pydantic import AnyUrl
from confz import ConfZ, ConfZEnvSource, ConfZFileSource


class Blazegraph(ConfZ):
    host: AnyUrl = "http://localhost"
    namespace: str = "intavia"
    port: int | None = 9999
    username: str = "root"
    password: str = "root"
    databaseurl: AnyUrl | None = None

    def __init__(self, **data: Any) -> None:
        if "databaseurl" not in data:
            host = data.get("host", self.__fields__["host"].default)
            port = data.get("port", self.__fields__["port"].default)
            namespace = data.get("namespace", self.__fields__["namespace"].default)
            self.__fields__[
                "databaseurl"
            ].default = f"{host}{':'+str(port) if port is not None else ''}/{namespace}/sparql"
        super().__init__(**data)


class APIConfig(ConfZ):
    blazegraph: Blazegraph = Blazegraph()
    debug: bool = False
    host: AnyUrl = "http://localhost"

    CONFIG_SOURCES = [
        ConfZFileSource(file_from_env="INTAVIA_CONFIG_FILE"),
        ConfZEnvSource(prefix="INTAVIA_", allow_all=True),
    ]
