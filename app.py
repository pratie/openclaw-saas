#!/usr/bin/env python3
"""
🤖 OpenClaw SaaS Platform
Cyberpunk Web Interface
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import os
from datetime import datetime, timedelta
from backend.database import Database
from backend.deployer import BotDeployer
from backend.auth import hash_password, verify_password
import secrets
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow

app = Flask(__name__)

# Use persistent secret key from environment variable
# IMPORTANT: Set SECRET_KEY in Railway to a random hex string
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    # Generate a random key for local development
    SECRET_KEY = secrets.token_hex(32)
    print("⚠️  WARNING: Using random SECRET_KEY. Set SECRET_KEY environment variable in production!")

app.secret_key = SECRET_KEY

# Session configuration for production
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('ENV') == 'production'  # HTTPS only in prod
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent XSS attacks
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # 7-day sessions

CORS(app)

# Initialize database
db = Database()

# Platform DigitalOcean token (must be set in environment variables)
DIGITALOCEAN_TOKEN = os.environ.get('DIGITALOCEAN_TOKEN')

# Platform NVIDIA NIM API key — used for all customer bot deployments
NVIDIA_API_KEY = os.environ.get('NVIDIA_API_KEY')

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')

# Disable HTTPS requirement for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

@app.route('/')
def index():
    """Main landing page"""
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard page - requires auth"""
    if 'username' not in session:
        return redirect(url_for('index'))

    username = session['username']
    user = db.get_user(username)
    bots = db.get_user_bots(username)

    return render_template('dashboard.html',
                         username=username,
                         bots=bots,
                         bot_count=len(bots),
                         active_count=len([b for b in bots if b['status'] == 'running']),
                         has_paid=user.get('has_paid', 0) if user else 0)

@app.route('/api/login', methods=['POST'])
def login():
    """Login endpoint"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = db.get_user(username)
    if user and verify_password(password, user['password_hash']):
        session.permanent = True  # Make session last for PERMANENT_SESSION_LIFETIME
        session['username'] = username
        return jsonify({'success': True, 'message': 'Login successful'})

    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/register', methods=['POST'])
def register():
    """Register endpoint"""
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if db.get_user(username):
        return jsonify({'success': False, 'message': 'Username already exists'}), 400

    password_hash = hash_password(password)
    if db.create_user(username, email, password_hash):
        return jsonify({'success': True, 'message': 'Account created'})

    return jsonify({'success': False, 'message': 'Registration failed'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout endpoint"""
    session.pop('username', None)
    session.pop('google_id', None)
    session.pop('email', None)
    return jsonify({'success': True})

# ========== GOOGLE OAUTH ROUTES ==========

