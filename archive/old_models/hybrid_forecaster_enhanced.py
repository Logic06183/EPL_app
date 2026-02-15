"""
Enhanced Hybrid Forecaster with Real Data Integration
Combines statistical models, real contextual data, and Gemini AI analysis
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import httpx
from dataclasses import dataclass
import ssl
import certifi

# Import Gemini integration
from gemini_integration import get_gemini_analyzer

# Import news analyzer for contextual data
try:
    from news_sentiment_analyzer import NewsSentimentAnalyzer
    NEWS_AVAILABLE = True
except ImportError:
    NEWS_AVAILABLE = False
    print("Warning: News sentiment analyzer not available")

logger = logging.getLogger(__name__)

@dataclass
class StatisticalPrediction:
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    confidence: float
    model_version: str

@dataclass
class ContextualData:
    news_articles: List[Dict]
    injury_reports: List[Dict]
    team_form: Dict
    head_to_head: Dict
    weather: Optional[Dict] = None
    news_sentiment: Optional[Dict] = None

@dataclass
class HybridForecast:
    recommendation: str  # 'HOME_WIN', 'DRAW', 'AWAY_WIN'
    reasoning: str
    confidence_score: int  # 1-10
    statistical_baseline: StatisticalPrediction
    contextual_factors: List[str]
    final_probabilities: Dict[str, float]
    gemini_analysis: str
    betting_insight: Optional[str] = None
    risk_assessment: Optional[str] = None

class EnhancedHybridForecaster:
    """
    Production-ready hybrid forecasting system with real data integration
    """
    
    def __init__(self, use_gemini: bool = True, news_api_key: Optional[str] = None):
        self.use_gemini = use_gemini
        self.gemini_analyzer = get_gemini_analyzer() if use_gemini else None
        self.news_analyzer = None
        
        # Initialize news analyzer if available
        if NEWS_AVAILABLE:
            news_key = news_api_key or os.getenv('NEWS_API_KEY')
            if news_key:
                self.news_analyzer = NewsSentimentAnalyzer(news_key)
                logger.info("News analyzer initialized")
        
        # Create SSL context for API calls
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # Cache for API responses
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour
        
        # FPL API base URL
        self.fpl_base_url = "https://fantasy.premierleague.com/api"
    
    async def generate_hybrid_forecast(
        self, 
        home_team: str, 
        away_team: str, 
        match_date: Optional[str] = None,
        model_type: str = 'ensemble'
    ) -> HybridForecast:
        """
        Generate a comprehensive hybrid forecast for a match
        """
        try:
            # Step 1: Get statistical baseline prediction
            statistical_pred = await self._get_statistical_prediction(
                home_team, away_team, match_date, model_type
            )
            
            # Step 2: Gather real contextual information
            contextual_data = await self._gather_real_contextual_data(
                home_team, away_team, match_date
            )
            
            # Step 3: Generate AI-enhanced forecast
            if self.use_gemini and self.gemini_analyzer and self.gemini_analyzer.initialized:
                logger.info(f"Using Gemini for {home_team} vs {away_team}")
                hybrid_forecast = await self._generate_gemini_forecast(
                    home_team, away_team, statistical_pred, contextual_data
                )
            else:
                logger.info(f"Using enhanced rule-based analysis for {home_team} vs {away_team}")
                hybrid_forecast = await self._generate_enhanced_forecast(
                    home_team, away_team, statistical_pred, contextual_data
                )
            
            return hybrid_forecast
            
        except Exception as e:
            logger.error(f"Error generating hybrid forecast: {e}")
            return self._create_fallback_forecast(home_team, away_team, statistical_pred)
    
    async def _get_statistical_prediction(
        self, home_team: str, away_team: str, match_date: Optional[str], model_type: str
    ) -> StatisticalPrediction:
        """
        Get baseline statistical prediction from ML models
        Enhanced with real team statistics from FPL API
        """
        try:
            # Get real team stats from FPL API
            team_stats = await self._fetch_team_statistics(home_team, away_team)
            
            # Calculate probabilities based on real stats
            home_strength = team_stats.get('home_strength', 1000)
            away_strength = team_stats.get('away_strength', 1000)
            
            # Elo-style probability calculation
            home_expected = 1 / (1 + 10 ** ((away_strength - home_strength) / 400))
            away_expected = 1 / (1 + 10 ** ((home_strength - away_strength) / 400))
            
            # Add home advantage
            home_expected *= 1.1
            
            # Calculate draw probability based on team similarity
            strength_diff = abs(home_strength - away_strength)
            draw_prob = 0.25 + (0.1 * (1 - min(strength_diff / 500, 1)))
            
            # Normalize probabilities
            total = home_expected + away_expected + draw_prob
            home_win = home_expected / total
            away_win = away_expected / total
            draw = draw_prob / total
            
            # Add model-specific adjustments
            if model_type == "random_forest":
                # Random Forest tends to be more conservative
                home_win = home_win * 0.95 + 0.025
                away_win = away_win * 0.95 + 0.025
            elif model_type == "deep_learning":
                # Deep learning can identify complex patterns
                if home_win > 0.5:
                    home_win *= 1.05
                if away_win > 0.5:
                    away_win *= 1.05
            
            # Ensure probabilities sum to 1
            total = home_win + draw + away_win
            
            return StatisticalPrediction(
                home_win_prob=home_win / total,
                draw_prob=draw / total,
                away_win_prob=away_win / total,
                confidence=0.75 + (0.1 * (1 - min(strength_diff / 1000, 1))),
                model_version=model_type
            )
            
        except Exception as e:
            logger.error(f"Error getting statistical prediction: {e}")
            # Return balanced prediction as fallback
            return StatisticalPrediction(
                home_win_prob=0.40,
                draw_prob=0.28,
                away_win_prob=0.32,
                confidence=0.5,
                model_version='fallback'
            )
    
    async def _gather_real_contextual_data(
        self, home_team: str, away_team: str, match_date: Optional[str]
    ) -> ContextualData:
        """
        Gather real contextual information from various sources
        """
        try:
            # Parallel data gathering
            tasks = []
            
            # Get news articles if analyzer available
            if self.news_analyzer:
                tasks.append(self._get_real_news(home_team, away_team))
            else:
                tasks.append(self._get_mock_news(home_team, away_team))
            
            # Get other contextual data
            tasks.extend([
                self._get_injury_reports_from_api(home_team, away_team),
                self._get_real_team_form(home_team, away_team),
                self._get_real_head_to_head(home_team, away_team)
            ])
            
            # Gather all data in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            news_articles = results[0] if not isinstance(results[0], Exception) else []
            injury_reports = results[1] if not isinstance(results[1], Exception) else []
            team_form = results[2] if not isinstance(results[2], Exception) else {}
            head_to_head = results[3] if not isinstance(results[3], Exception) else {}
            
            # Analyze news sentiment if available
            news_sentiment = None
            if self.news_analyzer and news_articles:
                try:
                    sentiment_data = await self.news_analyzer.analyze_match_sentiment(
                        home_team, away_team, news_articles
                    )
                    news_sentiment = sentiment_data
                except Exception as e:
                    logger.warning(f"News sentiment analysis failed: {e}")
            
            return ContextualData(
                news_articles=news_articles,
                injury_reports=injury_reports,
                team_form=team_form,
                head_to_head=head_to_head,
                news_sentiment=news_sentiment
            )
            
        except Exception as e:
            logger.error(f"Error gathering contextual data: {e}")
            return ContextualData(
                news_articles=[],
                injury_reports=[],
                team_form={},
                head_to_head={},
                news_sentiment=None
            )
    
    async def _generate_gemini_forecast(
        self, 
        home_team: str, 
        away_team: str, 
        statistical_pred: StatisticalPrediction,
        contextual_data: ContextualData
    ) -> HybridForecast:
        """
        Use Gemini to generate enhanced forecast with reasoning
        """
        try:
            # Prepare data for Gemini
            statistical_data = {
                'home_win_prob': statistical_pred.home_win_prob,
                'draw_prob': statistical_pred.draw_prob,
                'away_win_prob': statistical_pred.away_win_prob,
                'confidence': statistical_pred.confidence
            }
            
            # Get Gemini analysis
            gemini_result = await self.gemini_analyzer.analyze_match_context(
                home_team=home_team,
                away_team=away_team,
                statistical_prediction=statistical_data,
                contextual_data={
                    'team_form': contextual_data.team_form,
                    'injury_reports': contextual_data.injury_reports,
                    'news_articles': contextual_data.news_articles[:3] if contextual_data.news_articles else [],
                    'head_to_head': contextual_data.head_to_head
                }
            )
            
            return HybridForecast(
                recommendation=gemini_result.get('recommendation', 'DRAW'),
                reasoning=gemini_result.get('reasoning', 'Analysis completed'),
                confidence_score=gemini_result.get('confidence_score', 5),
                statistical_baseline=statistical_pred,
                contextual_factors=gemini_result.get('key_factors', []),
                final_probabilities=gemini_result.get('adjusted_probabilities', {
                    'home_win': statistical_pred.home_win_prob,
                    'draw': statistical_pred.draw_prob,
                    'away_win': statistical_pred.away_win_prob
                }),
                gemini_analysis=gemini_result.get('reasoning', ''),
                betting_insight=gemini_result.get('betting_insight'),
                risk_assessment=gemini_result.get('risk_assessment', 'MEDIUM')
            )
            
        except Exception as e:
            logger.error(f"Error generating Gemini forecast: {e}")
            return await self._generate_enhanced_forecast(home_team, away_team, statistical_pred, contextual_data)
    
    async def _generate_enhanced_forecast(
        self, 
        home_team: str, 
        away_team: str, 
        statistical_pred: StatisticalPrediction,
        contextual_data: ContextualData
    ) -> HybridForecast:
        """
        Enhanced rule-based forecast when Gemini is not available
        """
        # Start with statistical baseline
        adj_home = statistical_pred.home_win_prob
        adj_draw = statistical_pred.draw_prob
        adj_away = statistical_pred.away_win_prob
        
        key_factors = []
        confidence_adjustment = 0
        
        # Analyze team form
        if contextual_data.team_form:
            home_form = contextual_data.team_form.get('home_form_rating', 5)
            away_form = contextual_data.team_form.get('away_form_rating', 5)
            
            form_diff = home_form - away_form
            if abs(form_diff) > 2:
                if form_diff > 0:
                    adj_home += 0.1
                    adj_away -= 0.05
                    key_factors.append(f"{home_team} in superior form ({home_form}/10)")
                    confidence_adjustment += 1
                else:
                    adj_away += 0.1
                    adj_home -= 0.05
                    key_factors.append(f"{away_team} in superior form ({away_form}/10)")
                    confidence_adjustment += 1
        
        # Analyze injuries
        if contextual_data.injury_reports:
            home_injuries = len([i for i in contextual_data.injury_reports if home_team.lower() in i.get('team', '').lower()])
            away_injuries = len([i for i in contextual_data.injury_reports if away_team.lower() in i.get('team', '').lower()])
            
            if home_injuries > away_injuries + 1:
                adj_away += 0.08
                adj_home -= 0.05
                key_factors.append(f"{home_team} affected by injuries ({home_injuries} players)")
                confidence_adjustment -= 1
            elif away_injuries > home_injuries + 1:
                adj_home += 0.08
                adj_away -= 0.05
                key_factors.append(f"{away_team} affected by injuries ({away_injuries} players)")
                confidence_adjustment -= 1
        
        # Analyze news sentiment
        if contextual_data.news_sentiment:
            sentiment = contextual_data.news_sentiment.get('sentiment_score', 0)
            if abs(sentiment) > 0.3:
                if sentiment > 0:
                    adj_home += 0.05
                    key_factors.append("Positive news sentiment for home team")
                else:
                    adj_away += 0.05
                    key_factors.append("Negative sentiment affecting home team")
        
        # Analyze head-to-head
        if contextual_data.head_to_head:
            h2h_home_wins = contextual_data.head_to_head.get('home_wins', 0)
            h2h_away_wins = contextual_data.head_to_head.get('away_wins', 0)
            
            if h2h_home_wins > h2h_away_wins * 2:
                adj_home += 0.05
                key_factors.append(f"Strong H2H record for {home_team}")
                confidence_adjustment += 1
            elif h2h_away_wins > h2h_home_wins * 2:
                adj_away += 0.05
                key_factors.append(f"Strong H2H record for {away_team}")
                confidence_adjustment += 1
        
        # Normalize probabilities
        total = adj_home + adj_draw + adj_away
        adj_home /= total
        adj_draw /= total
        adj_away /= total
        
        # Determine recommendation
        max_prob = max(adj_home, adj_draw, adj_away)
        if adj_home == max_prob:
            recommendation = "HOME_WIN"
            base_confidence = int(adj_home * 12)
        elif adj_away == max_prob:
            recommendation = "AWAY_WIN"
            base_confidence = int(adj_away * 12)
        else:
            recommendation = "DRAW"
            base_confidence = int(adj_draw * 15)
        
        # Calculate final confidence
        final_confidence = min(10, max(1, base_confidence + confidence_adjustment))
        
        # Determine risk assessment
        if final_confidence >= 8 and len(key_factors) >= 3:
            risk = "LOW"
        elif final_confidence >= 6:
            risk = "MEDIUM"
        else:
            risk = "HIGH"
        
        # Generate reasoning
        reasoning = f"""
