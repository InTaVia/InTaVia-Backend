#!/bin/bash

memcached -d
uvicorn main:app --host 0.0.0.0 --port 5000