@app.route('/auth/google')
def google_auth():
    """Initiate Google OAuth flow"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return "Google OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.", 500

    # Create flow instance
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI]
            }
        },
        scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']
    )

    flow.redirect_uri = GOOGLE_REDIRECT_URI

    # Generate authorization URL
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )

    # Store state in session for CSRF protection
    session['state'] = state

    return redirect(authorization_url)

@app.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    # Verify state to prevent CSRF
    state = session.get('state')
    if not state:
        return "Invalid session state", 400

    try:
        # Create flow instance
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI]
                }
            },
            scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile'],
            state=state
        )

        flow.redirect_uri = GOOGLE_REDIRECT_URI

        # Exchange authorization code for tokens
        flow.fetch_token(authorization_response=request.url)

        # Get user info from Google
        credentials = flow.credentials
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )

        # Extract user information
        google_id = id_info['sub']
        email = id_info['email']
        name = id_info.get('name', email.split('@')[0])

        # Check if user exists
        user = db.get_user_by_google_id(google_id)

        if not user:
            # User doesn't exist, create new account
            # Generate username from email
            username = email.split('@')[0].replace('.', '_').replace('-', '_')

            # Ensure username is unique
            base_username = username
            counter = 1
            while db.get_user(username):
                username = f"{base_username}{counter}"
                counter += 1

            # Create user account (no password needed for OAuth users)
            db.create_google_user(username, email, google_id, name)
        else:
            username = user['username']

        # Log user in
        session.permanent = True
        session['username'] = username
        session['google_id'] = google_id
        session['email'] = email

        # Check if user has already connected Telegram
        # If not, redirect to Telegram connection screen
        # For now, always redirect to Telegram connection (we'll add a check later)
        return redirect(url_for('connect_telegram_page'))

    except Exception as e:
        print(f"❌ Google OAuth error: {str(e)}")
        return f"Authentication failed: {str(e)}", 500

# ========== TELEGRAM CONNECTION ROUTES ==========

@app.route('/connect/telegram')
def connect_telegram_page():
    """Telegram connection page - shown after Google OAuth"""
    if 'username' not in session:
        return redirect(url_for('index'))

    return render_template('connect-telegram.html')

@app.route('/api/connect-telegram', methods=['POST'])
def connect_telegram():
    """Save Telegram token to session"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.json
    telegram_token = data.get('telegram_token', '').strip()

    if not telegram_token or ':' not in telegram_token:
        return jsonify({'success': False, 'message': 'Invalid Telegram bot token'}), 400

    # Store in session (we'll validate it during deployment)
    session['telegram_token'] = telegram_token

    return jsonify({'success': True, 'message': 'Telegram connected'})

@app.route('/deploy')
def deploy_page():
    """Deploy screen - shown after Telegram connection"""
    if 'username' not in session:
        return redirect(url_for('index'))

    if 'telegram_token' not in session:
        return redirect(url_for('connect_telegram_page'))

    # For now, just show a simple message (we'll build the full deploy screen in Phase 4)
    return f"""
    <html>
    <head><title>Deploy - OpenClaw</title></head>
    <body style="background: #0a0a0a; color: #fafafa; font-family: 'Inter', sans-serif; padding: 60px; text-align: center;">
        <h1>✅ Telegram Connected!</h1>
        <p>Next step: Deploy your OpenClaw bot</p>
        <p>(Phase 4 - Coming next!)</p>
        <p><a href="/dashboard" style="color: #22c55e;">Go to Dashboard</a></p>
    </body>
    </html>
    """

@app.route('/api/deploy', methods=['POST'])
def deploy_bot():
    """Deploy new bot"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.json
    username = session['username']

    # Check if user has paid subscription
    user = db.get_user(username)
    if not user or not user.get('has_paid'):
        return jsonify({
            'success': False,
            'message': 'Active subscription required. Please subscribe to deploy AI agents.',
            'requires_payment': True
        }), 402  # 402 Payment Required

    try:
        # Check if platform keys are configured
        if not DIGITALOCEAN_TOKEN or DIGITALOCEAN_TOKEN == 'YOUR_DO_TOKEN_HERE':
            return jsonify({
                'success': False,
                'message': 'Platform DigitalOcean token not configured. Please contact administrator.'
            }), 500

        if not NVIDIA_API_KEY:
            return jsonify({
                'success': False,
                'message': 'Platform AI key not configured. Please contact administrator.'
            }), 500

        # Get optional user-provided OpenRouter key (for fallback models)
        api_keys = db.get_api_keys(username)
        openrouter_key = api_keys.get('anthropic_key') if api_keys else None  # Column name stays same

        # Use platform's DigitalOcean token
        deployer = BotDeployer(DIGITALOCEAN_TOKEN)

        # Get bot username from telegram token
        bot_username = deployer.get_bot_username(data['telegram_token'])

        if bot_username == 'unknown_bot':
            return jsonify({
                'success': False,
                'message': 'Invalid Telegram bot token. Please check your token from @BotFather.'
            }), 400

        # Sanitize bot name: only allow a-z, A-Z, 0-9, . and -
        import re
        safe_bot_name = re.sub(r'[^a-zA-Z0-9.-]', '-', bot_username.lower())
        safe_bot_name = f"openclaw-{safe_bot_name}"

        result = deployer.deploy(
            telegram_token=data['telegram_token'],
            nvidia_key=NVIDIA_API_KEY,           # Platform NVIDIA NIM key (default AI provider)
            openrouter_key=openrouter_key,        # User's OpenRouter key (optional fallback)
            region='nyc3',  # Hardcoded
            size='s-2vcpu-2gb',  # Starter Plan: 2 vCPU · 2 GB RAM · 20 GB SSD
            bot_name=safe_bot_name
        )

        if result['success']:
            # Save to database
            db.add_bot(
                username=username,
                bot_name=bot_username,  # Store original name for display
                bot_username=result['bot_username'],
                ip_address=result['ip_address'],
                gateway_token=result['gateway_token'],
                droplet_id=result['droplet_id'],
                region='nyc3'
            )

            return jsonify(result)

        return jsonify(result), 500

    except Exception as e:
        # Log error for debugging (server-side only)
        print(f"❌ Deployment error: {str(e)}")

        # Return user-friendly error message
        return jsonify({
            'success': False,
            'message': 'Failed to deploy AI agent. Please check your tokens and try again.'
        }), 500

@app.route('/api/bots', methods=['GET'])
def get_bots():
    """Get user's bots"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    bots = db.get_user_bots(session['username'])
    return jsonify({'success': True, 'bots': bots})

