"""Main FastAPI Application Entrypoint for LumiSense.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import init_db
from app.serial.collector import serial_collector
from app.services.simulation_worker import simulation_worker

from app.api.routes_system import router as system_router
from app.api.routes_sensors import router as sensors_router
from app.api.routes_ml import router as ml_router
from app.api.routes_simulation import router as simulation_router
from app.api.routes_recommendations import router as recommendations_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("lumisense")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing LumiSense Database...")
    init_db()

    logger.info("Starting background serial collector...")
    serial_collector.start()

    yield

    # Shutdown
    logger.info("Shutting down background workers...")
    serial_collector.stop()
    simulation_worker.stop()
    logger.info("LumiSense backend gracefully stopped.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_SUBTITLE,
    version=settings.VERSION,
    lifespan=lifespan
)

# Enable CORS for local React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(system_router, prefix="/api", tags=["System & Settings"])
app.include_router(sensors_router, prefix="/api/sensors", tags=["Sensors & Telemetry"])
app.include_router(ml_router, prefix="/api/ml", tags=["Machine Learning"])
app.include_router(simulation_router, prefix="/api/simulation", tags=["Simulation"])
app.include_router(recommendations_router, prefix="/api/recommendations", tags=["Recommendations & Efficiency"])

@app.get("/")
def root():
    return {
        "project": settings.PROJECT_NAME,
        "subtitle": settings.PROJECT_SUBTITLE,
        "docs_url": "/docs",
        "api_health": "/api/health",
        "system_status": "/api/status"
    }
