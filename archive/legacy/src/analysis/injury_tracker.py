import requests
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re

from ..data.live_data_manager import LiveDataManager
from .sentiment_analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)

class InjuryTracker:
    def __init__(self, cache_dir: str = "./data/injury_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.live_data_manager = LiveDataManager()
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # Injury severity keywords
        self.severity_keywords = {
            'minor': ['knock', 'slight', 'minor', 'precaution', 'rest'],
            'moderate': ['strain', 'sprain', 'bruise', 'fatigue', 'tired'],
            'major': ['tear', 'break', 'fracture', 'surgery', 'operation', 'serious'],
            'long_term': ['months', 'season', 'career', 'retirement', 'chronic']
        }
        
        # Transfer keywords
        self.transfer_keywords = {
            'incoming': ['sign', 'signed', 'joins', 'transfer', 'move', 'acquire'],
            'outgoing': ['leaves', 'sold', 'depart', 'exit', 'release'],
            'rumor': ['linked', 'target', 'interest', 'considering', 'might', 'could'],
            'loan': ['loan', 'borrowed', 'temporary']
        }
        
        # External injury data sources
        self.injury_sources = {
            'physioroom': 'https://www.physioroom.com/news/english_premier_league',
            'premierinjuries': 'https://www.premierinjuries.com/injury-table.php',
            'transfermarkt': 'https://www.transfermarkt.com/premier-league/verletztespieler/wettbewerb/GB1'
        }
    
    async def fetch_physioroom_data(self) -> List[Dict]:
        """Fetch injury data from PhysioRoom"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.injury_sources['physioroom'], timeout=15) as response:
                    content = await response.text()
                    
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Parse injury table (this would need adjustment based on actual HTML structure)
                    injury_data = []
                    
                    # Look for injury-related content
                    injury_divs = soup.find_all('div', class_=['injury-item', 'player-injury'])
                    
                    for div in injury_divs:
                        try:
                            player_name = div.find('span', class_='player-name')
                            injury_type = div.find('span', class_='injury-type')
                            return_date = div.find('span', class_='return-date')
                            team = div.find('span', class_='team')
                            
                            if player_name:
                                injury_data.append({
                                    'source': 'physioroom',
                                    'player_name': player_name.text.strip(),
                                    'injury_type': injury_type.text.strip() if injury_type else 'Unknown',
                                    'expected_return': return_date.text.strip() if return_date else 'Unknown',
                                    'team': team.text.strip() if team else 'Unknown',
                                    'timestamp': datetime.now().isoformat()
                                })
                        except Exception as e:
                            continue
                    
                    logger.info(f"Fetched {len(injury_data)} injuries from PhysioRoom")
                    return injury_data
                    
        except Exception as e:
            logger.error(f"Error fetching PhysioRoom data: {e}")
            return []
    
    def analyze_injury_severity(self, injury_description: str) -> Dict:
        """Analyze injury severity from description"""
        description_lower = injury_description.lower()
        
        severity_scores = {
            'minor': 0,
            'moderate': 0,
            'major': 0,
            'long_term': 0
        }
        
        for severity, keywords in self.severity_keywords.items():
            for keyword in keywords:
                if keyword in description_lower:
                    severity_scores[severity] += 1
        
        # Determine primary severity
        max_severity = max(severity_scores, key=severity_scores.get)
        
        # Estimate return timeframe
        if max_severity == 'minor':
            estimated_weeks = 1
        elif max_severity == 'moderate':
            estimated_weeks = 3
        elif max_severity == 'major':
            estimated_weeks = 8
        else:  # long_term
            estimated_weeks = 16
        
        return {
            'severity': max_severity,
            'estimated_weeks_out': estimated_weeks,
            'severity_scores': severity_scores,
            'confidence': max(severity_scores.values()) / max(1, sum(severity_scores.values()))
        }
    
    def get_fpl_injury_status(self) -> Dict:
        """Get official FPL injury status"""
        try:
            injury_status = self.live_data_manager.get_player_injury_status()
            
            detailed_status = {}
            
            for player_id, status in injury_status.items():
                if not status['is_available']:
                    # Analyze severity from news text
                    news_text = status.get('news', '')
                    severity_analysis = self.analyze_injury_severity(news_text)
                    
                    detailed_status[player_id] = {
                        **status,
                        **severity_analysis,
                        'fpl_status': status['status'],
                        'chance_of_playing': status.get('chance_of_playing'),
                        'analysis_timestamp': datetime.now().isoformat()
                    }
            
            return detailed_status
            
        except Exception as e:
            logger.error(f"Error getting FPL injury status: {e}")
            return {}
    
    async def get_comprehensive_injury_report(self) -> Dict:
        """Get comprehensive injury report from multiple sources"""
        try:
            logger.info("Generating comprehensive injury report...")
            
            # Get FPL official data
            fpl_injuries = self.get_fpl_injury_status()
            
            # Get external injury data
            external_injuries = await self.fetch_physioroom_data()
            
            # Get sentiment analysis injury flags
            cached_data = self.live_data_manager.get_cached_data()
            sentiment_injuries = []
            
            if 'players' in cached_data:
                players_df = cached_data['players']
                sentiment_results = await self.sentiment_analyzer.run_sentiment_analysis(players_df)
                
                for player_id, data in sentiment_results.get('player_sentiment', {}).items():
                    if data.get('injury_flags', 0) > 0:
                        sentiment_injuries.append({
                            'player_id': player_id,
                            'name': data['name'],
                            'team': data['team'],
                            'injury_flags': data['injury_flags'],
                            'injury_risk': data['injury_risk'],
                            'news_items': [item for item in data['news_items'] if item.get('injury_mentions', 0) > 0]
                        })
            
            # Combine all injury data
            comprehensive_report = {
                'timestamp': datetime.now().isoformat(),
                'fpl_official_injuries': fpl_injuries,
                'external_injury_reports': external_injuries,
                'sentiment_injury_flags': sentiment_injuries,
                'summary': {
                    'total_injured_players': len(fpl_injuries),
                    'external_reports': len(external_injuries),
                    'sentiment_flags': len(sentiment_injuries),
                    'high_risk_players': len([p for p in sentiment_injuries if p['injury_risk'] == 'high'])
                }
            }
            
            # Save report
            report_file = self.cache_dir / f"injury_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(comprehensive_report, f, indent=2)
            
            # Save latest report
            latest_file = self.cache_dir / "latest_injury_report.json"
            with open(latest_file, 'w') as f:
                json.dump(comprehensive_report, f, indent=2)
            
            logger.info(f"Generated injury report: {comprehensive_report['summary']}")
            
            return comprehensive_report
            
        except Exception as e:
            logger.error(f"Error generating injury report: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'fpl_official_injuries': {},
                'external_injury_reports': [],
                'sentiment_injury_flags': [],
                'summary': {}
            }
    
    def get_player_injury_history(self, player_id: int, days_back: int = 30) -> List[Dict]:
        """Get injury history for a specific player"""
        try:
            history = []
            
            # Check recent injury reports
            for i in range(days_back):
                date = datetime.now() - timedelta(days=i)
                date_str = date.strftime('%Y%m%d')
                
                # Look for cached reports from that day
                pattern = f"injury_report_{date_str}_*.json"
                matching_files = list(self.cache_dir.glob(pattern))
                
                for file_path in matching_files:
                    try:
                        with open(file_path, 'r') as f:
                            report = json.load(f)
                            
                            # Check if player was mentioned in this report
                            if str(player_id) in report.get('fpl_official_injuries', {}):
                                injury_data = report['fpl_official_injuries'][str(player_id)]
                                history.append({
                                    'date': date.isoformat(),
                                    'status': injury_data.get('fpl_status', 'unknown'),
                                    'news': injury_data.get('news', ''),
                                    'chance_of_playing': injury_data.get('chance_of_playing'),
                                    'severity': injury_data.get('severity', 'unknown')
                                })
                    except Exception as e:
                        continue
            
            return sorted(history, key=lambda x: x['date'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting player injury history: {e}")
            return []
    
    def get_transfer_rumors(self) -> List[Dict]:
        """Get transfer rumors and news"""
        try:
            # This would integrate with transfer news APIs/sites
            # For now, extract from sentiment analysis
            
            latest_sentiment_file = self.sentiment_analyzer.cache_dir / "latest_sentiment.json"
            
            if latest_sentiment_file.exists():
                with open(latest_sentiment_file, 'r') as f:
                    sentiment_data = json.load(f)
                
                transfer_news = []
                
                for news_item in sentiment_data.get('news_items', []):
                    title_lower = news_item['title'].lower()
                    description_lower = news_item.get('description', '').lower()
                    full_text = f"{title_lower} {description_lower}"
                    
                    # Check for transfer keywords
                    transfer_type = None
                    for t_type, keywords in self.transfer_keywords.items():
                        if any(keyword in full_text for keyword in keywords):
                            transfer_type = t_type
                            break
                    
                    if transfer_type:
                        transfer_news.append({
                            'title': news_item['title'],
                            'description': news_item.get('description', ''),
                            'source': news_item['source'],
                            'link': news_item.get('link', ''),
                            'transfer_type': transfer_type,
                            'pub_date': news_item.get('pub_date', ''),
                            'timestamp': news_item.get('timestamp', '')
                        })
                
                return transfer_news
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting transfer rumors: {e}")
            return []
    
    def get_weekly_injury_impact_report(self) -> Dict:
        """Generate weekly report on injury impact for FPL"""
        try:
            # Get latest injury report
            latest_file = self.cache_dir / "latest_injury_report.json"
            
            if not latest_file.exists():
                return {'error': 'No recent injury report available'}
            
            with open(latest_file, 'r') as f:
                injury_report = json.load(f)
            
            # Analyze impact on FPL selections
            impact_analysis = {
                'high_impact_injuries': [],
                'players_to_avoid': [],
                'differential_opportunities': [],
                'captain_risks': []
            }
            
            for player_id, injury_data in injury_report.get('fpl_official_injuries', {}).items():
                player_name = injury_data.get('name', 'Unknown')
                severity = injury_data.get('severity', 'unknown')
                chance_playing = injury_data.get('chance_of_playing')
                
                # High impact if popular player is injured
                if severity in ['major', 'long_term'] or (chance_playing and chance_playing < 50):
                    impact_analysis['high_impact_injuries'].append({
                        'player_id': player_id,
                        'name': player_name,
                        'severity': severity,
                        'chance_of_playing': chance_playing,
                        'recommendation': 'Transfer out immediately'
                    })
                
                # Players to avoid
                if chance_playing and chance_playing < 75:
                    impact_analysis['players_to_avoid'].append({
                        'player_id': player_id,
                        'name': player_name,
                        'reason': 'Injury doubt',
                        'chance_of_playing': chance_playing
                    })
            
            # Add sentiment-based risks
            for player_data in injury_report.get('sentiment_injury_flags', []):
                if player_data.get('injury_risk') == 'high':
                    impact_analysis['captain_risks'].append({
                        'player_id': player_data['player_id'],
                        'name': player_data['name'],
                        'risk_level': 'high',
                        'reason': 'Multiple injury mentions in news'
                    })
            
            impact_analysis['timestamp'] = datetime.now().isoformat()
            impact_analysis['gameweek'] = self.live_data_manager.get_current_gameweek()
            
            return impact_analysis
            
        except Exception as e:
            logger.error(f"Error generating weekly injury impact report: {e}")
            return {'error': str(e)}

if __name__ == "__main__":
    import asyncio
    
    async def test_injury_tracker():
        logging.basicConfig(level=logging.INFO)
        
        tracker = InjuryTracker()
        
        # Test comprehensive injury report
        report = await tracker.get_comprehensive_injury_report()
        print(f"Generated injury report with {report['summary']} summary")
        
        # Test weekly impact report
        impact = tracker.get_weekly_injury_impact_report()
        print(f"Weekly impact analysis: {len(impact.get('high_impact_injuries', []))} high impact injuries")
    
    # Run test
    # asyncio.run(test_injury_tracker())