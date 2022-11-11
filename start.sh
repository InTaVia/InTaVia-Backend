#!/bin/bash

#memcached -d
gunicorn main:app -w 4 --reload --timeout=200 --threads=4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:5010