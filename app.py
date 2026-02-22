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

@app.route('/robots.txt')
def robots():
    """Serve robots.txt for SEO"""
    from flask import send_from_directory
    return send_from_directory('static', 'robots.txt', mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap():
    """Serve sitemap.xml for SEO"""
    from flask import send_from_directory
    return send_from_directory('static', 'sitemap.xml', mimetype='application/xml')

@app.route('/blog/setup-guide')
def blog_setup_guide():
    """OpenClaw setup guide blog post"""
    from markupsafe import Markup

    content = Markup('''
<div class="tldr">
<strong>TL;DR:</strong> This guide covers three ways to get OpenClaw running — from 5-minute automated deploy to full manual setup. Includes free Kimi setup on Nvidia for zero API costs.
</div>

<h2>What is OpenClaw?</h2>

<p>OpenClaw is an open-source AI assistant gateway that runs on your own server. Unlike ChatGPT or Claude where your conversations train their models, OpenClaw keeps everything on your infrastructure.</p>

<ul>
<li><strong>Private:</strong> Your data never leaves your machine</li>
<li><strong>Flexible:</strong> Connect multiple AI providers (Claude, GPT, Gemini, Kimi)</li>
<li><strong>Multi-platform:</strong> Telegram, Discord, WhatsApp, Email, Slack</li>
<li><strong>Open source:</strong> <a href="https://github.com/openclaw/openclaw">github.com/openclaw/openclaw</a></li>
</ul>

<h2>Method 1: 5-Minute Deploy (Recommended)</h2>

<p>The fastest way to get OpenClaw running without touching a terminal.</p>

<p><strong>What you need:</strong></p>
<ul>
<li>A Telegram account (for bot integration)</li>
<li>An AI provider API key (we'll use free Kimi)</li>
</ul>

<p><strong>Steps:</strong></p>
<ol>
<li>Go to <a href="https://open-claw.space">open-claw.space</a></li>
<li>Choose your AI model (recommend: Kimi via Nvidia for free credits)</li>
<li>Paste your Telegram bot token</li>
<li>Click "Deploy"</li>
<li>Wait 5 minutes</li>
</ol>

<p><strong>Behind the scenes:</strong></p>
<ul>
<li>Server spins up (Ubuntu VPS)</li>
<li>OpenClaw installs automatically</li>
<li>Security configured (UFW firewall, fail2ban, non-root user)</li>
<li>Encrypted API keys</li>
<li>Telegram webhook connected</li>
</ul>

<p><strong>Result:</strong> Your OpenClaw instance running 24/7 on your own server.</p>

<p><strong>Cost:</strong> $49/month (includes deployment + $15 API credits)</p>

<h2>Method 2: Manual Setup (1-2 Hours)</h2>

<p>Want to understand every component? Do it yourself.</p>

<h3>Prerequisites</h3>
<ul>
<li>A VPS (DigitalOcean, Linode, Hetzner — $5-10/month)</li>
<li>SSH access</li>
<li>Basic Linux knowledge</li>
</ul>

<h3>Step 1: Spin Up VPS (15 min)</h3>
<pre><code># Ubuntu 22.04 LTS recommended
# Create droplet, get IP, SSH in
ssh root@your-vps-ip</code></pre>

<h3>Step 2: Install Node.js (5 min)</h3>
<pre><code>curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
node --version  # v20.x.x</code></pre>

<h3>Step 3: Install OpenClaw (7 min)</h3>
<pre><code>git clone https://github.com/openclaw/openclaw.git
cd openclaw
npm install
npm run build</code></pre>

<h3>Step 4: Configure Everything (10 min)</h3>
<pre><code># Copy example config
cp config.example.json config.json

# Edit with your settings
nano config.json</code></pre>

<p><strong>Key settings:</strong></p>
<ul>
<li><code>gateway.host</code>: Set to <code>localhost</code> (security)</li>
<li><code>telegram.botToken</code>: From @BotFather</li>
<li><code>ai.provider</code>: Choose your provider</li>
<li><code>ai.apiKey</code>: Your API key</li>
</ul>

<h3>Step 5: Set Up AI Provider (10 min)</h3>

<h4>Option A: Kimi (Free via Nvidia)</h4>
<ol>
<li>Go to <a href="https://build.nvidia.com/moonshot">build.nvidia.com/moonshot</a></li>
<li>Create free account</li>
<li>Generate API key</li>
<li>Paste into config</li>
</ol>

<p><strong>Free tier:</strong> 50,000 tokens/day</p>

<h4>Option B: Anthropic Claude</h4>
<ol>
<li><a href="https://console.anthropic.com">console.anthropic.com</a></li>
<li>Add billing</li>
<li>Generate API key</li>
</ol>

<h4>Option C: OpenAI</h4>
<ol>
<li><a href="https://platform.openai.com">platform.openai.com</a></li>
<li>Add billing</li>
<li>Generate API key</li>
</ol>

<h3>Step 6: Connect Telegram (10 min)</h3>
<ol>
<li>Message @BotFather → <code>/newbot</code></li>
<li>Name your bot</li>
<li>Copy token to config</li>
<li>Start OpenClaw: <code>npm start</code></li>
<li>Message your bot — it should reply</li>
</ol>

<h3>Step 7: Security Hardening (10 min)</h3>
<pre><code># Firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp  # SSH
sudo ufw enable

# fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban

# Non-root user
sudo useradd -m openclaw
sudo usermod -aG sudo openclaw
# Run OpenClaw as this user, not root</code></pre>

<h3>Step 8: Debug Why Nothing Works (?? min)</h3>

<p>This is where most people get stuck.</p>

<p><strong>Common issues:</strong></p>
<ul>
<li>Telegram webhook URL wrong</li>
<li>Firewall blocking requests</li>
<li>API key permissions</li>
<li>Node version mismatch</li>
<li>Config syntax errors</li>
</ul>

<p><strong>Debug steps:</strong></p>
<pre><code># Check logs
npm start 2>&1 | tee openclaw.log

# Test Telegram webhook
curl -X POST https://api.telegram.org/bot&lt;TOKEN&gt;/getMe

# Check if gateway is listening
netstat -tlnp | grep 3000</code></pre>

<p><strong>Total time:</strong> 1-2 hours if nothing goes wrong. Days if you're learning as you go.</p>

<h2>Method 3: Docker Deploy (30 min)</h2>

<p>For those who know Docker.</p>

<pre><code># Pull image
docker pull openclaw/openclaw:latest

# Run with config
docker run -d \\
  --name openclaw \\
  -v $(pwd)/config.json:/app/config.json \\
  -p 3000:3000 \\
  openclaw/openclaw:latest</code></pre>

<p><strong>Pros:</strong> Isolated, reproducible<br>
<strong>Cons:</strong> Still need to configure everything manually</p>

<h2>Which Method Should You Choose?</h2>

<table>
<thead>
<tr>
<th>Method</th>
<th>Time</th>
<th>Cost</th>
<th>Effort</th>
</tr>
</thead>
<tbody>
<tr>
<td>5-Min Deploy</td>
<td>5 min</td>
<td>$49/mo</td>
<td>Zero</td>
</tr>
<tr>
<td>Manual</td>
<td>1-2 hrs (or days)</td>
<td>$5-10/mo VPS + API costs</td>
<td>High</td>
</tr>
<tr>
<td>Docker</td>
<td>30 min</td>
<td>Same as manual</td>
<td>Medium</td>
</tr>
</tbody>
</table>

<p><strong>My recommendation:</strong> If you value your time, use the 5-minute deploy. If you want to learn OpenClaw's internals, do it manually once — then you'll appreciate the automation.</p>

<h2>Free AI: Kimi on Nvidia Explained</h2>

<p>Most guides skip this. Here's the exact setup.</p>

<p><strong>Why Kimi?</strong></p>
<ul>
<li>50,000 free tokens/day</li>
<li>Good quality (Moonshot's model)</li>
<li>No credit card required</li>
</ul>

<p><strong>Setup steps:</strong></p>
<ol>
<li>Go to <a href="https://build.nvidia.com/moonshot">build.nvidia.com/moonshot</a></li>
<li>Sign up with email</li>
<li>Click "Get API Key"</li>
<li>Copy key starting with <code>nvapi-...</code></li>
<li>In config.json:</li>
</ol>

<pre><code>{
  "ai": {
    "provider": "nvidia",
    "apiKey": "nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxx",
    "model": "kimi-k2.5"
  }
}</code></pre>

<ol start="6">
<li>Restart OpenClaw</li>
</ol>

<p><strong>Monitoring usage:</strong> Dashboard shows daily token usage. If you hit 50k/day, switch to another free tier or add paid credits.</p>

<h2>Troubleshooting Common Errors</h2>

<h3>"Webhook failed"</h3>
<ul>
<li>Check webhook URL in config</li>
<li>Ensure VPS IP is public</li>
<li>Verify SSL certificate (letsencrypt)</li>
</ul>

<h3>"API key invalid"</h3>
<ul>
<li>Check key has correct permissions</li>
<li>Ensure billing is active (for paid providers)</li>
<li>Verify key format (some need "Bearer" prefix)</li>
</ul>

<h3>"Gateway connection refused"</h3>
<ul>
<li>Check if OpenClaw is running: <code>pm2 status</code> or <code>ps aux | grep openclaw</code></li>
<li>Verify port 3000 isn't blocked</li>
<li>Check firewall rules</li>
</ul>

<h3>"Bot not responding"</h3>
<ul>
<li>Message @BotFather, ensure bot isn't blocked</li>
<li>Check webhook is set: <code>https://api.telegram.org/bot&lt;TOKEN&gt;/getWebhookInfo</code></li>
<li>Verify your VPS can reach Telegram servers</li>
</ul>

<h3>"Rate limited"</h3>
<ul>
<li>You're hitting API limits</li>
<li>Add API key for additional provider</li>
<li>Check token usage dashboard</li>
</ul>

<h2>Next Steps After Setup</h2>

<ol>
<li><strong>Add integrations:</strong> Connect Discord, WhatsApp, Email</li>
<li><strong>Configure skills:</strong> Enable browser automation, web search</li>
<li><strong>Set up cron:</strong> Schedule automated tasks</li>
<li><strong>Secure:</strong> Add 2FA to your VPS</li>
<li><strong>Backup:</strong> Export your config regularly</li>
</ol>

<h2>Resources</h2>

<ul>
<li><strong>OpenClaw Docs:</strong> <a href="https://docs.openclaw.ai">docs.openclaw.ai</a></li>
<li><strong>Community:</strong> <a href="https://github.com/openclaw/openclaw/discussions">github.com/openclaw/openclaw/discussions</a></li>
<li><strong>Nvidia Build:</strong> <a href="https://build.nvidia.com">build.nvidia.com</a></li>
</ul>

<h2>Summary</h2>

<p>Three ways to OpenClaw:</p>
<ul>
<li><strong>Fast:</strong> 5-minute deploy at open-claw.space</li>
<li><strong>Manual:</strong> 1-2 hours learning every component</li>
<li><strong>Docker:</strong> 30 minutes if you know containers</li>
</ul>

<p>The fastest route to private AI? 5-minute deploy. The most educational? Do it manually once, then automate.</p>

<p>Want to skip the headache? I built the 5-minute deploy after spending 3 days on manual setup so you don't have to.</p>

<hr>

<p style="font-style: italic; color: var(--text-muted);">Last updated: February 2026</p>
    ''')

    return render_template('blog-post.html',
                         title='How to Set Up OpenClaw: Complete Guide (2026)',
                         description='Three ways to get OpenClaw running — from 5-minute automated deploy to full manual setup. Includes free Kimi setup on Nvidia for zero API costs.',
                         slug='setup-guide',
                         date='February 21, 2026',
                         read_time='12',
                         content=content)

@app.route('/blog/openclaw-vs-claude')
def blog_openclaw_vs_claude():
    """OpenClaw vs Claude comparison blog post"""
    from markupsafe import Markup

    content = Markup('''
<div class="tldr">
<strong>TL;DR:</strong> Claude is an AI model. OpenClaw is an AI gateway that lets you use Claude (and GPT, Gemini, Kimi) from one private interface. They're not competitors—OpenClaw makes Claude more private and flexible.
</div>

<h2>The Confusion: OpenClaw vs Claude</h2>

<p>People keep asking: "Should I use OpenClaw or Claude?"</p>

<p>This is like asking "Should I use a TV or Netflix?"</p>

<p>They're not the same thing.</p>

<h2>What Claude Is</h2>

<p>Claude is an AI model made by Anthropic. It's one of the smartest AI assistants available.</p>

<p><strong>How you normally use Claude:</strong></p>
<ul>
<li>Go to claude.ai</li>
<li>Type your questions in their web interface</li>
<li>Your conversations train their systems</li>
<li>Your data lives on Anthropic's servers</li>
</ul>

<p><strong>Claude's pricing:</strong></p>
<ul>
<li>Free: 5 messages every 5 hours (very limited)</li>
<li>Pro: $20/month for higher limits</li>
<li>API: Pay-per-token (can get expensive fast)</li>
</ul>

<h2>What OpenClaw Is</h2>

<p>OpenClaw is an AI gateway that runs on your own server.</p>

<p><strong>What it does:</strong></p>
<ul>
<li>Connects to multiple AI providers (Claude, GPT, Gemini, Kimi)</li>
<li>Routes your requests to whichever model you choose</li>
<li>Keeps everything on your infrastructure</li>
<li>Works through Telegram, Discord, Email, etc.</li>
</ul>

<p><strong>Think of it as:</strong> Your private AI assistant that can talk to any model you want.</p>

<h2>The Key Difference</h2>

<table>
<thead>
<tr>
<th>Feature</th>
<th>Claude Direct</th>
<th>OpenClaw (with Claude)</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Privacy</strong></td>
<td>Data on Anthropic servers</td>
<td>Data on your server</td>
</tr>
<tr>
<td><strong>Model Choice</strong></td>
<td>Only Claude</td>
<td>Claude, GPT, Gemini, Kimi</td>
</tr>
<tr>
<td><strong>Interface</strong></td>
<td>Web only</td>
<td>Telegram, Discord, Email, etc.</td>
</tr>
<tr>
<td><strong>Training</strong></td>
<td>Your convos may train their model</td>
<td>Your data stays private</td>
</tr>
<tr>
<td><strong>Control</strong></td>
<td>Limited to their features</td>
<td>Full control, customize anything</td>
</tr>
<tr>
<td><strong>Cost</strong></td>
<td>$20/mo Pro or pay-per-token</td>
<td>$49/mo (includes $15 credits)</td>
</tr>
</tbody>
</table>

<h2>When to Use Claude Directly</h2>

<p><strong>Use claude.ai when:</strong></p>
<ul>
<li>You just need quick AI answers occasionally</li>
<li>You're okay with using their web interface</li>
<li>Privacy isn't your main concern</li>
<li>You don't need other AI models</li>
</ul>

<h2>When to Use OpenClaw (with Claude)</h2>

<p><strong>Use OpenClaw when:</strong></p>
<ul>
<li>You want complete privacy (data on your server)</li>
<li>You want to switch between Claude, GPT, and others</li>
<li>You want AI in Telegram, not just web</li>
<li>You're building business workflows</li>
<li>You need 24/7 automation</li>
<li>You want to customize everything</li>
</ul>

<h2>Can You Use Both?</h2>

<p>Yes. In fact, you can use Claude <em>through</em> OpenClaw.</p>

<p><strong>Here's how it works:</strong></p>
<ol>
<li>Get Claude API key from Anthropic</li>
<li>Connect it to your OpenClaw instance</li>
<li>Now you talk to Claude through your private gateway</li>
<li>Your data never touches Anthropic's training systems</li>
</ol>

<h2>Real-World Example</h2>

<p><strong>Sarah is a freelancer. She uses Claude for:</strong></p>
<ul>
<li>Writing client emails</li>
<li>Drafting proposals</li>
<li>Research</li>
</ul>

<p><strong>Problem:</strong> All her client data goes through Anthropic's servers. Not ideal for confidentiality.</p>

<p><strong>Solution:</strong> She switched to OpenClaw.</p>

<p><strong>Now:</strong></p>
<ul>
<li>OpenClaw runs on her VPS</li>
<li>She messages her Telegram bot</li>
<li>It routes to Claude API</li>
<li>No data stored on third-party servers</li>
<li>She also uses GPT for creative tasks</li>
<li>Switches models with one command</li>
</ul>

<h2>OpenClaw + Claude = Best of Both Worlds</h2>

<p><strong>What you get:</strong></p>
<ul>
<li>Claude's intelligence</li>
<li>GPT's versatility</li>
<li>Gemini's speed</li>
<li>Kimi's free tier</li>
<li>All from one private gateway</li>
</ul>

<p><strong>Your conversations:</strong></p>
<ul>
<li>Never leave your server</li>
<li>Don't train anyone's model</li>
<li>Completely under your control</li>
</ul>

<h2>Pricing Breakdown</h2>

<h3>Claude Direct ($20/month Pro)</h3>
<ul>
<li>Web interface only</li>
<li>Usage limits</li>
<li>Data on their servers</li>
<li>Only Claude models</li>
</ul>

<h3>OpenClaw ($49/month)</h3>
<ul>
<li>Telegram, Discord, Email, etc.</li>
<li>$15 in API credits included</li>
<li>Use with Claude, GPT, Gemini, Kimi</li>
<li>Your own dedicated server</li>
<li>Complete privacy</li>
<li>24/7 running</li>
</ul>

<p><strong>Which is better value?</strong></p>

<p>If you only use AI casually: Claude Pro ($20)</p>

<p>If you use AI for business or want privacy: OpenClaw ($49)</p>

<h2>Common Misconceptions</h2>

<p><strong>"OpenClaw is a cheaper Claude alternative"</strong></p>
<p>No. OpenClaw is infrastructure. You still use Claude (or any AI) through it.</p>

<p><strong>"I need to choose between them"</strong></p>
<p>No. You can use Claude <em>inside</em> OpenClaw for better privacy and control.</p>

<p><strong>"OpenClaw has its own AI model"</strong></p>
<p>No. OpenClaw connects to existing models (Claude, GPT, Gemini, Kimi).</p>

<h2>The Bottom Line</h2>

<p>Claude is an AI model. OpenClaw is your private gateway to AI models.</p>

<p><strong>Use Claude direct if:</strong> You want simple, occasional AI help</p>

<p><strong>Use OpenClaw if:</strong> You want privacy, control, and flexibility</p>

<p><strong>Best setup?</strong> OpenClaw with Claude API access—you get Claude's intelligence plus complete privacy.</p>

<h2>Try Both. See What Fits.</h2>

<p>Most people start with Claude direct. Then realize they need:</p>
<ul>
<li>More privacy (client data concerns)</li>
<li>More models (not just Claude)</li>
<li>Better integration (Telegram, not web)</li>
<li>24/7 automation</li>
</ul>

<p>That's when OpenClaw makes sense.</p>

<p>You don't have to choose. Use both. OpenClaw makes Claude better.</p>

<hr>

<p style="font-style: italic; color: var(--text-muted);">Last updated: February 2026</p>
    ''')

    return render_template('blog-post.html',
                         title='OpenClaw vs Claude: Which is Better? (2026 Comparison)',
                         description='Claude is an AI model. OpenClaw is an AI gateway. They work together. Complete comparison of features, privacy, and pricing to help you decide.',
                         slug='openclaw-vs-claude',
                         date='February 21, 2026',
                         read_time='8',
                         content=content)

@app.route('/blog/deploy-openclaw-vps')
def blog_deploy_vps():
    """How to deploy OpenClaw on VPS tutorial"""
    from markupsafe import Markup

    content = Markup('''
<div class="tldr">
<strong>TL;DR:</strong> Step-by-step guide to deploy OpenClaw on any VPS (DigitalOcean, Linode, Hetzner). Covers Ubuntu setup, security hardening, Telegram integration, and common troubleshooting. Takes 1-2 hours.
</div>

<h2>What You'll Need</h2>

<ul>
<li>A VPS (any provider—DigitalOcean, Linode, Hetzner, AWS)</li>
<li>Ubuntu 22.04 LTS (recommended)</li>
<li>SSH access</li>
<li>A Telegram account</li>
<li>An AI provider API key (we'll use free Kimi)</li>
<li>Basic terminal knowledge (we'll explain each command)</li>
</ul>

<p><strong>Cost:</strong> $5-10/month for VPS + API usage</p>
<p><strong>Time:</strong> 1-2 hours (first time), 30 min (if you know what you're doing)</p>

<h2>Why Deploy on Your Own VPS?</h2>

<p><strong>Benefits:</strong></p>
<ul>
<li>Complete control over your infrastructure</li>
<li>Cheaper long-term ($5-10/mo vs $49/mo managed)</li>
<li>Learn how OpenClaw works under the hood</li>
<li>Customize everything</li>
</ul>

<p><strong>Drawbacks:</strong></p>
<ul>
<li>You maintain everything yourself</li>
<li>Need to handle security updates</li>
<li>Troubleshooting is on you</li>
<li>Takes 1-2 hours to set up</li>
</ul>

<h2>Step 1: Create Your VPS (10 minutes)</h2>

<h3>DigitalOcean (Recommended for Beginners)</h3>

<ol>
<li>Go to <a href="https://digitalocean.com">digitalocean.com</a> and create account</li>
<li>Click "Create Droplet"</li>
<li>Choose Ubuntu 22.04 LTS</li>
<li>Select "Basic" plan</li>
<li>Pick $6/month option (1 GB RAM, 1 vCPU—enough for OpenClaw)</li>
<li>Choose region closest to you</li>
<li>Add SSH key (or use password—we'll secure it later)</li>
<li>Click "Create Droplet"</li>
</ol>

<p><strong>Alternative providers:</strong></p>
<ul>
<li><strong>Linode:</strong> Similar pricing, great support</li>
<li><strong>Hetzner:</strong> Cheapest ($4/mo), EU-based</li>
<li><strong>Vultr:</strong> More datacenter locations</li>
</ul>

<p>All providers work the same. Pick whichever you prefer.</p>

<h2>Step 2: Connect to Your VPS (5 minutes)</h2>

<p><strong>On Mac/Linux:</strong></p>
<pre><code>ssh root@your-vps-ip</code></pre>

<p><strong>On Windows:</strong></p>
<p>Use PuTTY or Windows Terminal with WSL.</p>

<p>You'll see something like:</p>
<pre><code>Welcome to Ubuntu 22.04 LTS
root@openclaw:~#</code></pre>

<p>You're in. Now we install OpenClaw.</p>

<h2>Step 3: Install Node.js (5 minutes)</h2>

<p>OpenClaw runs on Node.js. Install it:</p>

<pre><code># Update package list
apt update && apt upgrade -y

# Install Node.js 20.x (LTS)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Verify installation
node --version   # Should show v20.x.x
npm --version    # Should show 10.x.x</code></pre>

<p><strong>Why Node 20?</strong> OpenClaw requires Node 18+ for modern JavaScript features.</p>

<h2>Step 4: Install OpenClaw (7 minutes)</h2>

<pre><code># Clone OpenClaw repository
git clone https://github.com/openclaw/openclaw.git
cd openclaw

# Install dependencies
npm install

# Build the project
npm run build</code></pre>

<p>This takes 3-5 minutes. You'll see a bunch of package names scroll by. That's normal.</p>

<p><strong>If you see errors:</strong> Check Node version. Needs to be 18+.</p>

<h2>Step 5: Configure OpenClaw (10 minutes)</h2>

<pre><code># Copy example config
cp config.example.json config.json

# Edit with nano (or vim if you prefer)
nano config.json</code></pre>

<p><strong>Key settings to change:</strong></p>

<pre><code>{
  "gateway": {
    "host": "localhost",    // IMPORTANT: localhost only for security
    "port": 3000
  },
  "telegram": {
    "botToken": "YOUR_BOT_TOKEN_HERE"  // Get from @BotFather
  },
  "ai": {
    "provider": "nvidia",               // Free Kimi via Nvidia
    "apiKey": "nvapi-...",             // Your Nvidia API key
    "model": "kimi-k2.5"
  }
}</code></pre>

<p><strong>Security note:</strong> Always set <code>host: "localhost"</code>. Never expose to <code>0.0.0.0</code> without authentication.</p>

<p>Save with: <code>Ctrl+X</code>, then <code>Y</code>, then <code>Enter</code></p>

<h2>Step 6: Get Your Telegram Bot Token (10 minutes)</h2>

<ol>
<li>Open Telegram, search for <strong>@BotFather</strong></li>
<li>Send <code>/newbot</code></li>
<li>Choose a name: "My OpenClaw Bot"</li>
<li>Choose a username: "myopenclaw_bot" (must end in _bot)</li>
<li>Copy the token (looks like: <code>1234567890:ABCdefGHIjklMNOpqrsTUVwxyz</code>)</li>
<li>Paste it in config.json under <code>telegram.botToken</code></li>
</ol>

<h2>Step 7: Get Free AI Credits (Kimi via Nvidia) (10 minutes)</h2>

<p><strong>Why Kimi?</strong> 50,000 free tokens/day. No credit card required.</p>

<ol>
<li>Go to <a href="https://build.nvidia.com/moonshot/kimi-k2_5">build.nvidia.com/moonshot</a></li>
<li>Sign up with email</li>
<li>Click "Get API Key"</li>
<li>Copy the key (starts with <code>nvapi-...</code>)</li>
<li>Paste in config.json under <code>ai.apiKey</code></li>
</ol>

<p><strong>Alternative: Use Claude or GPT</strong></p>
<ul>
<li><strong>Claude:</strong> <a href="https://console.anthropic.com">console.anthropic.com</a> (paid)</li>
<li><strong>GPT:</strong> <a href="https://platform.openai.com">platform.openai.com</a> (paid)</li>
</ul>

<h2>Step 8: Start OpenClaw (2 minutes)</h2>

<pre><code># Start in foreground (to test)
npm start</code></pre>

<p>You should see:</p>
<pre><code>[gateway] gateway listening on localhost:3000
[telegram] starting provider
[telegram] bot connected: @your_bot_name</code></pre>

<p><strong>Test it:</strong> Message your bot on Telegram. It should reply.</p>

<p>If it works, press <code>Ctrl+C</code> to stop. We'll make it run 24/7 next.</p>

<h2>Step 9: Make It Run 24/7 with PM2 (5 minutes)</h2>

<pre><code># Install PM2 (process manager)
npm install -g pm2

# Start OpenClaw with PM2
pm2 start npm --name "openclaw" -- start

# Make it start on boot
pm2 startup
pm2 save</code></pre>

<p><strong>Useful PM2 commands:</strong></p>
<pre><code>pm2 status          # Check if running
pm2 logs openclaw   # View logs
pm2 restart openclaw  # Restart
pm2 stop openclaw   # Stop</code></pre>

<h2>Step 10: Security Hardening (10 minutes)</h2>

<p><strong>CRITICAL: Don't skip this step.</strong></p>

<h3>10.1: Set Up Firewall (UFW)</h3>

<pre><code># Install UFW
apt install ufw

# Default rules: deny incoming, allow outgoing
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (otherwise you'll lock yourself out)
ufw allow 22/tcp

# Enable firewall
ufw enable

# Check status
ufw status</code></pre>

<h3>10.2: Install fail2ban (Blocks Brute Force)</h3>

<pre><code>apt install fail2ban
systemctl enable fail2ban
systemctl start fail2ban</code></pre>

<h3>10.3: Create Non-Root User</h3>

<pre><code># Create user
useradd -m openclaw

# Add to sudo group
usermod -aG sudo openclaw

# Switch to this user for running OpenClaw
su - openclaw</code></pre>

<p><strong>Why?</strong> Running as root is dangerous. If OpenClaw gets compromised, attacker has full system access.</p>

<h2>Step 11: Verify Everything Works (5 minutes)</h2>

<p><strong>Checklist:</strong></p>
<ul>
<li>[ ] VPS is running</li>
<li>[ ] Node.js installed (version 20+)</li>
<li>[ ] OpenClaw cloned and built</li>
<li>[ ] config.json configured</li>
<li>[ ] Telegram bot token added</li>
<li>[ ] AI provider (Kimi) connected</li>
<li>[ ] PM2 running OpenClaw 24/7</li>
<li>[ ] Firewall (UFW) active</li>
<li>[ ] fail2ban protecting SSH</li>
</ul>

<p><strong>Test:</strong> Message your Telegram bot. Should reply instantly.</p>

<h2>Common Issues & Fixes</h2>

<h3>"Bot not responding"</h3>

<pre><code># Check if OpenClaw is running
pm2 status

# Check logs for errors
pm2 logs openclaw

# Verify Telegram token
curl https://api.telegram.org/bot&lt;YOUR_TOKEN&gt;/getMe</code></pre>

<h3>"API key invalid"</h3>

<ul>
<li>Check you copied the full key</li>
<li>Ensure no extra spaces in config.json</li>
<li>Verify key hasn't expired (Nvidia keys don't expire, but check dashboard)</li>
</ul>

<h3>"Gateway connection refused"</h3>

<pre><code># Check if port 3000 is listening
netstat -tlnp | grep 3000

# Restart OpenClaw
pm2 restart openclaw</code></pre>

<h3>"npm install" fails</h3>

<ul>
<li>Check Node version: <code>node --version</code> (needs 18+)</li>
<li>Try: <code>npm install --legacy-peer-deps</code></li>
<li>Clear cache: <code>npm cache clean --force</code></li>
</ul>

<h2>Maintenance Tips</h2>

<p><strong>Weekly:</strong></p>
<ul>
<li>Check PM2 status: <code>pm2 status</code></li>
<li>View logs for errors: <code>pm2 logs openclaw --lines 50</code></li>
</ul>

<p><strong>Monthly:</strong></p>
<ul>
<li>Update system: <code>apt update && apt upgrade -y</code></li>
<li>Update OpenClaw: <code>cd openclaw && git pull && npm install && npm run build && pm2 restart openclaw</code></li>
</ul>

<p><strong>Check disk space:</strong></p>
<pre><code>df -h</code></pre>

<p>If <code>/</code> is above 80%, clean logs:</p>
<pre><code>pm2 flush openclaw</code></pre>

<h2>Upgrading to Paid AI Models</h2>

<p>Free Kimi is great to start, but has limits (50k tokens/day).</p>

<p><strong>When you need more:</strong></p>

<h3>Add Claude API</h3>
<ol>
<li>Get key from <a href="https://console.anthropic.com">console.anthropic.com</a></li>
<li>Update config.json:</li>
</ol>

<pre><code>"ai": {
  "provider": "anthropic",
  "apiKey": "sk-ant-...",
  "model": "claude-opus-4.5"
}</code></pre>

<ol start="3">
<li>Restart: <code>pm2 restart openclaw</code></li>
</ol>

<h3>Switch to GPT</h3>

<pre><code>"ai": {
  "provider": "openai",
  "apiKey": "sk-proj-...",
  "model": "gpt-5.2"
}</code></pre>

<h2>Next Steps</h2>

<p><strong>Your OpenClaw is running. Now what?</strong></p>

<ol>
<li><strong>Add more channels:</strong> Discord, Email, WhatsApp</li>
<li><strong>Enable browser automation:</strong> Let it browse the web</li>
<li><strong>Set up web search:</strong> Connect to Google/Bing API</li>
<li><strong>Create custom skills:</strong> Teach it new abilities</li>
<li><strong>Backup config:</strong> <code>cp config.json config.backup.json</code></li>
</ol>

<h2>When Manual Setup Isn't Worth It</h2>

<p>If this guide feels overwhelming, or you don't want to maintain a VPS yourself, consider the managed option.</p>

<p><strong>5-minute automated deploy:</strong> <a href="https://open-claw.space">open-claw.space</a></p>

<ul>
<li>No terminal required</li>
<li>Security handled automatically</li>
<li>Automatic updates</li>
<li>$49/mo (includes $15 AI credits)</li>
</ul>

<p>Most people do manual setup once to learn how it works, then realize maintaining it isn't worth their time.</p>

<h2>Resources</h2>

<ul>
<li><strong>OpenClaw Docs:</strong> <a href="https://docs.openclaw.ai">docs.openclaw.ai</a></li>
<li><strong>Community:</strong> <a href="https://github.com/openclaw/openclaw/discussions">GitHub Discussions</a></li>
<li><strong>Free AI (Nvidia):</strong> <a href="https://build.nvidia.com">build.nvidia.com</a></li>
</ul>

<hr>

<p style="font-style: italic; color: var(--text-muted);">Last updated: February 2026</p>
    ''')

    return render_template('blog-post.html',
                         title='How to Deploy OpenClaw on VPS: Complete Guide (2026)',
                         description='Step-by-step tutorial to deploy OpenClaw on any VPS (DigitalOcean, Linode, Hetzner). Covers Ubuntu setup, security, Telegram, and troubleshooting.',
                         slug='deploy-openclaw-vps',
                         date='February 21, 2026',
                         read_time='15',
                         content=content)

@app.route('/blog/free-kimi-api-openclaw')
def blog_free_kimi():
    """Free Kimi API with OpenClaw tutorial"""
    from markupsafe import Markup

    content = Markup('''
<div class="tldr">
<strong>TL;DR:</strong> Get 50,000 free AI tokens per day using Kimi through Nvidia's API. No credit card required. Works perfectly with OpenClaw. This guide shows you exactly how to set it up.
</div>

<h2>Why Kimi is Perfect for OpenClaw</h2>

<p>Most AI APIs are expensive:</p>
<ul>
<li><strong>Claude:</strong> ~$15/million tokens</li>
<li><strong>GPT-4:</strong> ~$30/million tokens</li>
<li><strong>Gemini:</strong> Starts free, but limits are low</li>
</ul>

<p><strong>Kimi via Nvidia?</strong> 50,000 tokens/day. Completely free. Forever.</p>

<p><strong>What's the catch?</strong> None. Nvidia subsidizes it to get developers using their AI platform.</p>

<h2>What You Get for Free</h2>

<p><strong>Daily limits:</strong></p>
<ul>
<li>50,000 tokens/day</li>
<li>~38,000 words of output</li>
<li>~100-200 conversations (depends on length)</li>
</ul>

<p><strong>Model quality:</strong></p>
<ul>
<li>Kimi-k2.5: Smart enough for most tasks</li>
<li>Context: 200k tokens (handles long documents)</li>
<li>Response quality: Between GPT-3.5 and GPT-4</li>
</ul>

<p><strong>Perfect for:</strong></p>
<ul>
<li>Email summaries</li>
<li>Draft writing</li>
<li>Research</li>
<li>Code explanations</li>
<li>Personal assistant tasks</li>
</ul>

<p><strong>Not ideal for:</strong></p>
<ul>
<li>Creative writing (Claude is better)</li>
<li>Complex reasoning (GPT-4 or Claude Opus)</li>
<li>Heavy API usage (50k/day limit)</li>
</ul>

<h2>Step 1: Get Your Free Nvidia API Key (5 minutes)</h2>

<ol>
<li>Go to <a href="https://build.nvidia.com">build.nvidia.com</a></li>
<li>Click "Sign Up" (top right)</li>
<li>Use email or Google/GitHub login</li>
<li>Verify your email</li>
<li>Search for "Kimi" or "Moonshot"</li>
<li>Click "Get API Key"</li>
<li>Copy the key (starts with <code>nvapi-...</code>)</li>
</ol>

<p><strong>No credit card required. No trial expiry. Completely free.</strong></p>

<h2>Step 2: Connect Kimi to OpenClaw (2 minutes)</h2>

<p>If you're using the managed OpenClaw deploy at <a href="https://open-claw.space">open-claw.space</a>, Kimi is already set up. Just select "Kimi" during onboarding.</p>

<p><strong>For self-hosted OpenClaw:</strong></p>

<pre><code># Edit your config file
nano ~/openclaw/config.json</code></pre>

<p>Update the AI section:</p>

<pre><code>{
  "ai": {
    "provider": "nvidia",
    "apiKey": "nvapi-XXXXXXXXXXXXXXXXXXXXXXXXXX",
    "model": "kimi-k2.5",
    "baseURL": "https://integrate.api.nvidia.com/v1"
  }
}</code></pre>

<p>Save and restart OpenClaw:</p>

<pre><code>pm2 restart openclaw</code></pre>

<h2>Step 3: Test Your Setup (1 minute)</h2>

<p>Message your OpenClaw Telegram bot:</p>

<pre><code>Hello! Are you using Kimi?</code></pre>

<p>If it replies, you're good. Kimi is now powering your AI assistant—for free.</p>

<h2>Understanding Token Usage</h2>

<p><strong>What's a token?</strong></p>
<ul>
<li>~0.75 words in English</li>
<li>"Hello, how are you?" = ~5 tokens</li>
</ul>

<p><strong>50,000 tokens/day means:</strong></p>
<ul>
<li>~125 conversations (400 tokens each)</li>
<li>~250 short questions (200 tokens each)</li>
<li>~25 long research queries (2000 tokens each)</li>
</ul>

<p><strong>Usage examples:</strong></p>

<table>
<thead>
<tr>
<th>Task</th>
<th>Tokens</th>
<th>Per Day</th>
</tr>
</thead>
<tbody>
<tr>
<td>Email summary</td>
<td>~150</td>
<td>~333</td>
</tr>
<tr>
<td>Draft email reply</td>
<td>~300</td>
<td>~166</td>
</tr>
<tr>
<td>Code explanation</td>
<td>~800</td>
<td>~62</td>
</tr>
<tr>
<td>Research query</td>
<td>~1500</td>
<td>~33</td>
</tr>
<tr>
<td>Long document summary</td>
<td>~3000</td>
<td>~16</td>
</tr>
</tbody>
</table>

<h2>Monitoring Your Usage</h2>

<p><strong>Check usage in Nvidia dashboard:</strong></p>
<ol>
<li>Go to <a href="https://build.nvidia.com">build.nvidia.com</a></li>
<li>Click your profile (top right)</li>
<li>Select "API Keys"</li>
<li>View usage graph</li>
</ol>

<p><strong>What happens if you hit the limit?</strong></p>
<ul>
<li>Requests fail with "rate limit exceeded"</li>
<li>Limit resets at midnight UTC</li>
<li>No charges—it just stops working until reset</li>
</ul>

<h2>Upgrading When You Need More</h2>

<p><strong>If you consistently hit 50k/day, you have options:</strong></p>

<h3>Option 1: Add Fallback AI Provider</h3>

<p>Use Kimi as primary, Claude/GPT as fallback when limit is hit.</p>

<pre><code>{
  "ai": {
    "providers": [
      {
        "name": "nvidia",
        "apiKey": "nvapi-...",
        "model": "kimi-k2.5",
        "priority": 1
      },
      {
        "name": "anthropic",
        "apiKey": "sk-ant-...",
        "model": "claude-sonnet-4.5",
        "priority": 2
      }
    ]
  }
}</code></pre>

<p>OpenClaw will use Kimi first, switch to Claude if rate limited.</p>

<h3>Option 2: Multiple Free APIs</h3>

<p>Nvidia offers multiple free models. Rotate between them:</p>

<ul>
<li><strong>Kimi-k2.5:</strong> 50k/day</li>
<li><strong>Llama-3.1:</strong> 1000 requests/day</li>
<li><strong>Mixtral:</strong> 1000 requests/day</li>
</ul>

<p>Combine them = ~100k+ tokens/day free.</p>

<h3>Option 3: Upgrade to Paid</h3>

<p>If you need more than free tier:</p>

<ul>
<li><strong>Anthropic Claude:</strong> $15/million tokens</li>
<li><strong>OpenRouter:</strong> Access to 100+ models, pay as you go</li>
<li><strong>OpenAI:</strong> GPT-4 for $30/million tokens</li>
</ul>

<h2>Best Practices for Maximizing Free Tier</h2>

<h3>1. Use Concise Prompts</h3>

<p><strong>Bad:</strong> "Hey there! I was wondering if you could help me understand, like, what is the best way to..."</p>

<p><strong>Good:</strong> "Explain the best way to..."</p>

<p>Save 20-30% tokens with direct prompts.</p>

<h3>2. Limit Context</h3>

<p>Don't send entire documents if you only need summary.</p>

<p><strong>Bad:</strong> (Pastes 5000-word article) "Summarize this"</p>

<p><strong>Good:</strong> "Summarize: [paste only relevant sections]"</p>

<h3>3. Batch Requests</h3>

<p>Instead of:</p>
<ul>
<li>"Summarize email 1"</li>
<li>"Summarize email 2"</li>
<li>"Summarize email 3"</li>
</ul>

<p>Do:</p>
<ul>
<li>"Summarize these 3 emails: [all text]"</li>
</ul>

<p>Saves ~40% tokens (less overhead per request).</p>

<h2>Common Issues & Fixes</h2>

<h3>"Invalid API key"</h3>

<ul>
<li>Check you copied the full key (starts with <code>nvapi-</code>)</li>
<li>Ensure no spaces before/after in config</li>
<li>Regenerate key from Nvidia dashboard</li>
</ul>

<h3>"Rate limit exceeded"</h3>

<ul>
<li>You hit 50k tokens today</li>
<li>Wait until midnight UTC for reset</li>
<li>Or add fallback provider (Claude/GPT)</li>
</ul>

<h3>"Model not found"</h3>

<ul>
<li>Check model name: <code>kimi-k2.5</code> (not <code>kimi</code> or <code>kimi-2.5</code>)</li>
<li>Verify baseURL: <code>https://integrate.api.nvidia.com/v1</code></li>
</ul>

<h3>"Slow responses"</h3>

<ul>
<li>Kimi is slower than GPT-4 (~5-10 sec vs 2-3 sec)</li>
<li>This is normal for free tier</li>
<li>If it's >30 sec, check network/firewall</li>
</ul>

<h2>Kimi vs Other Free Options</h2>

<table>
<thead>
<tr>
<th>Provider</th>
<th>Free Tier</th>
<th>Quality</th>
<th>Best For</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Kimi (Nvidia)</strong></td>
<td>50k tokens/day</td>
<td>Good</td>
<td>Daily assistant use</td>
</tr>
<tr>
<td><strong>Gemini</strong></td>
<td>60 requests/min (low daily cap)</td>
<td>Very good</td>
<td>Testing, low volume</td>
</tr>
<tr>
<td><strong>Claude</strong></td>
<td>No free API tier</td>
<td>Excellent</td>
<td>Paid only</td>
</tr>
<tr>
<td><strong>GPT-3.5</strong></td>
<td>No longer free</td>
<td>Good</td>
<td>Paid only</td>
</tr>
</tbody>
</table>

<p><strong>Winner:</strong> Kimi via Nvidia. Best balance of free tier + quality.</p>

<h2>Real-World Usage: How Long Does 50k Last?</h2>

<p><strong>Light user (personal assistant):</strong></p>
<ul>
<li>10-20 queries/day</li>
<li>~5,000-10,000 tokens/day</li>
<li><strong>Verdict:</strong> Never hit the limit</li>
</ul>

<p><strong>Medium user (work + personal):</strong></p>
<ul>
<li>40-60 queries/day</li>
<li>~20,000-35,000 tokens/day</li>
<li><strong>Verdict:</strong> Occasionally hit limit on heavy days</li>
</ul>

<p><strong>Heavy user (business use):</strong></p>
<ul>
<li>100+ queries/day</li>
<li>~50,000+ tokens/day</li>
<li><strong>Verdict:</strong> Need fallback or paid tier</li>
</ul>

<h2>Combining Free Kimi with OpenClaw</h2>

<p><strong>Perfect combo:</strong></p>
<ul>
<li>OpenClaw handles infrastructure (Telegram, security, 24/7 running)</li>
<li>Kimi provides free AI (50k tokens/day)</li>
<li>Total cost: $0 if self-hosted, or $49/mo managed</li>
</ul>

<p><strong>What you get:</strong></p>
<ul>
<li>Private AI assistant</li>
<li>Running 24/7</li>
<li>Accessible via Telegram</li>
<li>Zero AI API costs</li>
</ul>

<h2>When to Upgrade to Paid AI</h2>

<p><strong>Stick with free Kimi if:</strong></p>
<ul>
<li>You use AI casually (20-50 queries/day)</li>
<li>Tasks are straightforward (summaries, drafts, research)</li>
<li>You're okay with occasional rate limits</li>
</ul>

<p><strong>Upgrade to Claude/GPT if:</strong></p>
<ul>
<li>You need top-tier reasoning (complex problems)</li>
<li>You're doing creative work (writing, brainstorming)</li>
<li>You consistently hit 50k/day limit</li>
<li>You need faster response times</li>
</ul>

<p><strong>Cost comparison:</strong></p>

<ul>
<li><strong>Free Kimi:</strong> $0/mo (50k tokens/day)</li>
<li><strong>Claude API:</strong> ~$15/mo (1 million tokens)</li>
<li><strong>GPT-4 API:</strong> ~$30/mo (1 million tokens)</li>
</ul>

<h2>Resources</h2>

<ul>
<li><strong>Nvidia Build Platform:</strong> <a href="https://build.nvidia.com">build.nvidia.com</a></li>
<li><strong>Kimi Model Docs:</strong> <a href="https://build.nvidia.com/moonshot/kimi-k2_5">build.nvidia.com/moonshot</a></li>
<li><strong>OpenClaw Setup Guide:</strong> <a href="/blog/setup-guide">Complete OpenClaw Guide</a></li>
<li><strong>Deploy in 5 Minutes:</strong> <a href="https://open-claw.space">open-claw.space</a></li>
</ul>

<h2>Summary</h2>

<p>Free Kimi API through Nvidia = 50,000 tokens/day at zero cost.</p>

<p>Perfect for running OpenClaw without paying for AI API usage.</p>

<p><strong>Setup takes 5 minutes. No credit card. No catch.</strong></p>

<p>Try it. If you need more later, add Claude/GPT as fallback. But most people never hit the free limit.</p>

<hr>

<p style="font-style: italic; color: var(--text-muted);">Last updated: February 2026</p>
    ''')

    return render_template('blog-post.html',
                         title='Free Kimi API with OpenClaw: Complete Guide (2026)',
                         description='Get 50,000 free AI tokens daily using Kimi through Nvidia. No credit card required. Perfect for OpenClaw. Step-by-step setup guide.',
                         slug='free-kimi-api-openclaw',
                         date='February 21, 2026',
                         read_time='10',
                         content=content)

@app.route('/dashboard')
def dashboard():
    """Dashboard page - requires auth"""
    if 'username' not in session:
        return redirect(url_for('index'))

    username = session['username']
    user = db.get_user(username)

    # If user doesn't exist in database, clear session and redirect to index
    if not user:
        session.clear()
        return redirect(url_for('index'))

    bots = db.get_user_bots(username)

    return render_template('dashboard.html',
                         username=username,
                         email=session.get('email', user.get('email', '')),
                         bots=bots,
                         bot_count=len(bots),
                         active_count=len([b for b in bots if b['status'] == 'running']),
                         has_paid=user.get('has_paid', 0))

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

    username = session['username']
    user = db.get_user(username)

    return render_template('deploy.html',
                         username=username,
                         email=session.get('email', user['email']),
                         telegram_token=session['telegram_token'],
                         has_paid=user.get('has_paid', 0))

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
        # billing_address omitted — Dodo's checkout page collects it from the user
        checkout_session = client.checkout_sessions.create(
            product_cart=[
                {"product_id": dodo_product_id, "quantity": 1}
            ],
            customer={
                "email": email,
                "name": email.split("@")[0],
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
    # Require valid session — prevent anyone from granting themselves free access
    email = session.get('email')
    if not email:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.json or {}
    payment_id = data.get('paymentId')

    user = db.get_user_by_email(email)
    if user and not user.get('has_paid'):
        db.update_payment_status(email, payment_id or 'manual', 'monthly')

    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
