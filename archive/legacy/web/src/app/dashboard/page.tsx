'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { 
  TrendingUpIcon, 
  TrophyIcon, 
  ExclamationTriangleIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  SparklesIcon,
  ShieldCheckIcon,
  BellAlertIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline'
import { fetchDashboardData } from '@/lib/api'
import { PredictionsCard } from '@/components/dashboard/PredictionsCard'
import { OptimizerCard } from '@/components/dashboard/OptimizerCard'
import { InjuryAlertsCard } from '@/components/dashboard/InjuryAlertsCard'
import { PriceChangesCard } from '@/components/dashboard/PriceChangesCard'
import { WeeklyInsightsCard } from '@/components/dashboard/WeeklyInsightsCard'
import { UpgradePrompt } from '@/components/UpgradePrompt'
import { LoadingSpinner } from '@/components/LoadingSpinner'

export default function Dashboard() {
  const { user, isLoading: authLoading } = useAuth()
  const [selectedGameweek, setSelectedGameweek] = useState<number | null>(null)

  const { data: dashboardData, isLoading, error } = useQuery({
    queryKey: ['dashboard', selectedGameweek],
    queryFn: () => fetchDashboardData(selectedGameweek),
    enabled: !!user,
    refetchInterval: 60000, // Refetch every minute
  })

  if (authLoading || isLoading) {
    return <LoadingSpinner />
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
            Please sign in to continue
          </h2>
          <a href="/login" className="btn-primary">
            Sign In
          </a>
        </div>
      </div>
    )
  }

  const isPremium = user.tier === 'premium' || user.tier === 'elite'
  const isElite = user.tier === 'elite'

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                FPL Dashboard
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mt-1">
                Gameweek {dashboardData?.currentGameweek || '--'} • 
                {user.tier === 'free' && ' Free Plan'}
                {user.tier === 'basic' && ' Basic Plan'}
                {user.tier === 'premium' && ' Premium Plan ⭐'}
                {user.tier === 'elite' && ' Elite Plan 👑'}
              </p>
            </div>
            
            <div className="flex gap-4">
              {user.tier === 'free' && (
                <UpgradePrompt 
                  feature="Advanced Analytics"
                  requiredTier="basic"
                />
              )}
              
              <button className="btn-secondary">
                <BellAlertIcon className="h-5 w-5 mr-2" />
                Alerts ({dashboardData?.unreadAlerts || 0})
              </button>
            </div>
          </div>
        </motion.div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <MetricCard
            title="Squad Value"
            value={`£${dashboardData?.squadValue || '0.0'}m`}
            change={dashboardData?.squadValueChange}
            icon={<TrophyIcon className="h-6 w-6" />}
            color="blue"
          />
          <MetricCard
            title="Overall Rank"
            value={dashboardData?.overallRank?.toLocaleString() || '--'}
            change={dashboardData?.rankChange}
            icon={<ChartBarIcon className="h-6 w-6" />}
            color="green"
          />
          <MetricCard
            title="GW Points"
            value={dashboardData?.gameweekPoints || '--'}
            change={dashboardData?.pointsVsAverage}
            icon={<TrendingUpIcon className="h-6 w-6" />}
            color="purple"
          />
          <MetricCard
            title="Predictions"
            value={`${dashboardData?.predictionsUsed || 0}/${user.tier === 'free' ? '5' : '∞'}`}
            subtitle="This Week"
            icon={<SparklesIcon className="h-6 w-6" />}
            color="orange"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Predictions & Optimizer */}
          <div className="lg:col-span-2 space-y-6">
            <PredictionsCard 
              predictions={dashboardData?.predictions}
              isPremium={isPremium}
              gameweek={selectedGameweek}
            />
            
            <OptimizerCard
              squad={dashboardData?.squad}
              recommendations={dashboardData?.optimizerRecommendations}
              isPremium={isPremium}
              isElite={isElite}
            />
            
            {isPremium && (
              <WeeklyInsightsCard
                insights={dashboardData?.weeklyInsights}
                gameweek={selectedGameweek}
              />
            )}
          </div>

          {/* Right Column - Alerts & Updates */}
          <div className="space-y-6">
            <InjuryAlertsCard
              alerts={dashboardData?.injuryAlerts}
              isPremium={isPremium}
            />
            
            <PriceChangesCard
              predictions={dashboardData?.pricePredictions}
              isPremium={isPremium}
            />
            
            {isPremium && (
              <SentimentCard
                sentimentData={dashboardData?.sentimentAnalysis}
              />
            )}
            
            {isElite && (
              <MiniLeagueCard
                leagues={dashboardData?.miniLeagues}
              />
            )}
          </div>
        </div>

        {/* Premium Features Showcase for Free Users */}
        {user.tier === 'free' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-12 bg-gradient-to-r from-purple-600 to-blue-600 rounded-2xl p-8 text-white"
          >
            <h2 className="text-2xl font-bold mb-4">
              Unlock Premium Features 🚀
            </h2>
            <div className="grid md:grid-cols-3 gap-6">
              <FeatureCard
                title="Advanced AI Predictions"
                description="ML-powered predictions with 85%+ accuracy"
                icon={<SparklesIcon className="h-8 w-8" />}
              />
              <FeatureCard
                title="Sentiment Analysis"
                description="Real-time news and injury tracking"
                icon={<ShieldCheckIcon className="h-8 w-8" />}
              />
              <FeatureCard
                title="Price Change Alerts"
                description="Never miss a price rise or fall"
                icon={<BellAlertIcon className="h-8 w-8" />}
              />
            </div>
            <div className="mt-6 flex gap-4">
              <a href="/pricing" className="btn-white">
                View Plans
              </a>
              <a href="/pricing#premium" className="btn-secondary">
                Start Free Trial
              </a>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}

