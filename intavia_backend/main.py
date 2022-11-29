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


app = FastAPI(
    docs_url="/",
    title="InTaVia IDM-Json Backend",
    description="Development version of the InTaVia backend.",
    version="0.1.0",
)
app.include_router(router_v1)
app.include_router(router_v2)
# origins = ["http://localhost:3000", "https://intavia.acdh-dev.oeaw.ac.at", "https://intavia-workshop.vercel.app"]
origins = [*]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sentry_sdk.init(
    dsn="https://a1253a59c2564963a8f126208f03a655@sentry.acdh-dev.oeaw.ac.at/9",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production,
    traces_sample_rate=1.0,
)

# app.add_middleware(SentryAsgiMiddleware)


@app.on_event("startup")
async def startup():
    redis = aioredis.from_url(
        f"redis://{os.environ.get('REDIS_HOST', 'localhost')}", encoding="utf8", decode_responses=True, db=1
    )
    FastAPICache.init(RedisBackend(redis), prefix="api-cache")


app = VersionedFastAPI(app, version_format="{major}", prefix_format="/v{major}")
