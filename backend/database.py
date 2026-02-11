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

        # Pending Payments table (for payments before user registration)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                payment_id TEXT NOT NULL,
                subscription_plan TEXT DEFAULT 'daily',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Add payment columns if they don't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN has_paid INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            cursor.execute('ALTER TABLE users ADD COLUMN payment_date TIMESTAMP')
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute('ALTER TABLE users ADD COLUMN dodo_payment_id TEXT')
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN subscription_plan TEXT DEFAULT 'none'")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute('ALTER TABLE users ADD COLUMN plan_expires_at TIMESTAMP')
        except sqlite3.OperationalError:
            pass

        conn.commit()
        conn.close()

    def create_user(self, username, email, password_hash):
        """Create a new user and auto-activate if pending payment exists"""
        try:
            from datetime import timedelta

            conn = self.get_connection()
            cursor = conn.cursor()

            # Check for pending payment
            pending = self.get_pending_payment(email)

            if pending:
                # Create user with payment already activated (daily subscription)
                plan_expires_at = datetime.now() + timedelta(days=1)
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, has_paid,
                                     payment_date, dodo_payment_id, subscription_plan, plan_expires_at)
                    VALUES (?, ?, ?, 1, ?, ?, ?, ?)
                ''', (username, email, password_hash, datetime.now(),
                      pending['payment_id'], pending['subscription_plan'], plan_expires_at))

                # Clear pending payment
                self.clear_pending_payment(email)
            else:
                # Create user normally
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

    def get_user_by_email(self, email):
        """Get user by email"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()

        conn.close()

        if user:
            return dict(user)
        return None

    def update_payment_status(self, email, payment_id, subscription_plan='daily'):
        """Update user payment status"""
        from datetime import timedelta

        conn = self.get_connection()
        cursor = conn.cursor()

        # For daily subscriptions, set expiration to 1 day from now
        # Note: Dodo handles the recurring billing automatically
        plan_expires_at = datetime.now() + timedelta(days=1)

        cursor.execute('''
            UPDATE users
            SET has_paid = 1,
                payment_date = ?,
                dodo_payment_id = ?,
                subscription_plan = ?,
                plan_expires_at = ?
            WHERE email = ?
        ''', (datetime.now(), payment_id, subscription_plan, plan_expires_at, email))

        conn.commit()
        conn.close()
        return True

    def store_pending_payment(self, email, payment_id, subscription_plan='daily'):
        """Store pending payment for users who haven't registered yet"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # First try to update existing user (if they exist)
        user = self.get_user_by_email(email)
        if user:
            cursor.execute('''
                UPDATE users
                SET dodo_payment_id = ?,
                    subscription_plan = 'pending_daily'
                WHERE email = ?
            ''', (payment_id, email))
        else:
            # Store in pending_payments table for future registration
            cursor.execute('''
                INSERT INTO pending_payments (email, payment_id, subscription_plan)
                VALUES (?, ?, ?)
            ''', (email, payment_id, subscription_plan))

        conn.commit()
        conn.close()
        return True

    def get_pending_payment(self, email):
        """Get pending payment for an email"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM pending_payments
            WHERE email = ?
            ORDER BY created_at DESC
            LIMIT 1
        ''', (email,))

        payment = cursor.fetchone()
        conn.close()

        if payment:
            return dict(payment)
        return None

    def clear_pending_payment(self, email):
        """Clear pending payment after user registration"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM pending_payments WHERE email = ?', (email,))

        conn.commit()
        conn.close()
        return True
