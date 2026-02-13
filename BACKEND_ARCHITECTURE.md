# OpenClaw SaaS Platform - Complete Backend Architecture

> Comprehensive documentation generated through deep analysis with 4 specialized AI agents

## Executive Summary

This is a **fully automated SaaS platform** that deploys private OpenClaw AI agent instances on DigitalOcean droplets. Each user gets their own dedicated Ubuntu 24.04 server running OpenClaw with Claude Opus 4, accessible via Telegram.

**Tech Stack:**
- **Backend**: Python Flask + SQLite
- **Infrastructure**: DigitalOcean API (pydo)
- **Payment**: Dodo Payments (daily subscription)
- **AI Agent**: OpenClaw (Node.js framework)
- **LLM**: Anthropic Claude Opus 4.6 (primary) + Haiku 3.5 (fallback)
- **Messaging**: Telegram (via BotFather)

---

## What is OpenClaw?

**OpenClaw** is a free, open-source (MIT) autonomous AI agent framework created by Peter Steinberger. It's a privacy-focused, local-first AI assistant that:

- Runs on your own server (not cloud-hosted)
- Integrates with 12+ messaging platforms (Telegram, WhatsApp, Discord, Signal, etc.)
- Supports 15+ LLM providers (Anthropic, OpenAI, Google, OpenRouter, etc.)
- Stores all data locally as Markdown/JSONL files
- Has 188,503+ GitHub stars
- Features autonomous scheduling, browser automation, and memory systems

**Key Features:**
- **Multi-agent routing**: Different channels → isolated agent instances
- **Heartbeat engine**: Autonomous monitoring and actions
- **AgentSkills**: 5,705+ community skills from ClawHub
- **Memory system**: JSONL transcripts + Markdown long-term memory
- **Browser automation**: Web scraping, semantic snapshots
- **Cron jobs**: Built-in scheduler with ISO 8601/cron syntax
- **Docker sandboxing**: Isolated execution for security

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Frontend (Flask Templates)              │
│         index.html (Landing) | dashboard.html           │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  Flask Backend (app.py)                  │
│  • Authentication (login/register/logout)               │
│  • Bot Management (deploy/list/delete)                  │
│  • Dodo Payments (checkout/webhook)                     │
│  • Settings (API keys)                                  │
└───────┬──────────────┬──────────────┬───────────────────┘
        │              │              │
        ▼              ▼              ▼
   ┌─────────┐   ┌──────────┐   ┌────────────┐
   │Database │   │Deployer  │   │Dodo        │
   │(SQLite) │   │(DigitalO)│   │Payments    │
   └─────────┘   └────┬─────┘   └────────────┘
                      │
                      ▼
              ┌───────────────┐
              │DigitalOcean   │
              │Creates Ubuntu │
              │+ OpenClaw     │
              └───────┬───────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
    Droplet 1                   Droplet 2
    (User A)                    (User B)
    ┌──────────────┐            ┌──────────────┐
    │OpenClaw      │            │OpenClaw      │
    │Gateway:18789 │            │Gateway:18789 │
    │              │            │              │
    │Telegram Bot  │            │Telegram Bot  │
    │Claude Opus 4 │            │Claude Opus 4 │
    │User's API key│            │User's API key│
    └──────────────┘            └──────────────┘
```

---

## Complete User Journey

### 1. **Landing Page → Payment** (Conversion Flow)

```
User visits https://open-claw.space
    ↓
Sees scarcity design: "13 left", "87% gone", "50% OFF"
    ↓
Clicks "TRY OPENCLAW RISK-FREE"
    ↓
Modal appears: "Enter email to checkout"
    ↓
POST /api/payment/create-checkout {"email": "user@example.com"}
    ↓
Backend: client.checkout_sessions.create()
    ↓
Dodo Payments returns: checkout_url
    ↓
User redirected to Dodo hosted checkout page
    ↓
User enters card details → Pays $3/day subscription
    ↓
Dodo Payments webhook → POST /api/payment/webhook
    ↓
