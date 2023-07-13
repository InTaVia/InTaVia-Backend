"""Wrapper around the FastApiCache-2 library"""
import os
from fastapi_cache.decorator import cache


def nocache(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

# I have an .env file, and my get_settings() reads the .env file
if os.environ.get("APIS_REDIS_CACHING", "True") == "True":
    cache = cache
else:
    cache = nocache