import json
import math
from pathlib import Path
from statistics import mean

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
    allow_credentials=False,
)

DATA_FILE = Path(__file__).resolve().parent / "q-vercel-latency.json"

with DATA_FILE.open(encoding="utf-8") as file:
    telemetry = json.load(file)


class MetricsRequest(BaseModel):
    regions: list[str]
    threshold_ms: float


def percentile_95(values):
    ordered = sorted(values)
    position = (len(ordered) - 1) * 0.95
    lower = math.floor(position)
    upper = math.ceil(position)

    return (
        ordered[lower]
        + (ordered[upper] - ordered[lower]) * (position - lower)
    )


@app.get("/")
def home():
    return {
        "message": "Telemetry API is running",
        "post_endpoint": "/metrics",
        "test_page": "/docs",
    }


@app.post("/metrics")
def calculate_metrics(body: MetricsRequest):
    result = {}

    for region in body.regions:
        records = [
            record
            for record in telemetry
            if record["region"] == region
        ]

        if not records:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown region: {region}",
            )

        latencies = [record["latency_ms"] for record in records]
        uptimes = [record["uptime_pct"] for record in records]

        result[region] = {
            "avg_latency": mean(latencies),
            "p95_latency": percentile_95(latencies),
            "avg_uptime": mean(uptimes),
            "breaches": sum(
                latency > body.threshold_ms
                for latency in latencies
            ),
        }

    return result