// Metric Card Component
function MetricCard({ title, value, change, subtitle, icon, color }: any) {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-300',
    green: 'bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-300',
    purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900 dark:text-purple-300',
    orange: 'bg-orange-100 text-orange-600 dark:bg-orange-900 dark:text-orange-300',
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-600 dark:text-gray-400">{title}</span>
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
      <div className="flex items-end justify-between">
        <div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {value}
          </p>
          {subtitle && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {subtitle}
            </p>
          )}
        </div>
        {change !== undefined && change !== null && (
          <div className={`flex items-center ${change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {change >= 0 ? (
              <ArrowUpIcon className="h-4 w-4 mr-1" />
            ) : (
              <ArrowDownIcon className="h-4 w-4 mr-1" />
            )}
            <span className="text-sm font-medium">
              {Math.abs(change)}%
            </span>
          </div>
        )}
      </div>
    </motion.div>
  )
}

// Feature Card for Premium Showcase
function FeatureCard({ title, description, icon }: any) {
  return (
    <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6">
      <div className="mb-4">{icon}</div>
      <h3 className="font-semibold mb-2">{title}</h3>
      <p className="text-sm text-white/80">{description}</p>
    </div>
  )
}

// Sentiment Analysis Card (Premium)
function SentimentCard({ sentimentData }: any) {
  if (!sentimentData) return null

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700"
    >
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        Sentiment Analysis 🎯
      </h3>
      <div className="space-y-3">
        {sentimentData.topPlayers?.map((player: any) => (
          <div key={player.id} className="flex justify-between items-center">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">
                {player.name}
              </p>
              <p className="text-xs text-gray-500">
                {player.team}
              </p>
            </div>
            <div className={`px-2 py-1 rounded-full text-xs font-medium ${
              player.sentiment === 'positive' ? 'bg-green-100 text-green-700' :
              player.sentiment === 'negative' ? 'bg-red-100 text-red-700' :
              'bg-gray-100 text-gray-700'
            }`}>
              {player.sentiment}
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  )
}

// Mini-League Analytics (Elite)
function MiniLeagueCard({ leagues }: any) {
  if (!leagues) return null

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700"
    >
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        Mini-League Analytics 🏆
      </h3>
      <div className="space-y-3">
        {leagues.map((league: any) => (
          <div key={league.id} className="border-b border-gray-200 dark:border-gray-700 pb-3">
            <div className="flex justify-between items-start">
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {league.name}
                </p>
                <p className="text-sm text-gray-500">
                  Rank: {league.rank}/{league.totalPlayers}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {league.points} pts
                </p>
                <p className="text-xs text-gray-500">
                  Gap: {league.gapToFirst}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  )
}