Backend verifies signature, processes payment.succeeded
    ↓
If user exists: Update has_paid=1, plan_expires_at=now+1day
If no user: Store in pending_payments table
    ↓
User redirected to: https://open-claw.space/?payment=success
```

**Payment Lifecycle:**
- Subscription: Daily recurring ($3/day)
- Dodo handles billing automatically
- Platform tracks: `has_paid`, `payment_date`, `dodo_payment_id`, `plan_expires_at`

### 2. **Registration** (Account Creation)

```
User clicks "Register" or auto-opens after payment
    ↓
POST /api/register {"username": "johndoe", "email": "user@example.com", "password": "secret"}
    ↓
Backend: hash_password() using PBKDF2-HMAC-SHA256 (100,000 iterations)
    ↓
Database: Check pending_payments for email
    ↓
If pending payment found:
    → Create user with has_paid=1
    → Set subscription_plan='daily'
    → Set plan_expires_at=now+1day
    → Clear pending payment
Else:
    → Create user with has_paid=0
    ↓
Return: {"success": true, "message": "Account created"}
```

**Security:**
- Passwords: PBKDF2-HMAC-SHA256, 32-byte salt, 100k iterations
- Sessions: 7-day lifetime, HTTPOnly cookies, HTTPS-only in production
- CSRF: SameSite=Lax cookies

### 3. **Login & Dashboard Access**

```
User logs in → POST /api/login {"username": "johndoe", "password": "secret"}
    ↓
Backend: verify_password() against stored hash
    ↓
Create Flask session (permanent, 7-day expiration)
    ↓
Redirect to /dashboard
    ↓
Dashboard shows:
    • Payment status (has_paid)
    • Bot count
    • Active bots
    • Deploy button (disabled if not paid)
```

### 4. **API Key Configuration** (Required for Deployment)

```
User goes to Settings tab
    ↓
Enters Anthropic API key: sk-ant-...
    ↓
POST /api/settings {"anthropic_key": "sk-ant-..."}
    ↓
Database: save_api_keys(username, anthropic_key)
    ↓
Stored in api_keys table (user_id, anthropic_key, updated_at)
```

**Note:** DigitalOcean token is platform-managed (DIGITALOCEAN_TOKEN env var), not user-provided.

### 5. **Bot Deployment** (The Magic Happens)

```
User clicks "DEPLOY BOT"
    ↓
Modal: "Enter Telegram Bot Token"
    ↓
User gets token from @BotFather on Telegram
    ↓
POST /api/deploy {"telegram_token": "1234567890:ABC..."}
    ↓
Backend validates:
    1. has_paid == 1 (else 402 Payment Required)
    2. anthropic_key exists (else 400 Bad Request)
    3. Telegram token valid (calls Telegram API)
    ↓
Create BotDeployer(DIGITALOCEAN_TOKEN)
    ↓
Generate gateway_token (32 random chars)
    ↓
Generate cloud-init script with:
    • User's telegram_token
    • User's anthropic_key
    • Generated gateway_token
    ↓
Call DigitalOcean API: droplets.create()
    ↓
Wait for droplet status="active" (max 2 minutes, poll every 5s)
    ↓
Get public IPv4 address
    ↓
Store in database: add_bot(username, bot_name, ip, gateway_token, droplet_id, region)
    ↓
Return: {"success": true, "ip_address": "165.227.x.x", "bot_username": "@my_bot", ...}
    ↓
Dashboard updates: Shows new bot card
```

**Droplet Specifications:**
- OS: Ubuntu 24.04 LTS x64
- Size: s-2vcpu-4gb (2 vCPUs, 4GB RAM, 80GB SSD)
- Region: nyc3 (New York)
- Cost: ~$24/month per droplet
- Tags: ["openclaw", "saas", "bot"]

### 6. **Cloud-Init Script Execution** (Runs on Droplet)

The cloud-init script auto-configures the fresh Ubuntu server:

```bash
#!/bin/bash