@app.route('/api/bots/<int:bot_id>', methods=['DELETE'])
def delete_bot(bot_id):
    """Delete a bot and its DigitalOcean droplet"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    # Get bot info before deleting (we need the droplet_id)
    bot = db.get_bot(bot_id)
    if not bot:
        return jsonify({'success': False, 'message': 'Bot not found'}), 404

    try:
        # Delete the DigitalOcean droplet
        from pydo import Client
        client = Client(token=DIGITALOCEAN_TOKEN)

        # Destroy the droplet
        client.droplets.destroy(droplet_id=bot['droplet_id'])

        # Delete from database
        if db.delete_bot(bot_id):
            return jsonify({'success': True, 'message': 'Bot and droplet deleted successfully'})

        return jsonify({'success': False, 'message': 'Droplet deleted but failed to remove from database'}), 500

    except Exception as e:
        # Log error for debugging (server-side only)
        print(f"❌ Delete droplet error: {str(e)}")

        # Try to delete from database even if droplet deletion fails
        db.delete_bot(bot_id)

        # Return user-friendly error message
        return jsonify({
            'success': False,
            'message': 'Failed to delete bot. The bot may have been removed from the list. Please contact support if the issue persists.'
        }), 500

@app.route('/api/logs/<int:bot_id>', methods=['GET'])
def get_logs(bot_id):
    """Get bot logs — cloud-init deploy logs + openclaw service logs"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    bot = db.get_bot(bot_id)
    if not bot:
        return jsonify({'success': False, 'message': 'Bot not found'}), 404

    import subprocess
    output_parts = []

    ssh_base = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8"]

    try:
        # 1. Cloud-init deployment logs (shows what's happening during setup)
        deploy_result = subprocess.run(
            ssh_base + [f"root@{bot['ip_address']}",
             "tail -n 80 /var/log/cloud-init-output.log 2>/dev/null || echo '(cloud-init log not available yet)'"],
            capture_output=True, text=True, timeout=12
        )
        if deploy_result.stdout.strip():
            output_parts.append("=== DEPLOYMENT LOG (cloud-init) ===")
            output_parts.append(deploy_result.stdout.strip())

        # 2. OpenClaw service startup logs (first 30 lines — shows initial Telegram connection)
        startup_result = subprocess.run(
            ssh_base + [f"root@{bot['ip_address']}",
             "journalctl -u openclaw-gateway --no-pager 2>/dev/null | head -30 || echo '(service not started yet)'"],
            capture_output=True, text=True, timeout=12
        )
        if startup_result.stdout.strip():
            output_parts.append("\n=== OPENCLAW STARTUP LOG ===")
            output_parts.append(startup_result.stdout.strip())

        # 3. Recent service logs filtered (no bonjour spam)
        recent_result = subprocess.run(
            ssh_base + [f"root@{bot['ip_address']}",
             "journalctl -u openclaw-gateway --no-pager 2>/dev/null | grep -v 'bonjour' | tail -30"],
            capture_output=True, text=True, timeout=12
        )
        if recent_result.stdout.strip():
            output_parts.append("\n=== RECENT ACTIVITY (bonjour filtered) ===")
            output_parts.append(recent_result.stdout.strip())

        if output_parts:
            return jsonify({'success': True, 'logs': '\n'.join(output_parts)})

        return jsonify({'success': True, 'logs': 'Server is starting up, logs not available yet. Try again in 30 seconds.'})

    except subprocess.TimeoutExpired:
        return jsonify({'success': True, 'logs': 'Server is still booting. Try again in 30 seconds.'})

    except Exception as e:
        print(f"❌ Fetch logs error: {str(e)}")
        return jsonify({'success': True, 'logs': 'Unable to connect to server yet. It may still be booting.'})

