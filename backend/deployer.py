"""
Bot Deployer module for OpenClaw SaaS
Handles bot deployment to DigitalOcean
"""

import os
import sys
import time
import random
import string
import subprocess
import requests

# Add parent directory to path to import the deployment script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from pydo import Client
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pydo"])
    from pydo import Client

class BotDeployer:
    def __init__(self, do_token):
        """Initialize deployer with DigitalOcean token"""
        self.do_token = do_token
        self.client = Client(token=do_token)

    def generate_token(self, length=32):
        """Generate secure random token"""
        chars = string.ascii_letters + string.digits + '_-'
        return ''.join(random.choice(chars) for _ in range(length))

    def get_bot_username(self, telegram_token):
        """Get Telegram bot username from token"""
        try:
            url = f"https://api.telegram.org/bot{telegram_token}/getMe"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data['result']['username']
        except:
            pass
        return 'unknown_bot'

    def create_cloud_init_script(self, telegram_token, openrouter_key, gateway_token, has_ssh_keys=False):
        """Create cloud-init script for bot deployment with security hardening"""

        # Conditional SSH hardening based on whether SSH keys are present
        ssh_hardening = ""
        if has_ssh_keys:
            # Full SSH hardening - disable password auth (safe because SSH keys exist)
            ssh_hardening = """
# Harden SSH - Disable root login and password authentication
sed -i 's/#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sed -i 's/#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/#*PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
systemctl reload sshd
"""
        else:
            # Partial SSH hardening - keep password auth but disable root login
            # (User has no SSH keys, so we can't lock them out)
            ssh_hardening = """
# Partial SSH hardening - Disable root password login only
sed -i 's/#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#*PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
systemctl reload sshd
"""

        return f"""#!/bin/bash
set -e

# Update system
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"

# Install dependencies
apt-get install -y curl git build-essential python3-pip python3-venv ufw fail2ban jq ffmpeg

# Install Node.js 22
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs

# Install OpenClaw
npm install -g pnpm@latest
npm install -g openclaw@latest

# Configure firewall - SECURE: Only allow SSH, block gateway port
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
# Gateway port 18789 is NOT exposed to internet (only localhost/LAN access)
ufw --force enable
{ssh_hardening}
# Configure fail2ban for SSH brute force protection
cat > /etc/fail2ban/jail.local << 'FAIL2BAN_EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s
FAIL2BAN_EOF
systemctl enable fail2ban
systemctl restart fail2ban

# Create dedicated user for security
useradd -r -m -s /bin/false -d /var/lib/openclaw openclaw || true
mkdir -p /var/lib/openclaw/.openclaw/workspace
chown -R openclaw:openclaw /var/lib/openclaw

# Harden directory permissions - prevent world-readable access
chmod 750 /var/lib/openclaw
chmod 750 /var/lib/openclaw/.openclaw
chmod 750 /var/lib/openclaw/.openclaw/workspace

# Write OpenClaw configuration
cat > /var/lib/openclaw/.openclaw/openclaw.json << 'EOF'
{{
  "gateway": {{
    "port": 18789,
    "mode": "local",
    "bind": "loopback",
    "auth": {{
      "mode": "token",
      "token": "{gateway_token}"
    }},
    "controlUi": {{
      "enabled": true
    }}
  }},
  "agents": {{
    "defaults": {{
      "model": {{
        "primary": "openrouter/moonshotai/kimi-k2.5",
        "fallbacks": ["openrouter/moonshotai/kimi-k2-turbo-preview"]
      }},
      "workspace": "~/.openclaw/workspace",
      "memorySearch": {{
        "enabled": true
      }}
    }}
  }},
  "channels": {{
    "telegram": {{
      "enabled": true,
      "botToken": "{telegram_token}",
      "dmPolicy": "open",
      "allowFrom": ["*"],
      "groupPolicy": "open",
      "groupAllowFrom": ["*"],
      "textChunkLimit": 4000,
      "chunkMode": "length",
      "linkPreview": true,
      "streamMode": "partial",
      "commands": {{
        "native": true
      }},
      "capabilities": {{
        "inlineButtons": "all"
      }},
      "reactionNotifications": "own",
      "actions": {{
        "reactions": true,
        "sendMessage": true,
        "sticker": true
      }}
    }}
  }},
  "auth": {{
    "profiles": {{
      "openrouter:default": {{
        "provider": "openrouter",
        "mode": "token"
      }}
    }}
  }},
  "plugins": {{
    "entries": {{
      "telegram": {{
        "enabled": true
      }}
    }}
  }},
  "session": {{
    "dmScope": "per-peer"
  }},
  "commands": {{
    "native": true,
    "nativeSkills": true,
    "config": false,
    "restart": false
  }},
  "update": {{
    "channel": "stable",
    "checkOnStart": true
  }},
  "cron": {{
    "enabled": true,
    "store": "~/.openclaw/cron/jobs.json",
    "maxConcurrentRuns": 1
  }}
}}
EOF

# Write environment file
cat > /var/lib/openclaw/.openclaw/.env << 'EOF'
OPENROUTER_API_KEY={openrouter_key}
OPENCLAW_GATEWAY_TOKEN={gateway_token}
NODE_ENV=production
EOF

# Set secure permissions on sensitive files
chmod 600 /var/lib/openclaw/.openclaw/.env
chmod 600 /var/lib/openclaw/.openclaw/openclaw.json
chown openclaw:openclaw /var/lib/openclaw/.openclaw/.env
chown openclaw:openclaw /var/lib/openclaw/.openclaw/openclaw.json

# Remove any backup files that may contain secrets
find /var/lib/openclaw/.openclaw -type f \\( -name "*.bak" -o -name "*.backup" -o -name "*~" \\) -delete

# Create daily cleanup script for backup files
cat > /etc/cron.daily/openclaw-cleanup << 'CLEANUP_EOF'
#!/bin/bash
# Remove backup files with secrets
find /var/lib/openclaw/.openclaw -type f \\( -name "*.bak" -o -name "*.backup" -o -name "*~" \\) -delete 2>/dev/null || true
CLEANUP_EOF
chmod +x /etc/cron.daily/openclaw-cleanup

# Run openclaw doctor to enable Telegram (as openclaw user)
su - openclaw -s /bin/bash -c "cd /var/lib/openclaw && openclaw doctor --fix --yes" || true

# Create systemd service with security hardening
cat > /etc/systemd/system/openclaw-gateway.service << 'EOF'
[Unit]
Description=OpenClaw Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=openclaw
Group=openclaw
WorkingDirectory=/var/lib/openclaw
Environment="NODE_ENV=production"
Environment="HOME=/var/lib/openclaw"
EnvironmentFile=/var/lib/openclaw/.openclaw/.env
ExecStart=/usr/bin/openclaw gateway --bind loopback --port 18789
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=openclaw

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/openclaw
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictRealtime=true
RestrictNamespaces=true

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
systemctl daemon-reload
systemctl enable openclaw-gateway
systemctl start openclaw-gateway

echo "OpenClaw deployment completed with security hardening!"
"""

    def deploy(self, telegram_token, openrouter_key, region='nyc3', size='s-2vcpu-4gb', bot_name='openclaw-bot'):
        """Deploy a new bot"""
        try:
            # Generate gateway token
            gateway_token = self.generate_token()

            # Get bot username
            bot_username = self.get_bot_username(telegram_token)

            # Get SSH keys
            ssh_key_ids = []
            try:
                ssh_keys_resp = self.client.ssh_keys.list()
                ssh_key_ids = [key["id"] for key in ssh_keys_resp["ssh_keys"]]
            except:
                pass

            # Create cloud-init script with conditional SSH hardening
            user_data = self.create_cloud_init_script(
                telegram_token,
                openrouter_key,
                gateway_token,
                has_ssh_keys=bool(ssh_key_ids)  # Full hardening only if keys exist
            )

            # Create droplet
            droplet_name = f"{bot_name}-{int(time.time())}"
            req = {
                "name": droplet_name,
                "region": region,
                "size": size,
                "image": "ubuntu-24-04-x64",
                "ssh_keys": ssh_key_ids,
                "backups": False,
                "ipv6": True,
                "monitoring": True,
                "tags": ["openclaw", "saas", "bot"],
                "user_data": user_data
            }

            resp = self.client.droplets.create(body=req)
            droplet_id = resp["droplet"]["id"]

            # Wait for droplet to become active
            max_wait = 120  # 2 minutes
            start_time = time.time()
            ip_address = None

            while time.time() - start_time < max_wait:
                droplet = self.client.droplets.get(droplet_id=droplet_id)
                status = droplet["droplet"]["status"]

                if status == "active":
                    networks = droplet["droplet"]["networks"]["v4"]
                    ip_address = next(
                        (net["ip_address"] for net in networks if net["type"] == "public"),
                        None
                    )
                    if ip_address:
                        break

                time.sleep(5)

            if not ip_address:
                return {
                    'success': False,
                    'error': 'Could not get IP address'
                }

            return {
                'success': True,
                'droplet_id': droplet_id,
                'ip_address': ip_address,
                'gateway_token': gateway_token,
                'bot_username': bot_username,
                'gateway_url': f'ws://127.0.0.1:18789'  # Gateway is localhost-only for security
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def delete_droplet(self, droplet_id):
        """Delete a droplet"""
        try:
            self.client.droplets.destroy(droplet_id=droplet_id)
            return True
        except:
            return False
