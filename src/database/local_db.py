import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class LocalDatabase:
    def __init__(self, db_path="./data/local_fpl.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
        self.seed_data()
    
    def init_database(self):
        """Initialize the local SQLite database with all necessary tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT,
            hashed_password TEXT NOT NULL,
            fpl_team_id INTEGER,
            tier TEXT DEFAULT 'free',
            is_active BOOLEAN DEFAULT 1,
            is_verified BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Players table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY,
            fpl_id INTEGER UNIQUE NOT NULL,
            first_name TEXT,
            second_name TEXT,
            web_name TEXT,
            team_id INTEGER,
            team_name TEXT,
            position TEXT,
            price REAL,
            selected_by_percent REAL,
            form REAL,
            total_points INTEGER,
            status TEXT DEFAULT 'a',
            chance_of_playing_next_round INTEGER,
            news TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # User predictions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            gameweek INTEGER,
            player_id INTEGER,
            predicted_points REAL,
            prediction_type TEXT DEFAULT 'ml_model',
            confidence_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (player_id) REFERENCES players (id)
        )
        ''')
        
        # User alerts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            alert_type TEXT,
            player_id INTEGER,
            player_name TEXT,
            title TEXT,
            message TEXT,
            urgency TEXT DEFAULT 'medium',
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # Price predictions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            current_price REAL,
            predicted_price REAL,
            probability REAL,
            direction TEXT,
            prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players (id)
        )
        ''')
        
        # Sentiment analysis table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sentiment_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            sentiment_score REAL,
            sentiment_label TEXT,
            news_sources TEXT,
            total_mentions INTEGER,
            positive_mentions INTEGER,
            negative_mentions INTEGER,
            injury_mentions INTEGER,
            injury_risk TEXT DEFAULT 'low',
            analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players (id)
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Local database initialized successfully")
    
    def seed_data(self):
        """Seed the database with sample FPL data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if data already exists
        cursor.execute("SELECT COUNT(*) FROM players")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return
        
        # Sample players data
        sample_players = [
            # Goalkeepers
            (1, 'Jordan', 'Pickford', 'Pickford', 1, 'Everton', 'GK', 5.0, 12.3, 4.5, 45, 'a', 100, ''),
            (2, 'Alisson', 'Becker', 'Alisson', 2, 'Liverpool', 'GK', 5.5, 8.7, 5.2, 68, 'a', 100, ''),
            (3, 'Aaron', 'Ramsdale', 'Ramsdale', 3, 'Arsenal', 'GK', 5.0, 15.6, 3.8, 42, 'a', 100, ''),
            
            # Defenders
            (4, 'Virgil', 'van Dijk', 'Van Dijk', 2, 'Liverpool', 'DEF', 6.5, 23.4, 5.8, 78, 'a', 100, ''),
            (5, 'William', 'Saliba', 'Saliba', 3, 'Arsenal', 'DEF', 5.5, 18.9, 6.2, 82, 'a', 100, ''),
            (6, 'Reece', 'James', 'James', 4, 'Chelsea', 'DEF', 6.0, 12.1, 4.1, 38, 'd', 75, 'Knock - 75% chance of playing'),
            (7, 'Kyle', 'Walker', 'Walker', 5, 'Man City', 'DEF', 5.5, 9.8, 5.0, 67, 'a', 100, ''),
            (8, 'Kieran', 'Trippier', 'Trippier', 6, 'Newcastle', 'DEF', 5.5, 25.6, 5.5, 71, 'a', 100, ''),
            
            # Midfielders
            (9, 'Mohamed', 'Salah', 'Salah', 2, 'Liverpool', 'MID', 13.0, 67.8, 8.9, 156, 'a', 100, ''),
            (10, 'Bukayo', 'Saka', 'Saka', 3, 'Arsenal', 'MID', 8.5, 34.5, 7.2, 134, 'a', 100, ''),
            (11, 'Kevin', 'De Bruyne', 'De Bruyne', 5, 'Man City', 'MID', 12.5, 45.6, 6.8, 98, 'i', 0, 'Hamstring injury - out for 4-6 weeks'),
            (12, 'Bruno', 'Fernandes', 'Fernandes', 7, 'Man Utd', 'MID', 8.5, 28.9, 5.4, 89, 'a', 100, ''),
            (13, 'Son', 'Heung-min', 'Son', 8, 'Tottenham', 'MID', 9.5, 22.3, 6.1, 102, 'a', 100, ''),
            (14, 'Phil', 'Foden', 'Foden', 5, 'Man City', 'MID', 8.0, 31.2, 7.8, 145, 'a', 100, ''),
            
            # Forwards
            (15, 'Erling', 'Haaland', 'Haaland', 5, 'Man City', 'FWD', 14.0, 89.5, 9.2, 187, 'a', 100, ''),
            (16, 'Harry', 'Kane', 'Kane', 8, 'Tottenham', 'FWD', 11.5, 45.7, 6.9, 123, 'a', 100, ''),
            (17, 'Darwin', 'Núñez', 'Núñez', 2, 'Liverpool', 'FWD', 9.0, 18.4, 5.8, 87, 'a', 100, ''),
            (18, 'Ivan', 'Toney', 'Toney', 9, 'Brentford', 'FWD', 7.5, 12.8, 4.2, 45, 's', 0, 'Suspended for betting - return date TBC'),
            (19, 'Alexander', 'Isak', 'Isak', 6, 'Newcastle', 'FWD', 8.5, 16.9, 6.5, 98, 'a', 100, ''),
            (20, 'Ollie', 'Watkins', 'Watkins', 10, 'Aston Villa', 'FWD', 7.5, 24.1, 5.9, 89, 'a', 100, ''),
        ]
        
        # Insert sample players
        cursor.executemany('''
        INSERT INTO players (fpl_id, first_name, second_name, web_name, team_id, team_name, position, price, selected_by_percent, form, total_points, status, chance_of_playing_next_round, news)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_players)
        
        # Create sample user
        cursor.execute('''
        INSERT INTO users (email, username, full_name, hashed_password, fpl_team_id, tier)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', ('demo@fplpredictor.com', 'demo_user', 'Demo User', 'hashed_demo_password', 123456, 'premium'))
        
        user_id = cursor.lastrowid
        
        # Create sample predictions for the demo user
        predictions_data = [
            (user_id, 15, 9, 12.5, 'ml_model', 0.89),    # Haaland
            (user_id, 15, 10, 8.2, 'ml_model', 0.76),    # Saka  
            (user_id, 15, 4, 6.8, 'ml_model', 0.71),     # Van Dijk
            (user_id, 15, 16, 7.9, 'ml_model', 0.68),    # Kane
            (user_id, 15, 14, 8.9, 'ml_model', 0.82),    # Foden
            (user_id, 15, 8, 6.1, 'ml_model', 0.74),     # Trippier
            (user_id, 15, 13, 6.7, 'ml_model', 0.69),    # Son
            (user_id, 15, 20, 6.8, 'ml_model', 0.72),    # Watkins
            (user_id, 15, 12, 5.9, 'ml_model', 0.65),    # Bruno
            (user_id, 15, 2, 6.2, 'ml_model', 0.71),     # Alisson
        ]
        
        cursor.executemany('''
        INSERT INTO user_predictions (user_id, gameweek, player_id, predicted_points, prediction_type, confidence_score)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', predictions_data)
        
        # Create sample alerts
        alerts_data = [
            (user_id, 'price_rise', 9, 'Salah', 'Price Rise Alert', 'Salah is predicted to rise by £0.1m tonight', 'high'),
            (user_id, 'injury', 11, 'De Bruyne', 'Injury Update', 'De Bruyne ruled out with hamstring injury', 'critical'),
            (user_id, 'price_fall', 6, 'James', 'Price Fall Warning', 'Reece James likely to fall due to injury doubt', 'medium'),
            (user_id, 'suspension', 18, 'Toney', 'Suspension Notice', 'Ivan Toney suspended for betting violations', 'critical'),
        ]
        
        cursor.executemany('''
        INSERT INTO user_alerts (user_id, alert_type, player_id, player_name, title, message, urgency)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', alerts_data)
        
        # Create sample price predictions
        price_predictions_data = [
            (9, 13.0, 13.1, 0.85, 'rise'),    # Salah
            (6, 6.0, 5.9, 0.72, 'fall'),      # James
            (15, 14.0, 14.1, 0.68, 'rise'),   # Haaland
            (11, 12.5, 12.4, 0.91, 'fall'),   # De Bruyne
            (10, 8.5, 8.6, 0.63, 'rise'),     # Saka
        ]
        
        cursor.executemany('''
        INSERT INTO price_predictions (player_id, current_price, predicted_price, probability, direction)
        VALUES (?, ?, ?, ?, ?)
        ''', price_predictions_data)
        
        # Create sample sentiment analysis
        sentiment_data = [
            (9, 0.8, 'positive', 'BBC,Sky Sports', 15, 12, 2, 0, 'low'),      # Salah positive
            (11, -0.6, 'negative', 'BBC,Guardian', 8, 1, 6, 3, 'high'),       # De Bruyne negative (injury)
            (15, 0.9, 'positive', 'Sky Sports,Telegraph', 20, 18, 1, 0, 'low'), # Haaland very positive
            (6, -0.3, 'negative', 'BBC,Sky Sports', 5, 1, 3, 2, 'medium'),    # James negative (injury)
            (18, -0.9, 'negative', 'All sources', 12, 0, 12, 0, 'low'),       # Toney very negative (suspension)
        ]
        
        cursor.executemany('''
        INSERT INTO sentiment_analyses (player_id, sentiment_score, sentiment_label, news_sources, total_mentions, positive_mentions, negative_mentions, injury_mentions, injury_risk)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sentiment_data)
        
        conn.commit()
        conn.close()
        
        logger.info("Sample data seeded successfully")
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def get_user_by_username(self, username):
        """Get user by username"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, email, username, full_name, fpl_team_id, tier, is_active, is_verified, created_at
        FROM users WHERE username = ? OR email = ?
        ''', (username, username))
        
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return {
                'id': user_data[0],
                'email': user_data[1],
                'username': user_data[2],
                'full_name': user_data[3],
                'fpl_team_id': user_data[4],
                'tier': user_data[5],
                'is_active': user_data[6],
                'is_verified': user_data[7],
                'created_at': user_data[8]
            }
        return None
    
    def get_all_players(self):
        """Get all players"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT fpl_id, first_name, second_name, web_name, team_name, position, 
               price, selected_by_percent, form, total_points, status, 
               chance_of_playing_next_round, news
        FROM players ORDER BY position, price DESC
        ''')
        
        players = []
        for row in cursor.fetchall():
            players.append({
                'id': row[0],
                'first_name': row[1],
                'second_name': row[2],
                'web_name': row[3],
                'team': row[4],
                'position': row[5],
                'now_cost': int(row[6] * 10),  # Convert back to FPL format
                'selected_by_percent': row[7],
                'form': row[8],
                'total_points': row[9],
                'status': row[10],
                'chance_of_playing_next_round': row[11],
                'news': row[12]
            })
        
        conn.close()
        return players
    
    def get_user_predictions(self, user_id, gameweek=None):
        """Get user predictions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if gameweek:
            cursor.execute('''
            SELECT p.web_name, p.team_name, p.position, up.predicted_points, 
                   up.confidence_score, up.prediction_type
            FROM user_predictions up
            JOIN players p ON up.player_id = p.fpl_id
            WHERE up.user_id = ? AND up.gameweek = ?
            ORDER BY up.predicted_points DESC
            ''', (user_id, gameweek))
        else:
            cursor.execute('''
            SELECT p.web_name, p.team_name, p.position, up.predicted_points, 
                   up.confidence_score, up.prediction_type, up.gameweek
            FROM user_predictions up
            JOIN players p ON up.player_id = p.fpl_id
            WHERE up.user_id = ?
            ORDER BY up.gameweek DESC, up.predicted_points DESC
            ''', (user_id,))
        
        predictions = []
        for row in cursor.fetchall():
            predictions.append({
                'player_name': row[0],
                'team': row[1],
                'position': row[2],
                'predicted_points': row[3],
                'confidence': row[4],
                'type': row[5],
                'gameweek': row[6] if len(row) > 6 else None
            })
        
        conn.close()
        return predictions
    
    def get_user_alerts(self, user_id, unread_only=False):
        """Get user alerts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT id, alert_type, player_name, title, message, urgency, is_read, created_at
        FROM user_alerts
        WHERE user_id = ?
        '''
        
        if unread_only:
            query += ' AND is_read = 0'
        
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query, (user_id,))
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                'id': row[0],
                'type': row[1],
                'player_name': row[2],
                'title': row[3],
                'message': row[4],
                'urgency': row[5],
                'is_read': row[6],
                'created_at': row[7]
            })
        
        conn.close()
        return alerts
    
    def get_price_predictions(self, limit=10):
        """Get price predictions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT p.web_name, p.team_name, pp.current_price, pp.predicted_price, 
               pp.probability, pp.direction
        FROM price_predictions pp
        JOIN players p ON pp.player_id = p.fpl_id
        ORDER BY pp.probability DESC
        LIMIT ?
        ''', (limit,))
        
        predictions = []
        for row in cursor.fetchall():
            predictions.append({
                'player_name': row[0],
                'team': row[1],
                'current_price': row[2],
                'predicted_price': row[3],
                'probability': row[4],
                'direction': row[5]
            })
        
        conn.close()
        return predictions
    
    def get_sentiment_analysis(self, limit=10):
        """Get sentiment analysis data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT p.web_name, p.team_name, sa.sentiment_score, sa.sentiment_label,
               sa.total_mentions, sa.injury_risk
        FROM sentiment_analyses sa
        JOIN players p ON sa.player_id = p.fpl_id
        ORDER BY ABS(sa.sentiment_score) DESC
        LIMIT ?
        ''', (limit,))
        
        sentiments = []
        for row in cursor.fetchall():
            sentiments.append({
                'player_name': row[0],
                'team': row[1],
                'sentiment_score': row[2],
                'sentiment_label': row[3],
                'total_mentions': row[4],
                'injury_risk': row[5]
            })
        
        conn.close()
        return sentiments