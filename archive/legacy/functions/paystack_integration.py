#!/usr/bin/env python3
"""
PayStack Payment Integration for South Africa and International Markets
Handles subscriptions, one-time payments, and recurring billing
"""

import os
import hashlib
import hmac
import json
import httpx
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, Header
from pydantic import BaseModel
import asyncio

logger = logging.getLogger(__name__)

class PayStackConfig:
    """PayStack configuration for payments"""
    SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
    PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY", "")
    WEBHOOK_SECRET = os.getenv("PAYSTACK_WEBHOOK_SECRET", "")
    BASE_URL = "https://api.paystack.co"
    
    # Subscription Plans (in cents/kobo for ZAR)
    PLANS = {
        "basic": {
            "name": "FPL AI Basic",
            "amount": 9999,  # R99.99
            "currency": "ZAR",
            "interval": "monthly",
            "description": "Basic predictions and analytics",
            "features": [
                "Top 20 player predictions",
                "Basic squad analysis",
                "Weekly email reports",
                "Community access"
            ]
        },
        "pro": {
            "name": "FPL AI Pro",
            "amount": 19999,  # R199.99
            "currency": "ZAR",
            "interval": "monthly",
            "description": "Advanced AI predictions and tools",
            "features": [
                "Unlimited predictions",
                "AI-powered insights",
                "Squad optimizer",
                "Transfer suggestions",
                "Priority support",
                "Live match predictions"
            ]
        },
        "premium": {
            "name": "FPL AI Premium",
            "amount": 39999,  # R399.99
            "currency": "ZAR",
            "interval": "monthly",
            "description": "Professional FPL management suite",
            "features": [
                "Everything in Pro",
                "Custom ML models",
                "API access",
                "League analytics",
                "WhatsApp alerts",
                "1-on-1 consultation"
            ]
        }
    }

