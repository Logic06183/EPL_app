'use client'

import { Star, DollarSign, TrendingUp, Users } from 'lucide-react'

export default function PlayerCard({ player, rank, showRank = true }) {
  const getPositionColor = (position) => {
    const colors = {
      'GK': 'bg-yellow-500',
      'DEF': 'bg-green-500', 
      'MID': 'bg-blue-500',
      'FWD': 'bg-red-500'
    }
    return colors[position] || 'bg-gray-500'
  }

  const getPositionGradient = (position) => {
    const gradients = {
      'GK': 'from-yellow-400 to-orange-500',
      'DEF': 'from-green-400 to-emerald-600',
      'MID': 'from-blue-400 to-indigo-600', 
      'FWD': 'from-red-400 to-rose-600'
    }
    return gradients[position] || 'from-gray-400 to-gray-600'
  }

  const getValueRating = () => {
    const value = player.predicted_points / player.price
    if (value >= 2.0) return { rating: 'Excellent', color: 'text-green-400' }
    if (value >= 1.5) return { rating: 'Good', color: 'text-blue-400' }
    if (value >= 1.0) return { rating: 'Fair', color: 'text-yellow-400' }
    return { rating: 'Poor', color: 'text-red-400' }
  }

  const valueRating = getValueRating()

  return (
    <div className="glass rounded-2xl p-4 card-hover group">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        {showRank && (
          <div className={`w-8 h-8 rounded-full bg-gradient-to-r ${getPositionGradient(player.position)} flex items-center justify-center text-white font-bold text-sm shadow-lg`}>
            {rank}
          </div>
        )}
        <div className={`px-3 py-1 rounded-full text-xs font-semibold ${getPositionColor(player.position)} text-white shadow-sm`}>
          {player.position}
        </div>
      </div>

      {/* Player Info */}
      <div className="mb-4">
        <h4 className="text-lg font-bold text-white group-hover:text-blue-300 transition-colors duration-300">
          {player.player_name}
        </h4>
        <p className="text-white/70 text-sm">{player.team}</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-white/10 rounded-lg p-3 backdrop-blur-sm">
          <div className="flex items-center gap-1 text-white/70 text-xs mb-1">
            <Star className="w-3 h-3" />
            Points
          </div>
          <div className="text-xl font-bold text-white">{player.predicted_points}</div>
        </div>
        
        <div className="bg-white/10 rounded-lg p-3 backdrop-blur-sm">
          <div className="flex items-center gap-1 text-white/70 text-xs mb-1">
            <DollarSign className="w-3 h-3" />
            Price
          </div>
          <div className="text-xl font-bold text-green-400">£{player.price}m</div>
        </div>
      </div>

      {/* Value Rating */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-1 text-white/70">
          <TrendingUp className="w-3 h-3" />
          Value
        </div>
        <span className={`font-semibold ${valueRating.color}`}>
          {valueRating.rating}
        </span>
      </div>

      {/* Confidence Indicator */}
      {player.confidence && (
        <div className="mt-3 pt-3 border-t border-white/20">
          <div className="flex items-center justify-between text-xs">
            <span className="text-white/70">Confidence</span>
            <div className="flex items-center gap-1">
              <div className="w-16 h-1.5 bg-white/20 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-blue-400 to-purple-500 transition-all duration-500"
                  style={{ width: `${player.confidence * 100}%` }}
                />
              </div>
              <span className="text-white/90 font-medium">
                {Math.round(player.confidence * 100)}%
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Hover Effect Overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/0 to-purple-500/0 group-hover:from-blue-500/10 group-hover:to-purple-500/10 rounded-2xl transition-all duration-300 pointer-events-none" />
    </div>
  )
}