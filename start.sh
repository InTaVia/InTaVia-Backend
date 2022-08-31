#!/bin/bash

memcached -d
gunicorn main:app -w 4 --timeout 200 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000