@app.route('/api/bots/<int:bot_id>/status', methods=['GET'])
def check_bot_status(bot_id):
    """Check if bot's Telegram is ready"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    bot = db.get_bot(bot_id)
    if not bot:
        return jsonify({'success': False, 'message': 'Bot not found'}), 404

    # Check if Telegram is connected by looking for the telegram startup log
    import subprocess
    try:
        result = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
             f"root@{bot['ip_address']}",
             "journalctl -u openclaw-gateway --no-pager | grep -q '\\[telegram\\].*starting provider' && echo 'ready' || echo 'initializing'"],
            capture_output=True,
            text=True,
            timeout=10
        )

        telegram_ready = 'ready' in result.stdout

        # Also check if service exists and is active
        service_result = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
             f"root@{bot['ip_address']}",
             "systemctl is-active openclaw-gateway 2>&1"],
            capture_output=True,
            text=True,
            timeout=10
        )

        service_active = 'active' in service_result.stdout

        if telegram_ready and service_active:
            status = 'ready'
        elif service_active:
            status = 'initializing'
        else:
            status = 'deploying'

        return jsonify({
            'success': True,
            'status': status,
            'telegram_ready': telegram_ready,
            'service_active': service_active
        })

    except Exception as e:
        return jsonify({
            'success': True,
            'status': 'deploying',
            'telegram_ready': False,
            'service_active': False
        })

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get user settings (masked)"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    api_keys = db.get_api_keys(session['username'])
    if api_keys:
        # Return masked values
        return jsonify({
            'success': True,
            'has_do_token': bool(api_keys.get('do_token')),
            'has_openrouter_key': bool(api_keys.get('anthropic_key'))  # Column name stays same
        })

    return jsonify({
        'success': True,
        'has_do_token': False,
        'has_openrouter_key': False
    })

@app.route('/api/settings', methods=['POST'])
def save_settings():
    """Save user settings"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.json
    username = session['username']

    openrouter_key = data.get('openrouter_key', '').strip()

    # OpenRouter key is optional — bots run on NVIDIA NIM by default
    # Providing it enables Claude fallback models
    if db.save_api_keys(username, anthropic_key=openrouter_key or None):  # Column name stays same
        msg = 'OpenRouter key saved (Claude fallbacks enabled)' if openrouter_key else 'Settings saved'
        return jsonify({'success': True, 'message': msg})

    return jsonify({'success': False, 'message': 'Failed to save settings'}), 500

# ========== PAYMENT ROUTES ==========