# 1. SYSTEM SETUP (~30-60 seconds)
apt-get update && upgrade -y
apt-get install curl git python3-pip ufw fail2ban jq

# Install Node.js 22
curl -fsSL https://deb.nodesource.com/setup_22.x | bash
apt-get install nodejs

# 2. OPENCLAW INSTALLATION (~20-30 seconds)
npm install -g pnpm@latest
npm install -g openclaw@latest

# 3. FIREWALL CONFIGURATION
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 18789/tcp  # OpenClaw Gateway
ufw --force enable

# 4. CREATE OPENCLAW CONFIG
mkdir -p /root/.openclaw/workspace
cat > /root/.openclaw/openclaw.json << 'EOF'
{
  "gateway": {
    "port": 18789,
    "mode": "local",
    "bind": "lan",
    "auth": {"mode": "token", "token": "<GATEWAY_TOKEN>"}
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "anthropic/claude-opus-4-6",
        "fallbacks": ["anthropic/claude-3-5-haiku-20241022"]
      },
      "workspace": "~/.openclaw/workspace",
      "memorySearch": {"enabled": true}
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "<TELEGRAM_TOKEN>",
      "dmPolicy": "open",
      "groupPolicy": "open",
      "streamMode": "partial"
    }
  },
  "auth": {
    "profiles": {
      "anthropic-main": {"provider": "anthropic", "mode": "token"}
    }
  }
}
EOF

# 5. CREATE ENVIRONMENT FILE
cat > /root/.openclaw/.env << 'EOF'
ANTHROPIC_API_KEY=<USER_API_KEY>
OPENCLAW_GATEWAY_TOKEN=<GATEWAY_TOKEN>
NODE_ENV=production
EOF

# 6. ENABLE TELEGRAM PLUGIN
openclaw doctor --fix --yes

# 7. CREATE SYSTEMD SERVICE
cat > /etc/systemd/system/openclaw-gateway.service << 'EOF'
[Unit]
Description=OpenClaw Gateway
After=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root
EnvironmentFile=/root/.openclaw/.env
ExecStart=/usr/bin/openclaw gateway --bind lan --port 18789
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 8. START SERVICE
systemctl daemon-reload
systemctl enable openclaw-gateway
systemctl start openclaw-gateway
```

**Total deployment time:** ~3-4 minutes from button click to Telegram bot responding.

### 7. **Bot Usage** (Steady State)

```
User messages Telegram bot
    ↓
Telegram sends webhook to droplet (via internet)
    ↓
OpenClaw Gateway receives message (port 18789)
    ↓
Gateway authenticates via gateway_token
    ↓
OpenClaw creates session context:
    • Loads conversation history from JSONL
    • Loads agent memory from AGENTS.md
    • Assembles system prompt
    ↓
Sends request to Anthropic API (Claude Opus 4.6)
    ↓
Anthropic returns response
    ↓
OpenClaw stores interaction in ~/.openclaw/agents/.../sessions/...jsonl
    ↓
Sends response back to Telegram
    ↓
User receives AI response
```

**Message Tracking:**
- Database: `increment_message_count(bot_id)` on each message
- Logs: `journalctl -u openclaw-gateway` (accessible via dashboard)

### 8. **Monitoring & Logs**

```
User clicks "View Logs" in dashboard
    ↓
GET /api/logs/<bot_id>
    ↓
Backend: SSH into droplet using platform's SSH key
    ↓
Run: journalctl -u openclaw-gateway -n 100 --no-pager
    ↓
Capture output and return to frontend
    ↓
Dashboard displays logs in terminal-style UI
```

**Status Checking:**
```
GET /api/bots/<bot_id>/status
    ↓
SSH: journalctl | grep '\\[telegram\\].*starting provider'
SSH: systemctl is-active openclaw-gateway
    ↓
Return status: "ready", "initializing", or "deploying"
```

### 9. **Bot Deletion**

```
User clicks "Delete Bot"
    ↓
DELETE /api/bots/<bot_id>
    ↓
Get bot info from database (need droplet_id)
    ↓
