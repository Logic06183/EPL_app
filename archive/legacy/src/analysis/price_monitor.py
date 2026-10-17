import pandas as pd
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path
import asyncio
import aiohttp
from collections import defaultdict

from ..data.live_data_manager import LiveDataManager

logger = logging.getLogger(__name__)

class FPLPriceMonitor:
    def __init__(self, cache_dir: str = "./data/price_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.live_data_manager = LiveDataManager()
        
        # External price tracking APIs
        self.price_apis = {
            'fplalerts': 'http://www.fplalerts.com/api/players',
            'fplstatistics': 'http://www.fplstatistics.co.uk/Home/AjaxPriceChangePrediction',
            'fantasy_football_fix': 'https://www.fantasyfootballfix.com/price/'
        }
        
        # Price change prediction thresholds
        self.rise_threshold = 100  # Target for price rise
        self.fall_threshold = -100  # Target for price fall
        
    def track_price_history(self, days_back: int = 7) -> Dict:
        """Track price changes over the last N days"""
        try:
            current_data = self.live_data_manager.get_current_season_data()
            
            price_history = {}
            
            # Load historical price data from cache
            for i in range(days_back):
                date = datetime.now() - timedelta(days=i)
                date_str = date.strftime('%Y%m%d')
                
                # Look for cached price data from that day
                cache_file = self.cache_dir / f"prices_{date_str}.csv"
                
                if cache_file.exists():
                    try:
                        historical_data = pd.read_csv(cache_file)
                        
                        for _, player in historical_data.iterrows():
                            player_id = player['id']
                            price = player['now_cost'] / 10
                            
                            if player_id not in price_history:
                                price_history[player_id] = {
                                    'name': f"{player.get('first_name', '')} {player.get('second_name', '')}",
                                    'team': player.get('name_team', ''),
                                    'position': player.get('position', ''),
                                    'prices': []
                                }
                            
                            price_history[player_id]['prices'].append({
                                'date': date_str,
                                'price': price,
                                'ownership': player.get('selected_by_percent', 0)
                            })
                    except Exception as e:
                        logger.warning(f"Error loading price data for {date_str}: {e}")
                        continue
            
            # Calculate price trends
            price_trends = {}
            
            for player_id, data in price_history.items():
                if len(data['prices']) >= 2:
                    prices = sorted(data['prices'], key=lambda x: x['date'])
                    
                    current_price = prices[-1]['price']
                    oldest_price = prices[0]['price']
                    
                    total_change = current_price - oldest_price
                    daily_changes = []
                    
                    for i in range(1, len(prices)):
                        daily_change = prices[i]['price'] - prices[i-1]['price']
                        daily_changes.append(daily_change)
                    
                    price_trends[player_id] = {
                        'name': data['name'],
                        'team': data['team'],
                        'position': data['position'],
                        'current_price': current_price,
                        'total_change': total_change,
                        'daily_changes': daily_changes,
                        'average_daily_change': sum(daily_changes) / len(daily_changes) if daily_changes else 0,
                        'volatility': max(daily_changes) - min(daily_changes) if daily_changes else 0,
                        'trend': 'rising' if total_change > 0.1 else 'falling' if total_change < -0.1 else 'stable'
                    }
            
            return {
                'timestamp': datetime.now().isoformat(),
                'players_tracked': len(price_trends),
                'days_analyzed': days_back,
                'price_trends': price_trends
            }
            
        except Exception as e:
            logger.error(f"Error tracking price history: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'players_tracked': 0,
                'price_trends': {}
            }
    
    async def fetch_price_predictions(self) -> Dict:
        """Fetch price change predictions from external sources"""
        try:
            predictions = {
                'risers': [],
                'fallers': [],
                'timestamp': datetime.now().isoformat()
            }
            
            # Note: These APIs may require authentication or have rate limits
            # This is a framework for integrating with price prediction services
            
            # For now, use FPL's own data to predict changes
            current_data = self.live_data_manager.get_current_season_data()
            
            # Simple heuristic-based predictions
            for _, player in current_data.iterrows():
                try:
                    ownership = float(player.get('selected_by_percent', 0))
                    transfers_in = player.get('transfers_in_event', 0)
                    transfers_out = player.get('transfers_out_event', 0)
                    
                    net_transfers = transfers_in - transfers_out
                    
                    # Calculate price change likelihood
                    # High ownership + high net transfers in = likely rise
                    # High ownership + high net transfers out = likely fall
                    
                    rise_score = 0
                    fall_score = 0
                    
                    if ownership > 10:  # Popular players
                        if net_transfers > 50000:  # Lots of people buying
                            rise_score = min(100, net_transfers / 1000)
                        elif net_transfers < -50000:  # Lots of people selling
                            fall_score = min(100, abs(net_transfers) / 1000)
                    
                    # Add predictions if significant
                    if rise_score > 30:
                        predictions['risers'].append({
                            'player_id': player['id'],
                            'name': f"{player.get('first_name', '')} {player.get('second_name', '')}",
                            'team': player.get('name_team', ''),
                            'current_price': player['now_cost'] / 10,
                            'ownership': ownership,
                            'net_transfers': net_transfers,
                            'rise_probability': rise_score,
                            'predicted_new_price': (player['now_cost'] + 1) / 10
                        })
                    
                    elif fall_score > 30:
                        predictions['fallers'].append({
                            'player_id': player['id'],
                            'name': f"{player.get('first_name', '')} {player.get('second_name', '')}",
                            'team': player.get('name_team', ''),
                            'current_price': player['now_cost'] / 10,
                            'ownership': ownership,
                            'net_transfers': net_transfers,
                            'fall_probability': fall_score,
                            'predicted_new_price': (player['now_cost'] - 1) / 10
                        })
                
                except Exception as e:
                    continue
            
            # Sort by probability
            predictions['risers'] = sorted(predictions['risers'], key=lambda x: x['rise_probability'], reverse=True)[:20]
            predictions['fallers'] = sorted(predictions['fallers'], key=lambda x: x['fall_probability'], reverse=True)[:20]
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error fetching price predictions: {e}")
            return {
                'risers': [],
                'fallers': [],
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def analyze_ownership_trends(self) -> Dict:
        """Analyze ownership trends that could lead to price changes"""
        try:
            current_data = self.live_data_manager.get_current_season_data()
            
            ownership_analysis = {
                'high_ownership_risks': [],
                'trending_players': [],
                'template_changes': [],
                'differential_opportunities': []
            }
            
            # High ownership players at risk
            high_ownership = current_data[current_data['selected_by_percent'].astype(float) > 30]
            
            for _, player in high_ownership.iterrows():
                # Players with high ownership but recent poor form
                recent_form = float(player.get('form', 0))
                ownership = float(player['selected_by_percent'])
                
                if recent_form < 3 and ownership > 30:  # Poor form, high ownership
                    ownership_analysis['high_ownership_risks'].append({
                        'player_id': player['id'],
                        'name': f"{player.get('first_name', '')} {player.get('second_name', '')}",
                        'team': player.get('name_team', ''),
                        'ownership': ownership,
                        'form': recent_form,
                        'price': player['now_cost'] / 10,
                        'risk_level': 'high' if ownership > 50 else 'medium'
                    })
            
            # Trending players (good form, increasing ownership)
            good_form = current_data[current_data['form'].astype(float) > 5]
            
            for _, player in good_form.iterrows():
                ownership = float(player['selected_by_percent'])
                form = float(player['form'])
                
                # Players with good form but still low ownership
                if ownership < 15 and form > 6:
                    ownership_analysis['differential_opportunities'].append({
                        'player_id': player['id'],
                        'name': f"{player.get('first_name', '')} {player.get('second_name', '')}",
                        'team': player.get('name_team', ''),
                        'ownership': ownership,
                        'form': form,
                        'price': player['now_cost'] / 10,
                        'value_score': form / (player['now_cost'] / 10)
                    })
            
            # Sort by relevance
            ownership_analysis['high_ownership_risks'] = sorted(
                ownership_analysis['high_ownership_risks'], 
                key=lambda x: x['ownership'], 
                reverse=True
            )[:10]
            
            ownership_analysis['differential_opportunities'] = sorted(
                ownership_analysis['differential_opportunities'], 
                key=lambda x: x['value_score'], 
                reverse=True
            )[:15]
            
            return {
                'timestamp': datetime.now().isoformat(),
                'analysis': ownership_analysis
            }
            
        except Exception as e:
            logger.error(f"Error analyzing ownership trends: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'analysis': {
                    'high_ownership_risks': [],
                    'trending_players': [],
                    'template_changes': [],
                    'differential_opportunities': []
                }
            }
    
    def generate_price_alerts(self, user_squad: List[Dict] = None) -> Dict:
        """Generate personalized price change alerts"""
        try:
            alerts = {
                'urgent_alerts': [],
                'watch_list': [],
                'opportunities': [],
                'squad_alerts': []
            }
            
            # Get predictions and trends
            predictions = asyncio.run(self.fetch_price_predictions())
            ownership_analysis = self.analyze_ownership_trends()
            
            # Urgent alerts (likely price changes tonight)
            for riser in predictions['risers'][:5]:
                if riser['rise_probability'] > 70:
                    alerts['urgent_alerts'].append({
                        'type': 'price_rise',
                        'player': riser,
                        'urgency': 'high',
                        'action': 'Consider buying before price rise',
                        'deadline': 'Tonight (01:30 GMT)'
                    })
            
            for faller in predictions['fallers'][:5]:
                if faller['fall_probability'] > 70:
                    alerts['urgent_alerts'].append({
                        'type': 'price_fall',
                        'player': faller,
                        'urgency': 'high',
                        'action': 'Consider selling before price drop',
                        'deadline': 'Tonight (01:30 GMT)'
                    })
            
            # Squad-specific alerts
            if user_squad:
                squad_ids = [player['id'] for player in user_squad]
                
                # Check if any squad players are likely to change price
                for riser in predictions['risers']:
                    if riser['player_id'] in squad_ids:
                        alerts['squad_alerts'].append({
                            'type': 'owned_player_rising',
                            'player': riser,
                            'message': f"Your player {riser['name']} likely to rise tonight (+£0.1m)"
                        })
                
                for faller in predictions['fallers']:
                    if faller['player_id'] in squad_ids:
                        alerts['squad_alerts'].append({
                            'type': 'owned_player_falling',
                            'player': faller,
                            'message': f"Your player {faller['name']} likely to fall tonight (-£0.1m)",
                            'urgency': 'medium'
                        })
            
            # Opportunities (good value players likely to rise)
            for opportunity in ownership_analysis['analysis']['differential_opportunities'][:5]:
                # Check if they're also predicted to rise
                is_predicted_riser = any(
                    r['player_id'] == opportunity['player_id'] 
                    for r in predictions['risers']
                )
                
                if is_predicted_riser:
                    alerts['opportunities'].append({
                        'type': 'value_before_rise',
                        'player': opportunity,
                        'message': f"Low ownership, good form player likely to rise soon",
                        'action': 'Consider as differential pick'
                    })
            
            # Save alerts
            alerts_file = self.cache_dir / f"price_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(alerts_file, 'w') as f:
                json.dump(alerts, f, indent=2)
            
            # Save latest alerts
            latest_file = self.cache_dir / "latest_price_alerts.json"
            with open(latest_file, 'w') as f:
                json.dump(alerts, f, indent=2)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'alerts': alerts,
                'total_alerts': len(alerts['urgent_alerts']) + len(alerts['squad_alerts']) + len(alerts['opportunities'])
            }
            
        except Exception as e:
            logger.error(f"Error generating price alerts: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'alerts': {
                    'urgent_alerts': [],
                    'watch_list': [],
                    'opportunities': [],
                    'squad_alerts': []
                },
                'total_alerts': 0
            }
    
    def save_daily_prices(self) -> bool:
        """Save current player prices for historical tracking"""
        try:
            current_data = self.live_data_manager.get_current_season_data()
            
            # Save today's prices
            today_str = datetime.now().strftime('%Y%m%d')
            prices_file = self.cache_dir / f"prices_{today_str}.csv"
            
            current_data.to_csv(prices_file, index=False)
            
            logger.info(f"Saved {len(current_data)} player prices for {today_str}")
            
            # Clean up old price files (keep last 30 days)
            cutoff_date = datetime.now() - timedelta(days=30)
            
            for price_file in self.cache_dir.glob("prices_*.csv"):
                try:
                    date_str = price_file.stem.split('_')[1]
                    file_date = datetime.strptime(date_str, '%Y%m%d')
                    
                    if file_date < cutoff_date:
                        price_file.unlink()
                        logger.info(f"Cleaned up old price file: {price_file}")
                        
                except Exception as e:
                    continue
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving daily prices: {e}")
            return False
    
    def get_price_change_summary(self, days: int = 7) -> Dict:
        """Get summary of price changes over last N days"""
        try:
            price_history = self.track_price_history(days)
            
            summary = {
                'total_changes': 0,
                'rises': 0,
                'falls': 0,
                'biggest_riser': None,
                'biggest_faller': None,
                'most_volatile': None,
                'stable_players': 0
            }
            
            biggest_rise = 0
            biggest_fall = 0
            highest_volatility = 0
            
            for player_id, trend in price_history.get('price_trends', {}).items():
                total_change = trend['total_change']
                volatility = trend['volatility']
                
                if abs(total_change) > 0.05:  # Changed by more than £0.05
                    summary['total_changes'] += 1
                    
                    if total_change > 0:
                        summary['rises'] += 1
                        if total_change > biggest_rise:
                            biggest_rise = total_change
                            summary['biggest_riser'] = {
                                'name': trend['name'],
                                'team': trend['team'],
                                'change': total_change,
                                'new_price': trend['current_price']
                            }
                    else:
                        summary['falls'] += 1
                        if total_change < biggest_fall:
                            biggest_fall = total_change
                            summary['biggest_faller'] = {
                                'name': trend['name'],
                                'team': trend['team'],
                                'change': total_change,
                                'new_price': trend['current_price']
                            }
                else:
                    summary['stable_players'] += 1
                
                if volatility > highest_volatility:
                    highest_volatility = volatility
                    summary['most_volatile'] = {
                        'name': trend['name'],
                        'team': trend['team'],
                        'volatility': volatility,
                        'price': trend['current_price']
                    }
            
            summary['timestamp'] = datetime.now().isoformat()
            summary['period_days'] = days
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting price change summary: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'total_changes': 0,
                'rises': 0,
                'falls': 0
            }

if __name__ == "__main__":
    import asyncio
    
    async def test_price_monitor():
        logging.basicConfig(level=logging.INFO)
        
        monitor = FPLPriceMonitor()
        
        # Test price tracking
        print("Testing price tracking...")
        history = monitor.track_price_history(7)
        print(f"Tracked {history['players_tracked']} players")
        
        # Test price predictions
        print("Testing price predictions...")
        predictions = await monitor.fetch_price_predictions()
        print(f"Found {len(predictions['risers'])} predicted risers, {len(predictions['fallers'])} predicted fallers")
        
        # Test alerts
        print("Testing price alerts...")
        alerts = monitor.generate_price_alerts()
        print(f"Generated {alerts['total_alerts']} alerts")
        
        # Save daily prices
        print("Saving daily prices...")
        saved = monitor.save_daily_prices()
        print(f"Prices saved: {saved}")
    
    # Run test
    # asyncio.run(test_price_monitor())