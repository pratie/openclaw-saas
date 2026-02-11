"""
Database module for OpenClaw SaaS
Handles all database operations using SQLite
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path

class Database:
    def __init__(self, db_path='openclaw_saas.db'):
        """Initialize database connection"""
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                credits REAL DEFAULT 50.0
            )
        ''')

        # Bots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                bot_name TEXT NOT NULL,
                bot_username TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                gateway_token TEXT NOT NULL,
                droplet_id INTEGER NOT NULL,
                region TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                message_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # API Keys table (for storing user's API keys)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                do_token TEXT,
                anthropic_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        conn.commit()
        conn.close()

    def create_user(self, username, email, password_hash):
        """Create a new user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO users (username, email, password_hash)
                VALUES (?, ?, ?)
            ''', (username, email, password_hash))

            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_user(self, username):
        """Get user by username"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

        conn.close()

        if user:
            return dict(user)
        return None

    def update_last_login(self, username):
        """Update user's last login time"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users
            SET last_login = ?
            WHERE username = ?
        ''', (datetime.now(), username))

        conn.commit()
        conn.close()

    def add_bot(self, username, bot_name, bot_username, ip_address, gateway_token, droplet_id, region):
        """Add a new bot"""
        user = self.get_user(username)
        if not user:
            return False

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO bots (user_id, bot_name, bot_username, ip_address,
                            gateway_token, droplet_id, region)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user['id'], bot_name, bot_username, ip_address, gateway_token, droplet_id, region))

        conn.commit()
        conn.close()
        return True

    def get_user_bots(self, username):
        """Get all bots for a user"""
        user = self.get_user(username)
        if not user:
            return []

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM bots
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user['id'],))

        bots = cursor.fetchall()
        conn.close()

        return [dict(bot) for bot in bots]

    def get_bot(self, bot_id):
        """Get bot by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
        bot = cursor.fetchone()

        conn.close()

        if bot:
            return dict(bot)
        return None

    def delete_bot(self, bot_id):
        """Delete a bot"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('DELETE FROM bots WHERE id = ?', (bot_id,))

            conn.commit()
            conn.close()
            return True
        except:
            return False

    def update_bot_status(self, bot_id, status):
        """Update bot status"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE bots
            SET status = ?
            WHERE id = ?
        ''', (status, bot_id))

        conn.commit()
        conn.close()

    def increment_message_count(self, bot_id):
        """Increment bot's message count"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE bots
            SET message_count = message_count + 1
            WHERE id = ?
        ''', (bot_id,))

        conn.commit()
        conn.close()

    def save_api_keys(self, username, anthropic_key=None):
        """Save user's API keys (DO token is managed by platform)"""
        user = self.get_user(username)
        if not user:
            return False

        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if keys exist
        cursor.execute('SELECT id FROM api_keys WHERE user_id = ?', (user['id'],))
        existing = cursor.fetchone()

        if existing:
            cursor.execute('''
                UPDATE api_keys
                SET anthropic_key = ?, updated_at = ?
                WHERE user_id = ?
            ''', (anthropic_key, datetime.now(), user['id']))
        else:
            cursor.execute('''
                INSERT INTO api_keys (user_id, anthropic_key)
                VALUES (?, ?)
            ''', (user['id'], anthropic_key))

        conn.commit()
        conn.close()
        return True

    def get_api_keys(self, username):
        """Get user's stored API keys"""
        user = self.get_user(username)
        if not user:
            return None

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM api_keys WHERE user_id = ?', (user['id'],))
        keys = cursor.fetchone()

        conn.close()

        if keys:
            return dict(keys)
        return None