DigitalOcean API: client.droplets.destroy(droplet_id)
    ↓
Delete from database: delete_bot(bot_id)
    ↓
Return: {"success": true, "message": "Bot and droplet deleted"}
```

**Cleanup:**
- Droplet permanently destroyed
- All data on droplet lost (conversations, configs, logs)
- Database record removed
- No refunds (subscription continues until canceled)

---

## Database Schema

### **users** table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    credits REAL DEFAULT 50.0,
    has_paid INTEGER DEFAULT 0,
    payment_date TIMESTAMP,
    dodo_payment_id TEXT,
    subscription_plan TEXT DEFAULT 'none',  -- 'daily', 'pending_daily'
    plan_expires_at TIMESTAMP
)
```

### **bots** table
```sql
CREATE TABLE bots (
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
```

### **api_keys** table
```sql
CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    do_token TEXT,  -- Not used (platform-managed)
    anthropic_key TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
```

### **pending_payments** table
```sql
CREATE TABLE pending_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    payment_id TEXT NOT NULL,
    subscription_plan TEXT DEFAULT 'daily',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Relationships:**
```
users (1) ←──── (N) bots
  ↑
  └──── (1) api_keys

pending_payments → users (linked by email during registration)
```

---

## LLM Configuration

### Model Setup in OpenClaw

**Primary Model:** Claude Opus 4.6
```json
{
  "model": {
    "primary": "anthropic/claude-opus-4-6",
    "fallbacks": ["anthropic/claude-3-5-haiku-20241022"]
  }
}
```

**Why Opus 4.6?**
- Long-context strength (200K tokens)
- Better prompt-injection resistance
- Superior reasoning capabilities
- Hardcoded in cloud-init (users can't change)

**Fallback Model:** Claude Haiku 3.5
- Used if Opus rate-limited or unavailable
- Cost savings for simpler queries
- Automatic failover by OpenClaw

### Authentication

**Environment Variables:**
```bash
ANTHROPIC_API_KEY=<user's key from database>
```

**Auth Profile:**
```json
{
  "auth": {
    "profiles": {
      "anthropic-main": {
        "provider": "anthropic",
        "mode": "token"
      }
    }
  }
}
```

**Security Note:**
- API keys stored in database (plain text, no encryption)
- Injected into droplet's `.env` file during deployment
- Each user uses their own Anthropic key (no shared keys)

### Other LLM Support (Not Implemented)

OpenClaw supports 15+ providers, but this platform only uses Anthropic:
- OpenAI (GPT-4, GPT-5)
- Google (Gemini, Vertex AI)
- OpenRouter (unified access)
- xAI, Groq, Cerebras, Mistral
- GitHub Copilot
- Ollama (local models)

**To Add Support:**
- Modify `create_cloud_init_script()` in deployer.py
- Add UI for model selection
- Update database to store model preferences
- Configure auth profiles for each provider

---

## Security Architecture

### Password Security
```python
# backend/auth.py
hash_password(password):
    salt = secrets.token_hex(32)  # 32-byte random salt
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return salt + hashed.hex()  # 128 characters total
```
- Algorithm: PBKDF2-HMAC-SHA256
- Iterations: 100,000
- Salt: 32 bytes (64 hex chars)
- Hash: 32 bytes (64 hex chars)
- Total: 128 characters stored

### Session Security
```python
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only in production
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
```

### Payment Webhook Verification
```python
from standardwebhooks import Webhook

wh = Webhook(webhook_secret)
wh.verify(raw_body, {
    "webhook-id": request.headers.get('webhook-id'),
    "webhook-signature": request.headers.get('webhook-signature'),
    "webhook-timestamp": request.headers.get('webhook-timestamp')
})
```
- Prevents webhook spoofing
- Rejects invalid signatures
- HMAC-based verification

### Droplet Security
```bash
# Firewall (UFW)
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 18789/tcp

