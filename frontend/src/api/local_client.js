// Local API client for development
const API_BASE_URL = 'http://localhost:8000'

class LocalApiClient {
  constructor() {
    this.token = 'mock_local_token' // Mock token for local development
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`
    
    const config = {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`,
        ...options.headers
      },
      ...options
    }

    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`)
      }

      const data = await response.json()
      return data
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error)
      throw error
    }
  }

  // Auth endpoints
  async login(credentials) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials)
    })
  }

  async getCurrentUser() {
    return this.request('/auth/me')
  }

  // Dashboard data
  async getDashboardData(gameweek = null) {
    const params = gameweek ? `?gameweek=${gameweek}` : ''
    return this.request(`/dashboard${params}`)
  }

  // Predictions
  async getPredictions(gameweek = null) {
    const params = gameweek ? `?gameweek=${gameweek}` : ''
    return this.request(`/predictions${params}`)
  }

  // Team optimizer
  async optimizeSquad(constraints = {}) {
    return this.request('/optimizer/squad', {
      method: 'POST',
      body: JSON.stringify(constraints)
    })
  }

  // Alerts
  async getAlerts(unreadOnly = false) {
    const params = unreadOnly ? '?unread_only=true' : ''
    return this.request(`/alerts${params}`)
  }

  async markAlertAsRead(alertId) {
    return this.request(`/alerts/${alertId}/read`, {
      method: 'POST'
    })
  }

  // Price changes
  async getPriceChanges() {
    return this.request('/price-changes')
  }

  // Sentiment analysis
  async getSentimentAnalysis() {
    return this.request('/sentiment')
  }

  // Player details
  async getPlayerDetails(playerId) {
    return this.request(`/players/${playerId}`)
  }

  // Live updates
  async getLiveUpdates() {
    return this.request('/live')
  }

  // Utility methods
  setToken(token) {
    this.token = token
  }

  clearToken() {
    this.token = null
  }
}

// Create singleton instance
const localApiClient = new LocalApiClient()

export default localApiClient