@app.route('/api/payment/create-checkout', methods=['POST'])
def create_checkout():
    """Create Dodo Payments checkout link (can be called before signup for max conversion)"""
    try:
        from dodopayments import DodoPayments

        data = request.json
        email = data.get('email')

        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400

        # Get Dodo credentials from environment
        dodo_api_key = os.environ.get('DODO_PAYMENTS_API_KEY')
        dodo_product_id = os.environ.get('DODO_PRODUCT_ID')

        if not dodo_api_key or not dodo_product_id:
            return jsonify({'success': False, 'message': 'Payment system not configured'}), 500

        # Initialize Dodo client (always use live_mode in production)
        client = DodoPayments(
            bearer_token=dodo_api_key,
            environment="live_mode"
        )

        # Create checkout session (correct method for subscription products)
        checkout_session = client.checkout_sessions.create(
            product_cart=[
                {"product_id": dodo_product_id, "quantity": 1}
            ],
            customer={
                "email": email,
                "name": email.split("@")[0],
            },
            billing_address={
                "city": "New York",
                "country": "US",
                "state": "NY",
                "street": "123 Example Street",
                "zipcode": "10001",
            },
            return_url=os.environ.get('DODO_SUCCESS_URL', 'https://open-claw.space/?payment=success')
        )

        # Webhook will handle storing payment status when user pays
        return jsonify({
            'success': True,
            'checkout_url': checkout_session.checkout_url,
            'price': '$49/month'
        })

    except Exception as e:
        # Log the actual error for debugging (server-side only)
        print(f"❌ Payment error: {str(e)}")

        # Return user-friendly error message (never expose internal details)
        return jsonify({
            'success': False,
            'message': 'Payment system temporarily unavailable. Please try again or contact support.'
        }), 500

@app.route('/api/payment/webhook', methods=['POST'])
def payment_webhook():
    """Handle Dodo Payments webhook (server-to-server payment confirmation)"""
    try:
        from standardwebhooks import Webhook

        webhook_secret = os.environ.get('DODO_PAYMENTS_WEBHOOK_SECRET')
        if not webhook_secret:
            return jsonify({'error': 'Webhook not configured'}), 500

        # Get webhook headers
        webhook_id = request.headers.get('webhook-id')
        webhook_signature = request.headers.get('webhook-signature')
        webhook_timestamp = request.headers.get('webhook-timestamp')

        # Verify signature
        wh = Webhook(webhook_secret)
        raw_body = request.get_data()

        try:
            wh.verify(raw_body, {
                "webhook-id": webhook_id,
                "webhook-signature": webhook_signature,
                "webhook-timestamp": webhook_timestamp,
            })
        except Exception:
            return jsonify({'error': 'Invalid signature'}), 400

        # Process webhook
        payload = request.json
        event_type = payload.get('type')

        if event_type == 'payment.succeeded':
            data = payload.get('data', {})
            payment_id = data.get('payment_id')
            customer = data.get('customer', {})
            customer_email = customer.get('email')

            if customer_email:
                # Try to update existing user first
                user = db.get_user_by_email(customer_email)
                if user:
                    # User exists, activate payment immediately (monthly subscription)
                    db.update_payment_status(customer_email, payment_id, 'monthly')
                else:
                    # User doesn't exist yet, store as pending payment
                    # Will be auto-activated when they register
                    db.store_pending_payment(customer_email, payment_id, 'monthly')

        return jsonify({'status': 'ok'})

    except Exception as e:
        # Log error for debugging (server-side only)
        print(f"❌ Webhook error: {str(e)}")

        # Return generic error (never expose internal webhook details)
        return jsonify({'error': 'Webhook processing failed'}), 500

@app.route('/api/payment/success', methods=['POST'])
def payment_success():
    """Called by frontend after user returns from Dodo checkout"""
    data = request.json
    email = data.get('email')
    payment_id = data.get('paymentId')

    if email:
        user = db.get_user_by_email(email)
        if user and not user.get('has_paid'):
            db.update_payment_status(email, payment_id or 'manual', 'monthly')

    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
