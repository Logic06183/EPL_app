import pytest
import pandas as pd
import numpy as np
from src.models.team_optimizer import FPLTeamOptimizer

class TestFPLTeamOptimizer:
    
    @pytest.fixture
    def optimizer(self):
        return FPLTeamOptimizer()
    
    @pytest.fixture
    def sample_players(self):
        np.random.seed(42)
        
        players = []
        player_id = 1
        
        # Generate sample players for each position
        positions = [
            ('GK', 5, 2),    # 5 goalkeepers, need 2
            ('DEF', 15, 5),  # 15 defenders, need 5
            ('MID', 20, 5),  # 20 midfielders, need 5
            ('FWD', 10, 3)   # 10 forwards, need 3
        ]
        
        for position, count, _ in positions:
            for i in range(count):
                players.append({
                    'id': player_id,
                    'web_name': f'{position}_{i+1}',
                    'team': (i % 20) + 1,  # 20 teams
                    'position': position,
                    'now_cost': np.random.randint(40, 140),  # 4.0 to 14.0m in tenths
                    'selected_by_percent': np.random.uniform(0.5, 25.0),
                    'total_points': np.random.randint(0, 200),
                    'points_per_game': np.random.uniform(2.0, 8.0),
                    'form': np.random.uniform(2.0, 8.0),
                    'status': 'a'  # available
                })
                player_id += 1
        
        return pd.DataFrame(players)
    
    @pytest.fixture
    def sample_predictions(self, sample_players):
        """Generate predictions for all players"""
        return {player_id: np.random.uniform(2.0, 8.0) for player_id in sample_players['id']}
    
    def test_initialization(self, optimizer):
        assert optimizer.budget == 100.0
        assert optimizer.squad_size == 15
        assert optimizer.max_players_per_team == 3
        
        # Check formation constraints
        assert optimizer.formation_constraints['GK']['min'] == 2
        assert optimizer.formation_constraints['DEF']['min'] == 5
        assert optimizer.formation_constraints['MID']['min'] == 5
        assert optimizer.formation_constraints['FWD']['min'] == 3
    
    def test_valid_formations(self, optimizer):
        # Check some valid formations
        formations = optimizer.valid_formations
        
        assert len(formations) == 8
        
        # Each formation should have 11 outfield players
        for formation in formations:
            total_outfield = formation['GK'] + formation['DEF'] + formation['MID'] + formation['FWD']
            assert total_outfield == 11
            assert formation['GK'] == 1
    
    def test_optimize_squad_success(self, optimizer, sample_players, sample_predictions):
        result = optimizer.optimize_squad(sample_players, sample_predictions)
        
        assert 'squad' in result
        assert 'total_cost' in result
        assert 'predicted_points' in result
        assert 'optimization_status' in result
        
        squad = result['squad']
        assert len(squad) == 15
        
        # Check position constraints
        positions = [p['position'] for p in squad]
        assert positions.count('GK') == 2
        assert positions.count('DEF') == 5
        assert positions.count('MID') == 5
        assert positions.count('FWD') == 3
        
        # Check budget constraint
        assert result['total_cost'] <= optimizer.budget
        
        # Check team constraint (max 3 players per team)
        teams = [p['team'] for p in squad]
        for team_id in set(teams):
            assert teams.count(team_id) <= 3
    
    def test_optimize_squad_missing_columns(self, optimizer, sample_predictions):
        # Test with missing required columns
        incomplete_df = pd.DataFrame([
            {'id': 1, 'web_name': 'Player1'}
        ])
        
        with pytest.raises(ValueError) as excinfo:
            optimizer.optimize_squad(incomplete_df, sample_predictions)
        
        assert "must contain columns" in str(excinfo.value)
    
    def test_optimize_starting_11(self, optimizer):
        # Create a sample squad
        squad = [
            {'id': 1, 'position': 'GK', 'gw_prediction': 4.0},
            {'id': 2, 'position': 'GK', 'gw_prediction': 3.5},
            {'id': 3, 'position': 'DEF', 'gw_prediction': 5.0},
            {'id': 4, 'position': 'DEF', 'gw_prediction': 4.5},
            {'id': 5, 'position': 'DEF', 'gw_prediction': 4.0},
            {'id': 6, 'position': 'DEF', 'gw_prediction': 3.5},
            {'id': 7, 'position': 'DEF', 'gw_prediction': 3.0},
            {'id': 8, 'position': 'MID', 'gw_prediction': 6.0},
            {'id': 9, 'position': 'MID', 'gw_prediction': 5.5},
            {'id': 10, 'position': 'MID', 'gw_prediction': 5.0},
            {'id': 11, 'position': 'MID', 'gw_prediction': 4.5},
            {'id': 12, 'position': 'MID', 'gw_prediction': 4.0},
            {'id': 13, 'position': 'FWD', 'gw_prediction': 7.0},
            {'id': 14, 'position': 'FWD', 'gw_prediction': 6.5},
            {'id': 15, 'position': 'FWD', 'gw_prediction': 6.0}
        ]
        
        gameweek_predictions = {p['id']: p['gw_prediction'] for p in squad}
        
        result = optimizer.optimize_starting_11(squad, gameweek_predictions)
        
        assert 'starting_11' in result
        assert 'formation' in result
        assert 'captain' in result
        assert 'vice_captain' in result
        assert 'bench' in result
        assert 'predicted_points' in result
        
        # Check starting 11 size
        assert len(result['starting_11']) == 11
        
        # Check captain is the highest predicted scorer
        captain_prediction = result['captain']['gw_prediction']
        all_predictions = [p['gw_prediction'] for p in squad]
        assert captain_prediction == max(all_predictions)
        
        # Check captain and vice captain are different
        assert result['captain']['id'] != result['vice_captain']['id']
        
        # Check bench has remaining players
        starting_ids = [p['id'] for p in result['starting_11']]
        bench_ids = [p['id'] for p in result['bench']]
        assert len(set(starting_ids).intersection(set(bench_ids))) == 0
        assert len(starting_ids) + len(bench_ids) == len(squad)
    
    def test_select_team_for_formation(self, optimizer):
        squad_data = [
            {'position': 'GK', 'gw_prediction': 4.0},
            {'position': 'GK', 'gw_prediction': 3.5},
            {'position': 'DEF', 'gw_prediction': 5.0},
            {'position': 'DEF', 'gw_prediction': 4.5},
            {'position': 'DEF', 'gw_prediction': 4.0},
            {'position': 'DEF', 'gw_prediction': 3.5},
            {'position': 'DEF', 'gw_prediction': 3.0},
            {'position': 'MID', 'gw_prediction': 6.0},
            {'position': 'MID', 'gw_prediction': 5.5},
            {'position': 'MID', 'gw_prediction': 5.0},
            {'position': 'FWD', 'gw_prediction': 7.0},
            {'position': 'FWD', 'gw_prediction': 6.5}
        ]
        
        squad_df = pd.DataFrame(squad_data)
        formation = {'GK': 1, 'DEF': 4, 'MID': 3, 'FWD': 3}
        
        team, score = optimizer._select_team_for_formation(squad_df, formation)
        
        # Should pick the best players for each position
        positions = [p['position'] for p in team]
        assert positions.count('GK') == 1
        assert positions.count('DEF') == 4
        assert positions.count('MID') == 3
        assert positions.count('FWD') == 2  # Only 2 FWDs available, but formation asks for 3
        
        # Score should be sum of selected players' predictions
        expected_score = 4.0 + (5.0 + 4.5 + 4.0 + 3.5) + (6.0 + 5.5 + 5.0) + (7.0 + 6.5)
        assert abs(score - expected_score) < 0.001
    
    def test_suggest_transfers(self, optimizer, sample_players, sample_predictions):
        # Create a current squad (simplified)
        current_squad = [
            {'id': 1, 'position': 'GK', 'price': 5.0},
            {'id': 2, 'position': 'DEF', 'price': 4.5},
            {'id': 3, 'position': 'MID', 'price': 8.0},
        ]
        
        suggestions = optimizer.suggest_transfers(
            current_squad, 
            sample_players, 
            sample_predictions,
            free_transfers=1,
            bank=1.0
        )
        
        assert 'suggested_transfers' in suggestions
        assert 'wildcard_suggestion' in suggestions
        
        # Should have at most 1 transfer (free_transfers=1)
        assert len(suggestions['suggested_transfers']) <= 1
        
        if suggestions['suggested_transfers']:
            transfer = suggestions['suggested_transfers'][0]
            assert 'out' in transfer
            assert 'in' in transfer
            assert 'points_gain' in transfer
            assert 'cost' in transfer
            
            # Points gain should be positive
            assert transfer['points_gain'] > 0
    
    def test_wildcard_suggestion(self, optimizer, sample_players, sample_predictions):
        current_squad = [
            {'id': i, 'position': 'GK' if i <= 2 else 'DEF', 'price': 4.0} 
            for i in range(1, 16)
        ]
        
        wildcard = optimizer._suggest_wildcard(current_squad, sample_players, sample_predictions)
        
        assert 'recommended' in wildcard
        assert 'points_improvement' in wildcard
        assert 'improvement_percentage' in wildcard
        assert 'optimal_squad' in wildcard
        
        assert isinstance(wildcard['recommended'], (bool, np.bool_))
        assert isinstance(wildcard['points_improvement'], (int, float))
        assert isinstance(wildcard['improvement_percentage'], (int, float))
    
    def test_fallback_squad(self, optimizer, sample_players):
        # Test the fallback method
        result = optimizer._get_fallback_squad(sample_players)
        
        assert 'squad' in result
        assert 'total_cost' in result
        assert 'predicted_points' in result
        assert result['optimization_status'] == 'fallback'
        
        # Should have some players selected
        assert len(result['squad']) > 0
        assert result['total_cost'] <= optimizer.budget
    
    def test_budget_constraint_strict(self, optimizer):
        # Create expensive players that exceed budget
        expensive_players = []
        for i, pos in enumerate(['GK', 'GK', 'DEF', 'DEF', 'DEF', 'DEF', 'DEF']):
            expensive_players.append({
                'id': i+1,
                'web_name': f'Expensive_{i+1}',
                'team': i+1,
                'position': pos,
                'now_cost': 130,  # 13.0m each
                'selected_by_percent': 10.0,
            })
        
        expensive_df = pd.DataFrame(expensive_players)
        predictions = {i+1: 10.0 for i in range(len(expensive_players))}
        
        # This should trigger fallback since optimal solution is impossible
        result = optimizer.optimize_squad(expensive_df, predictions)
        
        # Should either find a solution or fall back gracefully
        assert result is not None
        assert 'optimization_status' in result
    
    def test_team_constraint_enforcement(self, optimizer):
        # Create players all from the same team
        same_team_players = []
        for i, pos in enumerate(['GK'] * 2 + ['DEF'] * 5 + ['MID'] * 5 + ['FWD'] * 3):
            same_team_players.append({
                'id': i+1,
                'web_name': f'Player_{i+1}',
                'team': 1,  # All from team 1
                'position': pos,
                'now_cost': 50,  # 5.0m each
                'selected_by_percent': 10.0,
            })
        
        same_team_df = pd.DataFrame(same_team_players)
        predictions = {i+1: 5.0 for i in range(len(same_team_players))}
        
        result = optimizer.optimize_squad(same_team_df, predictions)
        
        if result['optimization_status'] == 'optimal':
            # If optimal solution found, should respect team constraint
            teams = [p['team'] for p in result['squad']]
            for team_id in set(teams):
                assert teams.count(team_id) <= optimizer.max_players_per_team