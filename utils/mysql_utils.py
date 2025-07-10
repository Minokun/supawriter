"""
MySQL database utilities for the Supawriter application.
This module provides functions to interact with the MySQL database,
including database initialization, user management, and other operations.
"""

import os
import logging
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database configuration
# Based on the error message format: mysql -u'5ecq13bs98c2qw:root' -p'123456' -h'yisurds-5ecq13bs98c2qw.rds.ysydb1.com'
DB_CONFIG = {
    'host': 'yisurds-6868f7b9934b60.rds.ysydb1.com',
    'port': 3306,
    'user': '6868f7b9934b60:supawriter',  # Format: <instance_id>:<username>
    'password': 'wxk@521666'
}

# Database name
DB_NAME = 'supawriter'

def create_connection(database=None):
    """
    Create a connection to the MySQL database.
    
    Args:
        database (str, optional): Database name to connect to. Defaults to None.
        
    Returns:
        mysql.connector.connection.MySQLConnection: Database connection object or None if connection fails
    """
    try:
        config = DB_CONFIG.copy()
        if database:
            config['database'] = database
        
        connection = mysql.connector.connect(**config)
        if connection.is_connected():
            logger.info(f"Connected to MySQL Server version {connection.get_server_info()}")
            return connection
    except Error as e:
        logger.error(f"Error connecting to MySQL: {e}")
        return None

def initialize_database():
    """
    Initialize the database by creating it if it doesn't exist
    and setting up the required tables.
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        logger.info(f"Database '{DB_NAME}' created or already exists")
        
        # Switch to the database
        cursor.execute(f"USE {DB_NAME}")
        
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
        logger.info("Users table created or already exists")
        
        # Create history table for article records
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
        logger.info("History table created or already exists")
        
        connection.commit()
        return True
    except Error as e:
        logger.error(f"Error initializing database: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            logger.info("MySQL connection closed")

def add_user(username, password, email=None):
    """
    Add a new user to the database.
    
    Args:
        username (str): Username
        password (str): Plain text password to be hashed
        email (str, optional): User's email. Defaults to None.
        
    Returns:
        bool: True if user was added successfully, False otherwise
    """
    connection = create_connection(DB_NAME)
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Hash the password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Check if user already exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
        if cursor.fetchone()[0] > 0:
            logger.warning(f"User '{username}' already exists")
            return False
        
        # Insert the new user
        query = """
        INSERT INTO users (username, password_hash, email, created_at)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (username, password_hash, email, datetime.now()))
        connection.commit()
        
        logger.info(f"User '{username}' added successfully")
        return True
    except Error as e:
        logger.error(f"Error adding user: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def authenticate_user(username, password):
    """
    Authenticate a user by username and password.
    
    Args:
        username (str): Username
        password (str): Plain text password
        
    Returns:
        dict or None: User data if authentication is successful, None otherwise
    """
    connection = create_connection(DB_NAME)
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Hash the password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Check credentials
        query = """
        SELECT id, username, email, created_at, last_login
        FROM users
        WHERE username = %s AND password_hash = %s
        """
        cursor.execute(query, (username, password_hash))
        user = cursor.fetchone()
        
        if user:
            # Update last login time
            update_query = """
            UPDATE users SET last_login = %s WHERE username = %s
            """
            cursor.execute(update_query, (datetime.now(), username))
            connection.commit()
            
            logger.info(f"User '{username}' authenticated successfully")
            return user
        
        logger.warning(f"Authentication failed for user '{username}'")
        return None
    except Error as e:
        logger.error(f"Error authenticating user: {e}")
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def get_user(username):
    """
    Get user data by username.
    
    Args:
        username (str): Username
        
    Returns:
        dict or None: User data if found, None otherwise
    """
    connection = create_connection(DB_NAME)
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT id, username, email, created_at, last_login
        FROM users
        WHERE username = %s
        """
        cursor.execute(query, (username,))
        user = cursor.fetchone()
        
        return user
    except Error as e:
        logger.error(f"Error getting user: {e}")
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def add_history_record(user_id, title, content, **kwargs):
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
    connection = create_connection(DB_NAME)
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        
        # Extract optional fields
        summary = kwargs.get('summary', '')
        model_type = kwargs.get('model_type', '')
        model_name = kwargs.get('model_name', '')
        spider_num = kwargs.get('spider_num', 0)
        custom_style = kwargs.get('custom_style', '')
        is_transformed = kwargs.get('is_transformed', False)
        original_article_id = kwargs.get('original_article_id', None)
        image_enabled = kwargs.get('image_enabled', False)
        
        # Insert the record
        query = """
        INSERT INTO history (
            user_id, title, content, summary, model_type, model_name,
            spider_num, custom_style, is_transformed, original_article_id, image_enabled
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            user_id, title, content, summary, model_type, model_name,
            spider_num, custom_style, is_transformed, original_article_id, image_enabled
        ))
        connection.commit()
        
        # Get the ID of the inserted record
        record_id = cursor.lastrowid
        logger.info(f"History record '{title}' added successfully with ID {record_id}")
        return record_id
    except Error as e:
        logger.error(f"Error adding history record: {e}")
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def get_user_history(user_id):
    """
    Get all history records for a user.
    
    Args:
        user_id (int): User ID
        
    Returns:
        list or None: List of history records if successful, None otherwise
    """
    connection = create_connection(DB_NAME)
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT * FROM history
        WHERE user_id = %s
        ORDER BY created_at DESC
        """
        cursor.execute(query, (user_id,))
        records = cursor.fetchall()
        
        return records
    except Error as e:
        logger.error(f"Error getting user history: {e}")
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def migrate_users_from_pickle():
    """
    Migrate users from the pickle file to the MySQL database.
    This function is intended to be used once during the transition.
    
    Returns:
        bool: True if migration was successful, False otherwise
    """
    try:
        import pickle
        import os
        
        # Path to the user database file
        USER_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'users.pkl')
        
        if not os.path.exists(USER_DB_PATH):
            logger.warning(f"User database file not found at {USER_DB_PATH}")
            return False
        
        # Load users from pickle
        with open(USER_DB_PATH, 'rb') as f:
            users = pickle.load(f)
        
        # Migrate each user to MySQL
        success_count = 0
        for username, user in users.items():
            connection = create_connection(DB_NAME)
            if not connection:
                continue
            
            try:
                cursor = connection.cursor()
                
                # Check if user already exists
                cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
                if cursor.fetchone()[0] > 0:
                    logger.info(f"User '{username}' already exists in MySQL, skipping")
                    continue
                
                # Insert the user
                query = """
                INSERT INTO users (username, password_hash, email, created_at, last_login)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    user.username,
                    user.password_hash,
                    user.email,
                    user.created_at,
                    user.last_login
                ))
                connection.commit()
                success_count += 1
                logger.info(f"User '{username}' migrated successfully")
            except Error as e:
                logger.error(f"Error migrating user '{username}': {e}")
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
        
        logger.info(f"Migration completed: {success_count} users migrated successfully")
        return success_count > 0
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        return False

# Main function to test the module
if __name__ == "__main__":
    # Initialize the database
    if initialize_database():
        print("Database initialized successfully")
    else:
        print("Failed to initialize database")
