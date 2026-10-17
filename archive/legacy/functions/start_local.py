#!/usr/bin/env python3
"""
Simple startup script for local FPL API
"""

import uvicorn
import logging
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting FPL Prediction App (Local Mode)")
    
    try:
        # Try to start the local API
        logger.info("Starting local API server on http://localhost:8000")
        uvicorn.run(
            "src.api.local_main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Failed to start local API: {e}")
        
        # Fallback: try the pytorch API without scheduler
        try:
            logger.info("Trying PyTorch API as fallback...")
            uvicorn.run(
                "src.api.pytorch_main:app",
                host="127.0.0.1", 
                port=8000,
                reload=False,
                log_level="info"
            )
        except Exception as e2:
            logger.error(f"Both APIs failed: {e2}")
            print("\nAPI startup failed. Let's run a simple health check instead.")
            
            # Simple health check
            from src.database.local_db import LocalDatabase
            db = LocalDatabase()
            players = db.get_all_players()
            print(f"✅ Database working: {len(players)} players loaded")
            return

if __name__ == "__main__":
    main()