'use client'

import { useState } from 'react'
import { Trophy, DollarSign, Users, Target, Loader2, AlertCircle, Crown, Shield } from 'lucide-react'
import PlayerCard from './PlayerCard'

export default function SquadOptimizer() {
  const [budget, setBudget] = useState(100.0)
  const [optimizationResult, setOptimizationResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const optimizeSquad = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/optimize/squad', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ budget: budget }),
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const data = await response.json()
      setOptimizationResult(data)
    } catch (error) {
      console.error('Error optimizing squad:', error)
      setError(error.message)
    } finally {
      setLoading(false)
    }
  }

  const getPositionPlayers = (position) => {
    if (!optimizationResult?.squad) return []
    return optimizationResult.squad.filter(player => player.position === position)
  }

  const getPositionIcon = (position) => {
    const icons = {
      'GK': '🥅',
      'DEF': '🛡️', 
      'MID': '⚽',
      'FWD': '🏃‍♂️'
    }
    return icons[position] || '👤'
  }

  const getPositionCount = (position) => {
    return getPositionPlayers(position).length
  }

  const formations = [
    { name: '3-5-2', positions: { GK: 1, DEF: 3, MID: 5, FWD: 2 } },
    { name: '3-4-3', positions: { GK: 1, DEF: 3, MID: 4, FWD: 3 } },
    { name: '4-5-1', positions: { GK: 1, DEF: 4, MID: 5, FWD: 1 } },
    { name: '4-4-2', positions: { GK: 1, DEF: 4, MID: 4, FWD: 2 } },
    { name: '4-3-3', positions: { GK: 1, DEF: 4, MID: 3, FWD: 3 } },
    { name: '5-4-1', positions: { GK: 1, DEF: 5, MID: 4, FWD: 1 } },
    { name: '5-3-2', positions: { GK: 1, DEF: 5, MID: 3, FWD: 2 } },
    { name: '5-2-3', positions: { GK: 1, DEF: 5, MID: 2, FWD: 3 } }
  ]

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <div className="glass rounded-3xl p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl">
              <Trophy className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">Squad Optimizer</h2>
              <p className="text-white/70">AI-powered team selection within your budget</p>
            </div>
          </div>
          
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
            <div className="flex items-center gap-3">
              <label htmlFor="budget" className="text-white font-medium whitespace-nowrap">
                Budget:
              </label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-white/70" />
                <input
                  id="budget"
                  type="number"
                  value={budget}
                  onChange={(e) => setBudget(parseFloat(e.target.value))}
                  min="80"
                  max="120"
                  step="0.1"
                  className="pl-10 pr-4 py-3 rounded-lg bg-white/20 text-white placeholder-white/50 border border-white/30 focus:border-white/50 focus:ring-2 focus:ring-white/20 backdrop-blur-lg w-32"
                />
                <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/70 text-sm">
                  m
                </span>
              </div>
            </div>
            
            <button
              onClick={optimizeSquad}
              disabled={loading}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed min-w-[140px]"
            >
              {loading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Optimizing...
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4" />
                  Optimize Squad
                </div>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="glass rounded-3xl p-12">
          <div className="flex flex-col items-center justify-center">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-white/20 rounded-full"></div>
              <div className="absolute top-0 left-0 w-16 h-16 border-4 border-white border-t-transparent rounded-full animate-spin"></div>
            </div>
            <h3 className="text-xl font-semibold text-white mt-6 mb-2">Optimizing Your Squad</h3>
            <p className="text-white/70 text-center max-w-md">
              Our AI is analyzing thousands of player combinations to find your perfect team...
            </p>
            <div className="mt-4 flex items-center gap-2 text-sm text-white/60">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
              </div>
              <span>This may take a few seconds</span>
            </div>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="glass rounded-3xl p-8">
          <div className="flex flex-col items-center justify-center">
            <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Optimization Failed</h3>
            <p className="text-white/70 text-center mb-6 max-w-md">
              {error}
            </p>
            <button
              onClick={optimizeSquad}
              className="btn-primary"
            >
              Try Again
            </button>
          </div>
        </div>
      )}

      {/* Results */}
      {optimizationResult && (
        <div className="space-y-6">
          {/* Summary Stats */}
          <div className="glass rounded-3xl p-6">
            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <Trophy className="w-5 h-5 text-yellow-400" />
              Optimization Summary
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                <div className="flex items-center gap-2 text-white/70 text-sm mb-1">
                  <DollarSign className="w-4 h-4" />
                  Total Cost
                </div>
                <div className="text-2xl font-bold text-green-400">
                  £{optimizationResult.total_cost.toFixed(1)}m
                </div>
                <div className="text-xs text-white/60">
                  of £{budget}m budget
                </div>
              </div>
              
              <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                <div className="flex items-center gap-2 text-white/70 text-sm mb-1">
                  <Target className="w-4 h-4" />
                  Predicted Points
                </div>
                <div className="text-2xl font-bold text-blue-400">
                  {optimizationResult.predicted_points.toFixed(0)}
                </div>
                <div className="text-xs text-white/60">
                  total points
                </div>
              </div>
              
              <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                <div className="flex items-center gap-2 text-white/70 text-sm mb-1">
                  <Users className="w-4 h-4" />
                  Squad Size
                </div>
                <div className="text-2xl font-bold text-purple-400">
                  {optimizationResult.squad.length}
                </div>
                <div className="text-xs text-white/60">
                  players
                </div>
              </div>
              
              <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                <div className="flex items-center gap-2 text-white/70 text-sm mb-1">
                  <Shield className="w-4 h-4" />
                  Status
                </div>
                <div className="text-lg font-bold text-white capitalize">
                  {optimizationResult.optimization_status}
                </div>
                <div className={`text-xs ${
                  optimizationResult.optimization_status === 'optimal' ? 'text-green-400' : 'text-yellow-400'
                }`}>
                  {optimizationResult.optimization_status === 'optimal' ? 'Perfect solution' : 'Good solution'}
                </div>
              </div>
            </div>
          </div>

          {/* Formation Visual */}
          <div className="glass rounded-3xl p-6">
            <h3 className="text-xl font-bold text-white mb-6">Squad Formation</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {['GK', 'DEF', 'MID', 'FWD'].map(position => (
                <div key={position} className="text-center">
                  <div className="text-3xl mb-2">{getPositionIcon(position)}</div>
                  <div className="text-lg font-bold text-white">{getPositionCount(position)}</div>
                  <div className="text-sm text-white/70">{position}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Squad by Position */}
          <div className="space-y-6">
            {['GK', 'DEF', 'MID', 'FWD'].map(position => {
              const players = getPositionPlayers(position)
              if (players.length === 0) return null
              
              return (
                <div key={position} className="glass rounded-3xl p-6">
                  <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                    <span className="text-2xl">{getPositionIcon(position)}</span>
                    {position} ({players.length})
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {players.map((player, index) => (
                      <div key={player.id} className="relative">
                        <PlayerCard
                          player={{
                            player_id: player.id,
                            player_name: player.name,
                            team: `Team ${player.team}`,
                            position: player.position,
                            predicted_points: player.predicted_points,
                            price: player.price
                          }}
                          rank={index + 1}
                          showRank={false}
                        />
                        {/* Best in position indicator */}
                        {index === 0 && (
                          <div className="absolute -top-2 -right-2">
                            <div className="bg-yellow-400 text-yellow-900 rounded-full p-1">
                              <Crown className="w-4 h-4" />
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* No Results State */}
      {!loading && !error && !optimizationResult && (
        <div className="glass rounded-3xl p-12">
          <div className="text-center">
            <Trophy className="w-16 h-16 text-white/50 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Ready to Optimize</h3>
            <p className="text-white/70 mb-6 max-w-md mx-auto">
              Set your budget and click "Optimize Squad" to get AI-powered team recommendations within your constraints.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-md mx-auto text-sm text-white/60">
              <div>2 Goalkeepers</div>
              <div>5 Defenders</div>
              <div>5 Midfielders</div>
              <div>3 Forwards</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}