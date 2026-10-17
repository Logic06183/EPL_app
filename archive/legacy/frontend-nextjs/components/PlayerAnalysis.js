'use client'

import { useState } from 'react'
import { Target, Search, TrendingUp, Loader2, AlertCircle, Star, DollarSign, Activity } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'

export default function PlayerAnalysis() {
  const [playerName, setPlayerName] = useState('')
  const [playerData, setPlayerData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const searchPlayer = async () => {
    if (!playerName.trim()) {
      setError('Please enter a player name')
      return
    }

    setLoading(true)
    setError(null)
    setPlayerData(null)

    try {
      // For demo purposes, we'll simulate a player search
      // In a real implementation, you'd have a search endpoint
      setTimeout(() => {
        const mockPlayerData = {
          player_info: {
            id: 1,
            name: playerName,
            team: 'Manchester City',
            position: 'FWD',
            price: 15.0,
            total_points: 180,
            points_per_game: 9.5,
            selected_by: '45.2%',
            form: 8.2,
            status: 'Available'
          },
          predictions: {
            next_5_gameweeks: [8.5, 7.2, 9.1, 6.8, 8.9],
            average: 8.1
          },
          recent_performance: [
            { gameweek: 'GW6', points: 12, minutes: 90, goals: 2, assists: 1 },
            { gameweek: 'GW7', points: 8, minutes: 90, goals: 1, assists: 0 },
            { gameweek: 'GW8', points: 15, minutes: 90, goals: 3, assists: 0 },
            { gameweek: 'GW9', points: 6, minutes: 90, goals: 0, assists: 1 },
            { gameweek: 'GW10', points: 10, minutes: 90, goals: 1, assists: 1 }
          ]
        }
        
        setPlayerData(mockPlayerData)
        setLoading(false)
      }, 1500)
    } catch (error) {
      console.error('Error searching player:', error)
      setError(error.message)
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      searchPlayer()
    }
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

  const getFormColor = (form) => {
    if (form >= 7) return 'text-green-400'
    if (form >= 5) return 'text-yellow-400'
    return 'text-red-400'
  }

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <div className="glass rounded-3xl p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl">
              <Target className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">Player Analysis</h2>
              <p className="text-white/70">Deep dive into individual player performance</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4 max-w-md w-full">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-white/70" />
              <input
                type="text"
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="e.g. Haaland, Salah, Kane..."
                className="w-full pl-10 pr-4 py-3 rounded-lg bg-white/20 text-white placeholder-white/50 border border-white/30 focus:border-white/50 focus:ring-2 focus:ring-white/20 backdrop-blur-lg"
              />
            </div>
            
            <button
              onClick={searchPlayer}
              disabled={loading || !playerName.trim()}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                'Analyze'
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="glass rounded-3xl p-12">
          <div className="flex flex-col items-center justify-center">
            <div className="relative mb-6">
              <div className="w-16 h-16 border-4 border-white/20 rounded-full"></div>
              <div className="absolute top-0 left-0 w-16 h-16 border-4 border-purple-400 border-t-transparent rounded-full animate-spin"></div>
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Analyzing {playerName}</h3>
            <p className="text-white/70 text-center max-w-md">
              Gathering performance data and generating detailed insights...
            </p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="glass rounded-3xl p-8">
          <div className="flex flex-col items-center justify-center">
            <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Analysis Failed</h3>
            <p className="text-white/70 text-center mb-6 max-w-md">
              {error}
            </p>
            <button
              onClick={searchPlayer}
              className="btn-primary"
            >
              Try Again
            </button>
          </div>
        </div>
      )}

      {/* Player Data */}
      {playerData && (
        <div className="space-y-6">
          {/* Player Overview */}
          <div className="glass rounded-3xl p-6">
            <div className="flex flex-col lg:flex-row lg:items-start gap-6">
              {/* Player Info */}
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-4">
                  <div className={`px-3 py-1 rounded-full text-xs font-semibold ${getPositionColor(playerData.player_info.position)} text-white`}>
                    {playerData.player_info.position}
                  </div>
                  <span className="text-white/70">{playerData.player_info.team}</span>
                </div>
                
                <h3 className="text-3xl font-bold text-white mb-2">{playerData.player_info.name}</h3>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-white/70 text-sm">Price</div>
                    <div className="text-xl font-bold text-green-400">£{playerData.player_info.price}m</div>
                  </div>
                  <div>
                    <div className="text-white/70 text-sm">Total Points</div>
                    <div className="text-xl font-bold text-white">{playerData.player_info.total_points}</div>
                  </div>
                  <div>
                    <div className="text-white/70 text-sm">PPG</div>
                    <div className="text-xl font-bold text-blue-400">{playerData.player_info.points_per_game}</div>
                  </div>
                  <div>
                    <div className="text-white/70 text-sm">Form</div>
                    <div className={`text-xl font-bold ${getFormColor(playerData.player_info.form)}`}>
                      {playerData.player_info.form}
                    </div>
                  </div>
                </div>
              </div>

              {/* Quick Stats */}
              <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm min-w-[200px]">
                <div className="text-center mb-3">
                  <div className="text-white/70 text-sm">Ownership</div>
                  <div className="text-2xl font-bold text-white">{playerData.player_info.selected_by}</div>
                </div>
                <div className="text-center">
                  <div className="text-white/70 text-sm">Status</div>
                  <div className="text-lg font-bold text-green-400">{playerData.player_info.status}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Predictions */}
          <div className="glass rounded-3xl p-6">
            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Next 5 Gameweeks Predictions
            </h3>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Predictions Chart */}
              <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={playerData.predictions.next_5_gameweeks.map((points, index) => ({
                      gameweek: `GW${index + 11}`,
                      points: points
                    }))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                      <XAxis dataKey="gameweek" stroke="rgba(255,255,255,0.7)" />
                      <YAxis stroke="rgba(255,255,255,0.7)" />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: 'rgba(255,255,255,0.1)', 
                          border: 'none',
                          borderRadius: '8px',
                          backdropFilter: 'blur(10px)'
                        }}
                      />
                      <Bar dataKey="points" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Prediction Stats */}
              <div className="space-y-4">
                <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                  <div className="flex items-center gap-2 text-white/70 text-sm mb-2">
                    <Star className="w-4 h-4" />
                    Average Predicted Points
                  </div>
                  <div className="text-3xl font-bold text-purple-400">
                    {playerData.predictions.average.toFixed(1)}
                  </div>
                </div>
                
                <div className="space-y-2">
                  {playerData.predictions.next_5_gameweeks.map((points, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                      <span className="text-white/70">GW{index + 11}</span>
                      <span className="font-bold text-white">{points.toFixed(1)} pts</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Recent Performance */}
          <div className="glass rounded-3xl p-6">
            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Recent Performance
            </h3>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Performance Chart */}
              <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={playerData.recent_performance}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                      <XAxis dataKey="gameweek" stroke="rgba(255,255,255,0.7)" />
                      <YAxis stroke="rgba(255,255,255,0.7)" />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: 'rgba(255,255,255,0.1)', 
                          border: 'none',
                          borderRadius: '8px',
                          backdropFilter: 'blur(10px)'
                        }}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="points" 
                        stroke="#10b981" 
                        strokeWidth={3}
                        dot={{ fill: '#10b981', strokeWidth: 2, r: 4 }}
                        activeDot={{ r: 6, fill: '#10b981' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Performance Details */}
              <div className="space-y-3">
                {playerData.recent_performance.map((gw, index) => (
                  <div key={index} className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-white">{gw.gameweek}</span>
                      <span className="text-lg font-bold text-green-400">{gw.points} pts</span>
                    </div>
                    <div className="grid grid-cols-3 gap-3 text-sm">
                      <div>
                        <span className="text-white/70">Goals: </span>
                        <span className="text-white font-medium">{gw.goals}</span>
                      </div>
                      <div>
                        <span className="text-white/70">Assists: </span>
                        <span className="text-white font-medium">{gw.assists}</span>
                      </div>
                      <div>
                        <span className="text-white/70">Mins: </span>
                        <span className="text-white font-medium">{gw.minutes}'</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* No Results State */}
      {!loading && !error && !playerData && (
        <div className="glass rounded-3xl p-12">
          <div className="text-center">
            <Target className="w-16 h-16 text-white/50 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Player Analysis Ready</h3>
            <p className="text-white/70 mb-6 max-w-md mx-auto">
              Search for any Premier League player to get detailed performance analysis, predictions, and insights.
            </p>
            <div className="text-sm text-white/60">
              Try searching: Haaland, Salah, De Bruyne, Son, Kane
            </div>
          </div>
        </div>
      )}
    </div>
  )
}