#!/usr/bin/env python3

import uvicorn
import logging
from src.api.main import app
from src.scheduler import FPLUpdateScheduler
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting FPL Prediction App")
    
    scheduler = FPLUpdateScheduler()
    scheduler.start()
    logger.info("Background scheduler started")
    
    port = int(os.getenv('API_PORT', 8000))
    host = os.getenv('API_HOST', '0.0.0.0')
    
    try:
        logger.info(f"Starting API server on {host}:{port}")
        uvicorn.run(
            "src.api.main:app",
            host=host,
            port=port,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        scheduler.stop()
    except Exception as e:
        logger.error(f"Server error: {e}")
        scheduler.stop()
        raise

if __name__ == "__main__":
    main()