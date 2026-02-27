#!/usr/bin/env python3
"""Start script for the OmniNode Cyber-Physical War Room multi-agent backend."""

import asyncio
import logging
import os
import uvicorn
from contextlib import asynccontextmanager

import argparse
from src.simulation.power_grid import PowerGridSimulation
from src.simulation.data_generator import DataGenerator
from src.common.llm_client import create_strategic_llm, create_coordinator_llm
from src.strategic.agent import StrategicAgent
from src.coordination.zone_coordinator import ZoneCoordinator
from src.strategic.monitor import MonitoringLoop
from src.registry.server import app

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# We will run the FastAPI 'app' from src.registry.server directly since it has the WS routes.
# Wait, src.registry.server.app is a global object, we just need to start the background tasks.
# We will use uvicorn to run it.

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start OmniNode War Room Backend")
    parser.add_argument("--real", action="store_true", help="Run with live LLMs and physical simulation instead of mock events")
    args = parser.parse_args()

    if args.real:
        logger.info("Starting OmniNode War Room Backend (REAL LLM MODE)")
        os.environ["DEMO_MODE"] = "0"
    else:
        logger.info("Starting OmniNode War Room Backend (MOCK DEMO MODE)")
        os.environ["DEMO_MODE"] = "1"
    
    # We will run the FastAPI 'app' from src.registry.server. 
    # Startup tasks in `registry/server.py` will boot either mock stream or real AI agents.
    uvicorn.run("src.registry.server:app", host="0.0.0.0", port=8000, reload=True)
