import pandas as pd
import requests
from typing import Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ExternalDatasets:
    def __init__(self, cache_dir: str = "./data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.vaastav_base_url = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"
        
    def fetch_vaastav_historical_data(self, season: str = "2024-25") -> pd.DataFrame:
        url = f"{self.vaastav_base_url}/{season}/gws/merged_gw.csv"
        cache_file = self.cache_dir / f"vaastav_{season.replace('-', '_')}.csv"
        
        try:
            if cache_file.exists():
                logger.info(f"Loading cached data from {cache_file}")
                return pd.read_csv(cache_file)
            
            logger.info(f"Fetching Vaastav data for season {season}")
            df = pd.read_csv(url)
            df.to_csv(cache_file, index=False)
            return df
        except Exception as e:
            logger.error(f"Error fetching Vaastav data: {e}")
            raise
    
    def fetch_player_historical_data(self, season: str = "2024-25") -> pd.DataFrame:
        url = f"{self.vaastav_base_url}/{season}/cleaned_players.csv"
        cache_file = self.cache_dir / f"players_{season.replace('-', '_')}.csv"
        
        try:
            if cache_file.exists():
                logger.info(f"Loading cached player data from {cache_file}")
                return pd.read_csv(cache_file)
            
            logger.info(f"Fetching player data for season {season}")
            df = pd.read_csv(url)
            df.to_csv(cache_file, index=False)
            return df
        except Exception as e:
            logger.error(f"Error fetching player data: {e}")
            raise
    
    def fetch_understat_data(self, player_name: str) -> Optional[pd.DataFrame]:
        pass
    
    def combine_historical_seasons(self, seasons: list) -> pd.DataFrame:
        all_data = []
        
        for season in seasons:
            try:
                season_data = self.fetch_vaastav_historical_data(season)
                season_data['season'] = season
                
                # Fix datetime column if it exists
                if 'kickoff_time' in season_data.columns:
                    season_data['kickoff_time'] = pd.to_datetime(season_data['kickoff_time'], utc=True)
                
                all_data.append(season_data)
            except Exception as e:
                logger.warning(f"Could not fetch data for season {season}: {e}")
                continue
        
        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            
            # Ensure kickoff_time is timezone-naive for comparison
            if 'kickoff_time' in combined.columns:
                combined['kickoff_time'] = pd.to_datetime(combined['kickoff_time']).dt.tz_localize(None)
            
            return combined
        else:
            raise ValueError("No data could be fetched for any season")
    
    def get_training_data(self) -> pd.DataFrame:
        # Skip 2024-25 due to data format issues
        seasons = ["2021-22", "2022-23", "2023-24"]
        
        combined_data = self.combine_historical_seasons(seasons)
        
        if 'kickoff_time' in combined_data.columns:
            combined_data = combined_data.sort_values(['name', 'kickoff_time'])
        
        return combined_data