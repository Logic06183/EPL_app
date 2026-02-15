'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, Star, DollarSign, Users, Loader2, AlertCircle, Trophy, Zap, Crown, Target } from 'lucide-react'
import { getPredictions, getEnhancedPredictions, getModelInfo, handleApiError } from '../lib/api'

export default function PlayerPredictionsEPL() {
  const [predictions, setPredictions] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [topN, setTopN] = useState(20)
  const [useGemini, setUseGemini] = useState(false)
  const [filter, setFilter] = useState('all')
  const [modelType, setModelType] = useState('random_forest')
  const [modelInfo, setModelInfo] = useState(null)
  const [userTier, setUserTier] = useState('free') // 'free', 'basic', 'premium'

  useEffect(() => {
    fetchModelInfo()
  }, [])

  useEffect(() => {
    fetchPredictions()
  }, [topN, useGemini, modelType, filter])

  const fetchModelInfo = async () => {
    try {
      const data = await getModelInfo()
      setModelInfo(data)
    } catch (error) {
      console.error('Error fetching model info:', error)
    }
  }

  const fetchPredictions = async () => {
    setLoading(true)
    setError(null)

    try {
      // Enforce tier restrictions
      let actualModel = modelType
      if (userTier === 'free') {
        actualModel = 'random_forest'
      }

      const position = filter === 'all' ? null : parseInt(filter)

      let data
      if (useGemini && userTier === 'premium') {
        // Enhanced predictions with Gemini AI (premium only)
        data = await getEnhancedPredictions({
          topN,
          model: actualModel,
          useGemini: true,
        })
      } else {
        // Standard predictions
        data = await getPredictions({
          topN,
          model: actualModel,
          position,
        })
      }

      // The new backend returns an array directly
      setPredictions(Array.isArray(data) ? data : [])
    } catch (error) {
      console.error('Error fetching predictions:', error)
      setError(handleApiError(error))
    } finally {
      setLoading(false)
    }
  }

  const getPositionColor = (position) => {
    const colors = {
      1: 'position-gk',  // GK
      2: 'position-def', // DEF
      3: 'position-mid', // MID
      4: 'position-fwd'  // FWD
    }
    return colors[position] || 'position-def'
  }

  const getPositionName = (position) => {
    const names = {
      1: 'GK',
      2: 'DEF',
      3: 'MID',
      4: 'FWD'
    }
    return names[position] || 'PLAYER'
  }

  const getFormColor = (form) => {
    if (form >= 7) return 'form-excellent'
    if (form >= 5) return 'form-good'
    if (form >= 3) return 'form-average'
    return 'form-poor'
  }

  if (loading) {
    return (
      <div className="glass-epl rounded-3xl p-8">
        <div className="flex flex-col items-center justify-center py-12">
          <div className="loading-epl mb-6"></div>
          <h3 className="text-xl font-semibold text-white mb-2">⚽ Analyzing Premier League Players</h3>
          <p className="text-white/70 text-center max-w-md">
            {useGemini ? 'AI is processing player data with advanced algorithms...' : 'Fetching the latest player statistics and predictions...'}
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
          <h3 className="text-xl font-semibold text-white mb-2">Connection Error</h3>
          <p className="text-white/70 text-center mb-6 max-w-md">
            {error}
          </p>
          <button onClick={fetchPredictions} className="btn-epl-primary">
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header Controls with EPL Theme */}
      <div className="glass-epl rounded-3xl p-6">
        <div className="header-epl mb-6">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="p-3 bg-gradient-to-r from-green-400 to-blue-500 rounded-full">
              <TrendingUp className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-3xl font-bold text-white">🏆 Top Player Predictions</h2>
          </div>
          <p className="text-white/80 text-lg">AI-powered insights for Fantasy Premier League success</p>
        </div>

        {/* Subscription Tier Notice */}
        <div className="bg-white/5 rounded-xl p-4 mb-6 border border-white/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="text-2xl">
                {userTier === 'free' && '📊'}
                {userTier === 'basic' && '🤖'}
                {userTier === 'premium' && '🚀'}
              </div>
              <div>
                <h3 className="text-white font-semibold">
                  {userTier === 'free' && 'Free Tier - Basic Predictions'}
                  {userTier === 'basic' && 'Basic Tier - AI Enhanced'}
                  {userTier === 'premium' && 'Premium Tier - Advanced AI'}
                </h3>
                <p className="text-white/70 text-sm">
                  {userTier === 'free' && 'Random Forest model available. Upgrade for advanced features.'}
                  {userTier === 'basic' && 'AI predictions with xG/xA analytics available.'}
                  {userTier === 'premium' && 'All models including Gemini AI insights.'}
                </p>
              </div>
            </div>
            <select
              value={userTier}
              onChange={(e) => setUserTier(e.target.value)}
              className="p-2 rounded-lg bg-white/20 text-white border border-white/30 focus:border-white/50 text-sm"
            >
              <option value="free" className="text-black">📊 Free</option>
              <option value="basic" className="text-black">🤖 Basic</option>
              <option value="premium" className="text-black">🚀 Premium</option>
            </select>
          </div>
        </div>

        {/* Controls Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          {/* Top N Players */}
          <div className="space-y-2">
            <label className="text-white font-medium text-sm uppercase tracking-wide">Show Top</label>
            <select
              value={topN}
              onChange={(e) => setTopN(parseInt(e.target.value))}
              className="w-full p-3 rounded-lg bg-white/20 text-white border border-green-400/30 focus:border-green-400 focus:ring-2 focus:ring-green-400/20 backdrop-blur-lg"
            >
              <option value={10} className="text-black">Top 10</option>
              <option value={20} className="text-black">Top 20</option>
              <option value={50} className="text-black">Top 50</option>
              <option value={100} className="text-black">Top 100</option>
            </select>
          </div>

          {/* Position Filter */}
          <div className="space-y-2">
            <label className="text-white font-medium text-sm uppercase tracking-wide">Position</label>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-full p-3 rounded-lg bg-white/20 text-white border border-green-400/30 focus:border-green-400 focus:ring-2 focus:ring-green-400/20 backdrop-blur-lg"
            >
              <option value="all" className="text-black">All Positions</option>
              <option value="1" className="text-black">Goalkeepers</option>
              <option value="2" className="text-black">Defenders</option>
              <option value="3" className="text-black">Midfielders</option>
              <option value="4" className="text-black">Forwards</option>
            </select>
          </div>

          {/* AI Model Selection */}
          <div className="space-y-2">
            <label className="text-white font-medium text-sm uppercase tracking-wide">AI Model</label>
            <select
              value={modelType}
              onChange={(e) => setModelType(e.target.value)}
              className="w-full p-3 rounded-lg bg-white/20 text-white border border-green-400/30 focus:border-green-400 focus:ring-2 focus:ring-green-400/20 backdrop-blur-lg"
            >
              <option value="random_forest" className="text-black">🌲 Random Forest (200 trees)</option>

              {userTier === 'premium' && (
                <>
                  <option value="cnn" className="text-black">🧠 CNN Deep Learning</option>
                  <option value="ensemble" className="text-black">🚀 Multi-Model Ensemble</option>
                </>
              )}
              {userTier !== 'premium' && (
                <>
                  <option value="cnn" className="text-black" disabled>🧠 CNN - PREMIUM ONLY</option>
                  <option value="ensemble" className="text-black" disabled>🚀 Ensemble - PREMIUM ONLY</option>
                </>
              )}
            </select>
          </div>

          {/* Gemini AI Toggle */}
          <div className="space-y-2">
            <label className="text-white font-medium text-sm uppercase tracking-wide">Gemini AI</label>
            <button
              onClick={() => setUseGemini(!useGemini)}
              disabled={userTier !== 'premium'}
              className={`w-full p-3 rounded-lg font-medium transition-all duration-300 border-2 ${
                useGemini
                  ? 'bg-gradient-to-r from-purple-500 to-pink-500 border-purple-400 text-white shadow-lg shadow-purple-500/30'
                  : 'bg-white/10 border-white/20 text-white/70 hover:bg-white/20'
              } ${userTier !== 'premium' ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              {useGemini ? '✨ AI Insights ON' : '💡 AI Insights OFF'}
            </button>
            {userTier !== 'premium' && (
              <p className="text-xs text-white/50 text-center">Premium required</p>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={fetchPredictions}
            className="btn-epl-primary"
          >
            🔄 Refresh Predictions
          </button>
          <div className="text-sm text-white/60">
            Showing {predictions.length} player{predictions.length !== 1 ? 's' : ''}
          </div>
        </div>
      </div>

      {/* Player Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {predictions.map((player, index) => (
          <div
            key={player.id || index}
            className="glass-epl rounded-2xl p-6 transform hover:scale-105 transition-all duration-300 hover:shadow-2xl border border-white/10 hover:border-green-400/50"
          >
            {/* Player Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className={`inline-block px-3 py-1 rounded-full text-sm font-bold mb-2 ${getPositionColor(player.position)}`}>
                  {getPositionName(player.position)}
                </div>
                <h3 className="text-lg font-bold text-white mb-1">{player.name}</h3>
                <p className="text-sm text-white/60">{player.team_name || 'Unknown Team'}</p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-green-400">
                  £{player.price?.toFixed(1) || '0.0'}m
                </div>
              </div>
            </div>

            {/* Prediction Score */}
            <div className="bg-gradient-to-r from-green-500/20 to-blue-500/20 rounded-xl p-4 mb-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-white/70 uppercase tracking-wide">Predicted Points</div>
                  <div className="text-3xl font-bold text-white">
                    {player.predicted_points?.toFixed(1) || '0.0'}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-white/70 uppercase tracking-wide">Confidence</div>
                  <div className="text-2xl font-bold text-green-400">
                    {player.confidence?.toFixed(0) || '0'}%
                  </div>
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="bg-white/5 rounded-lg p-3">
                <div className="text-xs text-white/60 uppercase">Form</div>
                <div className={`text-lg font-bold ${getFormColor(player.form)}`}>
                  {player.form?.toFixed(1) || '0.0'}
                </div>
              </div>
              <div className="bg-white/5 rounded-lg p-3">
                <div className="text-xs text-white/60 uppercase">Ownership</div>
                <div className="text-lg font-bold text-white">
                  {player.ownership?.toFixed(1) || '0.0'}%
                </div>
              </div>
            </div>

            {/* Advanced Analytics (if available) */}
            {player.advanced_stats && (
              <div className="bg-white/5 rounded-lg p-3 mb-4">
                <div className="text-xs text-white/60 uppercase mb-2">Advanced Stats</div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  {player.advanced_stats.expected_goals !== null && (
                    <div>
                      <div className="text-xs text-yellow-400">xG</div>
                      <div className="text-sm font-bold text-white">
                        {player.advanced_stats.expected_goals?.toFixed(2) || '0.00'}
                      </div>
                    </div>
                  )}
                  {player.advanced_stats.expected_assists !== null && (
                    <div>
                      <div className="text-xs text-blue-400">xA</div>
                      <div className="text-sm font-bold text-white">
                        {player.advanced_stats.expected_assists?.toFixed(2) || '0.00'}
                      </div>
                    </div>
                  )}
                  {player.advanced_stats.ict_index !== null && (
                    <div>
                      <div className="text-xs text-green-400">ICT</div>
                      <div className="text-sm font-bold text-white">
                        {player.advanced_stats.ict_index?.toFixed(1) || '0.0'}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* AI Insights */}
            {(player.reasoning || player.gemini_insight) && (
              <div className="bg-purple-500/10 border border-purple-400/30 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <Star className="w-4 h-4 text-purple-400 flex-shrink-0 mt-1" />
                  <p className="text-xs text-white/80 leading-relaxed">
                    {player.gemini_insight || player.reasoning}
                  </p>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* No Results */}
      {predictions.length === 0 && !loading && (
        <div className="glass-epl rounded-3xl p-12 text-center">
          <Trophy className="w-16 h-16 text-white/40 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No Predictions Available</h3>
          <p className="text-white/60">
            Try adjusting your filters or refresh the data
          </p>
        </div>
      )}
    </div>
  )
}
