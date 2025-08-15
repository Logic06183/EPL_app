import requests
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FPLDataFetcher:
    def __init__(self, base_url: str = "https://fantasy.premierleague.com/api"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def get_bootstrap_data(self) -> Dict:
        url = f"{self.base_url}/bootstrap-static/"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching bootstrap data: {e}")
            raise
    
    def get_player_history(self, player_id: int) -> Dict:
        url = f"{self.base_url}/element-summary/{player_id}/"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching player {player_id} history: {e}")
            raise
    
    def get_fixtures(self, gameweek: Optional[int] = None) -> List[Dict]:
        url = f"{self.base_url}/fixtures/"
        params = {"event": gameweek} if gameweek else {}
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching fixtures: {e}")
            raise
    
    def get_live_gameweek_data(self, gameweek: int) -> Dict:
        url = f"{self.base_url}/event/{gameweek}/live/"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching live gameweek {gameweek} data: {e}")
            raise
    
    def get_all_players_data(self) -> pd.DataFrame:
        data = self.get_bootstrap_data()
        players_df = pd.DataFrame(data['elements'])
        teams_df = pd.DataFrame(data['teams'])
        
        players_df = players_df.merge(
            teams_df[['id', 'name', 'short_name']], 
            left_on='team', 
            right_on='id', 
            suffixes=('', '_team')
        )
        
        position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        players_df['position'] = players_df['element_type'].map(position_map)
        
        return players_df
    
    def get_player_detailed_stats(self, player_id: int) -> pd.DataFrame:
        data = self.get_player_history(player_id)
        history_df = pd.DataFrame(data['history'])
        
        if not history_df.empty:
            history_df['kickoff_time'] = pd.to_datetime(history_df['kickoff_time'])
            history_df = history_df.sort_values('kickoff_time')
        
        return history_df
    
    def get_gameweek_picks(self, team_id: int, gameweek: int) -> Dict:
        url = f"{self.base_url}/entry/{team_id}/event/{gameweek}/picks/"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching team {team_id} picks for gameweek {gameweek}: {e}")
            raise