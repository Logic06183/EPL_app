"""
Hybrid Forecaster: Fusing Statistical Models with Contextual AI Analysis
Combines quantitative predictions with qualitative contextual analysis using Gemini AI
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import httpx
from dataclasses import dataclass

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

@dataclass
class HybridForecast:
    recommendation: str  # 'HOME_WIN', 'DRAW', 'AWAY_WIN'
    reasoning: str
    confidence_score: int  # 1-10
    statistical_baseline: StatisticalPrediction
    contextual_factors: List[str]
    final_probabilities: Dict[str, float]
    gemini_analysis: str

class HybridForecaster:
    """
    Advanced forecasting system that combines statistical models with AI contextual analysis
    """
    
    def __init__(self, use_gemini: bool = True):
        self.use_gemini = use_gemini
        self.statistical_models = {
            'xgboost': self._xgboost_prediction,
            'random_forest': self._random_forest_prediction,
            'ensemble': self._ensemble_prediction
        }
    
    async def generate_hybrid_forecast(
        self, 
        home_team: str, 
        away_team: str, 
        match_date: str,
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
            
            # Step 2: Gather contextual information
            contextual_data = await self._gather_contextual_data(
                home_team, away_team, match_date
            )
            
            # Step 3: Generate AI-enhanced forecast
            if self.use_gemini:
                hybrid_forecast = await self._generate_gemini_forecast(
                    home_team, away_team, statistical_pred, contextual_data
                )
            else:
                # Fallback to rule-based enhancement
                hybrid_forecast = self._generate_rule_based_forecast(
                    home_team, away_team, statistical_pred, contextual_data
                )
            
            return hybrid_forecast
            
        except Exception as e:
            logger.error(f"Error generating hybrid forecast: {e}")
            # Return basic statistical prediction as fallback
            return self._fallback_forecast(home_team, away_team, statistical_pred)
    
    async def _get_statistical_prediction(
        self, home_team: str, away_team: str, match_date: str, model_type: str
    ) -> StatisticalPrediction:
        """
        Get baseline statistical prediction from ML models
        """
        try:
            # Use the appropriate model
            model_func = self.statistical_models.get(model_type, self.statistical_models['ensemble'])
            probabilities = await model_func(home_team, away_team, match_date)
            
            return StatisticalPrediction(
                home_win_prob=probabilities['home_win'],
                draw_prob=probabilities['draw'],
                away_win_prob=probabilities['away_win'],
                confidence=probabilities.get('confidence', 0.75),
                model_version=model_type
            )
            
        except Exception as e:
            logger.error(f"Error getting statistical prediction: {e}")
            # Return balanced prediction as fallback
            return StatisticalPrediction(
                home_win_prob=0.35,
                draw_prob=0.30,
                away_win_prob=0.35,
                confidence=0.5,
                model_version='fallback'
            )
    
    async def _gather_contextual_data(
        self, home_team: str, away_team: str, match_date: str
    ) -> ContextualData:
        """
        Gather contextual information for the match
        """
        try:
            # Simulate gathering various contextual data sources
            # In production, these would be real API calls
            
            news_articles = await self._get_recent_news(home_team, away_team)
            injury_reports = await self._get_injury_reports(home_team, away_team)
            team_form = await self._get_team_form(home_team, away_team)
            head_to_head = await self._get_head_to_head(home_team, away_team)
            
            return ContextualData(
                news_articles=news_articles,
                injury_reports=injury_reports,
                team_form=team_form,
                head_to_head=head_to_head
            )
            
        except Exception as e:
            logger.error(f"Error gathering contextual data: {e}")
            return ContextualData(
                news_articles=[],
                injury_reports=[],
                team_form={},
                head_to_head={}
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
            # Construct prompt for Gemini
            system_prompt = """You are an expert betting analyst and football tactician. Your role is to synthesize a quantitative prediction from a statistical model with qualitative, real-world information to provide a final, nuanced prediction. You must explain your reasoning clearly, especially if your final recommendation conflicts with the initial statistical model's output. Structure your response as a valid JSON object."""
            
            user_prompt = f"""
            A statistical model predicts the following probabilities for {home_team} vs {away_team}:
            - Home Win: {statistical_pred.home_win_prob:.1%}
            - Draw: {statistical_pred.draw_prob:.1%}
            - Away Win: {statistical_pred.away_win_prob:.1%}
            
            Contextual information:
            - Recent news: {self._format_news(contextual_data.news_articles)}
            - Injury reports: {self._format_injuries(contextual_data.injury_reports)}
            - Team form: {self._format_team_form(contextual_data.team_form)}
            - Head-to-head record: {self._format_h2h(contextual_data.head_to_head)}
            
            Based on all this information, provide a final match prediction. Consider factors like:
            - Key player injuries or returns
            - Recent team form and momentum
            - Tactical matchups and playing styles
            - Motivation factors (league position, competitions)
            - Historical head-to-head patterns
            
            The JSON schema must have keys:
            - recommendation (string: 'HOME_WIN', 'DRAW', or 'AWAY_WIN')
            - reasoning (string: detailed explanation)
            - confidenceScore (integer 1-10)
            - adjustedProbabilities (object with home_win, draw, away_win as decimals)
            - keyFactors (array of strings)
            """
            
            # In a real implementation, this would call Gemini API
            # For now, simulate intelligent analysis
            gemini_response = await self._simulate_gemini_analysis(
                home_team, away_team, statistical_pred, contextual_data
            )
            
            return HybridForecast(
                recommendation=gemini_response['recommendation'],
                reasoning=gemini_response['reasoning'],
                confidence_score=gemini_response['confidenceScore'],
                statistical_baseline=statistical_pred,
                contextual_factors=gemini_response['keyFactors'],
                final_probabilities=gemini_response['adjustedProbabilities'],
                gemini_analysis=gemini_response['reasoning']
            )
            
        except Exception as e:
            logger.error(f"Error generating Gemini forecast: {e}")
            return self._generate_rule_based_forecast(home_team, away_team, statistical_pred, contextual_data)
    
    async def _simulate_gemini_analysis(
        self, home_team: str, away_team: str, 
        statistical_pred: StatisticalPrediction, 
        contextual_data: ContextualData
    ) -> Dict:
        """
        Simulate Gemini analysis (replace with actual API call in production)
        """
        # Simulate intelligent contextual analysis
        baseline_home = statistical_pred.home_win_prob
        baseline_draw = statistical_pred.draw_prob
        baseline_away = statistical_pred.away_win_prob
        
        # Apply contextual adjustments
        home_adjustment = 0.0
        away_adjustment = 0.0
        key_factors = []
        
        # Analyze team form
        if contextual_data.team_form:
            home_form = contextual_data.team_form.get('home_recent_form', 0)
            away_form = contextual_data.team_form.get('away_recent_form', 0)
            
            if home_form > away_form + 2:
                home_adjustment += 0.15
                key_factors.append(f"{home_team} in superior recent form")
            elif away_form > home_form + 2:
                away_adjustment += 0.15
                key_factors.append(f"{away_team} in superior recent form")
        
        # Analyze injuries
        if contextual_data.injury_reports:
            home_injuries = len([i for i in contextual_data.injury_reports if i.get('team') == home_team])
            away_injuries = len([i for i in contextual_data.injury_reports if i.get('team') == away_team])
            
            if home_injuries > away_injuries:
                home_adjustment -= 0.1
                key_factors.append(f"{home_team} missing key players due to injury")
            elif away_injuries > home_injuries:
                away_adjustment -= 0.1
                key_factors.append(f"{away_team} missing key players due to injury")
        
        # Apply adjustments
        adjusted_home = max(0.05, min(0.85, baseline_home + home_adjustment))
        adjusted_away = max(0.05, min(0.85, baseline_away + away_adjustment))
        adjusted_draw = max(0.1, 1.0 - adjusted_home - adjusted_away)
        
        # Normalize probabilities
        total = adjusted_home + adjusted_draw + adjusted_away
        adjusted_home /= total
        adjusted_draw /= total
        adjusted_away /= total
        
        # Determine recommendation
        if adjusted_home > adjusted_away and adjusted_home > adjusted_draw:
            recommendation = 'HOME_WIN'
            confidence = min(10, int(adjusted_home * 12))
        elif adjusted_away > adjusted_home and adjusted_away > adjusted_draw:
            recommendation = 'AWAY_WIN'
            confidence = min(10, int(adjusted_away * 12))
        else:
            recommendation = 'DRAW'
            confidence = min(10, int(adjusted_draw * 15))
        
        reasoning = f"""
        Statistical model baseline: {home_team} {baseline_home:.1%}, Draw {baseline_draw:.1%}, {away_team} {baseline_away:.1%}
        
        Key contextual factors considered:
        {' - ' + chr(10).join(key_factors) if key_factors else '- No significant contextual adjustments identified'}
        
        Final assessment: {recommendation.replace('_', ' ')} with {confidence}/10 confidence.
        The adjusted probabilities reflect {', '.join(key_factors[:2]) if key_factors else 'statistical baseline'}.
        """
        
        return {
            'recommendation': recommendation,
            'reasoning': reasoning.strip(),
            'confidenceScore': confidence,
            'adjustedProbabilities': {
                'home_win': round(adjusted_home, 3),
                'draw': round(adjusted_draw, 3),
                'away_win': round(adjusted_away, 3)
            },
            'keyFactors': key_factors
        }
    
    # Statistical model implementations
    async def _xgboost_prediction(self, home_team: str, away_team: str, match_date: str) -> Dict:
        """XGBoost model prediction"""
        # Simulate XGBoost model
        return {
            'home_win': 0.45,
            'draw': 0.30,
            'away_win': 0.25,
            'confidence': 0.82
        }
    
    async def _random_forest_prediction(self, home_team: str, away_team: str, match_date: str) -> Dict:
        """Random Forest model prediction"""
        # Simulate Random Forest model
        return {
            'home_win': 0.42,
            'draw': 0.32,
            'away_win': 0.26,
            'confidence': 0.78
        }
    
    async def _ensemble_prediction(self, home_team: str, away_team: str, match_date: str) -> Dict:
        """Ensemble model prediction"""
        # Simulate ensemble of multiple models
        return {
            'home_win': 0.44,
            'draw': 0.31,
            'away_win': 0.25,
            'confidence': 0.85
        }
    
    # Data gathering helper methods
    async def _get_recent_news(self, home_team: str, away_team: str) -> List[Dict]:
        """Get recent news articles about the teams"""
        return [
            {'title': f'{home_team} injury update', 'content': 'Key player returns from injury'},
            {'title': f'{away_team} tactics', 'content': 'Manager discusses new formation'}
        ]
    
    async def _get_injury_reports(self, home_team: str, away_team: str) -> List[Dict]:
        """Get current injury reports"""
        return [
            {'team': home_team, 'player': 'Key Player', 'status': 'doubtful'},
            {'team': away_team, 'player': 'Star Forward', 'status': 'fit'}
        ]
    
    async def _get_team_form(self, home_team: str, away_team: str) -> Dict:
        """Get recent team form"""
        return {
            'home_recent_form': 8,  # Out of 10
            'away_recent_form': 6,
            'home_last_5': 'WWLWD',
            'away_last_5': 'LWWLD'
        }
    
    async def _get_head_to_head(self, home_team: str, away_team: str) -> Dict:
        """Get head-to-head record"""
        return {
            'last_5_meetings': 'HWDHW',
            'home_wins': 3,
            'away_wins': 1,
            'draws': 1
        }
    
    # Utility methods
    def _format_news(self, news: List[Dict]) -> str:
        return '; '.join([f"{n['title']}: {n['content']}" for n in news[:3]])
    
    def _format_injuries(self, injuries: List[Dict]) -> str:
        return '; '.join([f"{i['team']}: {i['player']} ({i['status']})" for i in injuries])
    
    def _format_team_form(self, form: Dict) -> str:
        return f"Home: {form.get('home_last_5', 'N/A')}, Away: {form.get('away_last_5', 'N/A')}"
    
    def _format_h2h(self, h2h: Dict) -> str:
        return f"Last 5: {h2h.get('last_5_meetings', 'N/A')} (Home perspective)"
    
    def _generate_rule_based_forecast(
        self, home_team: str, away_team: str, 
        statistical_pred: StatisticalPrediction, contextual_data: ContextualData
    ) -> HybridForecast:
        """Fallback rule-based forecast when Gemini is unavailable"""
        return HybridForecast(
            recommendation='HOME_WIN' if statistical_pred.home_win_prob > 0.4 else 'AWAY_WIN',
            reasoning="Rule-based analysis using statistical baseline",
            confidence_score=int(statistical_pred.confidence * 10),
            statistical_baseline=statistical_pred,
            contextual_factors=["Statistical model only"],
            final_probabilities={
                'home_win': statistical_pred.home_win_prob,
                'draw': statistical_pred.draw_prob,
                'away_win': statistical_pred.away_win_prob
            },
            gemini_analysis="Gemini analysis unavailable - using statistical baseline"
        )
    
    def _fallback_forecast(self, home_team: str, away_team: str, statistical_pred: Optional[StatisticalPrediction]) -> HybridForecast:
        """Ultimate fallback when everything fails"""
        if not statistical_pred:
            statistical_pred = StatisticalPrediction(0.35, 0.30, 0.35, 0.5, 'fallback')
        
        return HybridForecast(
            recommendation='DRAW',
            reasoning="Insufficient data for reliable prediction",
            confidence_score=3,
            statistical_baseline=statistical_pred,
            contextual_factors=["Limited data"],
            final_probabilities={
                'home_win': 0.35,
                'draw': 0.30,
                'away_win': 0.35
            },
            gemini_analysis="Analysis unavailable"
        )