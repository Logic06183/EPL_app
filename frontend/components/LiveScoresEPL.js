'use client'

import { useState, useEffect } from 'react'
import { Clock, Users, Trophy, Target, Star, TrendingUp, Zap, AlertCircle } from 'lucide-react'

export default function LiveScoresEPL() {
  const [fixtures, setFixtures] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [gameweekInfo, setGameweekInfo] = useState(null)
  const [filterType, setFilterType] = useState('live') // 'live', 'today', 'recent', 'upcoming'

  useEffect(() => {
    fetchFixtures()
    fetchGameweekInfo()
    
    // Auto-refresh every 30 seconds for live matches
    const interval = setInterval(() => {
      if (filterType === 'live') {
        fetchFixtures()
      }
    }, 30000)
    
    return () => clearInterval(interval)
  }, [filterType])

  const fetchGameweekInfo = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://epl-backend-77913915885.us-central1.run.app'}/api/gameweek/current`)
      if (response.ok) {
        const data = await response.json()
        setGameweekInfo(data)
      }
    } catch (error) {
      console.error('Error fetching gameweek info:', error)
    }
  }

  const fetchFixtures = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const url = `${process.env.NEXT_PUBLIC_API_URL || 'https://epl-backend-77913915885.us-central1.run.app'}/api/fixtures?filter=${filterType}`
      console.log('Fetching fixtures from:', url)
      
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout
      
      const response = await fetch(url, {
        signal: controller.signal
      })
      clearTimeout(timeoutId)
      console.log('Fixtures response status:', response.status, response.statusText)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('Fixtures error response body:', errorText)
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      console.log('Fixtures data:', data)
      setFixtures(data.fixtures || [])
    } catch (error) {
      console.error('Error fetching fixtures:', error)
      setError(error.message)
    } finally {
      setLoading(false)
    }
  }

  const getMatchStatus = (fixture) => {
    if (!fixture.started) {
      return { status: 'upcoming', text: 'Not Started', color: 'text-blue-400' }
    } else if (fixture.started && !fixture.finished) {
      return { status: 'live', text: `${fixture.minutes}'`, color: 'text-green-400' }
    } else {
      return { status: 'finished', text: 'FT', color: 'text-white/60' }
    }
  }

  const formatKickoffTime = (kickoffTime) => {
    const date = new Date(kickoffTime)
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const matchDate = new Date(date.getFullYear(), date.getMonth(), date.getDate())
    
    const timeDiff = matchDate.getTime() - today.getTime()
    const daysDiff = Math.floor(timeDiff / (1000 * 60 * 60 * 24))
    
    const timeStr = date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false 
    })
    
    if (daysDiff === 0) return `Today ${timeStr}`
    if (daysDiff === 1) return `Tomorrow ${timeStr}`
    if (daysDiff === -1) return `Yesterday ${timeStr}`
    if (daysDiff > 1) return `${daysDiff}d ${timeStr}`
    if (daysDiff < -1) return `${Math.abs(daysDiff)}d ago`
    
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getTopPerformers = (fixture) => {
    if (!fixture.stats) return []
    
    const goalsData = fixture.stats.find(stat => stat.identifier === 'goals_scored')
    const assistsData = fixture.stats.find(stat => stat.identifier === 'assists')
    const bonusData = fixture.stats.find(stat => stat.identifier === 'bonus')
    
    let performers = []
    
    // Goals
    if (goalsData) {
      [...(goalsData.h || []), ...(goalsData.a || [])].forEach(goal => {
        performers.push({
          playerId: goal.element,
          type: 'goal',
          value: goal.value,
          icon: '⚽',
          color: 'text-yellow-400'
        })
      })
    }
    
    // Assists  
    if (assistsData) {
      [...(assistsData.h || []), ...(assistsData.a || [])].forEach(assist => {
        performers.push({
          playerId: assist.element,
          type: 'assist',
          value: assist.value,
          icon: '🅰️',
          color: 'text-blue-400'
        })
      })
    }
    
    // Bonus points
    if (bonusData) {
      [...(bonusData.h || []), ...(bonusData.a || [])].forEach(bonus => {
        performers.push({
          playerId: bonus.element,
          type: 'bonus',
          value: bonus.value,
          icon: '⭐',
          color: 'text-purple-400'
        })
      })
    }
    
    return performers.slice(0, 6) // Top 6 performers
  }

  if (loading && fixtures.length === 0) {
    return (
      <div className="glass-epl rounded-3xl p-8">
        <div className="flex flex-col items-center justify-center py-12">
          <div className="loading-epl mb-6"></div>
          <h3 className="text-xl font-semibold text-white mb-2">⚽ Loading Live Scores</h3>
          <p className="text-white/70 text-center max-w-md">
            Fetching the latest Premier League fixtures and results...
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
          <button onClick={fetchFixtures} className="btn-epl-primary">
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with Gameweek Info */}
      <div className="glass-epl rounded-3xl p-6">
        <div className="header-epl mb-6">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="p-3 bg-gradient-to-r from-green-400 to-blue-500 rounded-full">
              <Zap className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-3xl font-bold text-white">⚽ Live Scores</h2>
          </div>
          <p className="text-white/80 text-lg">Real-time Premier League fixtures and results</p>
          
          {gameweekInfo && (
            <div className="mt-4 p-4 bg-white/10 rounded-lg backdrop-blur-sm">
              <div className="text-center">
                <h3 className="text-xl font-bold text-green-400">{gameweekInfo.name}</h3>
                <p className="text-white/70 text-sm">
                  Deadline: {new Date(gameweekInfo.deadline).toLocaleString()}
                </p>
                <div className="flex items-center justify-center gap-2 mt-2">
                  <div className={`w-2 h-2 rounded-full ${gameweekInfo.is_current ? 'bg-green-400 animate-pulse' : 'bg-white/40'}`}></div>
                  <span className="text-white/60 text-sm">
                    {gameweekInfo.is_current ? 'Current Gameweek' : gameweekInfo.is_finished ? 'Finished' : 'Upcoming'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap gap-3 mb-6">
          {[
            { key: 'live', label: '🔴 Live', desc: 'Matches in progress' },
            { key: 'today', label: '📅 Today', desc: 'Today\'s fixtures' },
            { key: 'recent', label: '📊 Recent', desc: 'Latest results' },
            { key: 'upcoming', label: '⏱️ Upcoming', desc: 'Next matches' }
          ].map(filter => (
            <button
              key={filter.key}
              onClick={() => setFilterType(filter.key)}
              className={`p-3 rounded-lg font-medium transition-all duration-300 border-2 ${
                filterType === filter.key
                  ? 'bg-gradient-to-r from-green-500 to-blue-500 border-green-400 text-white shadow-lg'
                  : 'bg-white/10 border-white/30 text-white/70 hover:bg-white/20'
              }`}
            >
              <div className="text-sm font-semibold">{filter.label}</div>
              <div className="text-xs opacity-80">{filter.desc}</div>
            </button>
          ))}
        </div>

        {/* Live Status */}
        {filterType === 'live' && (
          <div className="flex items-center gap-2 mb-4 text-green-400">
            <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
            <span className="text-sm font-medium">Auto-refreshing every 30 seconds</span>
          </div>
        )}
      </div>

      {/* Fixtures List */}
      {fixtures.length > 0 ? (
        <div className="space-y-4">
          {fixtures.map((fixture) => {
            const matchStatus = getMatchStatus(fixture)
            const performers = getTopPerformers(fixture)
            
            return (
              <div key={fixture.id} className="glass-epl rounded-2xl p-6 hover:bg-white/10 transition-all duration-300">
                {/* Match Header */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`px-3 py-1 rounded-full text-sm font-bold ${
                      matchStatus.status === 'live' ? 'bg-green-500/20 text-green-400 animate-pulse' :
                      matchStatus.status === 'upcoming' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-white/20 text-white/60'
                    }`}>
                      {matchStatus.text}
                    </div>
                    {fixture.event && (
                      <span className="text-white/60 text-sm">GW {fixture.event}</span>
                    )}
                  </div>
                  <div className="text-white/60 text-sm">
                    {formatKickoffTime(fixture.kickoff_time)}
                  </div>
                </div>

                {/* Teams and Score */}
                <div className="grid grid-cols-3 gap-4 items-center mb-4">
                  {/* Home Team */}
                  <div className="text-right">
                    <div className="text-white font-bold text-lg">{fixture.team_h_name || `Team ${fixture.team_h}`}</div>
                    <div className="text-white/60 text-sm">Home</div>
                  </div>

                  {/* Score */}
                  <div className="text-center">
                    <div className="text-3xl font-bold text-white mb-1">
                      {fixture.started ? 
                        `${fixture.team_h_score || 0} - ${fixture.team_a_score || 0}` : 
                        'vs'
                      }
                    </div>
                    {fixture.started && (
                      <div className="text-sm text-white/60">
                        Difficulty: H{fixture.team_h_difficulty} / A{fixture.team_a_difficulty}
                      </div>
                    )}
                  </div>

                  {/* Away Team */}
                  <div className="text-left">
                    <div className="text-white font-bold text-lg">{fixture.team_a_name || `Team ${fixture.team_a}`}</div>
                    <div className="text-white/60 text-sm">Away</div>
                  </div>
                </div>

                {/* Match Stats */}
                {fixture.started && performers.length > 0 && (
                  <div className="border-t border-white/20 pt-4">
                    <div className="text-white/60 text-sm mb-2">Key Performers:</div>
                    <div className="flex flex-wrap gap-2">
                      {performers.map((performer, idx) => (
                        <div key={idx} className={`flex items-center gap-1 px-2 py-1 bg-white/10 rounded-full text-sm ${performer.color}`}>
                          <span>{performer.icon}</span>
                          <span>Player {performer.playerId}</span>
                          {performer.value > 1 && (
                            <span className="text-xs bg-white/20 px-1 rounded-full">x{performer.value}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ) : (
        <div className="glass-epl rounded-3xl p-12 text-center">
          <Clock className="w-16 h-16 text-white/50 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">
            {filterType === 'live' ? 'No Live Matches' : 'No Fixtures Found'}
          </h3>
          <p className="text-white/70 mb-6">
            {filterType === 'live' ? 
              'There are no matches currently in progress.' :
              'Try selecting a different filter to see more fixtures.'
            }
          </p>
          <button onClick={fetchFixtures} className="btn-epl-primary">
            Refresh Data
          </button>
        </div>
      )}
    </div>
  )
}