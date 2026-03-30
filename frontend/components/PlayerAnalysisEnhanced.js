'use client'

import { useState, useEffect } from 'react'
import { Target, Search, TrendingUp, Loader2, AlertCircle, Star, DollarSign, Activity, User, Shield } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'

export default function PlayerAnalysisEnhanced() {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [selectedPlayer, setSelectedPlayer] = useState(null)
  const [playerAnalysis, setPlayerAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState(null)
  const [trendingPlayers, setTrendingPlayers] = useState([])
  const [popularSearches, setPopularSearches] = useState([])
  const [recentlyViewed, setRecentlyViewed] = useState([])

  // Load initial data and suggestions
  useEffect(() => {
    loadInitialData()
    loadRecentlyViewed()
  }, [])

  const loadInitialData = async () => {
    try {
      // Load trending players (top performers)
      const trendingResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://epl-api-5d4hhzfrfq-uc.a.run.app'}/api/players/predictions?top_n=8`)
      if (trendingResponse.ok) {
        const trendingData = await trendingResponse.json()
        setTrendingPlayers(trendingData.predictions || [])
      }

      // Set popular searches - Updated for 2024/25 season
      setPopularSearches([
        'Haaland', 'Salah', 'De Bruyne', 'Son', 'Watkins', 'Rashford', 
        'Saka', 'Martinelli', 'Foden', 'Bruno Fernandes', 'Palmer', 'Isak'
      ])
    } catch (error) {
      console.error('Error loading initial data:', error)
    }
  }

  const loadRecentlyViewed = () => {
    const stored = localStorage.getItem('recentlyViewedPlayers')
    if (stored) {
      setRecentlyViewed(JSON.parse(stored))
    }
  }

  const addToRecentlyViewed = (player) => {
    const updated = [player, ...recentlyViewed.filter(p => p.id !== player.id)].slice(0, 5)
    setRecentlyViewed(updated)
    localStorage.setItem('recentlyViewedPlayers', JSON.stringify(updated))
  }

  // Search for players as user types
  useEffect(() => {
    const searchPlayers = async () => {
      if (!searchQuery.trim() || searchQuery.length < 2) {
        setSearchResults([])
        return
      }

      setSearching(true)
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://epl-api-5d4hhzfrfq-uc.a.run.app'}/api/players/search?q=${encodeURIComponent(searchQuery)}`)
        if (response.ok) {
          const data = await response.json()
          setSearchResults(data.players || [])
        }
      } catch (error) {
        console.error('Search error:', error)
      } finally {
        setSearching(false)
      }
    }

    const debounceTimer = setTimeout(searchPlayers, 300)
    return () => clearTimeout(debounceTimer)
  }, [searchQuery])

  const analyzePlayer = async (player) => {
    setSelectedPlayer(player)
    setLoading(true)
    setError(null)
    setPlayerAnalysis(null)
    setSearchResults([])
    setSearchQuery('')
    addToRecentlyViewed(player)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://epl-api-5d4hhzfrfq-uc.a.run.app'}/api/players/${player.id}/ai-analysis`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      setPlayerAnalysis(data)
    } catch (error) {
      console.error('Error analyzing player:', error)
      setError(error.message)
    } finally {
      setLoading(false)
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

  const getSentimentColor = (sentiment) => {
    if (sentiment === 'positive') return 'text-green-400'
    if (sentiment === 'negative') return 'text-red-400'
    return 'text-yellow-400'
  }

  return (
    <div className="space-y-6">
      {/* Header with Enhanced Search */}
      <div className="glass rounded-3xl p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl">
              <Target className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">Enhanced Player Analysis</h2>
              <p className="text-white/70">AI-powered insights with real FPL data</p>
            </div>
          </div>
          
          <div className="relative max-w-md w-full">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-white/70" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search players by name (e.g., Haaland, Salah)..."
              className="w-full pl-10 pr-4 py-3 rounded-lg bg-white/20 text-white placeholder-white/50 border border-white/30 focus:border-white/50 focus:ring-2 focus:ring-white/20 backdrop-blur-lg"
            />
            {searching && (
              <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 animate-spin text-white/70" />
            )}
            
            {/* Search Results Dropdown */}
            {searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-2 bg-white/10 backdrop-blur-lg rounded-lg border border-white/20 max-h-64 overflow-y-auto z-50">
                {searchResults.map((player) => (
                  <button
                    key={player.id}
                    onClick={() => analyzePlayer(player)}
                    className="w-full text-left p-3 hover:bg-white/20 border-b border-white/10 last:border-b-0 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`px-2 py-1 rounded text-xs font-semibold ${getPositionColor(player.position_name)} text-white`}>
                          {player.position_name}
                        </div>
                        <div>
                          <div className="text-white font-medium">{player.name}</div>
                          <div className="text-white/60 text-sm">{player.team_name}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-white font-medium">£{player.price}m</div>
                        <div className="text-white/60 text-sm">{player.total_points} pts</div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Suggestions and Quick Access */}
      {!selectedPlayer && !loading && (
        <div className="space-y-6">
          {/* Popular Searches */}
          <div className="glass rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-400" />
              Popular Searches
            </h3>
            <div className="flex flex-wrap gap-2">
              {popularSearches.map((name) => (
                <button
                  key={name}
                  onClick={() => setSearchQuery(name)}
                  className="px-3 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm transition-colors border border-white/20 hover:border-white/30"
                >
                  {name}
                </button>
              ))}
            </div>
          </div>

          {/* Trending Players */}
          <div className="glass rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Star className="w-5 h-5 text-yellow-400" />
              Top Performers This Week
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {trendingPlayers.map((player) => (
                <button
                  key={player.id}
                  onClick={() => analyzePlayer(player)}
                  className="bg-white/5 hover:bg-white/10 rounded-xl p-4 transition-colors border border-white/10 hover:border-white/20 text-left"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className={`px-2 py-1 rounded text-xs font-semibold ${getPositionColor(player.position_name)} text-white`}>
                      {player.position_name}
                    </div>
                    <div className="text-green-400 font-bold text-sm">
                      {player.predicted_points?.toFixed(1)} pts
                    </div>
                  </div>
                  <div className="text-white font-medium mb-1">{player.name}</div>
                  <div className="text-white/60 text-sm mb-2">{player.team_name}</div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-white/60">£{player.price}m</span>
                    <span className={`font-medium ${getFormColor(player.form)}`}>
                      Form: {player.form}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Recently Viewed */}
          {recentlyViewed.length > 0 && (
            <div className="glass rounded-2xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <User className="w-5 h-5 text-blue-400" />
                Recently Viewed
              </h3>
              <div className="flex flex-wrap gap-3">
                {recentlyViewed.map((player) => (
                  <button
                    key={player.id}
                    onClick={() => analyzePlayer(player)}
                    className="flex items-center gap-2 px-3 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm transition-colors border border-white/20 hover:border-white/30"
                  >
                    <div className={`w-2 h-2 rounded-full ${getPositionColor(player.position_name)}`}></div>
                    {player.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Enhanced Player Analysis Ready */}
          <div className="glass rounded-2xl p-8 text-center">
            <Target className="w-16 h-16 text-purple-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Enhanced Player Analysis Ready</h3>
            <p className="text-white/70 max-w-md mx-auto mb-6">
              Search for any Premier League player to get comprehensive AI analysis including:
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-white/80">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-green-400" />
                AI-powered predictions
              </div>
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-blue-400" />
                Sentiment analysis
              </div>
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-orange-400" />
                Performance insights
              </div>
              <div className="flex items-center gap-2">
                <Star className="w-4 h-4 text-yellow-400" />
                Captain potential
              </div>
            </div>
            <p className="text-white/60 text-sm mt-4">
              Try searching: Haaland, Salah, De Bruyne, Son, Watkins, Palmer, Isak
            </p>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="glass rounded-3xl p-12">
          <div className="flex flex-col items-center justify-center">
            <div className="relative mb-6">
              <div className="w-16 h-16 border-4 border-white/20 rounded-full"></div>
              <div className="absolute top-0 left-0 w-16 h-16 border-4 border-purple-400 border-t-transparent rounded-full animate-spin"></div>
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Analyzing {selectedPlayer?.name}</h3>
            <p className="text-white/70 text-center max-w-md">
              Running AI analysis on performance data, news sentiment, and FPL metrics...
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
            <p className="text-white/70 text-center mb-6 max-w-md">{error}</p>
            <button
              onClick={() => selectedPlayer && analyzePlayer(selectedPlayer)}
              className="btn-primary"
            >
              Try Again
            </button>
          </div>
        </div>
      )}

      {/* Player Analysis Results */}
      {playerAnalysis && !loading && (
        <div className="space-y-6">
          {/* Player Overview */}
          <div className="glass rounded-3xl p-6">
            <div className="flex flex-col lg:flex-row lg:items-start gap-6">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-4">
                  <div className={`px-3 py-1 rounded-full text-xs font-semibold ${getPositionColor(playerAnalysis.player.position_name)} text-white`}>
                    {playerAnalysis.player.position_name}
                  </div>
                  <span className="text-white/70">{playerAnalysis.player.team_name}</span>
                  {playerAnalysis.analysis.ai_enhanced && (
                    <span className="px-2 py-1 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full text-xs font-semibold text-white">
                      🤖 AI Enhanced
                    </span>
                  )}
                </div>
                
                <h3 className="text-3xl font-bold text-white mb-2">{playerAnalysis.player.full_name}</h3>
                <p className="text-white/60 mb-4">{playerAnalysis.player.name}</p>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-white/70 text-sm">Price</div>
                    <div className="text-xl font-bold text-green-400">£{playerAnalysis.player.price}m</div>
                  </div>
                  <div>
                    <div className="text-white/70 text-sm">Total Points</div>
                    <div className="text-xl font-bold text-white">{playerAnalysis.stats.total_points}</div>
                  </div>
                  <div>
                    <div className="text-white/70 text-sm">PPG</div>
                    <div className="text-xl font-bold text-blue-400">{playerAnalysis.stats.points_per_game}</div>
                  </div>
                  <div>
                    <div className="text-white/70 text-sm">Form</div>
                    <div className={`text-xl font-bold ${getFormColor(playerAnalysis.stats.form)}`}>
                      {playerAnalysis.stats.form}
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm min-w-[200px]">
                <div className="text-center mb-3">
                  <div className="text-white/70 text-sm">AI Prediction</div>
                  <div className="text-3xl font-bold text-purple-400">{playerAnalysis.analysis.prediction}</div>
                  <div className="text-white/60 text-xs">Next GW Points</div>
                </div>
                <div className="text-center">
                  <div className="text-white/70 text-sm">Confidence</div>
                  <div className="text-lg font-bold text-white">{Math.round(playerAnalysis.analysis.confidence * 100)}%</div>
                </div>
              </div>
            </div>
          </div>

          {/* AI Analysis */}
          <div className="glass rounded-3xl p-6">
            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              🤖 AI Insights
            </h3>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Analysis Summary */}
              <div className="space-y-4">
                <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                  <div className="text-white/70 text-sm mb-2">Analysis</div>
                  <div className="text-white">{playerAnalysis.analysis.reasoning}</div>
                </div>
                
                <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                  <div className="text-white/70 text-sm mb-2">Sentiment</div>
                  <div className={`font-bold capitalize ${getSentimentColor(playerAnalysis.analysis.sentiment)}`}>
                    {playerAnalysis.analysis.sentiment}
                  </div>
                </div>

                {playerAnalysis.analysis.news_summary && (
                  <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                    <div className="text-white/70 text-sm mb-2">News Summary</div>
                    <div className="text-white">{playerAnalysis.analysis.news_summary}</div>
                  </div>
                )}
              </div>

              {/* Stats Grid */}
              <div className="space-y-4">
                {playerAnalysis.analysis.captain_potential && (
                  <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-white/70 text-sm">Captain Potential</span>
                      <span className="text-lg font-bold text-yellow-400">{playerAnalysis.analysis.captain_potential}/10</span>
                    </div>
                  </div>
                )}

                {playerAnalysis.analysis.value_rating && (
                  <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-white/70 text-sm">Value Rating</span>
                      <span className="text-lg font-bold text-green-400">{playerAnalysis.analysis.value_rating}/10</span>
                    </div>
                  </div>
                )}

                <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-white/70 text-sm">Ownership</span>
                    <span className="text-lg font-bold text-white">{playerAnalysis.stats.ownership}%</span>
                  </div>
                </div>

                <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-white/70 text-sm">Minutes Played</span>
                    <span className="text-lg font-bold text-white">{playerAnalysis.stats.minutes}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Performance Stats */}
          <div className="glass rounded-3xl p-6">
            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Season Performance
            </h3>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm text-center">
                <div className="text-2xl font-bold text-white mb-1">{playerAnalysis.stats.goals_scored || 0}</div>
                <div className="text-white/70 text-sm">Goals</div>
              </div>
              
              <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm text-center">
                <div className="text-2xl font-bold text-white mb-1">{playerAnalysis.stats.assists || 0}</div>
                <div className="text-white/70 text-sm">Assists</div>
              </div>
              
              <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm text-center">
                <div className="text-2xl font-bold text-white mb-1">{playerAnalysis.stats.total_points}</div>
                <div className="text-white/70 text-sm">Total Points</div>
              </div>
              
              <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm text-center">
                <div className="text-2xl font-bold text-white mb-1">{playerAnalysis.stats.points_per_game}</div>
                <div className="text-white/70 text-sm">Points/Game</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* No Results State */}
      {!loading && !error && !playerAnalysis && (
        <div className="glass rounded-3xl p-12">
          <div className="text-center">
            <Target className="w-16 h-16 text-white/50 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Enhanced Player Analysis Ready</h3>
            <p className="text-white/70 mb-6 max-w-md mx-auto">
              Search for any Premier League player to get comprehensive AI analysis including:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-white/60 max-w-md mx-auto">
              <div className="flex items-center gap-2">
                <span>🤖</span> AI-powered predictions
              </div>
              <div className="flex items-center gap-2">
                <span>📰</span> Sentiment analysis
              </div>
              <div className="flex items-center gap-2">
                <span>📊</span> Performance insights
              </div>
              <div className="flex items-center gap-2">
                <span>⭐</span> Captain potential
              </div>
            </div>
            <div className="mt-6 text-sm text-white/60">
              Try searching: Haaland, Salah, De Bruyne, Son, Watkins, Palmer, Isak
            </div>
          </div>
        </div>
      )}
    </div>
  )
}