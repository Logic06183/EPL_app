from typing import Optional, Dict, List
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
import os
from sqlalchemy.orm import Session
import stripe
import logging

logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# User tiers
class UserTier:
    FREE = "free"
    BASIC = "basic"  # £4.99/month
    PREMIUM = "premium"  # £9.99/month
    ELITE = "elite"  # £19.99/month

class UserFeatures:
    TIERS = {
        UserTier.FREE: {
            "name": "Free",
            "price": 0,
            "features": {
                "predictions_per_week": 5,
                "basic_optimizer": True,
                "advanced_optimizer": False,
                "sentiment_analysis": False,
                "injury_alerts": False,
                "price_alerts": False,
                "api_calls_per_day": 10,
                "historical_data_days": 7,
                "custom_leagues": 0,
                "email_alerts": False,
                "priority_updates": False
            }
        },
        UserTier.BASIC: {
            "name": "Basic",
            "price": 4.99,
            "stripe_price_id": "price_basic_monthly",
            "features": {
                "predictions_per_week": 50,
                "basic_optimizer": True,
                "advanced_optimizer": True,
                "sentiment_analysis": False,
                "injury_alerts": True,
                "price_alerts": True,
                "api_calls_per_day": 100,
                "historical_data_days": 30,
                "custom_leagues": 3,
                "email_alerts": True,
                "priority_updates": False
            }
        },
        UserTier.PREMIUM: {
            "name": "Premium",
            "price": 9.99,
            "stripe_price_id": "price_premium_monthly",
            "features": {
                "predictions_per_week": -1,  # Unlimited
                "basic_optimizer": True,
                "advanced_optimizer": True,
                "sentiment_analysis": True,
                "injury_alerts": True,
                "price_alerts": True,
                "api_calls_per_day": 500,
                "historical_data_days": 90,
                "custom_leagues": 10,
                "email_alerts": True,
                "priority_updates": True,
                "whatsapp_alerts": True,
                "differential_finder": True,
                "captain_predictor": True
            }
        },
        UserTier.ELITE: {
            "name": "Elite",
            "price": 19.99,
            "stripe_price_id": "price_elite_monthly",
            "features": {
                "predictions_per_week": -1,  # Unlimited
                "basic_optimizer": True,
                "advanced_optimizer": True,
                "sentiment_analysis": True,
                "injury_alerts": True,
                "price_alerts": True,
                "api_calls_per_day": -1,  # Unlimited
                "historical_data_days": -1,  # All available
                "custom_leagues": -1,  # Unlimited
                "email_alerts": True,
                "priority_updates": True,
                "whatsapp_alerts": True,
                "differential_finder": True,
                "captain_predictor": True,
                "ai_transfer_advisor": True,
                "mini_league_analytics": True,
                "custom_notifications": True,
                "api_access": True,
                "discord_bot": True
            }
        }
    }

# Pydantic models
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    fpl_team_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    id: int
    hashed_password: str
    tier: str = UserTier.FREE
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_end_date: Optional[datetime] = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []

class SubscriptionUpdate(BaseModel):
    tier: str
    payment_method_id: Optional[str] = None

