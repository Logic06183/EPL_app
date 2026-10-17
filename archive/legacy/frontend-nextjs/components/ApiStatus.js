'use client'

import { CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react'

export default function ApiStatus({ status, onRetry }) {
  const getStatusConfig = () => {
    switch (status) {
      case 'connected':
        return {
          icon: CheckCircle,
          color: 'text-green-400',
          bg: 'bg-green-500/20',
          border: 'border-green-500/30',
          message: 'API Connected',
          description: 'Backend server is running and responsive'
        }
      case 'error':
        return {
          icon: XCircle,
          color: 'text-red-400',
          bg: 'bg-red-500/20',
          border: 'border-red-500/30',
          message: 'API Disconnected',
          description: 'Cannot connect to backend server'
        }
      case 'checking':
      default:
        return {
          icon: AlertCircle,
          color: 'text-yellow-400',
          bg: 'bg-yellow-500/20',
          border: 'border-yellow-500/30',
          message: 'Checking Connection',
          description: 'Verifying backend server status'
        }
    }
  }

  const config = getStatusConfig()
  const Icon = config.icon

  return (
    <div className={`inline-flex items-center gap-3 px-4 py-2 rounded-lg ${config.bg} ${config.border} border mt-4`}>
      <Icon className={`w-4 h-4 ${config.color} ${status === 'checking' ? 'animate-pulse' : ''}`} />
      <div>
        <div className={`text-sm font-medium ${config.color}`}>
          {config.message}
        </div>
        <div className="text-xs text-white/70">
          {config.description}
        </div>
      </div>
      
      {status === 'error' && onRetry && (
        <button
          onClick={onRetry}
          className="ml-2 p-1 hover:bg-white/10 rounded transition-colors"
          title="Retry connection"
        >
          <RefreshCw className="w-3 h-3 text-white/70 hover:text-white" />
        </button>
      )}
    </div>
  )
}