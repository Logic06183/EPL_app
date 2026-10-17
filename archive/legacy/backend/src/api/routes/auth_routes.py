from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

from jose import JWTError, jwt

from ...auth.auth_manager import (
    AuthManager, UserCreate, Token, SubscriptionUpdate,
    UserInDB, ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY, ALGORITHM, UserTier, UserFeatures
)
from ...database.models import User
from ..dependencies import get_db, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=Dict)
async def register(
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    try:
        auth_manager = AuthManager(db)
        
        # Create user
        new_user = await auth_manager.create_user(user)
        
        # Send verification email in background
        background_tasks.add_task(send_verification_email, new_user.email, new_user.username)
        
        # Create tokens
        access_token = auth_manager.create_access_token(
            data={"sub": new_user.username}
        )
        refresh_token = auth_manager.create_refresh_token(
            data={"sub": new_user.username}
        )
        
        return {
            "message": "User created successfully",
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "username": new_user.username,
                "tier": new_user.tier
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login with username/email and password"""
    auth_manager = AuthManager(db)
    
    user = await auth_manager.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Create tokens
    access_token = auth_manager.create_access_token(
        data={"sub": user.username}
    )
    refresh_token = auth_manager.create_refresh_token(
        data={"sub": user.username}
    )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    try:
        auth_manager = AuthManager(db)
        
        # Verify refresh token
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if username is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user
        user = await auth_manager.get_user(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Create new tokens
        new_access_token = auth_manager.create_access_token(
            data={"sub": user.username}
        )
        new_refresh_token = auth_manager.create_refresh_token(
            data={"sub": user.username}
        )
        
        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token
        )
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.get("/me", response_model=Dict)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile"""
    auth_manager = AuthManager(db)
    
    # Get user features based on tier
    features = UserFeatures.TIERS[current_user.tier]["features"]
    
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "username": current_user.username,
            "full_name": current_user.full_name,
            "fpl_team_id": current_user.fpl_team_id,
            "tier": current_user.tier,
            "is_verified": current_user.is_verified,
            "created_at": current_user.created_at,
            "subscription_end_date": current_user.subscription_end_date
        },
        "features": features,
        "usage": {
            "api_calls_today": await get_api_usage_today(current_user.id, db),
            "predictions_this_week": await get_predictions_this_week(current_user.id, db)
        }
    }

@router.post("/subscription/update", response_model=Dict)
async def update_subscription(
    subscription: SubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user subscription tier"""
    auth_manager = AuthManager(db)
    
    result = await auth_manager.update_subscription(current_user, subscription)
    
    return result

@router.post("/subscription/cancel", response_model=Dict)
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel current subscription"""
    auth_manager = AuthManager(db)
    
    # Downgrade to free tier
    subscription = SubscriptionUpdate(tier=UserTier.FREE)
    result = await auth_manager.update_subscription(current_user, subscription)
    
    return result

@router.post("/verify-email/{token}", response_model=Dict)
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
):
    """Verify user email with token"""
    # Verify the token and activate user
    user = db.query(User).filter(User.verification_token == token).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid verification token"
        )
    
    user.is_verified = True
    user.verification_token = None
    db.commit()
    
    return {"message": "Email verified successfully"}

@router.post("/reset-password", response_model=Dict)
async def request_password_reset(
    email: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Request password reset email"""
    user = db.query(User).filter(User.email == email).first()
    
    if user:
        # Generate reset token
        reset_token = generate_reset_token()
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        
        # Send reset email
        background_tasks.add_task(send_password_reset_email, email, reset_token)
    
    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a reset link has been sent"}

@router.post("/reset-password/{token}", response_model=Dict)
async def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """Reset password with token"""
    user = db.query(User).filter(
        User.reset_token == token,
        User.reset_token_expires > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired reset token"
        )
    
    # Update password
    auth_manager = AuthManager(db)
    user.hashed_password = auth_manager.get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    
    return {"message": "Password reset successfully"}

# Helper functions
async def send_verification_email(email: str, username: str):
    """Send verification email to user"""
    # Implement email sending logic
    logger.info(f"Sending verification email to {email}")

async def send_password_reset_email(email: str, token: str):
    """Send password reset email"""
    # Implement email sending logic
    logger.info(f"Sending password reset email to {email}")

async def get_api_usage_today(user_id: int, db: Session) -> int:
    """Get API usage count for today"""
    from datetime import date
    from ...database.models import ApiUsage
    
    today = date.today()
    usage = db.query(ApiUsage).filter(
        ApiUsage.user_id == user_id,
        ApiUsage.date >= today
    ).count()
    
    return usage

async def get_predictions_this_week(user_id: int, db: Session) -> int:
    """Get prediction count for this week"""
    from datetime import datetime, timedelta
    from ...database.models import UserPrediction
    
    week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    
    count = db.query(UserPrediction).filter(
        UserPrediction.user_id == user_id,
        UserPrediction.created_at >= week_start
    ).count()
    
    return count

def generate_reset_token() -> str:
    """Generate a secure reset token"""
    import secrets
    return secrets.token_urlsafe(32)