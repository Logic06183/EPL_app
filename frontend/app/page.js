'use client'

import { useState, useEffect } from 'react'
import { Activity, Trophy, TrendingUp, Users, Zap, Target, Calendar, Crown, Star, Brain } from 'lucide-react'
import PlayerPredictionsEPL from '../components/PlayerPredictionsEPL'
import SquadOptimizer from '../components/SquadOptimizer'
import PlayerAnalysisEnhanced from '../components/PlayerAnalysisEnhanced'
import GameweekInfo from '../components/GameweekInfo'
import PaymentModal from '../components/PaymentModal'
import LiveScoresEPL from '../components/LiveScoresEPL'
import MLMethodology from '../components/MLMethodology'
import HybridForecaster from '../components/HybridForecaster'
import PredictionTracker from '../components/PredictionTracker'

export default function EPLDashboard() {
  const [activeTab, setActiveTab] = useState('hybrid')
  const [apiStatus, setApiStatus] = useState('checking')
  const [showPaymentModal, setShowPaymentModal] = useState(false)
  const [stats, setStats] = useState({
    playersAnalyzed: '500+',
    accuracy: '87%',
    users: '2.5K+',
    predictions: '15K+'
  })

  useEffect(() => {
    checkApiStatus()
  }, [])

  const checkApiStatus = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://epl-backend-77913915885.us-central1.run.app'}/health`)
      if (response.ok) {
        const data = await response.json()
        setApiStatus(data.ai_enabled ? 'ai-enabled' : 'connected')
      } else {
        setApiStatus('error')
      }
    } catch (error) {
      console.error('API connection failed:', error)
      setApiStatus('error')
    }
  }

  const tabs = [
    { 
      id: 'predictions', 
      name: 'Top Players', 
      icon: TrendingUp, 
      description: 'AI-powered player predictions and rankings',
      benefits: [
        'Identifies highest-scoring players for each gameweek',
        'Uses form, fixtures, and sentiment analysis',
        'Provides confidence scores for each prediction'
      ]
    },
    { 
      id: 'live', 
      name: 'Live Scores', 
      icon: Zap, 
      description: 'Real-time matches and league standings',
      benefits: [
        'Track live matches and goal scorers',
        'Monitor your players\' performance in real-time',
        'Plan transfers based on live data'
      ]
    },
    { 
      id: 'optimizer', 
      name: 'Squad Builder', 
      icon: Trophy, 
      description: 'Build the perfect squad within budget and formation',
      benefits: [
        'Maximizes total points within budget constraints',
        'Supports all FPL formations (3-5-2, 4-4-2, etc.)',
        'Identifies value picks and optimal combinations'
      ]
    },
    { 
      id: 'analysis', 
      name: 'Player Intel', 
      icon: Target, 
      description: 'Deep dive analysis with comprehensive statistics',
      benefits: [
        'Detailed performance metrics and trends',
        'Fixture difficulty and upcoming opponents',
        'Price change predictions and ownership data'
      ]
    },
    { 
      id: 'gameweek', 
      name: 'Live Info', 
      icon: Calendar, 
      description: 'Current gameweek status and key information',
      benefits: [
        'Never miss transfer deadlines',
        'Track bonus points and price changes',
        'Get gameweek-specific insights'
      ]
    },
    { 
      id: 'hybrid', 
      name: 'AI Forecaster', 
      icon: Brain, 
      description: 'Advanced match predictions with contextual AI',
      benefits: [
        'Predicts match outcomes with high accuracy',
        'Considers team news, injuries, and form',
        'Helps plan captaincy and differential picks'
      ]
    },
    { 
      id: 'tracker', 
      name: 'Prediction Tracker', 
      icon: TrendingUp, 
      description: 'Track prediction accuracy and model improvements',
      benefits: [
        'See how predictions compare to actual results',
        'Track model accuracy improvements over time',
        'Understand how data feeds back into better predictions'
      ]
    },
  ]

  const renderActiveComponent = () => {
    switch (activeTab) {
      case 'predictions':
        return <PlayerPredictionsEPL />
      case 'live':
        return <LiveScoresEPL />
      case 'optimizer':
        return <SquadOptimizer />
      case 'analysis':
        return <PlayerAnalysisEnhanced />
      case 'gameweek':
        return <GameweekInfo />
      case 'hybrid':
        return <HybridForecaster />
      case 'tracker':
        return <PredictionTracker />
      default:
        return <PlayerPredictionsEPL />
    }
  }

  const getStatusIndicator = () => {
    switch (apiStatus) {
      case 'ai-enabled':
        return (
          <div className="flex items-center gap-2 px-4 py-2 bg-green-500/20 border border-green-400/30 rounded-full">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span className="text-green-300 text-sm font-medium">🤖 AI Enhanced</span>
          </div>
        )
      case 'connected':
        return (
          <div className="flex items-center gap-2 px-4 py-2 bg-blue-500/20 border border-blue-400/30 rounded-full">
            <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
            <span className="text-blue-300 text-sm font-medium">✅ Connected</span>
          </div>
        )
      case 'checking':
        return (
          <div className="flex items-center gap-2 px-4 py-2 bg-yellow-500/20 border border-yellow-400/30 rounded-full">
            <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
            <span className="text-yellow-300 text-sm font-medium">🔍 Checking...</span>
          </div>
        )
      default:
        return (
          <div className="flex items-center gap-2 px-4 py-2 bg-red-500/20 border border-red-400/30 rounded-full">
            <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse"></div>
            <span className="text-red-300 text-sm font-medium">❌ Offline</span>
          </div>
        )
    }
  }

  return (
    <div className="min-h-screen p-4">
      <div className="max-w-7xl mx-auto">
        {/* Hero Header */}
        <div className="header-epl text-center mb-8">
          <div className="glass-epl rounded-3xl p-8 mb-8">
            <div className="flex justify-center items-center gap-4 mb-6">
              <div className="p-4 bg-gradient-to-r from-green-400 to-blue-500 rounded-full backdrop-blur-lg shadow-lg">
                <Activity className="w-10 h-10 text-white" />
              </div>
              <div className="text-left">
                <h1 className="text-4xl md:text-6xl font-black text-white mb-2">
                  ⚽ FPL AI Pro
                </h1>
                <div className="text-lg text-green-300 font-semibold">
                  Premier League • Predictions • Performance
                </div>
              </div>
            </div>
            
            <p className="text-xl text-white/90 text-balance max-w-3xl mx-auto mb-6">
              Advanced Fantasy Premier League predictions powered by artificial intelligence. 
              Get real player insights, optimal squad suggestions, and live gameweek data.
            </p>

            {/* Status and Stats */}
            <div className="flex flex-col md:flex-row items-center justify-center gap-6">
              {getStatusIndicator()}
              
              <div className="grid grid-cols-4 gap-6 text-center">
                <div>
                  <div className="text-2xl font-bold text-green-400">{stats.playersAnalyzed}</div>
                  <div className="text-white/60 text-sm">Players</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-blue-400">{stats.accuracy}</div>
                  <div className="text-white/60 text-sm">Accuracy</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-purple-400">{stats.users}</div>
                  <div className="text-white/60 text-sm">Users</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-yellow-400">{stats.predictions}</div>
                  <div className="text-white/60 text-sm">Predictions</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Navigation Tabs with EPL Theme */}
        <div className="flex flex-wrap justify-center gap-3 mb-8">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  tab-epl group relative
                  ${activeTab === tab.id ? 'active' : ''}
                `}
                title={tab.description}
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-5 h-5" />
                  <div className="text-left">
                    <div className="font-semibold">{tab.name}</div>
                    <div className="text-xs opacity-70 group-hover:opacity-100 transition-opacity">
                      {tab.description}
                    </div>
                  </div>
                </div>
              </button>
            )
          })}
        </div>

        {/* ML Methodology */}
        <MLMethodology />

        {/* Main Content */}
        <div className="animate-fade-in">
          {renderActiveComponent()}
        </div>

        {/* Footer */}
        <div className="mt-16 text-center">
          <div className="glass-epl rounded-2xl p-6 max-w-2xl mx-auto">
            <div className="flex justify-center items-center gap-2 mb-3">
              <Crown className="w-5 h-5 text-yellow-400" />
              <span className="text-white font-semibold">FPL AI Pro</span>
            </div>
            <p className="text-white/70 text-sm mb-4">
              Powered by real-time FPL data, machine learning algorithms, and Google's Gemini AI. 
              Built for managers who want to dominate their leagues.
            </p>
            <div className="flex justify-center items-center gap-4 text-white/60 text-sm mb-4">
              <span>🏆 Premier League</span>
              <span>•</span>
              <span>🤖 AI Powered</span>
              <span>•</span>
              <span>⚡ Real-time Data</span>
            </div>
            
            {/* Upgrade CTA */}
            <button
              onClick={() => setShowPaymentModal(true)}
              className="bg-gradient-to-r from-green-500 to-blue-500 hover:from-green-600 hover:to-blue-600 text-white font-bold py-3 px-6 rounded-full transition-all duration-300 transform hover:scale-105 shadow-lg"
            >
              <div className="flex items-center gap-2">
                <Crown className="w-5 h-5" />
                <span>Upgrade to Pro - From $9.99/month</span>
              </div>
            </button>
          </div>
        </div>
      </div>
      
      {/* Payment Modal */}
      <PaymentModal 
        isOpen={showPaymentModal} 
        onClose={() => setShowPaymentModal(false)} 
      />
    </div>
  )
}