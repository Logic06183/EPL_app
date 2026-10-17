#!/usr/bin/env python3
"""
News Sentiment Analysis for FPL Players
Integrates with News API to analyze player sentiment and enhance predictions
"""

import os
import asyncio
import aiohttp
import ssl
import certifi
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from textblob import TextBlob
import re

logger = logging.getLogger(__name__)

class NewsSentimentAnalyzer:
    """Analyzes player news sentiment to enhance FPL predictions"""
    
    def __init__(self):
        self.news_api_key = os.getenv("NEWS_API_KEY", "")
        self.base_url = "https://newsapi.org/v2/everything"
        self.sentiment_cache = {}
        self.cache_expiry = {}
        
    async def get_player_sentiment(self, player_name: str, team_name: str) -> Dict:
        """Get sentiment analysis for a specific player"""
        
        # Check cache first (4 hour expiry)
        cache_key = f"{player_name}_{team_name}".lower()
        if (cache_key in self.sentiment_cache and 
            cache_key in self.cache_expiry and 
            datetime.now() < self.cache_expiry[cache_key]):
            return self.sentiment_cache[cache_key]
        
        if not self.news_api_key:
            return self._get_fallback_sentiment(player_name)
        
        try:
            sentiment_data = await self._fetch_news_sentiment(player_name, team_name)
            
            # Cache result for 4 hours
            self.sentiment_cache[cache_key] = sentiment_data
            self.cache_expiry[cache_key] = datetime.now() + timedelta(hours=4)
            
            return sentiment_data
            
        except Exception as e:
            logger.error(f"Error fetching sentiment for {player_name}: {e}")
            return self._get_fallback_sentiment(player_name)
    
    async def _fetch_news_sentiment(self, player_name: str, team_name: str) -> Dict:
        """Fetch and analyze news sentiment from News API"""
        
        # Search queries for player news
        queries = [
            f'"{player_name}" AND "{team_name}" AND (Premier League OR EPL OR FPL)',
            f'"{player_name}" AND (injury OR fitness OR form OR goal OR assist)',
            f'"{player_name}" AND (transfer OR contract OR manager)'
        ]
        
        all_articles = []
        
        # Create SSL context
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            for query in queries:
                params = {
                    'q': query,
                    'apiKey': self.news_api_key,
                    'language': 'en',
                    'sortBy': 'publishedAt',
                    'from': (datetime.now() - timedelta(days=7)).isoformat(),
                    'pageSize': 20
                }
                
                try:
                    async with session.get(self.base_url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            articles = data.get('articles', [])
                            all_articles.extend(articles)
                        else:
                            logger.warning(f"News API returned {response.status} for {player_name}")
                            
                except Exception as e:
                    logger.error(f"Error fetching news for query '{query}': {e}")
                    continue
        
        return self._analyze_articles(all_articles, player_name)
    
    def _analyze_articles(self, articles: List[Dict], player_name: str) -> Dict:
        """Analyze sentiment from news articles"""
        
        if not articles:
            return self._get_fallback_sentiment(player_name)
        
        sentiments = []
        injury_keywords = ['injury', 'injured', 'hurt', 'pain', 'surgery', 'recovery', 'rehabilitation']
        positive_keywords = ['goal', 'assist', 'win', 'victory', 'excellent', 'brilliant', 'outstanding', 'form']
        negative_keywords = ['miss', 'suspended', 'red card', 'poor', 'struggle', 'disappointing']
        
        relevant_articles = []
        
        for article in articles:
            title = article.get('title', '').lower()
            description = article.get('description', '').lower()
            content = article.get('content', '').lower()
            
            # Check if article is actually about this player
            if player_name.lower() in title or player_name.lower() in description:
                full_text = f"{title} {description} {content}"
                
                # Sentiment analysis using TextBlob
                blob = TextBlob(full_text)
                polarity = blob.sentiment.polarity  # -1 to 1
                
                # Adjust sentiment based on keywords
                sentiment_score = polarity
                
                # Injury detection (negative impact)
                if any(keyword in full_text for keyword in injury_keywords):
                    sentiment_score -= 0.3
                
                # Positive performance keywords
                if any(keyword in full_text for keyword in positive_keywords):
                    sentiment_score += 0.2
                
                # Negative performance keywords
                if any(keyword in full_text for keyword in negative_keywords):
                    sentiment_score -= 0.2
                
                # Clamp between -1 and 1
                sentiment_score = max(-1, min(1, sentiment_score))
                
                sentiments.append(sentiment_score)
                relevant_articles.append({
                    'title': article.get('title', ''),
                    'sentiment': sentiment_score,
                    'published': article.get('publishedAt', ''),
                    'source': article.get('source', {}).get('name', '')
                })
        
        if not sentiments:
            return self._get_fallback_sentiment(player_name)
        
        # Calculate overall sentiment
        avg_sentiment = sum(sentiments) / len(sentiments)
        
        # Convert to categorical
        if avg_sentiment > 0.1:
            sentiment_category = 'positive'
            sentiment_impact = min(1.0, avg_sentiment * 2)  # 0 to 1 scale
        elif avg_sentiment < -0.1:
            sentiment_category = 'negative'
            sentiment_impact = max(-1.0, avg_sentiment * 2)  # -1 to 0 scale
        else:
            sentiment_category = 'neutral'
            sentiment_impact = 0.0
        
        return {
            'sentiment': sentiment_category,
            'sentiment_score': round(avg_sentiment, 3),
            'sentiment_impact': round(sentiment_impact, 3),
            'articles_analyzed': len(relevant_articles),
            'confidence': min(0.9, 0.5 + (len(relevant_articles) * 0.1)),
            'recent_articles': relevant_articles[:3],  # Top 3 most recent
            'last_updated': datetime.now().isoformat(),
            'news_summary': self._generate_summary(relevant_articles)
        }
    
    def _generate_summary(self, articles: List[Dict]) -> str:
        """Generate a brief summary of recent news"""
        if not articles:
            return "No recent news found."
        
        recent_count = len(articles)
        positive_count = len([a for a in articles if a['sentiment'] > 0.1])
        negative_count = len([a for a in articles if a['sentiment'] < -0.1])
        
        if positive_count > negative_count:
            tone = "positive"
        elif negative_count > positive_count:
            tone = "negative"
        else:
            tone = "mixed"
        
        return f"Recent analysis of {recent_count} articles shows {tone} sentiment. Latest coverage includes performance updates and team news."
    
    def _get_fallback_sentiment(self, player_name: str) -> Dict:
        """Fallback sentiment when no news data is available"""
        return {
            'sentiment': 'neutral',
            'sentiment_score': 0.0,
            'sentiment_impact': 0.0,
            'articles_analyzed': 0,
            'confidence': 0.3,
            'recent_articles': [],
            'last_updated': datetime.now().isoformat(),
            'news_summary': f"No recent news available for {player_name}. Using neutral sentiment baseline."
        }

# Integration with existing AI Predictor
class EnhancedAIPredictor:
    """Enhanced AI Predictor with News Sentiment Analysis"""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.is_trained = False
        self.sentiment_analyzer = NewsSentimentAnalyzer()
        
    async def predict_with_sentiment(self, player_data: Dict) -> tuple:
        """Make predictions enhanced with news sentiment"""
        
        # Get base prediction
        base_prediction, base_confidence = self._base_predict(player_data)
        
        # Get sentiment analysis
        player_name = player_data.get('web_name', '')
        team_name = player_data.get('team_name', '')
        
        sentiment_data = await self.sentiment_analyzer.get_player_sentiment(player_name, team_name)
        
        # Enhance prediction with sentiment
        sentiment_impact = sentiment_data['sentiment_impact']
        sentiment_confidence = sentiment_data['confidence']
        
        # Adjust prediction based on sentiment
        enhanced_prediction = base_prediction + (sentiment_impact * 2.0)  # Up to ±2 points impact
        enhanced_confidence = (base_confidence + sentiment_confidence) / 2
        
        # Enhanced reasoning
        reasoning = self._generate_enhanced_reasoning(
            player_data, 
            base_prediction, 
            sentiment_data
        )
        
        return enhanced_prediction, enhanced_confidence, sentiment_data, reasoning
    
    def _base_predict(self, player_data: Dict) -> tuple:
        """Base prediction without sentiment (existing logic)"""
        form = float(player_data.get("form", 5.0))
        predicted_points = form + (form * 0.2)  # Simple form-based prediction
        confidence = 0.75
        return predicted_points, confidence
    
    def _generate_enhanced_reasoning(self, player_data: Dict, base_prediction: float, sentiment_data: Dict) -> str:
        """Generate enhanced reasoning with sentiment analysis"""
        
        form = player_data.get('form', 0)
        sentiment = sentiment_data['sentiment']
        articles_count = sentiment_data['articles_analyzed']
        
        base_text = f"Player showing form of {form}. "
        
        if articles_count > 0:
            if sentiment == 'positive':
                sentiment_text = f"Recent news analysis of {articles_count} articles shows positive sentiment, suggesting good momentum. "
            elif sentiment == 'negative':
                sentiment_text = f"Recent news analysis of {articles_count} articles shows concerning sentiment, potentially affecting performance. "
            else:
                sentiment_text = f"Recent news analysis of {articles_count} articles shows neutral sentiment. "
        else:
            sentiment_text = "No recent news sentiment data available. "
        
        prediction_text = f"AI prediction adjusted to {base_prediction:.1f} points considering both statistical performance and media sentiment."
        
        return base_text + sentiment_text + prediction_text

# Test function
async def test_sentiment_analyzer():
    """Test the sentiment analyzer"""
    analyzer = NewsSentimentAnalyzer()
    
    # Test with some popular players
    test_players = [
        ("Haaland", "Man City"),
        ("Salah", "Liverpool"),
        ("Kane", "Tottenham")
    ]
    
    for player, team in test_players:
        print(f"\nTesting sentiment for {player} ({team}):")
        sentiment = await analyzer.get_player_sentiment(player, team)
        print(f"Sentiment: {sentiment['sentiment']}")
        print(f"Score: {sentiment['sentiment_score']}")
        print(f"Articles: {sentiment['articles_analyzed']}")
        print(f"Summary: {sentiment['news_summary']}")

if __name__ == "__main__":
    asyncio.run(test_sentiment_analyzer())