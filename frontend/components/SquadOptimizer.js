'use client'

import { useState } from 'react'
import { Trophy, DollarSign, Users, Target, Loader2, AlertCircle, Crown, Shield } from 'lucide-react'
import PlayerCard from './PlayerCard'

export default function SquadOptimizer() {
  const [budget, setBudget] = useState(100.0)
  const [selectedFormation, setSelectedFormation] = useState('4-4-2')
  const [optimizationResult, setOptimizationResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [userTier, setUserTier] = useState('free') // 'free', 'basic', 'premium'

  const optimizeSquad = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Get formation constraints
      const formation = formations.find(f => f.name === selectedFormation)
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://epl-backend-77913915885.us-central1.run.app'}/api/optimize/squad`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          budget: budget,
          formation: selectedFormation,
          formation_constraints: formation?.positions,
          use_ai: userTier !== 'free'
        }),
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
    { 
      name: '3-5-2', 
      positions: { GK: 1, DEF: 3, MID: 5, FWD: 2 },
      description: 'Attacking midfield heavy formation'
    },
    { 
      name: '3-4-3', 
      positions: { GK: 1, DEF: 3, MID: 4, FWD: 3 },
      description: 'Balanced attack with 3 forwards'
    },
    { 
      name: '4-5-1', 
      positions: { GK: 1, DEF: 4, MID: 5, FWD: 1 },
      description: 'Defensive with strong midfield'
    },
    { 
      name: '4-4-2', 
      positions: { GK: 1, DEF: 4, MID: 4, FWD: 2 },
      description: 'Classic balanced formation'
    },
    { 
      name: '4-3-3', 
      positions: { GK: 1, DEF: 4, MID: 3, FWD: 3 },
      description: 'High attacking potential'
    },
    { 
      name: '5-4-1', 
      positions: { GK: 1, DEF: 5, MID: 4, FWD: 1 },
      description: 'Very defensive setup'
    },
    { 
      name: '5-3-2', 
      positions: { GK: 1, DEF: 5, MID: 3, FWD: 2 },
      description: 'Defensive with twin strike'
    },
    { 
      name: '5-2-3', 
      positions: { GK: 1, DEF: 5, MID: 2, FWD: 3 },
      description: 'Counter-attacking formation'
    }
  ]

  const getFormationDescription = () => {
    const formation = formations.find(f => f.name === selectedFormation)
    return formation?.description || 'Select a formation to see details'
  }

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <div className="glass rounded-3xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl">
            <Trophy className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Squad Optimizer</h2>
            <p className="text-white/70">AI-powered team selection within your budget and formation constraints</p>
          </div>
        </div>

        {/* Optimization Benefits */}
        <div className="bg-white/5 rounded-xl p-4 mb-6 border border-white/10">
          <h3 className="text-white font-semibold mb-2">🎯 How This Helps Your Team:</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-white/80">
            <div className="flex items-start gap-2">
              <span className="text-green-400">✓</span>
              <span><strong>Maximize Points:</strong> Finds the highest-scoring combination within your budget</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-green-400">✓</span>
              <span><strong>Formation Balance:</strong> Ensures proper player distribution across positions</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-green-400">✓</span>
              <span><strong>Value Analysis:</strong> Identifies underpriced players with high potential</span>
            </div>
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Formation Selection */}
          <div className="space-y-2">
            <label className="text-white font-medium text-sm uppercase tracking-wide">Formation</label>
            <select 
              value={selectedFormation} 
              onChange={(e) => setSelectedFormation(e.target.value)}
              className="w-full p-3 rounded-lg bg-white/20 text-white border border-white/30 focus:border-white/50 focus:ring-2 focus:ring-white/20 backdrop-blur-lg"
            >
              {formations.map(formation => (
                <option key={formation.name} value={formation.name} className="text-black">
                  {formation.name} - {formation.description}
                </option>
              ))}
            </select>
            <div className="text-xs text-white/60">
              {getFormationDescription()}
            </div>
          </div>

          {/* Budget Input */}
          <div className="space-y-2">
            <label htmlFor="budget" className="text-white font-medium text-sm uppercase tracking-wide">
              Budget (£m)
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
                className="w-full pl-10 pr-4 py-3 rounded-lg bg-white/20 text-white placeholder-white/50 border border-white/30 focus:border-white/50 focus:ring-2 focus:ring-white/20 backdrop-blur-lg"
              />
            </div>
            <div className="text-xs text-white/60">
              Standard budget: £100m
            </div>
          </div>

          {/* User Tier Selection */}
          <div className="space-y-2">
            <label className="text-white font-medium text-sm uppercase tracking-wide">AI Level</label>
            <select 
              value={userTier} 
              onChange={(e) => setUserTier(e.target.value)}
              className="w-full p-3 rounded-lg bg-white/20 text-white border border-white/30 focus:border-white/50 focus:ring-2 focus:ring-white/20 backdrop-blur-lg"
            >
              <option value="free" className="text-black">📊 Free - Basic Optimization</option>
              <option value="basic" className="text-black">🤖 Basic - AI Enhanced</option>
              <option value="premium" className="text-black">🚀 Premium - Advanced AI</option>
            </select>
            <div className="text-xs text-white/60">
              {userTier === 'free' && 'Form-based predictions only'}
              {userTier === 'basic' && 'AI predictions + sentiment analysis'}
              {userTier === 'premium' && 'Advanced ML models + deep insights'}
            </div>
          </div>

          {/* Optimize Button */}
          <div className="space-y-2">
            <label className="text-white font-medium text-sm uppercase tracking-wide">Action</label>
            <button
              onClick={optimizeSquad}
              disabled={loading}
              className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed h-12"
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
            <div className="text-xs text-white/60 text-center">
              Find your perfect team
            </div>
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
                  £{optimizationResult.total_cost ? optimizationResult.total_cost.toFixed(1) : '0.0'}m
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
                  {optimizationResult.predicted_points ? optimizationResult.predicted_points.toFixed(0) : '0'}
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
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-white">Squad Formation</h3>
              <div className="bg-white/10 px-4 py-2 rounded-lg border border-white/20">
                <span className="text-white font-medium">{selectedFormation}</span>
                <span className="text-white/60 text-sm ml-2">- {getFormationDescription()}</span>
              </div>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {['GK', 'DEF', 'MID', 'FWD'].map(position => {
                const formation = formations.find(f => f.name === selectedFormation)
                const expectedCount = formation?.positions[position] || 0
                const actualCount = getPositionCount(position)
                
                return (
                  <div key={position} className="text-center">
                    <div className="text-3xl mb-2">{getPositionIcon(position)}</div>
                    <div className="text-lg font-bold text-white">
                      {actualCount}
                      {optimizationResult && (
                        <span className="text-white/50 text-sm ml-1">/ {expectedCount}</span>
                      )}
                    </div>
                    <div className="text-sm text-white/70">{position}</div>
                    {optimizationResult && actualCount !== expectedCount && (
                      <div className="text-xs text-yellow-400 mt-1">
                        Expected: {expectedCount}
                      </div>
                    )}
                  </div>
                )
              })}
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
              Select your preferred formation and budget, then click "Optimize Squad" to get AI-powered team recommendations.
            </p>
            
            {/* Selected Formation Preview */}
            <div className="bg-white/5 rounded-xl p-4 mb-6 max-w-md mx-auto border border-white/10">
              <h4 className="text-white font-medium mb-3">Selected Formation: {selectedFormation}</h4>
              <div className="grid grid-cols-4 gap-4 text-sm text-white/60">
                {(() => {
                  const formation = formations.find(f => f.name === selectedFormation)
                  return Object.entries(formation?.positions || {}).map(([pos, count]) => (
                    <div key={pos} className="text-center">
                      <div className="text-2xl mb-1">{getPositionIcon(pos)}</div>
                      <div className="font-bold">{count}</div>
                      <div className="text-xs">{pos}</div>
                    </div>
                  ))
                })()}
              </div>
              <div className="text-xs text-white/50 mt-3">
                {getFormationDescription()}
              </div>
            </div>

            <div className="text-sm text-white/60">
              {userTier === 'free' && '📊 Using basic form-based optimization'}
              {userTier === 'basic' && '🤖 AI-enhanced optimization with sentiment analysis'}
              {userTier === 'premium' && '🚀 Advanced ML optimization with deep insights'}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}