class PayStackAPI:
    """PayStack API client for payment processing"""
    
    def __init__(self):
        self.secret_key = PayStackConfig.SECRET_KEY
        self.public_key = PayStackConfig.PUBLIC_KEY
        self.base_url = PayStackConfig.BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    async def create_plan(self, plan_code: str) -> Dict:
        """Create or update subscription plan on PayStack"""
        plan = PayStackConfig.PLANS.get(plan_code)
        if not plan:
            raise ValueError(f"Invalid plan code: {plan_code}")
        
        url = f"{self.base_url}/plan"
        data = {
            "name": plan["name"],
            "amount": plan["amount"],
            "interval": plan["interval"],
            "currency": plan["currency"],
            "description": plan["description"]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=self.headers)
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(f"Failed to create plan: {response.text}")
                return None
    
    async def initialize_transaction(
        self, 
        email: str, 
        amount: int, 
        plan: Optional[str] = None,
        metadata: Dict = None
    ) -> Dict:
        """Initialize a PayStack transaction"""
        url = f"{self.base_url}/transaction/initialize"
        
        data = {
            "email": email,
            "amount": amount,
            "currency": "ZAR",
            "channels": ["card", "eft", "bank", "qr", "mobile_money"],
            "metadata": metadata or {}
        }
        
        if plan:
            data["plan"] = plan
            data["metadata"]["plan_code"] = plan
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=self.headers)
            if response.status_code == 200:
                return response.json()["data"]
            else:
                raise HTTPException(status_code=400, detail="Failed to initialize transaction")
    
    async def verify_transaction(self, reference: str) -> Dict:
        """Verify a PayStack transaction"""
        url = f"{self.base_url}/transaction/verify/{reference}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()["data"]
            else:
                return None
    
    async def create_subscription(self, customer: str, plan: str) -> Dict:
        """Create a subscription for a customer"""
        url = f"{self.base_url}/subscription"
        
        data = {
            "customer": customer,
            "plan": plan
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=self.headers)
            if response.status_code == 200:
                return response.json()["data"]
            else:
                raise HTTPException(status_code=400, detail="Failed to create subscription")
    
    async def cancel_subscription(self, code: str) -> bool:
        """Cancel a subscription"""
        url = f"{self.base_url}/subscription/disable"
        
        data = {
            "code": code,
            "token": code
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=self.headers)
            return response.status_code == 200
    
    def verify_webhook(self, signature: str, body: bytes) -> bool:
        """Verify PayStack webhook signature"""
        expected = hmac.new(
            bytes(PayStackConfig.WEBHOOK_SECRET, 'utf-8'),
            body,
            hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


# Request/Response Models
class PaymentRequest(BaseModel):
    email: str
    plan_code: str
    return_url: Optional[str] = None

class WebhookEvent(BaseModel):
    event: str
    data: Dict


def add_paystack_routes(app: FastAPI):
    """Add PayStack payment routes to FastAPI app"""
    
    paystack = PayStackAPI()
    
    @app.get("/api/payment/plans")
    async def get_payment_plans():
        """Get available subscription plans with international pricing"""
        plans = {}
        for code, plan in PayStackConfig.PLANS.items():
            # Convert to multiple currencies for display
            zar_amount = plan["amount"] / 100
            usd_amount = zar_amount / 18  # Approximate conversion
            gbp_amount = zar_amount / 23  # Approximate conversion
            
            plans[code] = {
                "name": plan["name"],
                "prices": {
                    "ZAR": f"R{zar_amount:.2f}",
                    "USD": f"${usd_amount:.2f}",
                    "GBP": f"£{gbp_amount:.2f}"
                },
                "interval": plan["interval"],
                "features": plan["features"],
                "description": plan["description"],
                "popular": code == "pro"
            }
        
        return {
            "plans": plans,
            "payment_methods": ["Card", "EFT", "Bank Transfer", "QR Code", "Mobile Money"],
            "secure": True,
            "provider": "Secure Payment Processing"
        }
    
    @app.post("/api/payment/initialize")
    async def initialize_payment(request: PaymentRequest):
        """Initialize payment with PayStack"""
        try:
            plan = PayStackConfig.PLANS.get(request.plan_code)
            if not plan:
                raise HTTPException(status_code=400, detail="Invalid plan selected")
            
            # Initialize transaction
            transaction = await paystack.initialize_transaction(
                email=request.email,
                amount=plan["amount"],
                plan=request.plan_code,
                metadata={
                    "plan_name": plan["name"],
                    "features": plan["features"]
                }
            )
            
            return {
                "payment_url": transaction["authorization_url"],
                "access_code": transaction["access_code"],
                "reference": transaction["reference"],
                "amount": plan["amount"],
                "currency": plan["currency"]
            }
            
        except Exception as e:
            logger.error(f"Payment initialization failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Payment initialization failed")
    
    @app.get("/api/payment/verify/{reference}")
    async def verify_payment(reference: str):
        """Verify payment status"""
        try:
            transaction = await paystack.verify_transaction(reference)
            if transaction:
                return {
                    "status": transaction["status"],
                    "amount": transaction["amount"],
                    "currency": transaction["currency"],
                    "customer": transaction["customer"],
                    "paid_at": transaction.get("paid_at"),
                    "success": transaction["status"] == "success"
                }
            else:
                raise HTTPException(status_code=404, detail="Transaction not found")
                
        except Exception as e:
            logger.error(f"Payment verification failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Verification failed")
    
    @app.post("/api/payment/webhook")
    async def handle_webhook(
        request: Request,
        x_paystack_signature: str = Header(None)
    ):
        """Handle PayStack webhooks"""
        try:
            body = await request.body()
            
            # Verify webhook signature
            if not paystack.verify_webhook(x_paystack_signature, body):
                raise HTTPException(status_code=401, detail="Invalid signature")
            
            # Parse webhook data
            data = json.loads(body)
            event = data.get("event")
            event_data = data.get("data", {})
            
            # Handle different events
            if event == "charge.success":
                # Payment successful
                logger.info(f"Payment successful: {event_data.get('reference')}")
                # Update user subscription in database
                
            elif event == "subscription.create":
                # Subscription created
                logger.info(f"Subscription created: {event_data.get('subscription_code')}")
                
            elif event == "subscription.disable":
                # Subscription cancelled
                logger.info(f"Subscription cancelled: {event_data.get('subscription_code')}")
            
            return {"status": "ok"}
            
        except Exception as e:
            logger.error(f"Webhook processing failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Webhook processing failed")
    
    @app.post("/api/payment/cancel-subscription")
    async def cancel_subscription(subscription_code: str):
        """Cancel a subscription"""
        try:
            success = await paystack.cancel_subscription(subscription_code)
            if success:
                return {"status": "cancelled", "message": "Subscription cancelled successfully"}
            else:
                raise HTTPException(status_code=400, detail="Failed to cancel subscription")
                
        except Exception as e:
            logger.error(f"Subscription cancellation failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Cancellation failed")


# Test function
async def test_paystack():
    """Test PayStack integration"""
    api = PayStackAPI()
    
    # Test with dummy data (won't work without real keys)
    try:
        result = await api.initialize_transaction(
            email="test@example.com",
            amount=9999,
            plan="basic"
        )
        print("PayStack test result:", result)
    except Exception as e:
        print(f"PayStack test failed (expected without real keys): {e}")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_paystack())