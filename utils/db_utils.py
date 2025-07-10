"""
Database utilities for the Supawriter application.
This module provides a unified interface for database operations,
supporting both MySQL and SQLite backends.
"""

import os
import logging
import hashlib
import pickle
import sqlite3
from datetime import datetime
import json
import uuid
from pathlib import Path

# Try to import MySQL connector, but don't fail if not available
try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database configuration
# Connection config without database (for initial connection)
MYSQL_BASE_CONFIG = {
    'host': 'yisurds-6868f7b9934b60.rds.ysydb1.com',
    'port': 3306,
    'user': '6868f7b9934b603815:supawriter',  # Format based on error message
    'password': 'wxk@521666'
}

# Full config with database name
MYSQL_CONFIG = MYSQL_BASE_CONFIG.copy()
MYSQL_CONFIG['database'] = 'supawriter'

# SQLite configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_DB_PATH = os.path.join(BASE_DIR, 'data', 'supawriter.db')
USER_PICKLE_PATH = os.path.join(BASE_DIR, 'data', 'users.pkl')

# Ensure data directory exists
os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)

class DatabaseManager:
    """
    Database manager that provides a unified interface for both MySQL and SQLite.
    It tries MySQL first and falls back to SQLite if MySQL is not available or connection fails.
    """
    
    def __init__(self):
        self.db_type = None
        self.connection = None
        self.initialize_database()
    
    def initialize_database(self):
        """Initialize database connection and create tables if needed."""
        # Try MySQL first
        if MYSQL_AVAILABLE:
            try:
                # First try to connect without specifying the database
                conn = mysql.connector.connect(**MYSQL_BASE_CONFIG)
                if conn.is_connected():
                    cursor = conn.cursor()
                    
                    # Create the database if it doesn't exist
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_CONFIG['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    logger.info(f"Database '{MYSQL_CONFIG['database']}' created or already exists")
                    
                    # Close the initial connection
                    cursor.close()
                    conn.close()
                    
                    # Now connect with the database specified
                    self.connection = mysql.connector.connect(**MYSQL_CONFIG)
                    if self.connection.is_connected():
                        self.db_type = 'mysql'
                        logger.info(f"Connected to MySQL Server version {self.connection.get_server_info()}")
                        self._create_mysql_tables()
                        return
            except Exception as e:
                logger.warning(f"MySQL connection failed: {e}")
        
        # Fall back to SQLite
        try:
            self.connection = sqlite3.connect(SQLITE_DB_PATH)
            self.db_type = 'sqlite'
            logger.info(f"Connected to SQLite database at {SQLITE_DB_PATH}")
            self._create_sqlite_tables()
        except Exception as e:
            logger.error(f"SQLite connection failed: {e}")
            self.connection = None
            self.db_type = None
    
    def _create_mysql_tables(self):
        """Create necessary tables in MySQL if they don't exist."""
        try:
            cursor = self.connection.cursor()
            
            # Create users table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(64) NOT NULL,
                email VARCHAR(100),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                INDEX idx_username (username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Create history table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                model_type VARCHAR(50),
                model_name VARCHAR(50),
                spider_num INT,
                custom_style TEXT,
                is_transformed BOOLEAN DEFAULT FALSE,
                original_article_id INT,
                image_enabled BOOLEAN DEFAULT FALSE,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (original_article_id) REFERENCES history(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            self.connection.commit()
            logger.info("MySQL tables created successfully")
        except Exception as e:
            logger.error(f"Error creating MySQL tables: {e}")
    
    def _create_sqlite_tables(self):
        """Create necessary tables in SQLite if they don't exist."""
        try:
            cursor = self.connection.cursor()
            
            # Create users table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                created_at TEXT NOT NULL,
                last_login TEXT
            )
            """)
            
            # Create history table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                model_type TEXT,
                model_name TEXT,
                spider_num INTEGER,
                custom_style TEXT,
                is_transformed INTEGER DEFAULT 0,
                original_article_id INTEGER,
                image_enabled INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (original_article_id) REFERENCES history(id) ON DELETE SET NULL
            )
            """)
            
            self.connection.commit()
            logger.info("SQLite tables created successfully")
            
            # Migrate users from pickle if available
            self._migrate_users_from_pickle()
        except Exception as e:
            logger.error(f"Error creating SQLite tables: {e}")
    
    def _migrate_users_from_pickle(self):
        """Migrate users from pickle file to SQLite if pickle file exists."""
        if not os.path.exists(USER_PICKLE_PATH):
            return
        
        try:
            with open(USER_PICKLE_PATH, 'rb') as f:
                users = pickle.load(f)
            
            cursor = self.connection.cursor()
            
            for username, user in users.items():
                # Check if user already exists
                cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
                if cursor.fetchone()[0] > 0:
                    continue
                
                # Insert user
                created_at = user.created_at.isoformat() if hasattr(user, 'created_at') else datetime.now().isoformat()
                last_login = user.last_login.isoformat() if hasattr(user, 'last_login') and user.last_login else None
                
                cursor.execute(
                    "INSERT INTO users (username, password_hash, email, created_at, last_login) VALUES (?, ?, ?, ?, ?)",
                    (username, user.password_hash, getattr(user, 'email', None), created_at, last_login)
                )
            
            self.connection.commit()
            logger.info(f"Migrated {len(users)} users from pickle to SQLite")
        except Exception as e:
            logger.error(f"Error migrating users from pickle: {e}")
    
    def close(self):
        """Close the database connection."""
        if self.connection:
            if self.db_type == 'mysql' and self.connection.is_connected():
                self.connection.close()
            elif self.db_type == 'sqlite':
                self.connection.close()
            logger.info(f"{self.db_type.upper()} connection closed")
    
    def add_user(self, username, password, email=None):
        """
        Add a new user to the database.
        
        Args:
            username (str): Username
            password (str): Plain text password to be hashed
            email (str, optional): User's email
            
        Returns:
            int or None: User ID if successful, None otherwise
        """
        if not self.connection:
            logger.error("No database connection available")
            return None
        
        try:
            # Hash the password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            if self.db_type == 'mysql':
                cursor = self.connection.cursor()
                
                # Check if user exists
                cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
                if cursor.fetchone()[0] > 0:
                    logger.warning(f"User '{username}' already exists")
                    return None
                
                # Insert user
                query = """
                INSERT INTO users (username, password_hash, email, created_at)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(query, (username, password_hash, email, datetime.now()))
                self.connection.commit()
                
                user_id = cursor.lastrowid
                cursor.close()
                
                logger.info(f"User '{username}' added successfully with ID {user_id}")
                return user_id
            
            elif self.db_type == 'sqlite':
                cursor = self.connection.cursor()
                
                # Check if user exists
                cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
                if cursor.fetchone()[0] > 0:
                    logger.warning(f"User '{username}' already exists")
                    return None
                
                # Insert user
                query = """
                INSERT INTO users (username, password_hash, email, created_at)
                VALUES (?, ?, ?, ?)
                """
                cursor.execute(query, (username, password_hash, email, datetime.now().isoformat()))
                self.connection.commit()
                
                user_id = cursor.lastrowid
                cursor.close()
                
                logger.info(f"User '{username}' added successfully with ID {user_id}")
                return user_id
        
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return None
    
    def authenticate_user(self, username, password):
        """
        Authenticate a user by username and password.
        
        Args:
            username (str): Username
            password (str): Plain text password
            
        Returns:
            dict or None: User data if authentication is successful, None otherwise
        """
        if not self.connection:
            logger.error("No database connection available")
            return None
        
        try:
            # Hash the password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            if self.db_type == 'mysql':
                cursor = self.connection.cursor(dictionary=True)
                
                # Check credentials
                query = """
                SELECT id, username, email, created_at, last_login
                FROM users
                WHERE username = %s AND password_hash = %s
                """
                cursor.execute(query, (username, password_hash))
                user = cursor.fetchone()
                
                if user:
                    # Update last login
                    update_query = "UPDATE users SET last_login = %s WHERE username = %s"
                    cursor.execute(update_query, (datetime.now(), username))
                    self.connection.commit()
                    
                    logger.info(f"User '{username}' authenticated successfully")
                    cursor.close()
                    return user
                
                cursor.close()
                logger.warning(f"Authentication failed for user '{username}'")
                return None
            
            elif self.db_type == 'sqlite':
                cursor = self.connection.cursor()
                
                # Check credentials
                query = """
                SELECT id, username, email, created_at, last_login
                FROM users
                WHERE username = ? AND password_hash = ?
                """
                cursor.execute(query, (username, password_hash))
                result = cursor.fetchone()
                
                if result:
                    # Convert to dictionary
                    user = {
                        'id': result[0],
                        'username': result[1],
                        'email': result[2],
                        'created_at': result[3],
                        'last_login': result[4]
                    }
                    
                    # Update last login
                    update_query = "UPDATE users SET last_login = ? WHERE username = ?"
                    cursor.execute(update_query, (datetime.now().isoformat(), username))
                    self.connection.commit()
                    
                    logger.info(f"User '{username}' authenticated successfully")
                    cursor.close()
                    return user
                
                cursor.close()
                logger.warning(f"Authentication failed for user '{username}'")
                return None
        
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None
    
    def get_user(self, username):
        """
        Get user data by username.
        
        Args:
            username (str): Username
            
        Returns:
            dict or None: User data if found, None otherwise
        """
        if not self.connection:
            logger.error("No database connection available")
            return None
        
        try:
            if self.db_type == 'mysql':
                cursor = self.connection.cursor(dictionary=True)
                
                query = """
                SELECT id, username, email, created_at, last_login
                FROM users
                WHERE username = %s
                """
                cursor.execute(query, (username,))
                user = cursor.fetchone()
                cursor.close()
                
                return user
            
            elif self.db_type == 'sqlite':
                cursor = self.connection.cursor()
                
                query = """
                SELECT id, username, email, created_at, last_login
                FROM users
                WHERE username = ?
                """
                cursor.execute(query, (username,))
                result = cursor.fetchone()
                cursor.close()
                
                if result:
                    return {
                        'id': result[0],
                        'username': result[1],
                        'email': result[2],
                        'created_at': result[3],
                        'last_login': result[4]
                    }
                
                return None
        
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def add_history_record(self, user_id, title, content, **kwargs):
        """
        Add a new history record for an article.
        
        Args:
            user_id (int): User ID
            title (str): Article title
            content (str): Article content
            **kwargs: Additional fields like summary, model_type, etc.
            
        Returns:
            int or None: Record ID if successful, None otherwise
        """
        if not self.connection:
            logger.error("No database connection available")
            return None
        
        try:
            # Extract optional fields
            summary = kwargs.get('summary', '')
            model_type = kwargs.get('model_type', '')
            model_name = kwargs.get('model_name', '')
            spider_num = kwargs.get('spider_num', 0)
            custom_style = kwargs.get('custom_style', '')
            is_transformed = kwargs.get('is_transformed', False)
            original_article_id = kwargs.get('original_article_id', None)
            image_enabled = kwargs.get('image_enabled', False)
            
            if self.db_type == 'mysql':
                cursor = self.connection.cursor()
                
                # Insert record
                query = """
                INSERT INTO history (
                    user_id, title, content, summary, model_type, model_name,
                    spider_num, custom_style, is_transformed, original_article_id, image_enabled,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    user_id, title, content, summary, model_type, model_name,
                    spider_num, custom_style, is_transformed, original_article_id, image_enabled,
                    datetime.now()
                ))
                self.connection.commit()
                
                record_id = cursor.lastrowid
                cursor.close()
                
                logger.info(f"History record '{title}' added successfully with ID {record_id}")
                return record_id
            
            elif self.db_type == 'sqlite':
                cursor = self.connection.cursor()
                
                # Insert record
                query = """
                INSERT INTO history (
                    user_id, title, content, summary, model_type, model_name,
                    spider_num, custom_style, is_transformed, original_article_id, image_enabled,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(query, (
                    user_id, title, content, summary, model_type, model_name,
                    spider_num, custom_style, 1 if is_transformed else 0, original_article_id, 1 if image_enabled else 0,
                    datetime.now().isoformat()
                ))
                self.connection.commit()
                
                record_id = cursor.lastrowid
                cursor.close()
                
                logger.info(f"History record '{title}' added successfully with ID {record_id}")
                return record_id
        
        except Exception as e:
            logger.error(f"Error adding history record: {e}")
            return None
    
    def get_user_history(self, user_id):
        """
        Get all history records for a user.
        
        Args:
            user_id (int): User ID
            
        Returns:
            list or None: List of history records if successful, None otherwise
        """
        if not self.connection:
            logger.error("No database connection available")
            return None
        
        try:
            if self.db_type == 'mysql':
                cursor = self.connection.cursor(dictionary=True)
                
                query = """
                SELECT * FROM history
                WHERE user_id = %s
                ORDER BY created_at DESC
                """
                cursor.execute(query, (user_id,))
                records = cursor.fetchall()
                cursor.close()
                
                return records
            
            elif self.db_type == 'sqlite':
                cursor = self.connection.cursor()
                
                query = """
                SELECT * FROM history
                WHERE user_id = ?
                ORDER BY created_at DESC
                """
                cursor.execute(query, (user_id,))
                results = cursor.fetchall()
                cursor.close()
                
                # Convert to list of dictionaries
                columns = [desc[0] for desc in cursor.description]
                records = []
                
                for result in results:
                    record = dict(zip(columns, result))
                    # Convert boolean fields
                    record['is_transformed'] = bool(record['is_transformed'])
                    record['image_enabled'] = bool(record['image_enabled'])
                    records.append(record)
                
                return records
        
        except Exception as e:
            logger.error(f"Error getting user history: {e}")
            return None

# Create a singleton instance
db_manager = DatabaseManager()

# Compatibility functions to match existing code
def add_user(username, password, email=None):
    return db_manager.add_user(username, password, email)

def authenticate_user(username, password):
    return db_manager.authenticate_user(username, password)

def get_user(username):
    return db_manager.get_user(username)

def add_history_record(user_id, title, content, **kwargs):
    return db_manager.add_history_record(user_id, title, content, **kwargs)

def get_user_history(user_id):
    return db_manager.get_user_history(user_id)

# Main function to test the module
if __name__ == "__main__":
    # Test database connection
    print(f"Database type: {db_manager.db_type}")
    
    # Test user functions
    user_id = add_user("testuser", "testpassword", "test@example.com")
    print(f"Added user with ID: {user_id}")
    
    user = authenticate_user("testuser", "testpassword")
    print(f"Authenticated user: {user}")
    
    # Make sure we have a valid user_id for testing
    if user and 'id' in user:
        test_user_id = user['id']
        
        # Test history functions
        record_id = add_history_record(
            user_id=test_user_id,
            title="Test Article",
            content="This is a test article content.",
            summary="Test summary",
            model_type="test",
            model_name="test-model",
            spider_num=5,
            custom_style="Test style",
            is_transformed=False,
            image_enabled=True
        )
        print(f"Added history record with ID: {record_id}")
        
        history = get_user_history(test_user_id)
        print(f"User history: {history}")
    else:
        print("Cannot test history functions: No valid user ID")
    
    # Close the connection
    db_manager.close()
