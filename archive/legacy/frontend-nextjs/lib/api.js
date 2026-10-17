/**
 * API Client for FPL AI Pro Backend
 * Centralized API communication with the new backend
 */

// Get API URL from environment or fallback
// Next.js replaces process.env.NEXT_PUBLIC_* at build time
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Make a GET request to the API
 */
async function get(endpoint, params = {}, options = {}) {
  const url = new URL(`${API_URL}${endpoint}`)

  // Add query parameters
  Object.keys(params).forEach(key => {
    if (params[key] !== null && params[key] !== undefined) {
      url.searchParams.append(key, params[key])
    }
  })

  const controller = new AbortController()
  const timeout = options.timeout || 30000 // 30s default
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`)
    }

    return await response.json()
  } catch (error) {
    clearTimeout(timeoutId)
    if (error.name === 'AbortError') {
      throw new Error('Request timeout')
    }
    throw error
  }
}

/**
 * Make a POST request to the API
 */
async function post(endpoint, body = {}, options = {}) {
  const controller = new AbortController()
  const timeout = options.timeout || 30000
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`)
    }

    return await response.json()
  } catch (error) {
    clearTimeout(timeoutId)
    if (error.name === 'AbortError') {
      throw new Error('Request timeout')
    }
    throw error
  }
}

// ============================================================================
// Health & Status
// ============================================================================

export const checkHealth = async () => {
  return await get('/health')
}

export const getApiInfo = async () => {
  return await get('/')
}

// ============================================================================
// Players
// ============================================================================

export const getAllPlayers = async (filters = {}) => {
  return await get('/api/players', filters)
}

export const getPlayerById = async (playerId) => {
  return await get(`/api/players/${playerId}`)
}

export const searchPlayers = async (query, limit = 10) => {
  return await get(`/api/players/search/${query}`, { limit })
}

export const getPlayerHistory = async (playerId) => {
  return await get(`/api/players/${playerId}/history`)
}

// ============================================================================
// Predictions
// ============================================================================

export const getPredictions = async (options = {}) => {
  const {
    topN = 50,
    model = 'ensemble',
    position = null,
    maxPrice = null,
  } = options

  return await get('/api/players/predictions', {
    top_n: topN,
    model,
    position,
    max_price: maxPrice,
  })
}

export const getEnhancedPredictions = async (options = {}) => {
  const {
    topN = 20,
    model = 'ensemble',
    useGemini = true,
  } = options

  return await get('/api/players/predictions/enhanced', {
    top_n: topN,
    model,
    use_gemini: useGemini,
  }, {
    timeout: 45000, // Gemini AI can take longer
  })
}

export const getPlayerPrediction = async (playerId, options = {}) => {
  const { model = 'ensemble', useGemini = false } = options

  return await get(`/api/players/predictions/${playerId}`, {
    model,
    use_gemini: useGemini,
  })
}

export const getModelInfo = async () => {
  return await get('/api/predictions/models/info')
}

export const retrainModels = async () => {
  return await post('/api/predictions/models/retrain')
}

// ============================================================================
// Teams
// ============================================================================

export const optimizeTeam = async (options = {}) => {
  const {
    budget = 100.0,
    excludedPlayers = [],
    preferredPlayers = [],
    formation = null,
    optimizeFor = 'points',
  } = options

  return await post('/api/teams/optimize', {
    budget,
    excluded_players: excludedPlayers,
    preferred_players: preferredPlayers,
    formation,
    optimize_for: optimizeFor,
  })
}

export const getTransferSuggestions = async (options = {}) => {
  const {
    currentTeam = [],
    budget = 0,
    freeTransfers = 1,
    maxTransfers = 2,
    gameweek = null,
  } = options

  return await post('/api/teams/transfers', {
    current_team: currentTeam,
    budget,
    free_transfers: freeTransfers,
    max_transfers: maxTransfers,
    gameweek,
  })
}

export const getFormations = async () => {
  return await get('/api/teams/formations')
}

// ============================================================================
// Payments
// ============================================================================

export const getSubscriptionPlans = async () => {
  return await get('/api/payments/plans')
}

export const initializePayment = async (planId, email, callbackUrl) => {
  return await post('/api/payments/initialize', {
    plan_id: planId,
    email,
    callback_url: callbackUrl,
  })
}

export const verifyPayment = async (reference) => {
  return await post(`/api/payments/verify/${reference}`)
}

export const checkSubscriptionStatus = async (email) => {
  return await get('/api/payments/subscription/status', { email })
}

// ============================================================================
// Helper utilities
// ============================================================================

export const handleApiError = (error) => {
  console.error('API Error:', error)

  if (error.message === 'Request timeout') {
    return 'Request timed out. Please try again.'
  }

  if (error.message.includes('Failed to fetch')) {
    return 'Unable to connect to server. Please check your connection.'
  }

  return error.message || 'An unexpected error occurred'
}

// Export API_URL for components that need it
export { API_URL }
