#!/bin/bash

gunicorn intavia_backend.main:app -w 4 --timeout=200 --threads=4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000