# Fail2Ban (installed but not configured)
apt-get install fail2ban
```

**Security Gaps:**
1. API keys stored in plain text (database + droplet .env)
2. No encryption for sensitive data
3. SSH with StrictHostKeyChecking=no
4. Gateway token is only 32 characters
5. No rate limiting on API endpoints
6. No 2FA support

**Recommended Improvements:**
- Encrypt API keys in database
- Use vault service (HashiCorp Vault, AWS Secrets Manager)
- Implement rate limiting (Flask-Limiter)
- Add 2FA for user accounts
- Configure fail2ban rules
- Use proper SSH key fingerprint verification

---

## File Structure

```
/Users/prathapreddy/Desktop/digitalocean/saas/
├── app.py (510 lines)              # Flask application
├── requirements.txt                # Python dependencies
├── run.sh                          # Development startup script
├── backend/
│   ├── __init__.py
│   ├── auth.py (27 lines)         # Password hashing/verification
│   ├── database.py (411 lines)    # SQLite ORM
│   └── deployer.py (290 lines)    # DigitalOcean deployment
├── templates/
│   ├── index.html                 # Landing page (new design)
│   └── dashboard.html             # User dashboard
├── static/
│   ├── css/
│   │   ├── landing.css            # New clean design
│   │   ├── style.css              # Dashboard styles
│   │   └── style.css.backup
│   ├── js/
│   │   └── main.js                # Frontend logic
│   └── logo.png
└── BACKEND_ARCHITECTURE.md         # This document
```

**Total Backend Code:** ~1,283 lines (excluding tests)

---

## Environment Variables

### Required for Production

```bash
# Flask
SECRET_KEY=random_hex_string_64_chars

# DigitalOcean (Platform Token)
DIGITALOCEAN_TOKEN=dop_v1_xxxxxxxxxxxxx

# Dodo Payments
DODO_PAYMENTS_API_KEY=lp5JfYjLaguBQcWe...
DODO_PRODUCT_ID=pdt_0NYLeyWCKUSHjSGrFV3EC
DODO_PAYMENTS_WEBHOOK_SECRET=whsec_xxxxxxxx
DODO_SUCCESS_URL=https://open-claw.space/?payment=success

# Environment
ENV=production  # Enables HTTPS-only cookies
```

### Optional

```bash
# Database (defaults to openclaw_saas.db)
DATABASE_PATH=/path/to/database.db
```

---

## Cost Analysis

### Per User Economics

**Revenue:**
- Subscription: $3/day × 30 days = **$90/month**

**Costs:**
- DigitalOcean droplet (s-2vcpu-4gb): **$24/month**
- Dodo Payments fee (~3%): **$2.70/month**
- Total cost: **$26.70/month**

**Profit:** $90 - $26.70 = **$63.30/month per user** (70.3% margin)

**Scalability:**
- 10 users = $633/month profit
- 100 users = $6,330/month profit
- 1,000 users = $63,300/month profit

**Break-even:** ~42 cents per droplet per day

### Infrastructure Costs

**DigitalOcean Pricing:**
- s-2vcpu-4gb: $24/month
- s-1vcpu-2gb: $12/month (possible downgrade)
- Bandwidth: 1TB included (should be sufficient)
- Backups: Disabled (cost savings)
- Monitoring: Free (enabled)

**Potential Optimizations:**
1. Downgrade to s-1vcpu-2gb ($12/month) for low-usage users
2. Use DigitalOcean credits/promotions
3. Implement auto-shutdown for inactive bots
4. Shared droplets for free-tier users (multi-tenancy)

---

## Deployment Checklist

### Initial Setup
- [x] Create DigitalOcean account
- [x] Add SSH keys to DigitalOcean
- [x] Create Dodo Payments account
- [x] Create daily subscription product
- [x] Get Dodo API keys and webhook secret
- [ ] Set all environment variables in Railway
- [ ] Test payment flow end-to-end
- [ ] Test bot deployment

### Railway Configuration
```
DIGITALOCEAN_TOKEN=dop_v1_...
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
DODO_PAYMENTS_API_KEY=lp5JfYjLaguBQcWe...
DODO_PRODUCT_ID=pdt_0NYLeyWCKUSHjSGrFV3EC
DODO_PAYMENTS_WEBHOOK_SECRET=whsec_...
DODO_SUCCESS_URL=https://your-domain.com/?payment=success
ENV=production
```

### Post-Deployment Testing
1. User registration
2. Payment flow (Dodo checkout)
3. Webhook processing
4. API key configuration
5. Bot deployment
6. Telegram bot responds
7. Log viewing
8. Bot deletion

---

## Troubleshooting

### Common Issues

**1. "Product id does not exist" (404)**
- **Cause:** Wrong DODO_PRODUCT_ID or test/live mode mismatch
- **Fix:** Verify product ID in Dodo dashboard (must be live mode)

**2. Bot doesn't respond on Telegram**
- **Cause:** Invalid bot token or cloud-init script failed
- **Fix:** SSH into droplet, check `journalctl -u openclaw-gateway`

**3. "Active subscription required" (402)**
- **Cause:** User hasn't paid or webhook didn't process
- **Fix:** Check `has_paid` in database, verify webhook secret

**4. Droplet creation timeout**
- **Cause:** DigitalOcean API slow or region unavailable
- **Fix:** Try different region, increase timeout (currently 120s)

**5. SSH connection failed**
- **Cause:** No SSH keys in DigitalOcean account
- **Fix:** Add SSH keys to DO account, redeploy

### Debugging Commands

```bash
# Check user payment status
sqlite3 openclaw_saas.db "SELECT * FROM users WHERE email='user@example.com';"

