'use client'

import { useState, useEffect } from 'react'
import { Calendar, Clock, Trophy, Users, Loader2, AlertCircle } from 'lucide-react'

export default function GameweekInfo() {
  const [gameweekData, setGameweekData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchGameweekInfo()
  }, [])

  const fetchGameweekInfo = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/gameweek/current`, {
        signal: controller.signal
      })
      clearTimeout(timeoutId)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      setGameweekData(data)
    } catch (error) {
      console.error('Error fetching gameweek info:', error)
      setError(error.message)
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (data) => {
    if (data?.is_current) return { bg: 'bg-green-500', text: 'text-green-400', label: 'Active Now' }
    if (data?.is_finished) return { bg: 'bg-gray-500', text: 'text-gray-400', label: 'Finished' }
    return { bg: 'bg-blue-500', text: 'text-blue-400', label: 'Upcoming' }
  }

  const formatDeadline = (deadline) => {
    if (!deadline) return 'TBD'
    const date = new Date(deadline)
    const now = new Date()
    const timeDiff = date.getTime() - now.getTime()
    const daysDiff = Math.ceil(timeDiff / (1000 * 3600 * 24))
    
    if (daysDiff < 0) return 'Passed'
    if (daysDiff === 0) return 'Today'
    if (daysDiff === 1) return 'Tomorrow'
    if (daysDiff <= 7) return `In ${daysDiff} days`
    
    return date.toLocaleDateString('en-US', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getTimeUntilDeadline = (deadline) => {
    if (!deadline) return null
    const now = new Date()
    const deadlineDate = new Date(deadline)
    const timeDiff = deadlineDate.getTime() - now.getTime()
    
    if (timeDiff < 0) return { passed: true, text: 'Deadline has passed' }
    
    const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24))
    const hours = Math.floor((timeDiff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
    const minutes = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60))
    
    if (days > 0) return { text: `${days}d ${hours}h ${minutes}m`, urgent: days < 1 }
    if (hours > 0) return { text: `${hours}h ${minutes}m`, urgent: hours < 2 }
    return { text: `${minutes}m`, urgent: true }
  }

  if (loading) {
    return (
      <div className="glass rounded-3xl p-8">
        <div className="flex flex-col items-center justify-center py-8">
          <Loader2 className="w-12 h-12 text-white animate-spin mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">Loading Gameweek Info</h3>
          <p className="text-white/70 text-center">
            Fetching the latest gameweek information...
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass rounded-3xl p-8">
        <div className="flex flex-col items-center justify-center py-8">
          <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">Error Loading Data</h3>
          <p className="text-white/70 text-center mb-6">
            {error}
          </p>
          <button
            onClick={fetchGameweekInfo}
            className="btn-primary"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (!gameweekData) {
    return (
      <div className="glass rounded-3xl p-8">
        <div className="text-center">
          <Calendar className="w-16 h-16 text-white/50 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No Data Available</h3>
          <p className="text-white/70">
            Unable to load gameweek information
          </p>
        </div>
      </div>
    )
  }

  const statusInfo = getStatusColor(gameweekData)
  const timeUntil = getTimeUntilDeadline(gameweekData.deadline)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass rounded-3xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-gradient-to-r from-orange-500 to-red-500 rounded-xl">
            <Calendar className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Gameweek Information</h2>
            <p className="text-white/70">Current FPL gameweek status and deadlines</p>
          </div>
        </div>
      </div>

      {/* Main Gameweek Card */}
      <div className="glass rounded-3xl p-8">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className={`w-4 h-4 rounded-full ${statusInfo.bg} animate-pulse`}></div>
            <span className={`text-lg font-semibold ${statusInfo.text}`}>
              {statusInfo.label}
            </span>
          </div>
          
          <h3 className="text-4xl md:text-6xl font-bold text-white mb-2">
            {gameweekData.name}
          </h3>
          
          <p className="text-xl text-white/70">
            Gameweek {gameweekData.gameweek}
          </p>
        </div>

        {/* Deadline Info */}
        <div className="bg-white/10 rounded-2xl p-6 backdrop-blur-sm mb-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-3">
              <Clock className="w-6 h-6 text-white/70" />
              <div>
                <div className="text-white/70 text-sm">Deadline</div>
                <div className="text-lg font-semibold text-white">
                  {formatDeadline(gameweekData.deadline)}
                </div>
              </div>
            </div>
            
            {timeUntil && (
              <div className={`px-4 py-2 rounded-xl text-center ${
                timeUntil.passed ? 'bg-gray-500/20 text-gray-300' :
                timeUntil.urgent ? 'bg-red-500/20 text-red-300 animate-pulse' :
                'bg-blue-500/20 text-blue-300'
              }`}>
                <div className="text-sm font-medium">
                  {timeUntil.passed ? 'Deadline Passed' : 'Time Remaining'}
                </div>
                <div className="text-xl font-bold">
                  {timeUntil.text}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Status Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm text-center">
            <Trophy className="w-8 h-8 text-yellow-400 mx-auto mb-2" />
            <div className="text-white/70 text-sm">Status</div>
            <div className="text-lg font-bold text-white capitalize">
              {gameweekData.is_current ? 'Active' : 
               gameweekData.is_finished ? 'Completed' : 'Upcoming'}
            </div>
          </div>
          
          <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm text-center">
            <Users className="w-8 h-8 text-blue-400 mx-auto mb-2" />
            <div className="text-white/70 text-sm">Transfers</div>
            <div className="text-lg font-bold text-white">
              {gameweekData.is_finished ? 'Closed' : 
               timeUntil?.passed ? 'Closed' : 'Open'}
            </div>
          </div>
          
          <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm text-center">
            <Calendar className="w-8 h-8 text-green-400 mx-auto mb-2" />
            <div className="text-white/70 text-sm">Week</div>
            <div className="text-lg font-bold text-white">
              {gameweekData.gameweek}/38
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 mt-8 justify-center">
          <button
            onClick={fetchGameweekInfo}
            className="btn-secondary"
          >
            Refresh Info
          </button>
          
          {!gameweekData.is_finished && !timeUntil?.passed && (
            <button className="btn-primary">
              Plan Transfers
            </button>
          )}
        </div>
      </div>

      {/* Tips Section */}
      <div className="glass rounded-3xl p-6">
        <h3 className="text-lg font-bold text-white mb-4">💡 Gameweek Tips</h3>
        <div className="space-y-3 text-sm">
          {timeUntil?.urgent && !timeUntil?.passed && (
            <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-3">
              <div className="text-red-300 font-semibold">⚠️ Deadline Alert</div>
              <div className="text-white/90">
                Less than {timeUntil.text} remaining to make transfers!
              </div>
            </div>
          )}
          
          {gameweekData.is_current && (
            <div className="bg-green-500/20 border border-green-500/30 rounded-lg p-3">
              <div className="text-green-300 font-semibold">🔄 Live Gameweek</div>
              <div className="text-white/90">
                Matches are being played. Check live scores for captain performance.
              </div>
            </div>
          )}
          
          {!gameweekData.is_finished && !gameweekData.is_current && (
            <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-3">
              <div className="text-blue-300 font-semibold">📋 Planning Time</div>
              <div className="text-white/90">
                Use our Squad Optimizer and Player Predictions to plan your transfers.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}