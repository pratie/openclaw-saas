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

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app)

# Initialize database
db = Database()

# Platform DigitalOcean token (must be set in environment variables)
DIGITALOCEAN_TOKEN = os.environ.get('DIGITALOCEAN_TOKEN')

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
    bots = db.get_user_bots(username)

    return render_template('dashboard.html',
                         username=username,
                         bots=bots,
                         bot_count=len(bots),
                         active_count=len([b for b in bots if b['status'] == 'running']))

@app.route('/api/login', methods=['POST'])
def login():
    """Login endpoint"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = db.get_user(username)
    if user and verify_password(password, user['password_hash']):
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
    return jsonify({'success': True})

@app.route('/api/deploy', methods=['POST'])
def deploy_bot():
    """Deploy new bot"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.json
    username = session['username']

    # Get stored Anthropic API key
    api_keys = db.get_api_keys(username)
    if not api_keys or not api_keys.get('anthropic_key'):
        return jsonify({
            'success': False,
            'message': 'Please configure your Anthropic API key in Settings first'
        }), 400

    try:
        # Check if platform DO token is configured
        if not DIGITALOCEAN_TOKEN or DIGITALOCEAN_TOKEN == 'YOUR_DO_TOKEN_HERE':
            return jsonify({
                'success': False,
                'message': 'Platform DigitalOcean token not configured. Please contact administrator.'
            }), 500

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
            anthropic_key=api_keys['anthropic_key'],
            region='nyc3',  # Hardcoded
            size='s-2vcpu-4gb',  # Hardcoded
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
        return jsonify({'success': False, 'error': str(e)}), 500

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
        # Try to delete from database even if droplet deletion fails
        db.delete_bot(bot_id)
        return jsonify({'success': False, 'message': f'Error deleting droplet: {str(e)}'}), 500

@app.route('/api/logs/<int:bot_id>', methods=['GET'])
def get_logs(bot_id):
    """Get bot logs"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    bot = db.get_bot(bot_id)
    if not bot:
        return jsonify({'success': False, 'message': 'Bot not found'}), 404

    # Fetch logs via SSH
    import subprocess
    try:
        result = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", f"root@{bot['ip_address']}",
             "journalctl -u openclaw-gateway -n 100 --no-pager"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return jsonify({'success': True, 'logs': result.stdout})

        return jsonify({'success': False, 'message': 'Could not fetch logs'}), 500

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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
            'has_anthropic_key': bool(api_keys.get('anthropic_key'))
        })

    return jsonify({
        'success': True,
        'has_do_token': False,
        'has_anthropic_key': False
    })

@app.route('/api/settings', methods=['POST'])
def save_settings():
    """Save user settings"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.json
    username = session['username']

    anthropic_key = data.get('anthropic_key', '').strip()

    if not anthropic_key:
        return jsonify({
            'success': False,
            'message': 'Anthropic API key is required'
        }), 400

    if db.save_api_keys(username, anthropic_key=anthropic_key):
        return jsonify({'success': True, 'message': 'API key saved successfully'})

    return jsonify({'success': False, 'message': 'Failed to save API key'}), 500

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

        # Initialize Dodo client
        env_mode = os.environ.get('ENV', 'development')
        client = DodoPayments(
            bearer_token=dodo_api_key,
            environment="test_mode" if env_mode == "development" else "live_mode"
        )

        # Create payment
        payment = client.payments.create(
            payment_link=True,
            billing={
                "city": "New York",
                "country": "US",
                "state": "NY",
                "street": "123 Example Street",
                "zipcode": 10001,
            },
            customer={
                "email": email,
                "name": email.split("@")[0],
            },
            product_cart=[
                {"product_id": dodo_product_id, "quantity": 1}
            ],
            return_url=os.environ.get('DODO_SUCCESS_URL', 'https://open-claw.space/?payment=success')
        )

        # Webhook will handle storing payment status when user pays
        return jsonify({
            'success': True,
            'checkout_url': payment.payment_link,
            'price': '$50'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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
                    # User exists, activate payment immediately
                    db.update_payment_status(customer_email, payment_id, 'monthly')
                else:
                    # User doesn't exist yet, store as pending payment
                    # Will be auto-activated when they register
                    db.store_pending_payment(customer_email, payment_id, 'monthly')

        return jsonify({'status': 'ok'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
