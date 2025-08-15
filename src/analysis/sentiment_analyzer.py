import requests
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path
import re
from textblob import TextBlob
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import time

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    def __init__(self, cache_dir: str = "./data/news_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # News sources and their RSS feeds
        self.news_sources = {
            'bbc_sport': 'https://feeds.bbci.co.uk/sport/football/rss.xml',
            'sky_sports': 'https://www.skysports.com/rss/12040',
            'premier_league': 'https://www.premierleague.com/rss',
            'guardian': 'https://www.theguardian.com/football/premierleague/rss',
            'telegraph': 'https://www.telegraph.co.uk/football/rss'
        }
        
        # Injury/form keywords for sentiment analysis
        self.injury_keywords = [
            'injured', 'injury', 'hurt', 'pain', 'strain', 'tear', 'broken',
            'surgery', 'operation', 'sidelined', 'out', 'miss', 'doubt',
            'doubtful', 'unavailable', 'ruled out', 'withdrawn', 'substituted',
            'limping', 'treatment', 'medical', 'fitness test', 'scan'
        ]
        
        self.positive_keywords = [
            'excellent', 'outstanding', 'brilliant', 'fantastic', 'superb',
            'impressive', 'strong', 'confident', 'fit', 'ready', 'return',
            'recovered', 'sharp', 'form', 'goal', 'assist', 'clean sheet',
            'win', 'victory', 'champion', 'leader', 'best', 'top'
        ]
        
        self.negative_keywords = [
            'poor', 'disappointing', 'struggle', 'worst', 'fail', 'loss',
            'defeat', 'red card', 'yellow card', 'penalty', 'mistake',
            'error', 'suspended', 'ban', 'fine', 'criticism', 'dropped'
        ]
        
        # Premier League teams for context
        self.pl_teams = [
            'Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford', 'Brighton',
            'Burnley', 'Chelsea', 'Crystal Palace', 'Everton', 'Fulham',
            'Liverpool', 'Luton', 'Manchester City', 'Manchester United',
            'Newcastle', 'Nottingham Forest', 'Sheffield United', 'Tottenham',
            'West Ham', 'Wolves'
        ]
    
    async def fetch_news_from_source(self, source_name: str, url: str) -> List[Dict]:
        """Fetch news from a single RSS source"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    content = await response.text()
                    
                    # Parse RSS/HTML content
                    soup = BeautifulSoup(content, 'xml')
                    items = soup.find_all('item')
                    
                    if not items:
                        # Try HTML parsing for non-RSS sources
                        soup = BeautifulSoup(content, 'html.parser')
                        # This would need customization per site
                        items = []
                    
                    news_items = []
                    for item in items[:20]:  # Limit to recent items
                        title = item.find('title')
                        description = item.find('description')
                        pub_date = item.find('pubDate')
                        link = item.find('link')
                        
                        news_item = {
                            'source': source_name,
                            'title': title.text if title else '',
                            'description': description.text if description else '',
                            'pub_date': pub_date.text if pub_date else '',
                            'link': link.text if link else '',
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # Only include Premier League related news
                        if self.is_pl_related(news_item['title'] + ' ' + news_item['description']):
                            news_items.append(news_item)
                    
                    logger.info(f"Fetched {len(news_items)} PL-related items from {source_name}")
                    return news_items
                    
        except Exception as e:
            logger.error(f"Error fetching news from {source_name}: {e}")
            return []
    
    def is_pl_related(self, text: str) -> bool:
        """Check if text is Premier League related"""
        text_lower = text.lower()
        
        # Check for team names
        for team in self.pl_teams:
            if team.lower() in text_lower:
                return True
        
        # Check for Premier League keywords
        pl_keywords = ['premier league', 'epl', 'fpl', 'fantasy premier league']
        return any(keyword in text_lower for keyword in pl_keywords)
    
    async def fetch_all_news(self) -> List[Dict]:
        """Fetch news from all sources concurrently"""
        tasks = []
        for source_name, url in self.news_sources.items():
            task = self.fetch_news_from_source(source_name, url)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_news = []
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
            else:
                logger.error(f"News fetch error: {result}")
        
        return all_news
    
    def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of text"""
        try:
            # Clean text
            text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
            text = re.sub(r'[^\w\s]', ' ', text)  # Remove special chars
            text = text.lower().strip()
            
            # Use TextBlob for basic sentiment
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # -1 (negative) to 1 (positive)
            subjectivity = blob.sentiment.subjectivity  # 0 (objective) to 1 (subjective)
            
            # Custom sentiment scoring based on keywords
            custom_score = 0
            
            # Check for injury/negative keywords
            injury_mentions = sum(1 for keyword in self.injury_keywords if keyword in text)
            negative_mentions = sum(1 for keyword in self.negative_keywords if keyword in text)
            positive_mentions = sum(1 for keyword in self.positive_keywords if keyword in text)
            
            custom_score = positive_mentions - (injury_mentions * 2) - negative_mentions
            
            # Normalize custom score
            custom_normalized = max(-1, min(1, custom_score / 10))
            
            # Combine TextBlob and custom scoring
            final_score = (polarity + custom_normalized) / 2
            
            # Classify sentiment
            if final_score > 0.1:
                sentiment = 'positive'
            elif final_score < -0.1:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
            
            return {
                'sentiment': sentiment,
                'score': final_score,
                'polarity': polarity,
                'subjectivity': subjectivity,
                'injury_mentions': injury_mentions,
                'positive_mentions': positive_mentions,
                'negative_mentions': negative_mentions
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                'sentiment': 'neutral',
                'score': 0,
                'polarity': 0,
                'subjectivity': 0,
                'injury_mentions': 0,
                'positive_mentions': 0,
                'negative_mentions': 0
            }
    
    def extract_player_mentions(self, text: str, players_df: pd.DataFrame) -> List[Dict]:
        """Extract player mentions from text"""
        mentions = []
        text_lower = text.lower()
        
        for _, player in players_df.iterrows():
            # Check for full name
            full_name = f"{player['first_name']} {player['second_name']}".lower()
            if full_name in text_lower:
                mentions.append({
                    'player_id': player['id'],
                    'name': f"{player['first_name']} {player['second_name']}",
                    'team': player.get('name_team', ''),
                    'mention_type': 'full_name'
                })
            
            # Check for last name only (if unique enough)
            last_name = player['second_name'].lower()
            if len(last_name) > 4 and last_name in text_lower:
                mentions.append({
                    'player_id': player['id'],
                    'name': f"{player['first_name']} {player['second_name']}",
                    'team': player.get('name_team', ''),
                    'mention_type': 'last_name'
                })
        
        return mentions
    
    def process_news_for_players(self, news_items: List[Dict], players_df: pd.DataFrame) -> Dict:
        """Process news items and extract player-specific sentiment"""
        player_sentiment = {}
        
        for news_item in news_items:
            # Combine title and description for analysis
            full_text = f"{news_item['title']} {news_item['description']}"
            
            # Analyze overall sentiment
            sentiment_analysis = self.analyze_sentiment(full_text)
            
            # Extract player mentions
            player_mentions = self.extract_player_mentions(full_text, players_df)
            
            # Apply sentiment to mentioned players
            for mention in player_mentions:
                player_id = mention['player_id']
                
                if player_id not in player_sentiment:
                    player_sentiment[player_id] = {
                        'name': mention['name'],
                        'team': mention['team'],
                        'news_items': [],
                        'total_sentiment': 0,
                        'sentiment_count': 0,
                        'injury_flags': 0,
                        'positive_news': 0,
                        'negative_news': 0
                    }
                
                # Add news item to player
                player_sentiment[player_id]['news_items'].append({
                    'source': news_item['source'],
                    'title': news_item['title'],
                    'sentiment': sentiment_analysis['sentiment'],
                    'score': sentiment_analysis['score'],
                    'injury_mentions': sentiment_analysis['injury_mentions'],
                    'pub_date': news_item['pub_date'],
                    'link': news_item['link']
                })
                
                # Update aggregated sentiment
                player_sentiment[player_id]['total_sentiment'] += sentiment_analysis['score']
                player_sentiment[player_id]['sentiment_count'] += 1
                player_sentiment[player_id]['injury_flags'] += sentiment_analysis['injury_mentions']
                
                if sentiment_analysis['sentiment'] == 'positive':
                    player_sentiment[player_id]['positive_news'] += 1
                elif sentiment_analysis['sentiment'] == 'negative':
                    player_sentiment[player_id]['negative_news'] += 1
        
        # Calculate average sentiment for each player
        for player_id, data in player_sentiment.items():
            if data['sentiment_count'] > 0:
                data['average_sentiment'] = data['total_sentiment'] / data['sentiment_count']
                data['sentiment_label'] = 'positive' if data['average_sentiment'] > 0.1 else 'negative' if data['average_sentiment'] < -0.1 else 'neutral'
                data['injury_risk'] = 'high' if data['injury_flags'] > 2 else 'medium' if data['injury_flags'] > 0 else 'low'
            else:
                data['average_sentiment'] = 0
                data['sentiment_label'] = 'neutral'
                data['injury_risk'] = 'low'
        
        return player_sentiment
    
    async def run_sentiment_analysis(self, players_df: pd.DataFrame) -> Dict:
        """Run complete sentiment analysis"""
        try:
            logger.info("Starting sentiment analysis...")
            
            # Fetch all news
            news_items = await self.fetch_all_news()
            logger.info(f"Fetched {len(news_items)} total news items")
            
            # Process news for player sentiment
            player_sentiment = self.process_news_for_players(news_items, players_df)
            logger.info(f"Analyzed sentiment for {len(player_sentiment)} players")
            
            # Save results
            timestamp = datetime.now()
            results = {
                'timestamp': timestamp.isoformat(),
                'total_news_items': len(news_items),
                'players_analyzed': len(player_sentiment),
                'news_items': news_items,
                'player_sentiment': player_sentiment
            }
            
            # Cache results
            cache_file = self.cache_dir / f"sentiment_analysis_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            with open(cache_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            # Save latest results
            latest_file = self.cache_dir / "latest_sentiment.json"
            with open(latest_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info("Sentiment analysis completed")
            return results
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'total_news_items': 0,
                'players_analyzed': 0,
                'news_items': [],
                'player_sentiment': {}
            }
    
    def get_player_sentiment_score(self, player_id: int) -> Dict:
        """Get sentiment score for a specific player"""
        try:
            latest_file = self.cache_dir / "latest_sentiment.json"
            
            if latest_file.exists():
                with open(latest_file, 'r') as f:
                    data = json.load(f)
                    
                    player_sentiment = data.get('player_sentiment', {})
                    
                    if str(player_id) in player_sentiment:
                        return player_sentiment[str(player_id)]
            
            return {
                'average_sentiment': 0,
                'sentiment_label': 'neutral',
                'injury_risk': 'low',
                'news_items': []
            }
            
        except Exception as e:
            logger.error(f"Error getting player sentiment: {e}")
            return {
                'average_sentiment': 0,
                'sentiment_label': 'neutral',
                'injury_risk': 'low',
                'news_items': []
            }
    
    def get_latest_injury_news(self) -> List[Dict]:
        """Get latest injury-related news"""
        try:
            latest_file = self.cache_dir / "latest_sentiment.json"
            
            if latest_file.exists():
                with open(latest_file, 'r') as f:
                    data = json.load(f)
                    
                    injury_news = []
                    
                    for player_data in data.get('player_sentiment', {}).values():
                        if player_data.get('injury_flags', 0) > 0:
                            for news_item in player_data.get('news_items', []):
                                if news_item.get('injury_mentions', 0) > 0:
                                    injury_news.append({
                                        'player_name': player_data['name'],
                                        'team': player_data['team'],
                                        'title': news_item['title'],
                                        'source': news_item['source'],
                                        'link': news_item['link'],
                                        'injury_mentions': news_item['injury_mentions'],
                                        'pub_date': news_item['pub_date']
                                    })
                    
                    # Sort by injury mentions (most concerning first)
                    injury_news.sort(key=lambda x: x['injury_mentions'], reverse=True)
                    
                    return injury_news
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting injury news: {e}")
            return []

if __name__ == "__main__":
    import asyncio
    from ..data.live_data_manager import LiveDataManager
    
    async def test_sentiment_analyzer():
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        
        # Get current players data
        live_manager = LiveDataManager()
        cached_data = live_manager.get_cached_data()
        
        if 'players' in cached_data:
            players_df = cached_data['players']
            
            # Run sentiment analysis
            analyzer = SentimentAnalyzer()
            results = await analyzer.run_sentiment_analysis(players_df)
            
            print(f"Analyzed {results['players_analyzed']} players")
            print(f"Found {results['total_news_items']} news items")
            
            # Show some example results
            for player_id, data in list(results['player_sentiment'].items())[:5]:
                print(f"\n{data['name']} ({data['team']}):")
                print(f"  Sentiment: {data['sentiment_label']} ({data['average_sentiment']:.2f})")
                print(f"  Injury Risk: {data['injury_risk']}")
                print(f"  News Items: {len(data['news_items'])}")
    
    # Run test
    # asyncio.run(test_sentiment_analyzer())