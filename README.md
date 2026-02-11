# 🤖 OpenClaw SaaS Platform

**Cyberpunk-themed AI Bot Deployment Platform**

Deploy and manage OpenClaw AI bots with a beautiful terminal-inspired interface!

## ✨ Features

- 🎨 **Cyberpunk Terminal UI** - Neon glows, glitch effects, and futuristic design
- ⚡ **One-Click Bot Deployment** - Deploy AI bots to DigitalOcean in minutes
- 📊 **Real-Time Dashboard** - Monitor all your bots in one place
- 📜 **Live Logs Viewer** - Watch your bot logs in real-time
- 🔒 **Secure Authentication** - Password-based user accounts
- 💬 **Telegram Integration** - Instant bot setup for Telegram
- 🌍 **Multiple Regions** - Deploy globally (NYC, SF, London, Singapore, Bangalore)

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- DigitalOcean account with API token
- Telegram bot token (from @BotFather)
- Anthropic API key (for Claude AI)

### Installation

1. **Navigate to the SaaS directory:**
   ```bash
   cd /Users/prathapreddy/Desktop/digitalocean/saas
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open your browser:**
   ```
   http://localhost:5000
   ```

## 📖 Usage Guide

### 1. Create an Account

1. Click the **REGISTER** tab
2. Enter username, email, and password
3. Click **CREATE ACCOUNT**
4. Login with your new credentials

### 2. Deploy Your First Bot

1. Click **🚀 DEPLOY BOT** in the sidebar
2. Fill in the form:
   - **Bot Name**: Your bot's display name
   - **Telegram Token**: Get from @BotFather on Telegram
   - **Anthropic API Key**: Your Claude API key
   - **DigitalOcean Token**: Your DO API token
   - **Region**: Choose datacenter location
   - **Size**: Select server size (starts at $6/mo)
3. Click **⚡ DEPLOY BOT**
4. Wait 2-3 minutes for deployment
5. Your bot will be ready! ✅

### 3. Manage Your Bots

- **View Overview**: See all your bots at a glance
- **Check Logs**: Click the 📜 button on any bot
- **Delete Bot**: Click the 🗑️ button (permanent!)

### 4. View Logs

1. Go to **📜 LOGS** in sidebar
2. Select a bot from dropdown
3. Click **🔄 REFRESH** to update
4. Watch live logs appear!

## 🎨 UI Features

### Cyberpunk Aesthetics

- **Neon Green** primary color (#00ff41)
- **Glitch Effects** on titles
- **Glowing Borders** with shadow effects
- **Terminal Font** (Share Tech Mono)
- **Animated Background** with twinkling stars
- **Scan Lines** for that retro-future feel

### Interactive Elements

- **Hover Effects** on all buttons
- **Smooth Transitions** everywhere
- **Progress Bars** during deployment
- **Status Indicators** (🟢 Online / 🔴 Offline)
- **Real-time Updates** without page refresh

## 🏗️ Architecture

```
saas/
├── app.py                      # Flask backend API
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── backend/                    # Backend logic
│   ├── __init__.py
│   ├── database.py             # SQLite database operations
│   ├── deployer.py             # Bot deployment logic
│   └── auth.py                 # Password hashing & auth
│
├── templates/                  # HTML templates
│   ├── index.html              # Login/Register page
│   └── dashboard.html          # Main dashboard
│
└── static/                     # Frontend assets
    ├── css/
    │   └── style.css          # Cyberpunk styling
    └── js/
        ├── main.js            # Landing page logic
        └── dashboard.js       # Dashboard functionality
```

## 🗄️ Database Schema

### Users Table
- `id` - Auto-increment primary key
- `username` - Unique username
- `email` - User email
- `password_hash` - Hashed password
- `created_at` - Registration timestamp
- `credits` - Account balance (default: $50)

### Bots Table
- `id` - Auto-increment primary key
- `user_id` - Foreign key to users
- `bot_name` - Display name
- `bot_username` - Telegram @username
- `ip_address` - Server IP
- `gateway_token` - Auth token
- `droplet_id` - DigitalOcean droplet ID
- `region` - Datacenter region
- `status` - running/stopped
- `message_count` - Total messages processed
- `created_at` - Deployment timestamp

## 🔧 Configuration

### Environment Variables (Optional)

Create a `.env` file in the `saas/` directory:

```env
FLASK_SECRET_KEY=your-secret-key-here
FLASK_DEBUG=True
DATABASE_PATH=openclaw_saas.db
```

### Customization

#### Change Colors

Edit `static/css/style.css`:

```css
:root {
    --primary-green: #00ff41;  /* Change to your color */
    --primary-cyan: #00ffff;
    --primary-purple: #b24bf3;
    --primary-pink: #ff006e;
}
```

#### Modify Bot Configuration

Edit `backend/deployer.py` in the `create_cloud_init_script()` method to customize:
- AI model (default: claude-opus-4-6)
- Gateway settings
- Telegram policies
- Memory settings

## 📊 API Endpoints

### Authentication
- `POST /api/login` - User login
- `POST /api/register` - Create account
- `POST /api/logout` - User logout

### Bots Management
- `GET /api/bots` - List user's bots
- `POST /api/deploy` - Deploy new bot
- `DELETE /api/bots/<id>` - Delete bot
- `GET /api/logs/<id>` - Get bot logs

## 🚀 Deployment to Production

### Option 1: Run on Local Server

```bash
# Install screen or tmux
sudo apt install screen

# Start in background
screen -S openclaw-saas
python app.py

# Detach with Ctrl+A, D
```

### Option 2: Deploy to DigitalOcean App Platform

1. Push code to GitHub
2. Create new App on DigitalOcean
3. Connect repository
4. Set run command: `python app.py`
5. Deploy!

### Option 3: Use Gunicorn (Production)

```bash
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 🔒 Security Notes

- ⚠️ This is an MVP - add proper session management for production
- ⚠️ API tokens are stored in plain text - encrypt for production
- ⚠️ Add rate limiting to prevent abuse
- ⚠️ Implement CSRF protection
- ⚠️ Use HTTPS in production

## 💰 Pricing Tiers (Future)

**Free Tier**
- 1 bot
- Basic support
- $50 credits

**Pro Tier** ($19/mo)
- 5 bots
- Priority support
- Advanced analytics

**Enterprise** ($99/mo)
- Unlimited bots
- Dedicated support
- Custom features

## 🛣️ Roadmap

- [ ] Stripe payment integration
- [ ] Email notifications
- [ ] Bot usage analytics
- [ ] Auto-scaling
- [ ] Multi-platform support (Discord, Slack, etc.)
- [ ] Webhook integration
- [ ] Bot templates marketplace
- [ ] Team collaboration
- [ ] API access for developers

## 🐛 Troubleshooting

### Bot Won't Deploy
- Check DigitalOcean token is valid
- Ensure you have credits in DO account
- Verify Telegram token with @BotFather
- Check Anthropic API key is active

### Can't See Logs
- Wait 2-3 minutes after deployment
- Check bot status is "running"
- Verify SSH keys in DigitalOcean

### Login Not Working
- Clear browser cookies
- Check database file permissions
- Restart Flask app

## 📞 Support

Found a bug? Want a feature?

Create an issue or contact support!

## 📄 License

MIT License - feel free to use and modify!

---

**Built with ❤️ for the OpenClaw community**

*Powered by Flask, DigitalOcean, and Anthropic Claude*
