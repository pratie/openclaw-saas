"""
Authentication module for OpenClaw SaaS
Handles password hashing and verification
"""

import hashlib
import secrets

def hash_password(password):
    """Hash a password with salt"""
    salt = secrets.token_hex(32)
    pwdhash = hashlib.pbkdf2_hmac('sha256',
                                   password.encode('utf-8'),
                                   salt.encode('utf-8'),
                                   100000)
    return salt + pwdhash.hex()

def verify_password(password, stored_hash):
    """Verify a password against stored hash"""
    salt = stored_hash[:64]
    stored_pwdhash = stored_hash[64:]
    pwdhash = hashlib.pbkdf2_hmac('sha256',
                                   password.encode('utf-8'),
                                   salt.encode('utf-8'),
                                   100000)
    return pwdhash.hex() == stored_pwdhash