class AuthManager:
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    async def get_user(self, username: str) -> Optional[UserInDB]:
        # This would query your database
        # For now, returning a mock user
        return None
    
    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        # Query database by email
        return None
    
    async def create_user(self, user: UserCreate) -> UserInDB:
        """Create a new user with Stripe customer"""
        try:
            # Check if user exists
            existing_user = await self.get_user_by_email(user.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Create Stripe customer
            stripe_customer = stripe.Customer.create(
                email=user.email,
                name=user.full_name or user.username,
                metadata={
                    "username": user.username,
                    "fpl_team_id": str(user.fpl_team_id) if user.fpl_team_id else ""
                }
            )
            
            # Create user in database
            db_user = UserInDB(
                **user.dict(),
                id=0,  # Auto-increment in DB
                hashed_password=self.get_password_hash(user.password),
                tier=UserTier.FREE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                stripe_customer_id=stripe_customer.id
            )
            
            # Save to database (implement this)
            # self.db.add(db_user)
            # self.db.commit()
            
            return db_user
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating customer account"
            )
    
    async def authenticate_user(self, username: str, password: str) -> Optional[UserInDB]:
        user = await self.get_user(username)
        if not user:
            user = await self.get_user_by_email(username)  # Allow email login
        
        if not user or not self.verify_password(password, user.hashed_password):
            return None
        
        return user
    
    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> UserInDB:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            token_type: str = payload.get("type")
            
            if username is None or token_type != "access":
                raise credentials_exception
                
            token_data = TokenData(username=username)
            
        except JWTError:
            raise credentials_exception
        
        user = await self.get_user(username=token_data.username)
        if user is None:
            raise credentials_exception
        
        return user
    
    def check_feature_access(self, user: UserInDB, feature: str) -> bool:
        """Check if user has access to a specific feature"""
        user_features = UserFeatures.TIERS.get(user.tier, {}).get("features", {})
        
        # Check if feature exists and user has access
        if feature not in user_features:
            return False
        
        feature_value = user_features[feature]
        
        # -1 means unlimited, any positive number or True means allowed
        return feature_value == True or feature_value == -1 or (isinstance(feature_value, int) and feature_value > 0)
    
    def get_feature_limit(self, user: UserInDB, feature: str) -> int:
        """Get the limit for a specific feature"""
        user_features = UserFeatures.TIERS.get(user.tier, {}).get("features", {})
        feature_value = user_features.get(feature, 0)
        
        if isinstance(feature_value, bool):
            return 1 if feature_value else 0
        
        return feature_value
    
    async def update_subscription(self, user: UserInDB, subscription: SubscriptionUpdate) -> Dict:
        """Update user subscription tier"""
        try:
            # Validate tier
            if subscription.tier not in [UserTier.FREE, UserTier.BASIC, UserTier.PREMIUM, UserTier.ELITE]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid subscription tier"
                )
            
            # Handle downgrade to free
            if subscription.tier == UserTier.FREE:
                if user.stripe_subscription_id:
                    # Cancel Stripe subscription
                    stripe.Subscription.delete(user.stripe_subscription_id)
                
                # Update user in database
                user.tier = UserTier.FREE
                user.stripe_subscription_id = None
                user.subscription_end_date = None
                
                return {"message": "Subscription cancelled", "new_tier": UserTier.FREE}
            
            # Handle paid tiers
            tier_info = UserFeatures.TIERS[subscription.tier]
            
            # Create or update Stripe subscription
            if user.stripe_subscription_id:
                # Update existing subscription
                subscription_obj = stripe.Subscription.retrieve(user.stripe_subscription_id)
                stripe.Subscription.modify(
                    user.stripe_subscription_id,
                    items=[{
                        'id': subscription_obj['items']['data'][0].id,
                        'price': tier_info['stripe_price_id']
                    }]
                )
            else:
                # Create new subscription
                if not subscription.payment_method_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Payment method required for paid subscription"
                    )
                
                # Attach payment method to customer
                stripe.PaymentMethod.attach(
                    subscription.payment_method_id,
                    customer=user.stripe_customer_id
                )
                
                # Set as default payment method
                stripe.Customer.modify(
                    user.stripe_customer_id,
                    invoice_settings={
                        'default_payment_method': subscription.payment_method_id
                    }
                )
                
                # Create subscription
                stripe_subscription = stripe.Subscription.create(
                    customer=user.stripe_customer_id,
                    items=[{'price': tier_info['stripe_price_id']}],
                    expand=['latest_invoice.payment_intent']
                )
                
                user.stripe_subscription_id = stripe_subscription.id
            
            # Update user tier
            user.tier = subscription.tier
            user.subscription_end_date = datetime.utcnow() + timedelta(days=30)
            user.updated_at = datetime.utcnow()
            
            # Save to database
            # self.db.commit()
            
            return {
                "message": "Subscription updated successfully",
                "new_tier": subscription.tier,
                "features": tier_info['features']
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error updating subscription: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing subscription update"
            )
    
    async def track_api_usage(self, user: UserInDB, endpoint: str) -> bool:
        """Track and limit API usage based on tier"""
        # Get daily limit
        daily_limit = self.get_feature_limit(user, "api_calls_per_day")
        
        if daily_limit == -1:  # Unlimited
            return True
        
        # Check Redis or database for usage count
        # This is a simplified example
        usage_key = f"api_usage:{user.id}:{datetime.utcnow().date()}"
        
        # Increment usage count (implement with Redis)
        # current_usage = redis.incr(usage_key)
        # redis.expire(usage_key, 86400)  # Expire after 24 hours
        
        current_usage = 0  # Placeholder
        
        if current_usage > daily_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"API rate limit exceeded. Upgrade to {UserTier.PREMIUM} for more requests."
            )
        
        return True