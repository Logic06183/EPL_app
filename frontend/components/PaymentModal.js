'use client'

import { useState } from 'react'
import { X, Crown, Check, CreditCard, DollarSign } from 'lucide-react'

const SUBSCRIPTION_PLANS = {
  basic: {
    name: "FPL AI Basic",
    prices: { ZAR: "R99.99", USD: "$5.50", GBP: "£4.30" },
    interval: "month",
    features: [
      "Top 20 player predictions",
      "Basic squad analysis",
      "Weekly email reports",
      "Community access"
    ],
    popular: false,
    color: "from-blue-500 to-blue-600"
  },
  pro: {
    name: "FPL AI Pro",
    prices: { ZAR: "R199.99", USD: "$11.00", GBP: "£8.70" },
    interval: "month",
    features: [
      "Unlimited predictions",
      "AI-powered insights",
      "Squad optimizer",
      "Transfer suggestions",
      "Priority support",
      "Live match predictions"
    ],
    popular: true,
    color: "from-green-500 to-green-600"
  },
  premium: {
    name: "FPL AI Premium",
    prices: { ZAR: "R399.99", USD: "$22.00", GBP: "£17.40" },
    interval: "month",
    features: [
      "Everything in Pro",
      "Custom ML models",
      "API access",
      "League analytics",
      "WhatsApp alerts",
      "1-on-1 consultation"
    ],
    popular: false,
    color: "from-purple-500 to-purple-600"
  }
}

export default function PaymentModal({ isOpen, onClose, selectedPlan = 'pro' }) {
  const [loading, setLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [selectedPlanId, setSelectedPlanId] = useState(selectedPlan)

  if (!isOpen) return null

  const handleSubscription = async (planId) => {
    if (!email.trim()) {
      alert('Please enter your email address')
      return
    }

    setLoading(true)
    
    try {
      // Call PayStack API to initialize payment
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://epl-api-5d4hhzfrfq-uc.a.run.app'}/api/payment/initialize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email,
          plan_code: planId,
          return_url: window.location.origin + '/payment/success'
        }),
      })

      const data = await response.json()
      
      if (data.payment_url) {
        // Redirect to PayStack checkout
        window.location.href = data.payment_url
      } else {
        throw new Error('Failed to initialize payment')
      }
    } catch (error) {
      console.error('Payment error:', error)
      alert('Failed to start payment process. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const formatPrice = (plan, currency = 'ZAR') => {
    return plan.prices[currency] || plan.prices.ZAR
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-2xl max-w-6xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Crown className="w-8 h-8 text-yellow-400" />
              <div>
                <h2 className="text-2xl font-bold text-white">Upgrade to FPL AI Pro</h2>
                <p className="text-gray-400">Unlock advanced features and dominate your league</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <X className="w-6 h-6 text-gray-400" />
            </button>
          </div>
        </div>

        <div className="p-6">
          {/* Email input */}
          <div className="mb-6">
            <label className="block text-white font-medium mb-2">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your.email@example.com"
              className="w-full p-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:border-green-400 focus:ring-2 focus:ring-green-400/20"
              required
            />
          </div>

          {/* Subscription plans */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            {Object.entries(SUBSCRIPTION_PLANS).map(([planId, plan]) => (
              <div
                key={planId}
                className={`relative border-2 rounded-xl p-6 cursor-pointer transition-all ${
                  selectedPlanId === planId
                    ? 'border-green-400 bg-green-400/10'
                    : 'border-gray-600 hover:border-gray-500'
                } ${plan.popular ? 'ring-2 ring-yellow-400/50' : ''}`}
                onClick={() => setSelectedPlanId(planId)}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                    <span className="bg-yellow-400 text-black px-3 py-1 rounded-full text-sm font-bold">
                      Most Popular
                    </span>
                  </div>
                )}

                <div className="text-center mb-4">
                  <h3 className="text-xl font-bold text-white mb-2">{plan.name}</h3>
                  <div className="mb-4">
                    <span className="text-3xl font-bold text-white">
                      {formatPrice(plan)}
                    </span>
                    <span className="text-gray-400">/{plan.interval}</span>
                  </div>
                </div>

                <ul className="space-y-3 mb-6">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="flex items-center gap-2 text-gray-300">
                      <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
                      <span className="text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>

                {selectedPlanId === planId && (
                  <div className="absolute inset-0 border-2 border-green-400 rounded-xl pointer-events-none"></div>
                )}
              </div>
            ))}
          </div>

          {/* Payment info */}
          <div className="bg-gray-800 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2 mb-2">
              <CreditCard className="w-5 h-5 text-blue-400" />
              <span className="text-white font-medium">Secure Payment</span>
            </div>
            <p className="text-gray-400 text-sm">
              Payments processed securely with bank-grade encryption. Multiple payment methods supported. Cancel anytime.
            </p>
          </div>

          {/* International payment options */}
          <div className="bg-blue-900/20 border border-blue-400/30 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="w-5 h-5 text-blue-400" />
              <span className="text-white font-medium">💳 Payment Methods</span>
            </div>
            <p className="text-blue-200 text-sm">
              Card payments, EFT, bank transfers, QR codes, and mobile money supported. International cards welcome.
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex gap-4">
            <button
              onClick={onClose}
              className="flex-1 py-3 px-6 border border-gray-600 text-gray-300 rounded-lg hover:bg-gray-700 transition-colors"
            >
              Maybe Later
            </button>
            <button
              onClick={() => handleSubscription(selectedPlanId)}
              disabled={loading || !email.trim()}
              className={`flex-1 py-3 px-6 rounded-lg font-semibold transition-colors ${
                loading || !email.trim()
                  ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                  : `bg-gradient-to-r ${SUBSCRIPTION_PLANS[selectedPlanId].color} text-white hover:shadow-lg`
              }`}
            >
              {loading ? 'Processing...' : `Subscribe to ${SUBSCRIPTION_PLANS[selectedPlanId].name}`}
            </button>
          </div>

          {/* Trust indicators */}
          <div className="mt-6 text-center">
            <p className="text-gray-500 text-sm">
              🔒 SSL Encrypted • 30-day money-back guarantee • Cancel anytime
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}