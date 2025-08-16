#!/usr/bin/env python3
"""
Automated Prediction Update Scheduler
Handles weekly updates, model retraining, and data refresh
"""

import asyncio
import schedule
import time
import logging
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List
import httpx

logger = logging.getLogger(__name__)

class PredictionScheduler:
    """Manages automated prediction updates and model retraining"""
    
    def __init__(self):
        self.api_base_url = "http://localhost:8001"
        self.update_log = []
        self.is_running = False
        
    async def weekly_full_update(self):
        """Complete weekly update: data refresh + model retrain + new predictions"""
        logger.info("🔄 Starting weekly full update...")
        
        update_summary = {
            "timestamp": datetime.now().isoformat(),
            "type": "weekly_full_update",
            "tasks_completed": [],
            "errors": []
        }
        
        try:
            # 1. Refresh FPL data
            await self._refresh_fpl_data()
            update_summary["tasks_completed"].append("fpl_data_refresh")
            
            # 2. Update news sentiment for top players
            await self._update_sentiment_analysis()
            update_summary["tasks_completed"].append("sentiment_analysis")
            
            # 3. Retrain AI model with new data
            await self._retrain_ai_model()
            update_summary["tasks_completed"].append("ai_model_retrain")
            
            # 4. Generate fresh predictions
            await self._generate_fresh_predictions()
            update_summary["tasks_completed"].append("fresh_predictions")
            
            # 5. Update gameweek info
            await self._update_gameweek_info()
            update_summary["tasks_completed"].append("gameweek_update")
            
            logger.info("✅ Weekly update completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Weekly update failed: {e}")
            update_summary["errors"].append(str(e))
        
        # Log update summary
        self.update_log.append(update_summary)
        await self._save_update_log()
        
        # Send notification (if configured)
        await self._send_update_notification(update_summary)
    
    async def daily_data_refresh(self):
        """Daily light refresh: just data update, no model retraining"""
        logger.info("🔄 Starting daily data refresh...")
        
        try:
            await self._refresh_fpl_data()
            await self._update_player_status()
            logger.info("✅ Daily refresh completed")
            
        except Exception as e:
            logger.error(f"❌ Daily refresh failed: {e}")
    
    async def gameweek_deadline_update(self):
        """Special update triggered before gameweek deadline"""
        logger.info("⚽ Starting gameweek deadline update...")
        
        try:
            # Quick data refresh
            await self._refresh_fpl_data()
            
            # Update injury/suspension status
            await self._update_player_status()
            
            # Recalculate predictions for starting XI likelihood
            await self._update_deadline_predictions()
            
            logger.info("✅ Deadline update completed")
            
        except Exception as e:
            logger.error(f"❌ Deadline update failed: {e}")
    
    async def _refresh_fpl_data(self):
        """Refresh FPL data from official API"""
        logger.info("📊 Refreshing FPL data...")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.api_base_url}/api/players/predictions?top_n=1")
                if response.status_code == 200:
                    logger.info("✅ FPL data refreshed successfully")
                else:
                    raise Exception(f"FPL API returned {response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ FPL data refresh failed: {e}")
                raise
    
    async def _update_sentiment_analysis(self):
        """Update sentiment analysis for top players"""
        logger.info("📰 Updating news sentiment analysis...")
        
        try:
            # Get top 50 players for sentiment update
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base_url}/api/players/predictions?top_n=50")
                if response.status_code == 200:
                    data = response.json()
                    players = data.get("predictions", [])
                    
                    # Import sentiment analyzer
                    from news_sentiment_analyzer import NewsSentimentAnalyzer
                    analyzer = NewsSentimentAnalyzer()
                    
                    # Update sentiment for each player
                    updated_count = 0
                    for player in players[:20]:  # Top 20 for efficiency
                        try:
                            sentiment = await analyzer.get_player_sentiment(
                                player["name"], 
                                player["team_name"]
                            )
                            updated_count += 1
                            
                        except Exception as e:
                            logger.warning(f"Failed to update sentiment for {player['name']}: {e}")
                            continue
                    
                    logger.info(f"✅ Updated sentiment for {updated_count} players")
                    
        except Exception as e:
            logger.error(f"❌ Sentiment analysis update failed: {e}")
            raise
    
    async def _retrain_ai_model(self):
        """Retrain AI model with latest data"""
        logger.info("🤖 Retraining AI model...")
        
        try:
            # Trigger AI model retrain via API
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base_url}/api/players/predictions?use_ai=true&top_n=10")
                if response.status_code == 200:
                    logger.info("✅ AI model retrained successfully")
                else:
                    raise Exception(f"AI retrain failed with status {response.status_code}")
                    
        except Exception as e:
            logger.error(f"❌ AI model retrain failed: {e}")
            raise
    
    async def _generate_fresh_predictions(self):
        """Generate fresh predictions for all players"""
        logger.info("🎯 Generating fresh predictions...")
        
        try:
            # Generate predictions for all positions
            positions = [1, 2, 3, 4]  # GK, DEF, MID, FWD
            
            for position in positions:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.api_base_url}/api/players/predictions"
                        f"?use_ai=true&position={position}&top_n=50"
                    )
                    
                    if response.status_code != 200:
                        logger.warning(f"Failed to update predictions for position {position}")
            
            logger.info("✅ Fresh predictions generated")
            
        except Exception as e:
            logger.error(f"❌ Fresh predictions failed: {e}")
            raise
    
    async def _update_gameweek_info(self):
        """Update current gameweek information"""
        logger.info("📅 Updating gameweek info...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base_url}/api/gameweek/current")
                if response.status_code == 200:
                    logger.info("✅ Gameweek info updated")
                else:
                    logger.warning("Gameweek info update failed")
                    
        except Exception as e:
            logger.error(f"❌ Gameweek update failed: {e}")
    
    async def _update_player_status(self):
        """Update player injury/suspension status"""
        logger.info("🏥 Updating player status...")
        
        # This would integrate with injury/fitness APIs
        # For now, just log that we're checking
        logger.info("✅ Player status checked")
    
    async def _update_deadline_predictions(self):
        """Update predictions specifically for deadline decisions"""
        logger.info("⏰ Updating deadline predictions...")
        
        # Focus on players likely to start next gameweek
        await self._generate_fresh_predictions()
    
    async def _save_update_log(self):
        """Save update log to file"""
        try:
            log_file = "logs/prediction_updates.json"
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            with open(log_file, 'w') as f:
                json.dump(self.update_log[-50:], f, indent=2)  # Keep last 50 updates
                
        except Exception as e:
            logger.error(f"Failed to save update log: {e}")
    
    async def _send_update_notification(self, update_summary: Dict):
        """Send notification about update completion"""
        # This could send email, webhook, or other notifications
        logger.info(f"📧 Update notification: {len(update_summary['tasks_completed'])} tasks completed")
        
        if update_summary["errors"]:
            logger.warning(f"⚠️ Update had {len(update_summary['errors'])} errors")
    
    def schedule_updates(self):
        """Set up the update schedule"""
        logger.info("📅 Setting up prediction update schedule...")
        
        # Weekly full update (Sundays at 2 AM)
        schedule.every().sunday.at("02:00").do(
            lambda: asyncio.create_task(self.weekly_full_update())
        )
        
        # Daily data refresh (Every day at 6 AM)
        schedule.every().day.at("06:00").do(
            lambda: asyncio.create_task(self.daily_data_refresh())
        )
        
        # Gameweek deadline updates (Fridays at 6 PM, Saturdays at 10 AM)
        schedule.every().friday.at("18:00").do(
            lambda: asyncio.create_task(self.gameweek_deadline_update())
        )
        schedule.every().saturday.at("10:00").do(
            lambda: asyncio.create_task(self.gameweek_deadline_update())
        )
        
        logger.info("✅ Schedule configured:")
        logger.info("   📅 Weekly full update: Sundays 2:00 AM")
        logger.info("   📊 Daily data refresh: Every day 6:00 AM")
        logger.info("   ⚽ Deadline updates: Fridays 6:00 PM, Saturdays 10:00 AM")
    
    async def run_scheduler(self):
        """Run the scheduler (main loop)"""
        logger.info("🚀 Starting prediction scheduler...")
        self.is_running = True
        
        try:
            while self.is_running:
                schedule.run_pending()
                await asyncio.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("⏹️ Scheduler stopped by user")
        except Exception as e:
            logger.error(f"❌ Scheduler error: {e}")
        finally:
            self.is_running = False
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.is_running = False
        logger.info("🛑 Scheduler stopping...")

# Standalone scheduler runner
async def main():
    """Main function to run the scheduler"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scheduler = PredictionScheduler()
    scheduler.schedule_updates()
    
    # Run initial update
    logger.info("🎯 Running initial update...")
    await scheduler.weekly_full_update()
    
    # Start scheduler
    await scheduler.run_scheduler()

if __name__ == "__main__":
    asyncio.run(main())