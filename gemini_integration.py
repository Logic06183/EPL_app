"""
Gemini AI Integration for Hybrid Forecaster
Provides real contextual analysis using Google's Gemini API
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

# Check for Gemini/Vertex AI availability
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: Google Generative AI not installed. Install with: pip install google-generativeai")

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """
    Gemini-powered contextual analysis for football predictions
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini analyzer
        
        Args:
            api_key: Google AI API key (or set GOOGLE_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        self.model = None
        self.initialized = False
        
        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                self.initialized = True
                logger.info("Gemini AI initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.initialized = False
        else:
            logger.warning("Gemini not available - using fallback analysis")
    
    async def analyze_match_context(
        self,
        home_team: str,
        away_team: str,
        statistical_prediction: Dict,
        contextual_data: Dict
    ) -> Dict:
        """
        Use Gemini to analyze match context and generate enhanced prediction
        
        Args:
            home_team: Home team name
            away_team: Away team name
            statistical_prediction: ML model predictions
            contextual_data: Additional context (news, injuries, form)
            
        Returns:
            Dict with AI analysis and adjusted predictions
        """
        if not self.initialized:
            return self._fallback_analysis(home_team, away_team, statistical_prediction, contextual_data)
        
        try:
            # Construct the prompt for Gemini
            prompt = self._build_analysis_prompt(
                home_team, away_team, statistical_prediction, contextual_data
            )
            
            # Generate response from Gemini
            response = await self._generate_gemini_response(prompt)
            
            # Parse and structure the response
            return self._parse_gemini_response(response)
            
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return self._fallback_analysis(home_team, away_team, statistical_prediction, contextual_data)
    
    def _build_analysis_prompt(
        self,
        home_team: str,
        away_team: str,
        statistical_prediction: Dict,
        contextual_data: Dict
    ) -> str:
        """
        Build a comprehensive prompt for Gemini analysis
        """
        prompt = f"""
You are an expert football analyst and betting advisor. Analyze the upcoming match between {home_team} (home) and {away_team} (away).

STATISTICAL MODEL PREDICTIONS:
- Home Win: {statistical_prediction.get('home_win_prob', 0):.1%}
- Draw: {statistical_prediction.get('draw_prob', 0):.1%}
- Away Win: {statistical_prediction.get('away_win_prob', 0):.1%}
- Model Confidence: {statistical_prediction.get('confidence', 0):.1%}

CONTEXTUAL INFORMATION:
"""
        
        # Add recent form
        if contextual_data.get('team_form'):
            form = contextual_data['team_form']
            prompt += f"""
RECENT FORM:
- {home_team} last 5 matches: {form.get('home_last_5', 'N/A')} (Form rating: {form.get('home_recent_form', 0)}/10)
- {away_team} last 5 matches: {form.get('away_last_5', 'N/A')} (Form rating: {form.get('away_recent_form', 0)}/10)
"""
        
        # Add injury information
        if contextual_data.get('injury_reports'):
            prompt += "\nINJURY REPORTS:\n"
            for injury in contextual_data['injury_reports'][:5]:
                prompt += f"- {injury.get('team')}: {injury.get('player')} - {injury.get('status')}\n"
        
        # Add news context
        if contextual_data.get('news_articles'):
            prompt += "\nRECENT NEWS:\n"
            for article in contextual_data['news_articles'][:3]:
                prompt += f"- {article.get('title')}: {article.get('content', '')[:100]}\n"
        
        # Add head-to-head
        if contextual_data.get('head_to_head'):
            h2h = contextual_data['head_to_head']
            prompt += f"""
HEAD-TO-HEAD RECORD:
- Last 5 meetings: {h2h.get('last_5_meetings', 'N/A')}
- {home_team} wins: {h2h.get('home_wins', 0)}
- {away_team} wins: {h2h.get('away_wins', 0)}
- Draws: {h2h.get('draws', 0)}
"""
        
        prompt += """

Based on ALL the above information, provide your expert analysis. You must respond with a valid JSON object containing:
{
    "recommendation": "HOME_WIN" or "DRAW" or "AWAY_WIN",
    "confidence_score": <integer 1-10>,
    "adjusted_probabilities": {
        "home_win": <decimal 0-1>,
        "draw": <decimal 0-1>,
        "away_win": <decimal 0-1>
    },
    "key_factors": [<list of 3-5 most important factors>],
    "reasoning": "<detailed explanation of your prediction>",
    "betting_insight": "<specific advice for bettors>",
    "risk_assessment": "LOW" or "MEDIUM" or "HIGH"
}

Consider:
1. How recent form affects the statistical baseline
2. Impact of injuries on key players
3. Historical head-to-head patterns
4. Home advantage factors
5. Motivation (league position, recent results)
6. Tactical matchups and playing styles

Provide your analysis as a JSON object only, no additional text.
"""
        return prompt
    
    async def _generate_gemini_response(self, prompt: str) -> str:
        """
        Generate response from Gemini model
        """
        if not self.initialized or not self.model:
            raise Exception("Gemini not initialized")
        
        try:
            # Use async generation if available
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            raise
    
    def _parse_gemini_response(self, response_text: str) -> Dict:
        """
        Parse Gemini's JSON response
        """
        try:
            # Clean the response text
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            # Parse JSON
            result = json.loads(response_text.strip())
            
            # Validate required fields
            required_fields = ['recommendation', 'confidence_score', 'adjusted_probabilities', 'reasoning']
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")
            
            # Normalize probabilities
            probs = result['adjusted_probabilities']
            total = probs['home_win'] + probs['draw'] + probs['away_win']
            if total > 0:
                probs['home_win'] /= total
                probs['draw'] /= total
                probs['away_win'] /= total
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.debug(f"Response text: {response_text}")
            
            # Try to extract key information from text response
            return self._extract_from_text(response_text)
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
            raise
    
    def _extract_from_text(self, text: str) -> Dict:
        """
        Fallback extraction from text if JSON parsing fails
        """
        # Simple keyword extraction
        recommendation = "DRAW"  # Default
        if "home win" in text.lower() or "home team" in text.lower():
            recommendation = "HOME_WIN"
        elif "away win" in text.lower() or "away team" in text.lower():
            recommendation = "AWAY_WIN"
        
        # Extract confidence (look for numbers 1-10)
        confidence = 5
        import re
        confidence_match = re.search(r'confidence[:\s]+(\d+)', text.lower())
        if confidence_match:
            confidence = min(10, max(1, int(confidence_match.group(1))))
        
        return {
            "recommendation": recommendation,
            "confidence_score": confidence,
            "adjusted_probabilities": {
                "home_win": 0.35,
                "draw": 0.30,
                "away_win": 0.35
            },
            "key_factors": ["Analysis extracted from text response"],
            "reasoning": text[:500] if len(text) > 500 else text,
            "betting_insight": "Gemini analysis available but response format unclear",
            "risk_assessment": "MEDIUM"
        }
    
    def _fallback_analysis(
        self,
        home_team: str,
        away_team: str,
        statistical_prediction: Dict,
        contextual_data: Dict
    ) -> Dict:
        """
        Fallback analysis when Gemini is not available
        """
        # Simple rule-based adjustments
        base_home = statistical_prediction.get('home_win_prob', 0.35)
        base_draw = statistical_prediction.get('draw_prob', 0.30)
        base_away = statistical_prediction.get('away_win_prob', 0.35)
        
        adjustments = []
        home_adj = 0
        away_adj = 0
        
        # Analyze form
        if contextual_data.get('team_form'):
            form = contextual_data['team_form']
            home_form = form.get('home_recent_form', 5)
            away_form = form.get('away_recent_form', 5)
            
            if home_form > away_form + 2:
                home_adj += 0.1
                adjustments.append(f"{home_team} in better form")
            elif away_form > home_form + 2:
                away_adj += 0.1
                adjustments.append(f"{away_team} in better form")
        
        # Analyze injuries
        if contextual_data.get('injury_reports'):
            home_injuries = sum(1 for i in contextual_data['injury_reports'] if i.get('team') == home_team)
            away_injuries = sum(1 for i in contextual_data['injury_reports'] if i.get('team') == away_team)
            
            if home_injuries > away_injuries:
                away_adj += 0.05
                adjustments.append(f"{home_team} has more injuries")
            elif away_injuries > home_injuries:
                home_adj += 0.05
                adjustments.append(f"{away_team} has more injuries")
        
        # Apply adjustments
        adj_home = min(0.85, max(0.1, base_home + home_adj))
        adj_away = min(0.85, max(0.1, base_away + away_adj))
        adj_draw = max(0.05, 1.0 - adj_home - adj_away)
        
        # Normalize
        total = adj_home + adj_draw + adj_away
        adj_home /= total
        adj_draw /= total
        adj_away /= total
        
        # Determine recommendation
        if adj_home > adj_away and adj_home > adj_draw:
            recommendation = "HOME_WIN"
            confidence = int(adj_home * 10)
        elif adj_away > adj_home and adj_away > adj_draw:
            recommendation = "AWAY_WIN"
            confidence = int(adj_away * 10)
        else:
            recommendation = "DRAW"
            confidence = int(adj_draw * 12)
        
        confidence = min(10, max(1, confidence))
        
        return {
            "recommendation": recommendation,
            "confidence_score": confidence,
            "adjusted_probabilities": {
                "home_win": round(adj_home, 3),
                "draw": round(adj_draw, 3),
                "away_win": round(adj_away, 3)
            },
            "key_factors": adjustments[:3] if adjustments else ["Statistical baseline only"],
            "reasoning": f"Based on statistical models and available context. {' '.join(adjustments[:2])}",
            "betting_insight": "Consider current odds and your risk tolerance",
            "risk_assessment": "MEDIUM" if confidence >= 7 else "HIGH"
        }
    
    async def analyze_news_sentiment(self, articles: List[Dict]) -> Dict:
        """
        Analyze sentiment of news articles using Gemini
        """
        if not self.initialized or not articles:
            return {"sentiment": "neutral", "summary": "No news available"}
        
        try:
            prompt = f"""
Analyze the sentiment and key themes from these football news articles:

{json.dumps(articles, indent=2)}

Provide a JSON response with:
{{
    "overall_sentiment": "positive" or "neutral" or "negative",
    "sentiment_score": <decimal -1 to 1>,
    "key_themes": [<list of main topics>],
    "summary": "<brief summary of news>",
    "impact_on_match": "high" or "medium" or "low"
}}
"""
            response = await self._generate_gemini_response(prompt)
            return self._parse_gemini_response(response)
            
        except Exception as e:
            logger.error(f"News sentiment analysis failed: {e}")
            return {"sentiment": "neutral", "summary": "Analysis unavailable"}

# Singleton instance
_gemini_analyzer = None

def get_gemini_analyzer(api_key: Optional[str] = None) -> GeminiAnalyzer:
    """
    Get or create the Gemini analyzer singleton
    """
    global _gemini_analyzer
    if _gemini_analyzer is None:
        _gemini_analyzer = GeminiAnalyzer(api_key)
    return _gemini_analyzer