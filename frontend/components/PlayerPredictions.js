'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, Star, DollarSign, Users, Loader2, AlertCircle, Trophy } from 'lucide-react'
import PlayerCard from './PlayerCard'

export default function PlayerPredictions() {
  const [predictions, setPredictions] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [topN, setTopN] = useState(15)

  useEffect(() => {
    fetchPredictions()
  }, [])

  const fetchPredictions = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`http://localhost:8000/predictions`, {
        headers: {
          'Authorization': 'Bearer mock_local_token',
          'Content-Type': 'application/json'
        }
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      setPredictions(data.predictions.slice(0, topN))
    } catch (error) {
      console.error('Error fetching predictions:', error)
      setError(error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleTopNChange = (e) => {
    const value = parseInt(e.target.value)
    setTopN(value)
  }

  const handleFetchClick = () => {
    fetchPredictions()
  }

  const getPositionColor = (position) => {
    const colors = {
      'GK': 'bg-yellow-500',
      'DEF': 'bg-green-500',
      'MID': 'bg-blue-500',
      'FWD': 'bg-red-500'
    }
    return colors[position] || 'bg-gray-500'
  }

  const getPositionGradient = (position) => {
    const gradients = {
      'GK': 'from-yellow-400 to-orange-500',
      'DEF': 'from-green-400 to-emerald-600',
      'MID': 'from-blue-400 to-indigo-600',
      'FWD': 'from-red-400 to-rose-600'
    }
    return gradients[position] || 'from-gray-400 to-gray-600'
  }

  if (loading) {
    return (
      <div className="glass rounded-3xl p-8">
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2 className="w-12 h-12 text-white animate-spin mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">Analyzing Player Performance</h3>
          <p className="text-white/70 text-center max-w-md">
            Our AI is processing the latest player statistics and generating predictions...
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass rounded-3xl p-8">
        <div className="flex flex-col items-center justify-center py-12">
          <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">Connection Error</h3>
          <p className="text-white/70 text-center mb-6 max-w-md">
            {error}
          </p>
          <button
            onClick={handleFetchClick}
            className="btn-primary"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <div className="glass rounded-3xl p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl">
              <TrendingUp className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">Top Player Predictions</h2>
              <p className="text-white/70">AI-powered performance forecasts</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <label htmlFor="topN" className="text-white font-medium">Show top:</label>
              <select
                id="topN"
                value={topN}
                onChange={handleTopNChange}
                className="px-3 py-2 rounded-lg bg-white/20 text-white border border-white/30 focus:border-white/50 focus:ring-2 focus:ring-white/20 backdrop-blur-lg"
              >
                <option value={10} className="text-gray-800">10 players</option>
                <option value={15} className="text-gray-800">15 players</option>
                <option value={25} className="text-gray-800">25 players</option>
                <option value={50} className="text-gray-800">50 players</option>
              </select>
            </div>
            
            <button
              onClick={handleFetchClick}
              disabled={loading}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                'Refresh'
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Predictions Grid */}
      {predictions.length > 0 ? (
        <div className="space-y-4">
          {/* Top 3 Highlighted */}
          {predictions.slice(0, 3).length > 0 && (
            <div className="glass rounded-3xl p-6">
              <div className="flex items-center gap-2 mb-6">
                <Trophy className="w-6 h-6 text-yellow-400" />
                <h3 className="text-xl font-bold text-white">Top 3 Predictions</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {predictions.slice(0, 3).map((player, index) => (
                  <div key={player.player_id} className="relative">
                    <div className="glass rounded-2xl p-6 card-hover border-2 border-yellow-400/30">
                      <div className="flex items-center justify-between mb-4">
                        <div className={`w-8 h-8 rounded-full bg-gradient-to-r ${getPositionGradient(player.position)} flex items-center justify-center text-white font-bold text-sm`}>
                          {index + 1}
                        </div>
                        <div className={`px-3 py-1 rounded-full text-xs font-semibold ${getPositionColor(player.position)} text-white`}>
                          {player.position}
                        </div>
                      </div>
                      
                      <h4 className="text-lg font-bold text-white mb-1">{player.web_name}</h4>
                      <p className="text-white/70 text-sm mb-4">{player.team}</p>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <div className="flex items-center gap-1 text-white/70 text-xs mb-1">
                            <Star className="w-3 h-3" />
                            Predicted Points
                          </div>
                          <div className="text-2xl font-bold text-white">{player.predicted_points}</div>
                        </div>
                        <div>
                          <div className="flex items-center gap-1 text-white/70 text-xs mb-1">
                            <DollarSign className="w-3 h-3" />
                            Price
                          </div>
                          <div className="text-xl font-bold text-green-400">£{player.price}m</div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Remaining Players */}
          {predictions.length > 3 && (
            <div className="glass rounded-3xl p-6">
              <h3 className="text-xl font-bold text-white mb-6">All Predictions</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {predictions.map((player, index) => (
                  <div key={player.player_id} className="glass rounded-2xl p-4 card-hover">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-white/70 text-sm">#{index + 1}</span>
                      <div className={`px-2 py-1 rounded-full text-xs font-semibold ${getPositionColor(player.position)} text-white`}>
                        {player.position}
                      </div>
                    </div>
                    <h4 className="text-lg font-bold text-white mb-1">{player.web_name}</h4>
                    <p className="text-white/70 text-sm mb-3">{player.team}</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <div className="text-white/70 text-xs mb-1">Predicted Points</div>
                        <div className="text-xl font-bold text-white">{player.predicted_points}</div>
                      </div>
                      <div>
                        <div className="text-white/70 text-xs mb-1">Price</div>
                        <div className="text-lg font-bold text-green-400">£{player.price}m</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="glass rounded-3xl p-12">
          <div className="text-center">
            <Users className="w-16 h-16 text-white/50 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No Predictions Available</h3>
            <p className="text-white/70 mb-6">
              Click "Refresh" to load the latest player predictions
            </p>
            <button
              onClick={handleFetchClick}
              className="btn-primary"
            >
              Load Predictions
            </button>
          </div>
        </div>
      )}
    </div>
  )
}