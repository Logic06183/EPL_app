from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    hashed_password = Column(String, nullable=False)
    
    # FPL Integration
    fpl_team_id = Column(Integer, unique=True, nullable=True)
    fpl_team_name = Column(String)
    
    # Subscription
    tier = Column(String, default="free")
    stripe_customer_id = Column(String, unique=True)
    stripe_subscription_id = Column(String, unique=True)
    subscription_end_date = Column(DateTime)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    squads = relationship("UserSquad", back_populates="user", cascade="all, delete-orphan")
    predictions = relationship("UserPrediction", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("UserAlert", back_populates="user", cascade="all, delete-orphan")
    api_usage = relationship("ApiUsage", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", cascade="all, delete-orphan")

class UserSquad(Base):
    __tablename__ = "user_squads"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    gameweek = Column(Integer, nullable=False)
    
    # Squad composition (store as JSON for flexibility)
    players = Column(JSON)  # List of player IDs
    captain_id = Column(Integer)
    vice_captain_id = Column(Integer)
    bench_order = Column(JSON)  # Ordered list of bench player IDs
    
    # Financial
    total_value = Column(Float)
    bank = Column(Float)
    free_transfers = Column(Integer, default=1)
    
    # Performance
    points = Column(Integer)
    gameweek_rank = Column(Integer)
    overall_rank = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="squads")

class UserPrediction(Base):
    __tablename__ = "user_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Prediction details
    gameweek = Column(Integer, nullable=False)
    player_id = Column(Integer, nullable=False)
    predicted_points = Column(Float)
    actual_points = Column(Float)
    
    # Metadata
    prediction_type = Column(String)  # "ml_model", "sentiment_adjusted", "manual"
    confidence_score = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="predictions")

class UserAlert(Base):
    __tablename__ = "user_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Alert details
    alert_type = Column(String)  # "price_rise", "price_fall", "injury", "suspension", etc.
    player_id = Column(Integer)
    player_name = Column(String)
    
    # Content
    title = Column(String)
    message = Column(Text)
    urgency = Column(String)  # "low", "medium", "high", "critical"
    
    # Status
    is_read = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)
    sent_via = Column(JSON)  # ["email", "push", "whatsapp"]
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime)
    expires_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="alerts")

class ApiUsage(Base):
    __tablename__ = "api_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Usage details
    endpoint = Column(String)
    method = Column(String)
    status_code = Column(Integer)
    response_time_ms = Column(Integer)
    
    # Rate limiting
    date = Column(DateTime, default=datetime.utcnow)
    hour = Column(Integer)
    count = Column(Integer, default=1)
    
    # Relationships
    user = relationship("User", back_populates="api_usage")

class UserPreference(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Notification preferences
    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=True)
    whatsapp_notifications = Column(Boolean, default=False)
    
    # Alert preferences
    price_rise_alerts = Column(Boolean, default=True)
    price_fall_alerts = Column(Boolean, default=True)
    injury_alerts = Column(Boolean, default=True)
    lineup_alerts = Column(Boolean, default=True)
    
    # Thresholds
    price_alert_threshold = Column(Float, default=0.1)  # Alert when price changes by this amount
    ownership_alert_threshold = Column(Float, default=5.0)  # Alert when ownership changes by this %
    
    # Display preferences
    theme = Column(String, default="light")  # "light", "dark", "auto"
    language = Column(String, default="en")
    timezone = Column(String, default="UTC")
    
    # Custom settings
    favorite_team = Column(String)
    watchlist_players = Column(JSON)  # List of player IDs to track
    mini_leagues = Column(JSON)  # List of mini-league IDs
    
    # Relationships
    user = relationship("User", back_populates="preferences", uselist=False)

class Player(Base):
    __tablename__ = "players"
    
    id = Column(Integer, primary_key=True, index=True)
    fpl_id = Column(Integer, unique=True, nullable=False)
    
    # Basic info
    first_name = Column(String)
    second_name = Column(String)
    web_name = Column(String)
    team_id = Column(Integer)
    team_name = Column(String)
    position = Column(String)  # GK, DEF, MID, FWD
    
    # Current stats
    price = Column(Float)
    selected_by_percent = Column(Float)
    form = Column(Float)
    points_per_game = Column(Float)
    total_points = Column(Integer)
    
    # Performance metrics
    goals_scored = Column(Integer)
    assists = Column(Integer)
    clean_sheets = Column(Integer)
    saves = Column(Integer)
    yellow_cards = Column(Integer)
    red_cards = Column(Integer)
    
    # Status
    status = Column(String)  # "a" = available, "i" = injured, etc.
    chance_of_playing_next_round = Column(Integer)
    news = Column(Text)
    news_added = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PricePrediction(Base):
    __tablename__ = "price_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    
    # Prediction details
    prediction_date = Column(DateTime, default=datetime.utcnow)
    current_price = Column(Float)
    predicted_price = Column(Float)
    probability = Column(Float)
    direction = Column(String)  # "rise", "fall", "stable"
    
    # Transfer data
    transfers_in = Column(Integer)
    transfers_out = Column(Integer)
    net_transfers = Column(Integer)
    ownership_change = Column(Float)
    
    # Outcome
    actual_price = Column(Float)
    was_correct = Column(Boolean)

class SentimentAnalysis(Base):
    __tablename__ = "sentiment_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    
    # Analysis details
    analysis_date = Column(DateTime, default=datetime.utcnow)
    sentiment_score = Column(Float)  # -1 to 1
    sentiment_label = Column(String)  # "positive", "negative", "neutral"
    
    # Source data
    news_sources = Column(JSON)  # List of news sources analyzed
    total_mentions = Column(Integer)
    positive_mentions = Column(Integer)
    negative_mentions = Column(Integer)
    injury_mentions = Column(Integer)
    
    # Key insights
    key_topics = Column(JSON)  # List of main topics discussed
    injury_risk = Column(String)  # "low", "medium", "high"
    form_trend = Column(String)  # "improving", "declining", "stable"

class ModelPerformance(Base):
    __tablename__ = "model_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Model details
    model_version = Column(String)
    model_type = Column(String)  # "cnn", "lstm", "ensemble"
    
    # Training metrics
    training_date = Column(DateTime, default=datetime.utcnow)
    training_samples = Column(Integer)
    validation_samples = Column(Integer)
    training_loss = Column(Float)
    validation_loss = Column(Float)
    mae = Column(Float)
    rmse = Column(Float)
    
    # Production metrics
    predictions_made = Column(Integer, default=0)
    average_error = Column(Float)
    accuracy_rate = Column(Float)  # Percentage of predictions within threshold
    
    # Status
    is_active = Column(Boolean, default=True)
    replaced_by = Column(String)  # Version that replaced this model
    notes = Column(Text)