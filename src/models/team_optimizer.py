import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from scipy.optimize import linprog
import pulp
import logging
from datetime import datetime, timedelta
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class FPLTeamOptimizer:
    def __init__(self, cache_dir: str = "./data/optimizer_cache"):
        self.budget = 100.0
        self.squad_size = 15
        self.max_players_per_team = 3
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.formation_constraints = {
            'GK': {'min': 2, 'max': 2},
            'DEF': {'min': 5, 'max': 5},
            'MID': {'min': 5, 'max': 5},
            'FWD': {'min': 3, 'max': 3}
        }
        
        self.valid_formations = [
            {'GK': 1, 'DEF': 3, 'MID': 5, 'FWD': 2},
            {'GK': 1, 'DEF': 3, 'MID': 4, 'FWD': 3},
            {'GK': 1, 'DEF': 4, 'MID': 5, 'FWD': 1},
            {'GK': 1, 'DEF': 4, 'MID': 4, 'FWD': 2},
            {'GK': 1, 'DEF': 4, 'MID': 3, 'FWD': 3},
            {'GK': 1, 'DEF': 5, 'MID': 4, 'FWD': 1},
            {'GK': 1, 'DEF': 5, 'MID': 3, 'FWD': 2},
            {'GK': 1, 'DEF': 5, 'MID': 2, 'FWD': 3}
        ]
    
    def optimize_squad(self, players_df: pd.DataFrame, predictions: Dict[int, float]) -> Dict:
        required_columns = ['id', 'web_name', 'team', 'position', 'now_cost', 'selected_by_percent']
        if not all(col in players_df.columns for col in required_columns):
            raise ValueError(f"Players dataframe must contain columns: {required_columns}")
        
        players_df = players_df.copy()
        players_df['predicted_points'] = players_df['id'].map(predictions).fillna(0)
        players_df['value_score'] = players_df['predicted_points'] / (players_df['now_cost'] / 10 + 1)
        players_df['price'] = players_df['now_cost'] / 10
        
        prob = pulp.LpProblem("FPL_Squad_Selection", pulp.LpMaximize)
        
        player_vars = {}
        for idx, player in players_df.iterrows():
            var_name = f"player_{player['id']}"
            player_vars[player['id']] = pulp.LpVariable(var_name, cat='Binary')
        
        prob += pulp.lpSum([
            player_vars[player['id']] * player['predicted_points']
            for _, player in players_df.iterrows()
        ])
        
        prob += pulp.lpSum([
            player_vars[player['id']] * player['price']
            for _, player in players_df.iterrows()
        ]) <= self.budget
        
        prob += pulp.lpSum(player_vars.values()) == self.squad_size
        
        for position, constraints in self.formation_constraints.items():
            position_players = players_df[players_df['position'] == position]
            prob += pulp.lpSum([
                player_vars[player['id']]
                for _, player in position_players.iterrows()
            ]) == constraints['min']
        
        for team_id in players_df['team'].unique():
            team_players = players_df[players_df['team'] == team_id]
            prob += pulp.lpSum([
                player_vars[player['id']]
                for _, player in team_players.iterrows()
            ]) <= self.max_players_per_team
        
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        
        if prob.status != pulp.LpStatusOptimal:
            logger.warning("Optimization did not find optimal solution")
            return self._get_fallback_squad(players_df)
        
        selected_players = []
        for player_id, var in player_vars.items():
            if var.varValue == 1:
                player_data = players_df[players_df['id'] == player_id].iloc[0]
                selected_players.append({
                    'id': player_id,
                    'name': player_data['web_name'],
                    'position': player_data['position'],
                    'team': player_data['team'],
                    'price': player_data['price'],
                    'predicted_points': player_data['predicted_points'],
                    'ownership': player_data['selected_by_percent']
                })
        
        return {
            'squad': selected_players,
            'total_cost': sum(p['price'] for p in selected_players),
            'predicted_points': sum(p['predicted_points'] for p in selected_players),
            'optimization_status': 'optimal'
        }
    
    def optimize_starting_11(self, squad: List[Dict], gameweek_predictions: Dict[int, float]) -> Dict:
        squad_df = pd.DataFrame(squad)
        squad_df['gw_prediction'] = squad_df['id'].map(gameweek_predictions).fillna(0)
        
        best_team = None
        best_score = -1
        best_formation = None
        
        for formation in self.valid_formations:
            team, score = self._select_team_for_formation(squad_df, formation)
            if score > best_score:
                best_score = score
                best_team = team
                best_formation = formation
        
        captain = max(best_team, key=lambda x: x['gw_prediction'])
        vice_captain = max([p for p in best_team if p['id'] != captain['id']], 
                          key=lambda x: x['gw_prediction'])
        
        bench = [p for p in squad if p['id'] not in [player['id'] for player in best_team]]
        bench_sorted = sorted(bench, key=lambda x: gameweek_predictions.get(x['id'], 0), reverse=True)
        
        return {
            'starting_11': best_team,
            'formation': best_formation,
            'captain': captain,
            'vice_captain': vice_captain,
            'bench': bench_sorted,
            'predicted_points': best_score + captain['gw_prediction']
        }
    
    def _select_team_for_formation(self, squad_df: pd.DataFrame, formation: Dict) -> Tuple[List[Dict], float]:
        team = []
        total_score = 0
        
        for position, count in formation.items():
            position_players = squad_df[squad_df['position'] == position].nlargest(count, 'gw_prediction')
            for _, player in position_players.iterrows():
                team.append(player.to_dict())
                total_score += player['gw_prediction']
        
        return team, total_score
    
    def suggest_transfers(self, 
                         current_squad: List[Dict], 
                         all_players_df: pd.DataFrame,
                         predictions: Dict[int, float],
                         free_transfers: int = 1,
                         bank: float = 0.0) -> Dict:
        
        current_ids = [p['id'] for p in current_squad]
        current_value = sum(p['price'] for p in current_squad)
        
        all_players_df = all_players_df.copy()
        all_players_df['predicted_points'] = all_players_df['id'].map(predictions).fillna(0)
        all_players_df['price'] = all_players_df['now_cost'] / 10
        
        potential_out = sorted(current_squad, 
                              key=lambda x: predictions.get(x['id'], 0))[:3]
        
        transfer_suggestions = []
        
        for player_out in potential_out:
            position = player_out['position']
            max_price = player_out['price'] + bank
            
            candidates = all_players_df[
                (all_players_df['position'] == position) &
                (all_players_df['price'] <= max_price) &
                (~all_players_df['id'].isin(current_ids))
            ].nlargest(3, 'predicted_points')
            
            for _, player_in in candidates.iterrows():
                gain = player_in['predicted_points'] - predictions.get(player_out['id'], 0)
                if gain > 0:
                    transfer_suggestions.append({
                        'out': player_out,
                        'in': {
                            'id': player_in['id'],
                            'name': player_in['web_name'],
                            'team': player_in['team'],
                            'price': player_in['price'],
                            'predicted_points': player_in['predicted_points']
                        },
                        'points_gain': gain,
                        'cost': player_in['price'] - player_out['price']
                    })
        
        transfer_suggestions = sorted(transfer_suggestions, 
                                     key=lambda x: x['points_gain'], 
                                     reverse=True)
        
        return {
            'suggested_transfers': transfer_suggestions[:free_transfers],
            'wildcard_suggestion': self._suggest_wildcard(current_squad, all_players_df, predictions)
        }
    
    def _suggest_wildcard(self, current_squad: List[Dict], 
                         all_players_df: pd.DataFrame,
                         predictions: Dict[int, float]) -> Dict:
        
        optimal_squad = self.optimize_squad(all_players_df, predictions)
        
        current_predicted = sum(predictions.get(p['id'], 0) for p in current_squad)
        optimal_predicted = optimal_squad['predicted_points']
        
        improvement = optimal_predicted - current_predicted
        improvement_pct = (improvement / current_predicted * 100) if current_predicted > 0 else 0
        
        return {
            'recommended': improvement_pct > 15,
            'points_improvement': improvement,
            'improvement_percentage': improvement_pct,
            'optimal_squad': optimal_squad['squad'][:5]
        }
    
    def _get_fallback_squad(self, players_df: pd.DataFrame) -> Dict:
        selected_players = []
        remaining_budget = self.budget
        
        # Create value_score column if it doesn't exist
        players_df = players_df.copy()
        if 'predicted_points' not in players_df.columns:
            players_df['predicted_points'] = players_df.get('total_points', 0)
        players_df['price'] = players_df['now_cost'] / 10
        players_df['value_score'] = players_df['predicted_points'] / (players_df['price'] + 1)
        
        for position, constraints in self.formation_constraints.items():
            position_players = players_df[players_df['position'] == position]
            position_players = position_players.sort_values('value_score', ascending=False)
            
            count = 0
            for _, player in position_players.iterrows():
                if count >= constraints['min']:
                    break
                if player['price'] <= remaining_budget:
                    selected_players.append({
                        'id': player['id'],
                        'name': player['web_name'],
                        'position': player['position'],
                        'team': player['team'],
                        'price': player['price'],
                        'predicted_points': player['predicted_points']
                    })
                    remaining_budget -= player['price']
                    count += 1
        
        return {
            'squad': selected_players,
            'total_cost': self.budget - remaining_budget,
            'predicted_points': sum(p['predicted_points'] for p in selected_players),
            'optimization_status': 'fallback'
        }
    
    def get_fixture_difficulty_analysis(self, fixtures_df: pd.DataFrame, teams_df: pd.DataFrame) -> Dict:
        """Analyze fixture difficulty for upcoming gameweeks"""
        try:
            # Calculate fixture difficulty for next 5 gameweeks
            difficulty_analysis = {}
            
            for _, fixture in fixtures_df.iterrows():
                home_team = fixture.get('team_h')
                away_team = fixture.get('team_a')
                gameweek = fixture.get('gameweek', fixture.get('event'))
                
                if home_team and away_team and gameweek:
                    # Simple difficulty scoring based on team strength
                    home_difficulty = self._calculate_team_difficulty(home_team, teams_df, is_home=True)
                    away_difficulty = self._calculate_team_difficulty(away_team, teams_df, is_home=False)
                    
                    if gameweek not in difficulty_analysis:
                        difficulty_analysis[gameweek] = {}
                    
                    difficulty_analysis[gameweek][home_team] = {
                        'opponent': away_team,
                        'difficulty': home_difficulty,
                        'venue': 'home'
                    }
                    
                    difficulty_analysis[gameweek][away_team] = {
                        'opponent': home_team,
                        'difficulty': away_difficulty,
                        'venue': 'away'
                    }
            
            return difficulty_analysis
            
        except Exception as e:
            logger.error(f"Error in fixture difficulty analysis: {e}")
            return {}
    
    def _calculate_team_difficulty(self, team_id: int, teams_df: pd.DataFrame, is_home: bool = True) -> int:
        """Calculate fixture difficulty (1=easy, 5=hard)"""
        try:
            team_data = teams_df[teams_df['id'] == team_id]
            
            if team_data.empty:
                return 3  # Default difficulty
            
            team_info = team_data.iloc[0]
            
            # Use team strength as proxy for difficulty
            strength = team_info.get('strength', 3)
            
            # Adjust for home/away
            if is_home:
                strength += team_info.get('strength_attack_home', 0) - team_info.get('strength_defence_away', 0)
            else:
                strength += team_info.get('strength_attack_away', 0) - team_info.get('strength_defence_home', 0)
            
            # Convert to 1-5 scale
            if strength >= 1400:
                return 5  # Very difficult
            elif strength >= 1200:
                return 4  # Difficult
            elif strength >= 1000:
                return 3  # Average
            elif strength >= 800:
                return 2  # Easy
            else:
                return 1  # Very easy
                
        except Exception as e:
            logger.error(f"Error calculating team difficulty: {e}")
            return 3
    
    def optimize_with_sentiment_and_injuries(self, 
                                           players_df: pd.DataFrame,
                                           predictions: Dict[int, float],
                                           sentiment_data: Dict = None,
                                           injury_data: Dict = None,
                                           fixtures_df: pd.DataFrame = None) -> Dict:
        """Enhanced optimization incorporating sentiment analysis and injury data"""
        try:
            logger.info("Running enhanced optimization with sentiment and injury analysis...")
            
            enhanced_df = players_df.copy()
            
            # Apply sentiment adjustments
            if sentiment_data:
                enhanced_df = self._apply_sentiment_adjustments(enhanced_df, sentiment_data, predictions)
            
            # Apply injury risk adjustments
            if injury_data:
                enhanced_df = self._apply_injury_risk_adjustments(enhanced_df, injury_data, predictions)
            
            # Apply fixture difficulty adjustments
            if fixtures_df is not None:
                enhanced_df = self._apply_fixture_difficulty_adjustments(enhanced_df, fixtures_df, predictions)
            
            # Run optimization with enhanced predictions
            enhanced_predictions = {}
            for _, player in enhanced_df.iterrows():
                enhanced_predictions[player['id']] = player.get('enhanced_prediction', predictions.get(player['id'], 0))
            
            result = self.optimize_squad(enhanced_df, enhanced_predictions)
            
            # Add analysis details
            result['enhancement_details'] = {
                'sentiment_applied': sentiment_data is not None,
                'injury_risk_applied': injury_data is not None,
                'fixture_difficulty_applied': fixtures_df is not None,
                'total_adjustments': len([p for _, p in enhanced_df.iterrows() if p.get('adjustment_applied', False)])
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in enhanced optimization: {e}")
            return self.optimize_squad(players_df, predictions)
    
    def _apply_sentiment_adjustments(self, players_df: pd.DataFrame, sentiment_data: Dict, predictions: Dict) -> pd.DataFrame:
        """Apply sentiment-based adjustments to predictions"""
        df = players_df.copy()
        
        for player_id, sentiment_info in sentiment_data.get('player_sentiment', {}).items():
            try:
                player_idx = df[df['id'] == int(player_id)].index
                
                if not player_idx.empty:
                    idx = player_idx[0]
                    base_prediction = predictions.get(int(player_id), 0)
                    
                    # Apply sentiment multiplier
                    sentiment_score = sentiment_info.get('average_sentiment', 0)
                    sentiment_multiplier = 1 + (sentiment_score * 0.1)  # ±10% max adjustment
                    
                    # Reduce prediction for high injury risk
                    injury_risk = sentiment_info.get('injury_risk', 'low')
                    if injury_risk == 'high':
                        sentiment_multiplier *= 0.8  # 20% reduction
                    elif injury_risk == 'medium':
                        sentiment_multiplier *= 0.9  # 10% reduction
                    
                    enhanced_prediction = base_prediction * sentiment_multiplier
                    
                    df.at[idx, 'enhanced_prediction'] = enhanced_prediction
                    df.at[idx, 'sentiment_adjustment'] = sentiment_multiplier
                    df.at[idx, 'adjustment_applied'] = True
                    
            except Exception as e:
                logger.warning(f"Error applying sentiment adjustment for player {player_id}: {e}")
                continue
        
        return df
    
    def _apply_injury_risk_adjustments(self, players_df: pd.DataFrame, injury_data: Dict, predictions: Dict) -> pd.DataFrame:
        """Apply injury risk adjustments to predictions"""
        df = players_df.copy()
        
        for player_id, injury_info in injury_data.get('fpl_official_injuries', {}).items():
            try:
                player_idx = df[df['id'] == int(player_id)].index
                
                if not player_idx.empty:
                    idx = player_idx[0]
                    base_prediction = df.at[idx, 'enhanced_prediction'] if 'enhanced_prediction' in df.columns else predictions.get(int(player_id), 0)
                    
                    # Apply injury adjustment based on availability
                    chance_of_playing = injury_info.get('chance_of_playing')
                    
                    if chance_of_playing is not None:
                        if chance_of_playing < 25:
                            adjustment = 0.1  # 90% reduction
                        elif chance_of_playing < 50:
                            adjustment = 0.5  # 50% reduction
                        elif chance_of_playing < 75:
                            adjustment = 0.7  # 30% reduction
                        else:
                            adjustment = 0.9  # 10% reduction
                    else:
                        # If not available at all
                        if not injury_info.get('is_available', True):
                            adjustment = 0.05  # 95% reduction
                        else:
                            adjustment = 1.0
                    
                    enhanced_prediction = base_prediction * adjustment
                    
                    df.at[idx, 'enhanced_prediction'] = enhanced_prediction
                    df.at[idx, 'injury_adjustment'] = adjustment
                    df.at[idx, 'adjustment_applied'] = True
                    
            except Exception as e:
                logger.warning(f"Error applying injury adjustment for player {player_id}: {e}")
                continue
        
        return df
    
    def _apply_fixture_difficulty_adjustments(self, players_df: pd.DataFrame, fixtures_df: pd.DataFrame, predictions: Dict) -> pd.DataFrame:
        """Apply fixture difficulty adjustments based on upcoming matches"""
        df = players_df.copy()
        
        try:
            # Get next gameweek fixtures
            next_gw = fixtures_df['gameweek'].min() if 'gameweek' in fixtures_df.columns else fixtures_df.get('event', pd.Series()).min()
            
            if pd.isna(next_gw):
                return df
            
            next_fixtures = fixtures_df[fixtures_df.get('gameweek', fixtures_df.get('event', pd.Series())) == next_gw]
            
            for _, player in df.iterrows():
                try:
                    player_team = player['team']
                    
                    # Find player's team fixture
                    team_fixture = next_fixtures[
                        (next_fixtures.get('team_h') == player_team) | 
                        (next_fixtures.get('team_a') == player_team)
                    ]
                    
                    if not team_fixture.empty:
                        fixture = team_fixture.iloc[0]
                        
                        # Determine difficulty
                        if fixture.get('team_h') == player_team:
                            difficulty = fixture.get('team_h_difficulty', 3)
                        else:
                            difficulty = fixture.get('team_a_difficulty', 3)
                        
                        # Apply difficulty adjustment
                        if difficulty == 1:
                            multiplier = 1.2  # 20% boost for easy fixtures
                        elif difficulty == 2:
                            multiplier = 1.1  # 10% boost
                        elif difficulty == 4:
                            multiplier = 0.9  # 10% reduction for hard fixtures
                        elif difficulty == 5:
                            multiplier = 0.8  # 20% reduction for very hard fixtures
                        else:
                            multiplier = 1.0  # No adjustment for average
                        
                        player_idx = df[df['id'] == player['id']].index[0]
                        base_prediction = df.at[player_idx, 'enhanced_prediction'] if 'enhanced_prediction' in df.columns else predictions.get(player['id'], 0)
                        
                        df.at[player_idx, 'enhanced_prediction'] = base_prediction * multiplier
                        df.at[player_idx, 'fixture_adjustment'] = multiplier
                        df.at[player_idx, 'adjustment_applied'] = True
                        
                except Exception as e:
                    continue
        
        except Exception as e:
            logger.error(f"Error applying fixture difficulty adjustments: {e}")
        
        return df
    
    def generate_weekly_insights(self, 
                               players_df: pd.DataFrame,
                               predictions: Dict[int, float],
                               sentiment_data: Dict = None,
                               injury_data: Dict = None,
                               price_changes: List[Dict] = None) -> Dict:
        """Generate comprehensive weekly insights for FPL managers"""
        try:
            insights = {
                'timestamp': datetime.now().isoformat(),
                'top_picks': [],
                'avoid_players': [],
                'captain_options': [],
                'differential_picks': [],
                'price_alerts': [],
                'injury_alerts': [],
                'value_picks': []
            }
            
            # Calculate enhanced predictions
            enhanced_df = players_df.copy()
            enhanced_df['predicted_points'] = enhanced_df['id'].map(predictions).fillna(0)
            enhanced_df['price'] = enhanced_df['now_cost'] / 10
            enhanced_df['value_score'] = enhanced_df['predicted_points'] / (enhanced_df['price'] + 0.1)
            enhanced_df['ownership'] = enhanced_df.get('selected_by_percent', 0).astype(float)
            
            # Top picks by position
            for position in ['GK', 'DEF', 'MID', 'FWD']:
                position_players = enhanced_df[enhanced_df['position'] == position]
                top_in_position = position_players.nlargest(3, 'predicted_points')
                
                for _, player in top_in_position.iterrows():
                    insights['top_picks'].append({
                        'id': player['id'],
                        'name': player.get('web_name', player.get('name', 'Unknown')),
                        'team': player.get('name_team', player.get('team_name', 'Unknown')),
                        'position': player['position'],
                        'predicted_points': player['predicted_points'],
                        'price': player['price'],
                        'ownership': player['ownership']
                    })
            
            # Captain options (high predicted points, high ownership)
            captain_candidates = enhanced_df[
                (enhanced_df['predicted_points'] > enhanced_df['predicted_points'].quantile(0.9)) &
                (enhanced_df['ownership'] > 10)
            ].nlargest(5, 'predicted_points')
            
            for _, player in captain_candidates.iterrows():
                insights['captain_options'].append({
                    'id': player['id'],
                    'name': player.get('web_name', player.get('name', 'Unknown')),
                    'team': player.get('name_team', player.get('team_name', 'Unknown')),
                    'predicted_points': player['predicted_points'],
                    'ownership': player['ownership'],
                    'captaincy_appeal': 'high'
                })
            
            # Differential picks (low ownership, high predicted points)
            differentials = enhanced_df[
                (enhanced_df['predicted_points'] > enhanced_df['predicted_points'].quantile(0.75)) &
                (enhanced_df['ownership'] < 5)
            ].nlargest(10, 'value_score')
            
            for _, player in differentials.iterrows():
                insights['differential_picks'].append({
                    'id': player['id'],
                    'name': player.get('web_name', player.get('name', 'Unknown')),
                    'team': player.get('name_team', player.get('team_name', 'Unknown')),
                    'predicted_points': player['predicted_points'],
                    'ownership': player['ownership'],
                    'value_score': player['value_score']
                })
            
            # Value picks (best value for money)
            value_picks = enhanced_df[enhanced_df['price'] <= 8.0].nlargest(10, 'value_score')
            
            for _, player in value_picks.iterrows():
                insights['value_picks'].append({
                    'id': player['id'],
                    'name': player.get('web_name', player.get('name', 'Unknown')),
                    'team': player.get('name_team', player.get('team_name', 'Unknown')),
                    'predicted_points': player['predicted_points'],
                    'price': player['price'],
                    'value_score': player['value_score']
                })
            
            # Add injury alerts
            if injury_data:
                for player_id, injury_info in injury_data.get('fpl_official_injuries', {}).items():
                    if not injury_info.get('is_available', True):
                        insights['injury_alerts'].append({
                            'player_id': player_id,
                            'name': injury_info.get('name', 'Unknown'),
                            'status': injury_info.get('fpl_status', 'unknown'),
                            'chance_of_playing': injury_info.get('chance_of_playing'),
                            'news': injury_info.get('news', ''),
                            'severity': injury_info.get('severity', 'unknown')
                        })
            
            # Add price change alerts
            if price_changes:
                for change in price_changes[:10]:  # Top 10 price changes
                    insights['price_alerts'].append({
                        'player_id': change.get('player_id'),
                        'name': change.get('name'),
                        'price_change': change.get('event_change', 0),
                        'new_price': change.get('current_price'),
                        'ownership': change.get('ownership', 0)
                    })
            
            # Save insights
            insights_file = self.cache_dir / f"weekly_insights_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(insights_file, 'w') as f:
                json.dump(insights, f, indent=2)
            
            # Save latest insights
            latest_file = self.cache_dir / "latest_weekly_insights.json"
            with open(latest_file, 'w') as f:
                json.dump(insights, f, indent=2)
            
            logger.info(f"Generated weekly insights with {len(insights['top_picks'])} recommendations")
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating weekly insights: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'top_picks': [],
                'avoid_players': [],
                'captain_options': [],
                'differential_picks': [],
                'price_alerts': [],
                'injury_alerts': [],
                'value_picks': []
            }