import pandas as pd
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import asyncio
import aiohttp
from pathlib import Path
import json
from .fpl_api import FPLDataFetcher

logger = logging.getLogger(__name__)

class LiveDataManager:
    def __init__(self, cache_dir: str = "./data/live_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.fpl_fetcher = FPLDataFetcher()
        self.last_update = None
        
    def get_current_gameweek(self) -> int:
        """Get the current active gameweek"""
        try:
            bootstrap = self.fpl_fetcher.get_bootstrap_data()
            events = bootstrap['events']
            
            for event in events:
                if event['is_current']:
                    return event['id']
            
            # If no current gameweek, find next one
            for event in events:
                if event['is_next']:
                    return event['id']
                    
            return 1  # Fallback
        except Exception as e:
            logger.error(f"Error getting current gameweek: {e}")
            return 1
    
    def get_current_season_data(self) -> pd.DataFrame:
        """Fetch current season player data with latest stats"""
        try:
            players_df = self.fpl_fetcher.get_all_players_data()
            
            # Add additional calculated fields
            players_df['form_rating'] = players_df['form'].astype(float)
            players_df['value_score'] = (
                players_df['total_points'].astype(float) / 
                (players_df['now_cost'].astype(float) / 10)
            )
            
            # Add price change trend
            players_df['price_change_trend'] = (
                players_df['cost_change_event'].astype(float) + 
                players_df['cost_change_start'].astype(float)
            )
            
            return players_df
            
        except Exception as e:
            logger.error(f"Error fetching current season data: {e}")
            raise
    
    def get_upcoming_fixtures(self, gameweeks: int = 5) -> pd.DataFrame:
        """Get upcoming fixtures for next N gameweeks"""
        try:
            current_gw = self.get_current_gameweek()
            all_fixtures = []
            
            for gw in range(current_gw, current_gw + gameweeks):
                fixtures = self.fpl_fetcher.get_fixtures(gw)
                for fixture in fixtures:
                    fixture['gameweek'] = gw
                all_fixtures.extend(fixtures)
            
            fixtures_df = pd.DataFrame(all_fixtures)
            
            if not fixtures_df.empty:
                fixtures_df['kickoff_time'] = pd.to_datetime(fixtures_df['kickoff_time'])
                fixtures_df = fixtures_df.sort_values('kickoff_time')
            
            return fixtures_df
            
        except Exception as e:
            logger.error(f"Error fetching upcoming fixtures: {e}")
            return pd.DataFrame()
    
    def get_live_gameweek_updates(self) -> Dict:
        """Get live updates for current gameweek"""
        try:
            current_gw = self.get_current_gameweek()
            live_data = self.fpl_fetcher.get_live_gameweek_data(current_gw)
            
            # Process live player stats
            live_stats = {}
            if 'elements' in live_data:
                for player_data in live_data['elements']:
                    player_id = player_data['id']
                    stats = player_data['stats']
                    
                    live_stats[player_id] = {
                        'minutes': stats.get('minutes', 0),
                        'goals_scored': stats.get('goals_scored', 0),
                        'assists': stats.get('assists', 0),
                        'clean_sheets': stats.get('clean_sheets', 0),
                        'goals_conceded': stats.get('goals_conceded', 0),
                        'yellow_cards': stats.get('yellow_cards', 0),
                        'red_cards': stats.get('red_cards', 0),
                        'saves': stats.get('saves', 0),
                        'bonus': stats.get('bonus', 0),
                        'total_points': stats.get('total_points', 0)
                    }
            
            return {
                'gameweek': current_gw,
                'player_stats': live_stats,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error fetching live gameweek updates: {e}")
            return {}
    
    def get_player_injury_status(self) -> Dict:
        """Get injury and availability status for all players"""
        try:
            players_df = self.fpl_fetcher.get_all_players_data()
            
            injury_status = {}
            for _, player in players_df.iterrows():
                player_id = player['id']
                status = player.get('status', 'a')  # 'a' = available
                chance_of_playing = player.get('chance_of_playing_next_round')
                
                injury_status[player_id] = {
                    'name': f"{player['first_name']} {player['second_name']}",
                    'status': status,
                    'chance_of_playing': chance_of_playing,
                    'news': player.get('news', ''),
                    'news_added': player.get('news_added', ''),
                    'is_available': status == 'a',
                    'is_injured': status in ['i', 'd'],  # injured, doubtful
                    'is_suspended': status == 's'
                }
            
            return injury_status
            
        except Exception as e:
            logger.error(f"Error fetching injury status: {e}")
            return {}
    
    def get_price_changes(self) -> List[Dict]:
        """Track recent price changes"""
        try:
            players_df = self.fpl_fetcher.get_all_players_data()
            
            price_changes = []
            for _, player in players_df.iterrows():
                event_change = player.get('cost_change_event', 0)
                season_change = player.get('cost_change_start', 0)
                
                if event_change != 0:
                    price_changes.append({
                        'player_id': player['id'],
                        'name': f"{player['first_name']} {player['second_name']}",
                        'team': player['name_team'],
                        'position': player['position'],
                        'current_price': player['now_cost'] / 10,
                        'event_change': event_change / 10,
                        'season_change': season_change / 10,
                        'ownership': player.get('selected_by_percent', 0)
                    })
            
            # Sort by absolute change amount
            price_changes.sort(key=lambda x: abs(x['event_change']), reverse=True)
            
            return price_changes
            
        except Exception as e:
            logger.error(f"Error fetching price changes: {e}")
            return []
    
    def update_live_data(self) -> Dict:
        """Comprehensive live data update"""
        try:
            logger.info("Starting live data update...")
            
            # Get all live data
            current_players = self.get_current_season_data()
            fixtures = self.get_upcoming_fixtures()
            live_gameweek = self.get_live_gameweek_updates()
            injury_status = self.get_player_injury_status()
            price_changes = self.get_price_changes()
            
            # Cache the data
            timestamp = datetime.now()
            cache_data = {
                'timestamp': timestamp.isoformat(),
                'current_gameweek': self.get_current_gameweek(),
                'players_count': len(current_players),
                'fixtures_count': len(fixtures),
                'live_updates': live_gameweek,
                'injury_updates': len([p for p in injury_status.values() if not p['is_available']]),
                'price_changes': len(price_changes)
            }
            
            # Save to cache
            cache_file = self.cache_dir / f"live_update_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            # Save current data
            current_players.to_csv(self.cache_dir / "current_players.csv", index=False)
            fixtures.to_csv(self.cache_dir / "upcoming_fixtures.csv", index=False)
            
            with open(self.cache_dir / "injury_status.json", 'w') as f:
                json.dump(injury_status, f, indent=2)
            
            with open(self.cache_dir / "price_changes.json", 'w') as f:
                json.dump(price_changes, f, indent=2)
            
            self.last_update = timestamp
            
            logger.info(f"Live data update completed at {timestamp}")
            
            return {
                'success': True,
                'timestamp': timestamp.isoformat(),
                'summary': cache_data
            }
            
        except Exception as e:
            logger.error(f"Error in live data update: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def should_update(self, max_age_minutes: int = 30) -> bool:
        """Check if data needs updating based on age"""
        if self.last_update is None:
            return True
        
        age = datetime.now() - self.last_update
        return age.total_seconds() / 60 > max_age_minutes
    
    def get_cached_data(self) -> Dict:
        """Get the most recent cached data"""
        try:
            players_file = self.cache_dir / "current_players.csv"
            fixtures_file = self.cache_dir / "upcoming_fixtures.csv"
            injury_file = self.cache_dir / "injury_status.json"
            price_file = self.cache_dir / "price_changes.json"
            
            data = {}
            
            if players_file.exists():
                data['players'] = pd.read_csv(players_file)
            
            if fixtures_file.exists():
                data['fixtures'] = pd.read_csv(fixtures_file)
            
            if injury_file.exists():
                with open(injury_file, 'r') as f:
                    data['injuries'] = json.load(f)
            
            if price_file.exists():
                with open(price_file, 'r') as f:
                    data['price_changes'] = json.load(f)
            
            return data
            
        except Exception as e:
            logger.error(f"Error loading cached data: {e}")
            return {}