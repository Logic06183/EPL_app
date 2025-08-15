from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import tweepy
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
import re

logger = logging.getLogger(__name__)

class PlayerSentimentAnalyzer:
    def __init__(self, twitter_credentials: Optional[Dict] = None, news_api_key: Optional[str] = None):
        self.transformer_sentiment = pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest"
        )
        
        self.vader = SentimentIntensityAnalyzer()
        
        self.twitter_client = None
        if twitter_credentials:
            self._setup_twitter(twitter_credentials)
        
        self.news_api_key = news_api_key
        
    def _setup_twitter(self, credentials: Dict):
        try:
            auth = tweepy.OAuthHandler(
                credentials['api_key'],
                credentials['api_secret']
            )
            auth.set_access_token(
                credentials['access_token'],
                credentials['access_token_secret']
            )
            self.twitter_client = tweepy.API(auth)
        except Exception as e:
            logger.error(f"Failed to setup Twitter client: {e}")
    
    def analyze_text_sentiment(self, text: str) -> Dict:
        text_clean = re.sub(r'http\S+', '', text)
        text_clean = re.sub(r'@\w+', '', text_clean)
        text_clean = text_clean[:512]
        
        try:
            transformer_result = self.transformer_sentiment(text_clean)[0]
            
            label_to_score = {
                'POSITIVE': 1.0,
                'NEGATIVE': -1.0,
                'NEUTRAL': 0.0
            }
            transformer_score = label_to_score.get(
                transformer_result['label'].upper(), 
                0.0
            ) * transformer_result['score']
        except Exception as e:
            logger.warning(f"Transformer analysis failed: {e}")
            transformer_score = 0.0
        
        vader_scores = self.vader.polarity_scores(text)
        
        combined_score = (transformer_score + vader_scores['compound']) / 2
        
        return {
            'text': text[:100],
            'transformer_score': transformer_score,
            'vader_compound': vader_scores['compound'],
            'combined_score': combined_score,
            'sentiment_label': self._score_to_label(combined_score)
        }
    
    def _score_to_label(self, score: float) -> str:
        if score > 0.1:
            return 'positive'
        elif score < -0.1:
            return 'negative'
        else:
            return 'neutral'
    
    def get_player_tweets(self, player_name: str, limit: int = 100) -> List[Dict]:
        if not self.twitter_client:
            logger.warning("Twitter client not configured")
            return []
        
        tweets = []
        try:
            for tweet in tweepy.Cursor(
                self.twitter_client.search_tweets,
                q=f"{player_name} -filter:retweets",
                lang="en",
                tweet_mode="extended"
            ).items(limit):
                sentiment = self.analyze_text_sentiment(tweet.full_text)
                tweets.append({
                    'created_at': tweet.created_at,
                    'text': tweet.full_text,
                    **sentiment
                })
        except Exception as e:
            logger.error(f"Error fetching tweets: {e}")
        
        return tweets
    
    def get_player_news_sentiment(self, player_name: str, team_name: str = "") -> List[Dict]:
        if not self.news_api_key:
            logger.warning("News API key not configured")
            return []
        
        articles = []
        query = f"{player_name} {team_name} Premier League".strip()
        
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': query,
                'apiKey': self.news_api_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'from': (datetime.now() - timedelta(days=7)).isoformat()
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            for article in data.get('articles', [])[:20]:
                text = f"{article.get('title', '')} {article.get('description', '')}"
                sentiment = self.analyze_text_sentiment(text)
                
                articles.append({
                    'published_at': article.get('publishedAt'),
                    'source': article.get('source', {}).get('name'),
                    'title': article.get('title'),
                    'url': article.get('url'),
                    **sentiment
                })
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
        
        return articles
    
    def get_aggregated_sentiment(self, player_name: str, team_name: str = "") -> Dict:
        tweets = self.get_player_tweets(player_name)
        news = self.get_player_news_sentiment(player_name, team_name)
        
        all_sentiments = tweets + news
        
        if not all_sentiments:
            return {
                'player_name': player_name,
                'sentiment_score': 0.0,
                'sentiment_label': 'neutral',
                'sample_size': 0,
                'positive_ratio': 0.0,
                'negative_ratio': 0.0,
                'sources': {'twitter': 0, 'news': 0}
            }
        
        scores = [item['combined_score'] for item in all_sentiments]
        avg_score = sum(scores) / len(scores)
        
        positive_count = sum(1 for s in scores if s > 0.1)
        negative_count = sum(1 for s in scores if s < -0.1)
        
        return {
            'player_name': player_name,
            'sentiment_score': avg_score,
            'sentiment_label': self._score_to_label(avg_score),
            'sample_size': len(all_sentiments),
            'positive_ratio': positive_count / len(all_sentiments),
            'negative_ratio': negative_count / len(all_sentiments),
            'sources': {
                'twitter': len(tweets),
                'news': len(news)
            },
            'recent_headlines': [n['title'] for n in news[:3]]
        }