# Check bot status
sqlite3 openclaw_saas.db "SELECT * FROM bots WHERE user_id=1;"

# View pending payments
sqlite3 openclaw_saas.db "SELECT * FROM pending_payments;"

# SSH into droplet
ssh root@165.227.x.x

# Check OpenClaw service
systemctl status openclaw-gateway

# View OpenClaw logs
journalctl -u openclaw-gateway -f

# Check OpenClaw config
cat /root/.openclaw/openclaw.json

# Test Telegram bot manually
curl https://api.telegram.org/bot<TOKEN>/getMe
```

---

## Future Enhancements

### Short-term (Next Sprint)
1. **Email notifications** for bot deployment success/failure
2. **Usage metrics** - Graph message count over time
3. **Bot status polling** - Auto-refresh status every 10s
4. **Custom model selection** - Let users choose Opus vs Haiku
5. **Multi-platform support** - Add Discord, WhatsApp configuration

### Medium-term (Next Quarter)
1. **Auto-scaling** - Detect usage and upgrade/downgrade droplet size
2. **Bot templates** - Pre-configured bots for different use cases
3. **Shared skills** - Install AgentSkills via UI
4. **Analytics dashboard** - Bot performance metrics
5. **Team accounts** - Multi-user organizations

### Long-term (Future)
1. **Multi-region deployment** - Let users choose datacenter
2. **LLM marketplace** - Support all OpenClaw providers
3. **Bot marketplace** - Pre-built agents users can clone
4. **API access** - Let users integrate bots into their apps
5. **White-label** - Let others resell the platform

---

## Documentation Generated

**By:** 4 Specialized AI Agents (Explore, General-Purpose Research)
**Date:** February 13, 2026
**Version:** 1.0

**Agents Used:**
1. **Explore Agent** - Backend directory structure and file analysis
2. **Research Agent 1** - OpenClaw repository and documentation
3. **Research Agent 2** - Deployer.py deep dive
4. **Research Agent 3** - Database schema and operations

**Lines Analyzed:** 1,283+ lines of backend code + 5,000+ lines of OpenClaw docs

---

## Contact & Support

**Repository:** https://github.com/pratie/openclaw-saas
**OpenClaw Docs:** https://docs.openclaw.ai
**ClawHub:** https://clawhub.com

---

*This comprehensive documentation provides everything needed to understand, maintain, and extend the OpenClaw SaaS platform.*
