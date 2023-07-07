# InTaVia Backend
The InTaVia backend provides a RestAPI to the InTaVia triplestore. It expects the data in the blazegraph triplestore in the [IDM-RDF](https://github.com/InTaVia/idm-rdf/) format.

The API serves a [Ophttps://intavia-backend.acdh-dev.oeaw.ac.at/#/StatisticsenAPI3 compliant definition](https://intavia-backend.acdh-dev.oeaw.ac.at/openapi.json) of the return format as well as the query parameters.

## Endpoints

- [Query Entities](https://intavia-backend.acdh-dev.oeaw.ac.at/api/entities/search): allows to query for entities. Basic functionality of the endpoint is implemented
- [Retrieve Entity](https://intavia-backend.acdh-dev.oeaw.ac.at/api/entities/id): Allows to retriev entities by ID. Basic funtionality is implemented.
- [several vocabularies endpoints](https://intavia-backend.acdh-dev.oeaw.ac.at/#/Vocabularies): these endpoints allow to retrieve vocabulary IDs by querying for a string. The Vocab IDs can in a second step be used to query entities. Basic functionality implemented for occupations vocabulary only. Needs more vocabs.
- [several statistic endpoints](https://intavia-backend.acdh-dev.oeaw.ac.at/#/Statistics): allows to retrieve statistics on the data of the graph. These endpoints allow for the same wuery parameters as the query entities endpoint, but will return stats only. Implemented for date of birth/death and occupations

## setup for local development
The InTaVia backend needs Python 3.10 to be installed. To install a local dev version you can either use the vscode .devconteiner configuration or install a local version of [poetry](https://python-poetry.org/) and run `poetry install`.

In addition to the InTaVia backend itself and python you need a [blazegraph](https://github.com/blazegraph) and a [redis](https://github.com/redis/redis) instance running on the default ports. Easiest is to install both via docker. A docker-compose file will follow.

