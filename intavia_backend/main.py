import os
import aioredis
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi_versioning import VersionedFastAPI
import sentry_sdk
from .main_v1 import router as router_v1
from .main_v2 import router as router_v2
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache


app = FastAPI(
    docs_url="/",
    title="InTaVia IDM-Json Backend",
    description="Development version of the InTaVia backend.",
    version="0.1.0",
)


app.include_router(router_v1)
app.include_router(router_v2)
# origins = ["http://localhost:3000", "https://intavia.acdh-dev.oeaw.ac.at", "https://intavia-workshop.vercel.app"]
origins = ["*"]

sentry_sdk.init(
    dsn="https://936a6c77abda4ced81e17cd4e27906a7@o4504360778661888.ingest.sentry.io/4504361556574208",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production,
    traces_sample_rate=1.0,
)


app = VersionedFastAPI(app, version_format="{major}", prefix_format="/v{major}")


@app.on_event("startup")
async def startup():
    redis = aioredis.from_url(
        f"redis://{os.environ.get('REDIS_HOST', 'localhost')}", encoding="utf8", decode_responses=True, db=1
    )
    FastAPICache.init(RedisBackend(redis), prefix="api-cache")


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
