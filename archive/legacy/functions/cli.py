#!/usr/bin/env python3

import click
import pandas as pd
from tabulate import tabulate
from src.prediction_engine import FPLPredictionEngine
from src.data.fpl_api import FPLDataFetcher
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.group()
def cli():
    pass

@cli.command()
@click.option('--budget', default=100.0, help='Budget in millions')
@click.option('--output', default='table', type=click.Choice(['table', 'json']))
def optimize(budget, output):
    click.echo("Optimizing FPL squad...")
    
    engine = FPLPredictionEngine()
    result = engine.optimize_team_selection(budget=budget)
    
    squad_df = pd.DataFrame(result['squad']['squad'])
    
    if output == 'table':
        click.echo("\n=== OPTIMIZED SQUAD ===")
        click.echo(tabulate(squad_df[['name', 'position', 'team', 'price', 'predicted_points']], 
                           headers='keys', tablefmt='pretty'))
        click.echo(f"\nTotal Cost: £{result['squad']['total_cost']:.1f}m")
        click.echo(f"Predicted Points: {result['squad']['predicted_points']:.1f}")
        
        click.echo("\n=== STARTING 11 ===")
        starting_df = pd.DataFrame(result['starting_11']['starting_11'])
        click.echo(tabulate(starting_df[['name', 'position', 'gw_prediction']], 
                           headers='keys', tablefmt='pretty'))
        
        click.echo(f"\nCaptain: {result['starting_11']['captain']['name']}")
        click.echo(f"Vice Captain: {result['starting_11']['vice_captain']['name']}")
        click.echo(f"Formation: {result['starting_11']['formation']}")
    else:
        import json
        click.echo(json.dumps(result, indent=2, default=str))

@cli.command()
@click.option('--top', default=20, help='Number of top players to show')
def predictions(top):
    click.echo("Getting player predictions...")
    
    engine = FPLPredictionEngine()
    predictions = engine.get_player_predictions()
    fetcher = FPLDataFetcher()
    players_df = fetcher.get_all_players_data()
    
    results = []
    for player_id, pred_points in predictions.items():
        player_data = players_df[players_df['id'] == player_id]
        if not player_data.empty:
            player = player_data.iloc[0]
            results.append({
                'Name': player['web_name'],
                'Team': player['short_name_team'],
                'Pos': player['position'],
                'Price': f"£{player['now_cost']/10:.1f}",
                'Predicted': f"{pred_points:.1f}",
                'Value': f"{pred_points/(player['now_cost']/10):.2f}"
            })
    
    results.sort(key=lambda x: float(x['Predicted']), reverse=True)
    
    click.echo("\n=== TOP PLAYER PREDICTIONS ===")
    click.echo(tabulate(results[:top], headers='keys', tablefmt='pretty'))

@cli.command()
@click.argument('player_name')
def player(player_name):
    click.echo(f"Searching for player: {player_name}")
    
    fetcher = FPLDataFetcher()
    players_df = fetcher.get_all_players_data()
    
    matches = players_df[players_df['web_name'].str.contains(player_name, case=False)]
    
    if matches.empty:
        click.echo(f"No player found matching '{player_name}'")
        return
    
    if len(matches) > 1:
        click.echo("Multiple players found:")
        for _, p in matches.iterrows():
            click.echo(f"  - {p['web_name']} ({p['name_team']})")
        return
    
    player_data = matches.iloc[0]
    player_id = player_data['id']
    
    click.echo(f"\n=== {player_data['web_name']} ===")
    click.echo(f"Team: {player_data['name_team']}")
    click.echo(f"Position: {player_data['position']}")
    click.echo(f"Price: £{player_data['now_cost']/10:.1f}m")
    click.echo(f"Total Points: {player_data['total_points']}")
    click.echo(f"Points Per Game: {player_data['points_per_game']}")
    click.echo(f"Selected By: {player_data['selected_by_percent']}%")
    click.echo(f"Form: {player_data['form']}")
    
    engine = FPLPredictionEngine()
    try:
        history = fetcher.get_player_detailed_stats(player_id)
        if len(history) >= 6:
            predictions = engine.cnn_predictor.predict_multiple_gameweeks(history, 5)
            click.echo(f"\nNext 5 GW Predictions: {[f'{p:.1f}' for p in predictions]}")
            click.echo(f"Average: {sum(predictions)/len(predictions):.1f} points")
    except:
        pass

@cli.command()
def train():
    click.echo("Training models...")
    
    engine = FPLPredictionEngine()
    engine.train_models(force_retrain=True)
    
    click.echo("Training complete!")

@cli.command()
def gameweek():
    click.echo("Getting current gameweek info...")
    
    fetcher = FPLDataFetcher()
    bootstrap_data = fetcher.get_bootstrap_data()
    
    for event in bootstrap_data['events']:
        if event.get('is_current'):
            click.echo(f"\n=== GAMEWEEK {event['id']} ===")
            click.echo(f"Name: {event['name']}")
            click.echo(f"Deadline: {event['deadline_time']}")
            click.echo(f"Finished: {event.get('finished', False)}")
            
            fixtures = fetcher.get_fixtures(event['id'])
            click.echo(f"\nFixtures ({len(fixtures)} matches):")
            for fix in fixtures[:5]:
                click.echo(f"  GW{fix['event']}: Team {fix['team_h']} vs Team {fix['team_a']}")
            break

if __name__ == '__main__':
    cli()