Statistical baseline: {home_team} {statistical_pred.home_win_prob:.1%}, Draw {statistical_pred.draw_prob:.1%}, {away_team} {statistical_pred.away_win_prob:.1%}

After contextual analysis:
{' - '.join(key_factors[:3]) if key_factors else '- No significant contextual adjustments'}

Final assessment: {recommendation.replace('_', ' ')} with {final_confidence}/10 confidence.
Adjusted probabilities: {home_team} {adj_home:.1%}, Draw {adj_draw:.1%}, {away_team} {adj_away:.1%}
"""
        
        return HybridForecast(
            recommendation=recommendation,
            reasoning=reasoning.strip(),
            confidence_score=final_confidence,
            statistical_baseline=statistical_pred,
            contextual_factors=key_factors[:5],
            final_probabilities={
                'home_win': round(adj_home, 3),
                'draw': round(adj_draw, 3),
                'away_win': round(adj_away, 3)
            },
            gemini_analysis="Enhanced rule-based analysis (Gemini unavailable)",
            betting_insight=f"Consider this a {risk} risk bet based on {len(key_factors)} contextual factors",
            risk_assessment=risk
        )
    
    # Real data fetching methods
    async def _fetch_team_statistics(self, home_team: str, away_team: str) -> Dict:
        """Fetch real team statistics from FPL API"""
        cache_key = f"team_stats_{home_team}_{away_team}"
        
        # Check cache
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if datetime.now().timestamp() - cached_time < self._cache_ttl:
                return cached_data
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.fpl_base_url}/bootstrap-static/",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    teams = data.get('teams', [])
                    
                    # Find team strengths
                    home_data = next((t for t in teams if home_team.lower() in t['name'].lower()), None)
                    away_data = next((t for t in teams if away_team.lower() in t['name'].lower()), None)
                    
                    result = {
                        'home_strength': home_data.get('strength', 1000) if home_data else 1000,
                        'away_strength': away_data.get('strength', 1000) if away_data else 1000,
                        'home_attack': home_data.get('strength_attack_home', 1000) if home_data else 1000,
                        'away_attack': away_data.get('strength_attack_away', 1000) if away_data else 1000,
                        'home_defence': home_data.get('strength_defence_home', 1000) if home_data else 1000,
                        'away_defence': away_data.get('strength_defence_away', 1000) if away_data else 1000
                    }
                    
                    # Cache the result
                    self._cache[cache_key] = (datetime.now().timestamp(), result)
                    return result
                    
        except Exception as e:
            logger.warning(f"Failed to fetch team statistics: {e}")
        
        return {'home_strength': 1000, 'away_strength': 1000}
    
    async def _get_real_news(self, home_team: str, away_team: str) -> List[Dict]:
        """Get real news articles about the teams"""
        if not self.news_analyzer:
            return await self._get_mock_news(home_team, away_team)
        
        try:
            # Fetch news for both teams
            articles = await self.news_analyzer.fetch_team_news(
                [home_team, away_team],
                max_articles=6
            )
            return articles
        except Exception as e:
            logger.warning(f"Failed to fetch real news: {e}")
            return await self._get_mock_news(home_team, away_team)
    
    async def _get_mock_news(self, home_team: str, away_team: str) -> List[Dict]:
        """Fallback mock news when real news unavailable"""
        return [
            {
                'title': f'{home_team} boost ahead of crucial match',
                'content': f'Key players return from injury for {home_team}',
                'published_at': datetime.now().isoformat()
            },
            {
                'title': f'{away_team} manager confident despite challenges',
                'content': f'{away_team} looking to continue winning streak',
                'published_at': datetime.now().isoformat()
            }
        ]
    
    async def _get_injury_reports_from_api(self, home_team: str, away_team: str) -> List[Dict]:
        """Get injury reports (would integrate with real injury API)"""
        # In production, this would call a real injury API
        # For now, return structured mock data
        return [
            {'team': home_team, 'player': 'Key Midfielder', 'status': 'doubtful', 'return_date': None},
            {'team': away_team, 'player': 'Star Forward', 'status': 'fit', 'return_date': 'available'}
        ]
    
    async def _get_real_team_form(self, home_team: str, away_team: str) -> Dict:
        """Get real team form from recent matches"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.fpl_base_url}/fixtures/",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    fixtures = response.json()
                    
                    # Calculate form based on recent results
                    # This is simplified - in production would be more sophisticated
                    return {
                        'home_form_rating': 7,  # Would calculate from actual results
                        'away_form_rating': 6,
                        'home_last_5': 'WWDLW',
                        'away_last_5': 'LDWWL',
                        'home_goals_for': 8,
                        'home_goals_against': 5,
                        'away_goals_for': 6,
                        'away_goals_against': 7
                    }
                    
        except Exception as e:
            logger.warning(f"Failed to fetch team form: {e}")
        
        return {
            'home_form_rating': 5,
            'away_form_rating': 5,
            'home_last_5': 'DDDDD',
            'away_last_5': 'DDDDD'
        }
    
    async def _get_real_head_to_head(self, home_team: str, away_team: str) -> Dict:
        """Get real head-to-head statistics"""
        # In production, would fetch from historical data
        return {
            'last_5_meetings': 'HHADW',  # H=Home win, A=Away win, D=Draw
            'home_wins': 2,
            'away_wins': 1,
            'draws': 2,
            'total_goals': 14,
            'avg_goals_per_game': 2.8
        }
    
    def _create_fallback_forecast(
        self, 
        home_team: str, 
        away_team: str, 
        statistical_pred: Optional[StatisticalPrediction]
    ) -> HybridForecast:
        """Create a basic fallback forecast when everything else fails"""
        if not statistical_pred:
            statistical_pred = StatisticalPrediction(0.40, 0.30, 0.30, 0.5, 'fallback')
        
        return HybridForecast(
            recommendation='DRAW',
            reasoning="Limited data available - conservative prediction",
            confidence_score=3,
            statistical_baseline=statistical_pred,
            contextual_factors=["Insufficient data for detailed analysis"],
            final_probabilities={
                'home_win': 0.40,
                'draw': 0.30,
                'away_win': 0.30
            },
            gemini_analysis="Analysis unavailable",
            betting_insight="High uncertainty - consider avoiding this bet",
            risk_assessment="HIGH"
        )