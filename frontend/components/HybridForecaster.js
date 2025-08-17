'use client'

import { useState, useEffect } from 'react'
import { Brain, TrendingUp, Target, Zap, AlertCircle, CheckCircle, BarChart3, Lightbulb } from 'lucide-react'

export default function HybridForecaster() {
  const [predictions, setPredictions] = useState([])
  const [selectedMatch, setSelectedMatch] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    console.log('🏁 HybridForecaster component mounted - starting prediction fetch')
    fetchMatchPredictions()
    
    // Also try fetching after a short delay in case of timing issues
    const timer = setTimeout(() => {
      if (predictions.length === 0 && !loading) {
        console.log('⏰ Backup fetch triggered after 2 seconds')
        fetchMatchPredictions()
      }
    }, 2000)
    
    return () => clearTimeout(timer)
  }, [])

  const fetchMatchPredictions = async () => {
    console.log('🚀 fetchMatchPredictions called - setting loading to true')
    setLoading(true)
    setError(null)
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://epl-backend-77913915885.us-central1.run.app'
      const fullUrl = `${apiUrl}/api/match-predictions?limit=8`
      console.log('🔍 Fetching predictions from:', fullUrl)
      console.log('📊 Environment API URL:', process.env.NEXT_PUBLIC_API_URL)
      console.log('📊 Actual API URL used:', apiUrl)
      
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 15000) // 15 second timeout for AI analysis
      
      const response = await fetch(fullUrl, {
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      })
      clearTimeout(timeoutId)
      
      console.log('📊 Response status:', response.status, response.statusText)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const data = await response.json()
      console.log('✅ Predictions received:', data.predictions?.length || 0, 'matches')
      console.log('📋 Full response:', data)
      console.log('📊 Setting predictions to:', data.predictions)
      setPredictions(data.predictions || [])
    } catch (error) {
      console.error('❌ Error fetching hybrid predictions:', error)
      setError(error.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchDetailedForecast = async (homeTeam, awayTeam, matchDate) => {
    setLoading(true)
    
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'https://epl-backend-77913915885.us-central1.run.app'}/api/hybrid-forecast/${encodeURIComponent(homeTeam)}/${encodeURIComponent(awayTeam)}?match_date=${encodeURIComponent(matchDate)}`
      )
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const data = await response.json()
      setSelectedMatch(data)
    } catch (error) {
      console.error('Error fetching detailed forecast:', error)
      setError(error.message)
    } finally {
      setLoading(false)
    }
  }

  const getRecommendationColor = (recommendation) => {
    switch (recommendation) {
      case 'HOME_WIN': return 'text-green-400 bg-green-500/20'
      case 'AWAY_WIN': return 'text-blue-400 bg-blue-500/20'
      case 'DRAW': return 'text-yellow-400 bg-yellow-500/20'
      default: return 'text-white/60 bg-white/10'
    }
  }

  const getConfidenceColor = (confidence) => {
    if (confidence >= 8) return 'text-green-400'
    if (confidence >= 6) return 'text-yellow-400'
    return 'text-red-400'
  }

  const formatMatchTime = (kickoffTime) => {
    if (!kickoffTime) return 'TBD'
    const date = new Date(kickoffTime)
    return date.toLocaleDateString('en-US', { 
      weekday: 'short', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading && predictions.length === 0) {
    return (
      <div className="glass-epl rounded-3xl p-8">
        <div className="flex flex-col items-center justify-center py-12">
          <div className="loading-epl mb-6"></div>
          <h3 className="text-xl font-semibold text-white mb-2">🧠 Generating AI Forecasts</h3>
          <p className="text-white/70 text-center max-w-md">
            Combining statistical models with contextual analysis to generate hybrid predictions...
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass-epl rounded-3xl p-8">
        <div className="flex flex-col items-center justify-center py-12">
          <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">Analysis Error</h3>
          <p className="text-white/70 text-center mb-6 max-w-md">
            {error}
          </p>
          <button onClick={fetchMatchPredictions} className="btn-epl-primary">
            Retry Analysis
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-epl rounded-3xl p-6">
        <div className="header-epl mb-6">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="p-3 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full">
              <Brain className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-3xl font-bold text-white">🔮 Hybrid AI Forecaster</h2>
            {predictions.length === 0 && !loading && !error && (
              <button 
                onClick={() => {
                  console.log('🔄 Force refresh triggered by user')
                  fetchMatchPredictions()
                }}
                className="ml-4 px-3 py-1 bg-blue-500 text-white text-sm rounded animate-pulse"
              >
                🔄 Debug Refresh
              </button>
            )}
            <div className="ml-4 text-xs text-white/50">
              {loading ? 'Loading...' : error ? 'Error' : predictions.length > 0 ? `${predictions.length} predictions` : 'No data'}
            </div>
          </div>
          <p className="text-white/80 text-lg text-center">
            Advanced match predictions combining statistical models with contextual AI analysis
          </p>
        </div>

        {/* Methodology Overview */}
        <div className="bg-gradient-to-r from-purple-500/10 to-indigo-500/10 border border-purple-400/30 rounded-xl p-4 mb-6">
          <div className="flex items-start gap-3">
            <Lightbulb className="w-6 h-6 text-purple-400 mt-1" />
            <div>
              <h4 className="text-purple-200 font-medium mb-2">How Hybrid Forecasting Works</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-purple-200/80">
                <div>
                  <strong>Step 1:</strong> Statistical baseline using ensemble ML models (XGBoost, Random Forest)
                </div>
                <div>
                  <strong>Step 2:</strong> Contextual analysis of injuries, form, head-to-head, and news
                </div>
                <div>
                  <strong>Step 3:</strong> AI synthesis generates final prediction with detailed reasoning
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="stat-card-epl">
            <div className="text-2xl font-bold text-purple-400 mb-1">{predictions.length}</div>
            <div className="text-white/70 text-sm">Matches Analyzed</div>
            <div className="text-xs text-purple-300 mt-1">
              {loading ? 'Loading...' : error ? 'Error' : 'Ready'}
            </div>
          </div>
          <div className="stat-card-epl">
            <div className="text-2xl font-bold text-green-400 mb-1">
              {Math.round(predictions.reduce((sum, p) => sum + p.confidence, 0) / predictions.length || 0)}
            </div>
            <div className="text-white/70 text-sm">Avg Confidence</div>
          </div>
          <div className="stat-card-epl">
            <div className="text-2xl font-bold text-blue-400 mb-1">3</div>
            <div className="text-white/70 text-sm">AI Models</div>
          </div>
          <div className="stat-card-epl">
            <div className="text-2xl font-bold text-yellow-400 mb-1">15+</div>
            <div className="text-white/70 text-sm">Context Factors</div>
          </div>
        </div>
      </div>

      {/* Match Predictions Grid */}
      {predictions.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {predictions.map((prediction, index) => (
            <div 
              key={prediction.fixture_id} 
              className="glass-epl rounded-2xl p-6 hover:bg-white/10 transition-all duration-300 cursor-pointer group"
              onClick={() => fetchDetailedForecast(prediction.home_team, prediction.away_team, prediction.kickoff_time)}
            >
              {/* Match Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="text-white/60 text-sm">
                  {formatMatchTime(prediction.kickoff_time)}
                </div>
                <div className={`px-3 py-1 rounded-full text-sm font-bold ${getRecommendationColor(prediction.recommendation)}`}>
                  {prediction.recommendation.replace('_', ' ')}
                </div>
              </div>

              {/* Teams */}
              <div className="grid grid-cols-3 gap-4 items-center mb-4">
                <div className="text-right">
                  <div className="text-white font-bold text-lg">{prediction.home_team}</div>
                  <div className="text-white/60 text-sm">Home</div>
                </div>
                
                <div className="text-center">
                  <div className="text-2xl font-bold text-white mb-1">VS</div>
                  <div className={`text-sm font-medium ${getConfidenceColor(prediction.confidence)}`}>
                    {prediction.confidence}/10 confidence
                  </div>
                </div>
                
                <div className="text-left">
                  <div className="text-white font-bold text-lg">{prediction.away_team}</div>
                  <div className="text-white/60 text-sm">Away</div>
                </div>
              </div>

              {/* Probabilities */}
              <div className="grid grid-cols-3 gap-2 mb-4">
                <div className="text-center p-2 bg-white/10 rounded-lg">
                  <div className="text-green-400 font-bold">{Math.round(prediction.probabilities.home_win * 100)}%</div>
                  <div className="text-white/60 text-xs">Home Win</div>
                </div>
                <div className="text-center p-2 bg-white/10 rounded-lg">
                  <div className="text-yellow-400 font-bold">{Math.round(prediction.probabilities.draw * 100)}%</div>
                  <div className="text-white/60 text-xs">Draw</div>
                </div>
                <div className="text-center p-2 bg-white/10 rounded-lg">
                  <div className="text-blue-400 font-bold">{Math.round(prediction.probabilities.away_win * 100)}%</div>
                  <div className="text-white/60 text-xs">Away Win</div>
                </div>
              </div>

              {/* Key Factors */}
              {prediction.key_factors && prediction.key_factors.length > 0 && (
                <div className="mb-4">
                  <div className="text-white/60 text-sm mb-2">Key Factors:</div>
                  <div className="flex flex-wrap gap-2">
                    {prediction.key_factors.slice(0, 2).map((factor, idx) => (
                      <div key={idx} className="px-2 py-1 bg-purple-500/20 text-purple-300 rounded-full text-xs">
                        {factor}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Reasoning Preview */}
              <div className="text-xs text-white/60 italic border-t border-white/20 pt-3">
                "{prediction.reasoning_summary}"
              </div>

              {/* Hover Indicator */}
              <div className="opacity-0 group-hover:opacity-100 transition-opacity mt-3 text-center">
                <span className="text-purple-300 text-sm">Click for detailed analysis →</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="glass-epl rounded-3xl p-12 text-center">
          <BarChart3 className="w-16 h-16 text-white/50 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No Predictions Available</h3>
          <p className="text-white/70 mb-6">
            No upcoming matches found for analysis
          </p>
          <button onClick={fetchMatchPredictions} className="btn-epl-primary">
            Refresh Predictions
          </button>
        </div>
      )}

      {/* Detailed Forecast Modal */}
      {selectedMatch && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gradient-to-br from-gray-900 to-black border border-white/20 rounded-3xl p-8 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-2xl font-bold text-white">Detailed Hybrid Analysis</h3>
              <button 
                onClick={() => setSelectedMatch(null)}
                className="text-white/60 hover:text-white text-2xl"
              >
                ×
              </button>
            </div>

            <div className="space-y-6">
              {/* Match Info */}
              <div className="text-center">
                <h4 className="text-xl font-bold text-white mb-2">
                  {selectedMatch.match.home_team} vs {selectedMatch.match.away_team}
                </h4>
                <div className={`inline-block px-4 py-2 rounded-full text-lg font-bold ${getRecommendationColor(selectedMatch.forecast.recommendation)}`}>
                  Prediction: {selectedMatch.forecast.recommendation.replace('_', ' ')}
                </div>
                <div className="mt-2">
                  <span className={`text-lg font-medium ${getConfidenceColor(selectedMatch.forecast.confidence_score)}`}>
                    Confidence: {selectedMatch.forecast.confidence_score}/10
                  </span>
                </div>
              </div>

              {/* Statistical Baseline vs Final Probabilities */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white/10 rounded-xl p-4">
                  <h5 className="text-white font-semibold mb-3">Statistical Baseline</h5>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-white/70">Home Win:</span>
                      <span className="text-green-400 font-bold">{Math.round(selectedMatch.forecast.statistical_baseline.home_win * 100)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-white/70">Draw:</span>
                      <span className="text-yellow-400 font-bold">{Math.round(selectedMatch.forecast.statistical_baseline.draw * 100)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-white/70">Away Win:</span>
                      <span className="text-blue-400 font-bold">{Math.round(selectedMatch.forecast.statistical_baseline.away_win * 100)}%</span>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-br from-purple-500/20 to-indigo-500/20 border border-purple-400/30 rounded-xl p-4">
                  <h5 className="text-purple-200 font-semibold mb-3">AI-Enhanced Final</h5>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-purple-200/70">Home Win:</span>
                      <span className="text-green-400 font-bold">{Math.round(selectedMatch.forecast.final_probabilities.home_win * 100)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-purple-200/70">Draw:</span>
                      <span className="text-yellow-400 font-bold">{Math.round(selectedMatch.forecast.final_probabilities.draw * 100)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-purple-200/70">Away Win:</span>
                      <span className="text-blue-400 font-bold">{Math.round(selectedMatch.forecast.final_probabilities.away_win * 100)}%</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Contextual Factors */}
              {selectedMatch.forecast.contextual_factors.length > 0 && (
                <div className="bg-white/10 rounded-xl p-4">
                  <h5 className="text-white font-semibold mb-3">Contextual Factors Considered</h5>
                  <div className="flex flex-wrap gap-2">
                    {selectedMatch.forecast.contextual_factors.map((factor, idx) => (
                      <div key={idx} className="px-3 py-1 bg-blue-500/20 text-blue-300 rounded-full text-sm">
                        {factor}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Detailed Reasoning */}
              <div className="bg-white/10 rounded-xl p-4">
                <h5 className="text-white font-semibold mb-3">AI Analysis & Reasoning</h5>
                <div className="text-white/80 text-sm leading-relaxed whitespace-pre-line">
                  {selectedMatch.forecast.reasoning}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Action Button */}
      <div className="text-center">
        <button 
          onClick={fetchMatchPredictions} 
          disabled={loading}
          className="btn-epl-primary"
        >
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            {loading ? 'Analyzing...' : 'Refresh Predictions'}
          </div>
        </button>
      </div>
    </div>
  )
}