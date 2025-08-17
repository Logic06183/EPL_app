'use client'

import { useState, useEffect } from 'react'
import { Trophy, Clock, Users, TrendingUp, AlertCircle, Zap } from 'lucide-react'

export default function LiveScores() {
  const [liveMatches, setLiveMatches] = useState([])
  const [standings, setStandings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('live')

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [activeTab])

  const fetchData = async () => {
    try {
      if (activeTab === 'live') {
        // When SportMonks is configured, this will fetch real live scores
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://epl-backend-77913915885.us-central1.run.app'}/api/sportmonks/live`)
        if (response.ok) {
          const data = await response.json()
          setLiveMatches(data.matches || [])
        } else {
          // Fallback to mock data
          setLiveMatches(getMockLiveMatches())
        }
      } else if (activeTab === 'standings') {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://epl-backend-77913915885.us-central1.run.app'}/api/sportmonks/standings`)
        if (response.ok) {
          const data = await response.json()
          setStandings(data.standings || getMockStandings())
        } else {
          setStandings(getMockStandings())
        }
      }
    } catch (err) {
      console.error('Error fetching data:', err)
      // Use mock data as fallback
      if (activeTab === 'live') {
        setLiveMatches(getMockLiveMatches())
      } else {
        setStandings(getMockStandings())
      }
    } finally {
      setLoading(false)
    }
  }

  const getMockLiveMatches = () => {
    return [
      {
        id: 1,
        home_team: 'Arsenal',
        away_team: 'Chelsea',
        home_score: 2,
        away_score: 1,
        minute: 67,
        status: 'LIVE',
        venue: 'Emirates Stadium'
      },
      {
        id: 2,
        home_team: 'Man City',
        away_team: 'Liverpool',
        home_score: 1,
        away_score: 1,
        minute: 45,
        status: 'HT',
        venue: 'Etihad Stadium'
      },
      {
        id: 3,
        home_team: 'Man United',
        away_team: 'Tottenham',
        home_score: 0,
        away_score: 0,
        minute: 15,
        status: 'LIVE',
        venue: 'Old Trafford'
      }
    ]
  }

  const getMockStandings = () => {
    return [
      { position: 1, team: 'Arsenal', played: 20, won: 15, drawn: 3, lost: 2, gf: 45, ga: 15, gd: 30, points: 48 },
      { position: 2, team: 'Man City', played: 20, won: 14, drawn: 4, lost: 2, gf: 50, ga: 20, gd: 30, points: 46 },
      { position: 3, team: 'Liverpool', played: 20, won: 13, drawn: 5, lost: 2, gf: 42, ga: 18, gd: 24, points: 44 },
      { position: 4, team: 'Chelsea', played: 20, won: 12, drawn: 4, lost: 4, gf: 38, ga: 22, gd: 16, points: 40 },
      { position: 5, team: 'Tottenham', played: 20, won: 11, drawn: 3, lost: 6, gf: 35, ga: 25, gd: 10, points: 36 }
    ]
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'LIVE': return 'text-green-400 animate-pulse'
      case 'HT': return 'text-yellow-400'
      case 'FT': return 'text-gray-400'
      default: return 'text-gray-400'
    }
  }

  return (
    <div className="glass-epl rounded-3xl p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-r from-red-500 to-red-600 rounded-xl">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Live Premier League</h2>
            <p className="text-white/60 text-sm">Real-time scores and standings</p>
          </div>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('live')}
            className={`px-4 py-2 rounded-lg transition-all ${
              activeTab === 'live' 
                ? 'bg-green-500/20 text-green-400 border border-green-400/30' 
                : 'bg-white/5 text-white/60 hover:bg-white/10'
            }`}
          >
            Live Matches
          </button>
          <button
            onClick={() => setActiveTab('standings')}
            className={`px-4 py-2 rounded-lg transition-all ${
              activeTab === 'standings' 
                ? 'bg-blue-500/20 text-blue-400 border border-blue-400/30' 
                : 'bg-white/5 text-white/60 hover:bg-white/10'
            }`}
          >
            Table
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-8">
          <div className="inline-flex items-center gap-2 text-white/60">
            <div className="animate-spin rounded-full h-5 w-5 border-2 border-white/20 border-t-white/60"></div>
            <span>Loading...</span>
          </div>
        </div>
      ) : (
        <>
          {activeTab === 'live' && (
            <div className="space-y-3">
              {liveMatches.length === 0 ? (
                <div className="text-center py-8 text-white/60">
                  <AlertCircle className="w-8 h-8 mx-auto mb-2" />
                  <p>No live matches at the moment</p>
                </div>
              ) : (
                liveMatches.map((match) => (
                  <div key={match.id} className="bg-white/5 rounded-xl p-4 hover:bg-white/10 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-white font-medium">{match.home_team}</span>
                          <span className="text-2xl font-bold text-white">{match.home_score}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-white font-medium">{match.away_team}</span>
                          <span className="text-2xl font-bold text-white">{match.away_score}</span>
                        </div>
                      </div>
                      
                      <div className="ml-6 text-center">
                        <div className={`text-sm font-bold ${getStatusColor(match.status)}`}>
                          {match.status === 'LIVE' ? `${match.minute}'` : match.status}
                        </div>
                        <div className="text-xs text-white/40 mt-1">
                          {match.venue}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'standings' && (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-white/60 text-sm">
                    <th className="text-left pb-3">Pos</th>
                    <th className="text-left pb-3">Team</th>
                    <th className="text-center pb-3">P</th>
                    <th className="text-center pb-3">W</th>
                    <th className="text-center pb-3">D</th>
                    <th className="text-center pb-3">L</th>
                    <th className="text-center pb-3">GD</th>
                    <th className="text-center pb-3">Pts</th>
                  </tr>
                </thead>
                <tbody>
                  {standings.map((team, index) => (
                    <tr key={team.position} className="border-t border-white/10">
                      <td className="py-3">
                        <span className={`font-bold ${
                          index < 4 ? 'text-green-400' : 
                          index === 4 ? 'text-orange-400' : 
                          index > 16 ? 'text-red-400' : 
                          'text-white'
                        }`}>
                          {team.position}
                        </span>
                      </td>
                      <td className="py-3 text-white font-medium">{team.team}</td>
                      <td className="py-3 text-center text-white/70">{team.played}</td>
                      <td className="py-3 text-center text-green-400">{team.won}</td>
                      <td className="py-3 text-center text-yellow-400">{team.drawn}</td>
                      <td className="py-3 text-center text-red-400">{team.lost}</td>
                      <td className="py-3 text-center text-white/70">{team.gd > 0 ? '+' : ''}{team.gd}</td>
                      <td className="py-3 text-center text-white font-bold">{team.points}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              
              <div className="mt-4 pt-4 border-t border-white/10">
                <div className="flex items-center gap-6 text-xs text-white/60">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-green-400 rounded-full"></div>
                    <span>Champions League</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-orange-400 rounded-full"></div>
                    <span>Europa League</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-red-400 rounded-full"></div>
                    <span>Relegation</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
      
      {/* SportMonks Integration Notice */}
      <div className="mt-4 p-3 bg-blue-500/10 border border-blue-400/30 rounded-lg">
        <div className="flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-blue-400 mt-0.5" />
          <div className="text-sm text-blue-200">
            <p className="font-medium">SportMonks API Ready</p>
            <p className="text-blue-200/70 text-xs mt-1">
              Live scores will update automatically when SportMonks API is activated. Currently showing demo data.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}