'use client'

import { useState, useEffect } from 'react'
import { Activity, Trophy, TrendingUp, Users, Zap, Target, Calendar } from 'lucide-react'
import PlayerPredictions from '../components/PlayerPredictions'
import SquadOptimizer from '../components/SquadOptimizer'
import PlayerAnalysis from '../components/PlayerAnalysis'
import GameweekInfo from '../components/GameweekInfo'
import ApiStatus from '../components/ApiStatus'

export default function Home() {
  const [activeTab, setActiveTab] = useState('predictions')
  const [apiStatus, setApiStatus] = useState('checking')

  useEffect(() => {
    checkApiStatus()
  }, [])

  const checkApiStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/health')
      setApiStatus(response.ok ? 'connected' : 'error')
    } catch (error) {
      console.error('API connection failed:', error)
      setApiStatus('error')
    }
  }

  const tabs = [
    { id: 'predictions', name: 'Top Predictions', icon: TrendingUp, color: 'from-blue-500 to-cyan-500' },
    { id: 'optimizer', name: 'Squad Optimizer', icon: Trophy, color: 'from-green-500 to-emerald-500' },
    { id: 'analysis', name: 'Player Analysis', icon: Target, color: 'from-purple-500 to-pink-500' },
    { id: 'gameweek', name: 'Gameweek Info', icon: Calendar, color: 'from-orange-500 to-red-500' },
  ]

  const renderActiveComponent = () => {
    switch (activeTab) {
      case 'predictions':
        return <PlayerPredictions />
      case 'optimizer':
        return <SquadOptimizer />
      case 'analysis':
        return <PlayerAnalysis />
      case 'gameweek':
        return <GameweekInfo />
      default:
        return <PlayerPredictions />
    }
  }

  return (
    <div className="min-h-screen p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center items-center gap-3 mb-4">
            <div className="p-3 bg-white/20 rounded-full backdrop-blur-lg">
              <Activity className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-4xl md:text-6xl font-bold text-white text-balance">
              FPL AI Dashboard
            </h1>
          </div>
          <p className="text-xl text-white/90 text-balance max-w-2xl mx-auto">
            Advanced Fantasy Premier League predictions powered by machine learning and optimization algorithms
          </p>
          <ApiStatus status={apiStatus} onRetry={checkApiStatus} />
        </div>

        {/* Navigation Tabs */}
        <div className="flex flex-wrap justify-center gap-2 mb-8">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-2 px-6 py-3 rounded-xl font-semibold transition-all duration-300
                  ${activeTab === tab.id
                    ? `bg-gradient-to-r ${tab.color} text-white shadow-lg scale-105`
                    : 'bg-white/20 text-white hover:bg-white/30 backdrop-blur-lg'
                  }
                `}
              >
                <Icon className="w-5 h-5" />
                <span className="hidden sm:inline">{tab.name}</span>
              </button>
            )
          })}
        </div>

        {/* Main Content */}
        <div className="animate-fade-in">
          {renderActiveComponent()}
        </div>

        {/* Footer */}
        <div className="mt-16 text-center text-white/70">
          <div className="flex justify-center items-center gap-2 mb-2">
            <Zap className="w-4 h-4" />
            <span>Powered by TensorFlow, Linear Programming & Real-time FPL API</span>
          </div>
          <p className="text-sm">
            Built with Next.js, React, and Tailwind CSS
          </p>
        </div>
      </div>
    </div>
  )
}