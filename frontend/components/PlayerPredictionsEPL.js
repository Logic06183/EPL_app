'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, Star, DollarSign, Users, Loader2, AlertCircle, Trophy, Zap, Crown, Target } from 'lucide-react'

export default function PlayerPredictionsEPL() {
  const [predictions, setPredictions] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [topN, setTopN] = useState(20)
  const [useAI, setUseAI] = useState(false)
  const [filter, setFilter] = useState('all')
  const [modelType, setModelType] = useState('basic')
  const [availableModels, setAvailableModels] = useState({})
  const [userTier, setUserTier] = useState('free') // 'free', 'basic', 'premium'

  useEffect(() => {
    fetchAvailableModels()
  }, [])

  useEffect(() => {
    fetchPredictions()
  }, [topN, useAI, modelType])

  const fetchAvailableModels = async () => {
    try {
      const apiUrl = typeof window !== 'undefined' ? 
        (process.env.NEXT_PUBLIC_API_URL || 'https://epl-backend-77913915885.us-central1.run.app') :
        'https://epl-backend-77913915885.us-central1.run.app'
      const response = await fetch(`${apiUrl}/api/models/info`)
      console.log('Models API response status:', response.status)
      if (response.ok) {
        const data = await response.json()
        console.log('Available models data:', data)
        setAvailableModels(data.available_models || {})
      } else {
        console.error('Models API failed:', response.status, response.statusText)
      }
    } catch (error) {
      console.error('Error fetching available models:', error)
    }
  }

  const fetchPredictions = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Restrict AI models based on user tier
      let actualModelType = modelType
      if (userTier === 'free' && modelType !== 'basic') {
        actualModelType = 'basic'
      }
      
      const params = new URLSearchParams({
        top_n: topN,
        use_ai: useAI || actualModelType !== 'basic',
        model_type: actualModelType
      })
      
      const apiUrl = typeof window !== 'undefined' ? 
        (process.env.NEXT_PUBLIC_API_URL || 'https://epl-backend-77913915885.us-central1.run.app') :
        'https://epl-backend-77913915885.us-central1.run.app'
      const url = `${apiUrl}/api/players/predictions/enhanced?${params}`
      console.log('Fetching predictions from:', url)
      
      const controller = new AbortController()
      // Longer timeout for ML model predictions (30 seconds)
      const timeoutDuration = (modelType !== 'basic') ? 30000 : 10000
      const timeoutId = setTimeout(() => controller.abort(), timeoutDuration)
      
      const response = await fetch(url, {
        signal: controller.signal
      })
      clearTimeout(timeoutId)
      console.log('Response status:', response.status, response.statusText)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('Error response body:', errorText)
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      console.log('Predictions data:', data)
      setPredictions(data.predictions || [])
    } catch (error) {
      console.error('Error fetching predictions:', error)
      setError(error.message)
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

  const filteredPredictions = predictions.filter(player => {
    if (filter === 'all') return true
    return player.position === parseInt(filter)
  })

  if (loading) {
    return (
      <div className="glass-epl rounded-3xl p-8">
        <div className="flex flex-col items-center justify-center py-12">
          <div className="loading-epl mb-6"></div>
          <h3 className="text-xl font-semibold text-white mb-2">⚽ Analyzing Premier League Players</h3>
          <p className="text-white/70 text-center max-w-md">
            {useAI ? 'AI is processing player data with advanced algorithms...' : 'Fetching the latest player statistics and predictions...'}
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
                  {userTier === 'free' && 'Form-based predictions available. Upgrade for AI models.'}
                  {userTier === 'basic' && 'AI predictions and Random Forest model available.'}
                  {userTier === 'premium' && 'All AI models including Deep Learning and Ensemble.'}
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
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
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
              <option value="basic" className="text-black">📊 Basic (Form-based) - FREE</option>
              
              {userTier !== 'free' && (
                <option value="random_forest" className="text-black">🌲 Random Forest ML - BASIC+</option>
              )}
              {userTier === 'free' && (
                <option value="random_forest" className="text-black" disabled>🌲 Random Forest ML - UPGRADE REQUIRED</option>
              )}
              
              {userTier === 'premium' && (
                <>
                  <option value="deep_learning" className="text-black">🧠 Deep Learning CNN - PREMIUM</option>
                  <option value="ensemble" className="text-black">🚀 Multi-Model Ensemble - PREMIUM</option>
                </>
              )}
              {userTier !== 'premium' && (
                <>
                  <option value="deep_learning" className="text-black" disabled>🧠 Deep Learning CNN - PREMIUM ONLY</option>
                  <option value="ensemble" className="text-black" disabled>🚀 Multi-Model Ensemble - PREMIUM ONLY</option>
                </>
              )}
            </select>
            <div className="text-xs text-white/60">
              {userTier === 'free' && modelType !== 'basic' && '🔒 Upgrade required for this model'}
              {userTier === 'basic' && ['deep_learning', 'ensemble'].includes(modelType) && '🔒 Premium required for this model'}
              {(userTier !== 'free' || modelType === 'basic') && (availableModels[modelType]?.accuracy || 'Standard accuracy')}
            </div>
          </div>

          {/* AI Enhancement Toggle */}
          <div className="space-y-2">
            <label className="text-white font-medium text-sm uppercase tracking-wide">AI Mode</label>
            <button
              onClick={() => setUseAI(!useAI)}
              className={`w-full p-3 rounded-lg font-medium transition-all duration-300 border-2 ${
                useAI || modelType !== 'basic'
                  ? 'bg-gradient-to-r from-purple-500 to-indigo-500 border-purple-400 text-white shadow-lg' 
                  : 'bg-white/10 border-white/30 text-white/70 hover:bg-white/20'
              }`}
            >
              <div className="flex items-center justify-center gap-2">
                {useAI || modelType !== 'basic' ? (
                  <>
                    <span className="text-lg">🤖</span>
                    <span>AI Active</span>
                  </>
                ) : (
                  <>
                    <span className="text-lg">📊</span>
                    <span>Standard</span>
                  </>
                )}
              </div>
              <div className="text-xs mt-1 opacity-80">
                {modelType !== 'basic' ? availableModels[modelType]?.name : 'Click to Enable AI'}
              </div>
            </button>
          </div>

          {/* Refresh Button */}
          <div className="space-y-2">
            <label className="text-white font-medium text-sm uppercase tracking-wide">Actions</label>
            <button onClick={fetchPredictions} className="btn-epl-primary w-full">
              <div className="flex items-center gap-2 justify-center">
                <Target className="w-4 h-4" />
                Refresh Data
              </div>
            </button>
          </div>
        </div>

        {/* Stats Summary */}
        {predictions.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="stat-card-epl">
              <div className="text-2xl font-bold text-white mb-1">{predictions.length}</div>
              <div className="text-white/70 text-sm">Players Analyzed</div>
            </div>
            <div className="stat-card-epl">
              <div className="text-2xl font-bold text-green-400 mb-1">
                {predictions.filter(p => p.ai_enhanced).length}
              </div>
              <div className="text-white/70 text-sm">AI Enhanced</div>
            </div>
            <div className="stat-card-epl">
              <div className="text-2xl font-bold text-yellow-400 mb-1">
                £{predictions.reduce((sum, p) => sum + p.price, 0).toFixed(1)}m
              </div>
              <div className="text-white/70 text-sm">Total Value</div>
            </div>
            <div className="stat-card-epl">
              <div className="text-2xl font-bold text-purple-400 mb-1">
                {Math.round(predictions.reduce((sum, p) => sum + p.predicted_points, 0))}
              </div>
              <div className="text-white/70 text-sm">Total Points</div>
            </div>
          </div>
        )}
      </div>

      {/* Players Grid */}
      {filteredPredictions.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredPredictions.map((player, index) => (
            <div key={player.id} className="player-card-epl group">
              {/* Rank Badge */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  {index < 3 && (
                    <div className="text-2xl">
                      {index === 0 ? '🥇' : index === 1 ? '🥈' : '🥉'}
                    </div>
                  )}
                  <span className="text-white/60 font-bold text-lg">#{index + 1}</span>
                </div>
                {player.ai_enhanced && (
                  <div className="flex items-center gap-1 px-2 py-1 bg-purple-500/30 rounded-full">
                    <Zap className="w-3 h-3 text-purple-300" />
                    <span className="text-purple-300 text-xs font-medium">AI</span>
                  </div>
                )}
              </div>

              {/* Player Info */}
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-bold ${getPositionColor(player.position)}`}>
                    {getPositionName(player.position)}
                  </span>
                  <span className="text-white/60 text-sm">{player.team_name || `Team ${player.team}`}</span>
                </div>
                
                <h3 className="text-white font-bold text-lg mb-1 group-hover:text-green-300 transition-colors">
                  {player.full_name || player.name}
                </h3>
                
                {player.name !== player.full_name && (
                  <p className="text-white/60 text-sm">{player.name}</p>
                )}
              </div>

              {/* Prediction Score */}
              <div className="text-center mb-4 p-3 bg-white/10 rounded-lg backdrop-blur-sm">
                <div className="text-3xl font-bold text-green-400 mb-1">
                  {player.predicted_points}
                </div>
                <div className="text-white/70 text-sm">Predicted Points</div>
                {player.confidence && (
                  <div className="text-xs text-white/50 mt-1">
                    {Math.round(player.confidence * 100)}% confident
                  </div>
                )}
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="text-center">
                  <div className="text-white font-bold">£{player.price}m</div>
                  <div className="text-white/60 text-xs">Price</div>
                </div>
                <div className="text-center">
                  <div className={`font-bold ${getFormColor(parseFloat(player.form))}`}>
                    {player.form}
                  </div>
                  <div className="text-white/60 text-xs">Form</div>
                </div>
                <div className="text-center">
                  <div className="text-white font-bold">{player.ownership}%</div>
                  <div className="text-white/60 text-xs">Owned</div>
                </div>
              </div>

              {/* Reasoning */}
              {player.reasoning && (
                <div className="text-xs text-white/60 italic border-t border-white/20 pt-3">
                  "{player.reasoning}"
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="glass-epl rounded-3xl p-12 text-center">
          <Trophy className="w-16 h-16 text-white/50 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No Players Found</h3>
          <p className="text-white/70 mb-6">
            Try adjusting your filters or refreshing the data
          </p>
          <button onClick={fetchPredictions} className="btn-epl-primary">
            Refresh Data
          </button>
        </div>
      )}
    </div>
  )
}