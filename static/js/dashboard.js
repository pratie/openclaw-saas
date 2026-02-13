// Dashboard JavaScript

// Load bots on page load
document.addEventListener('DOMContentLoaded', () => {
    loadBots();
    populateBotSelects();
});

function showPanel(panelName) {
    // Hide all panels
    document.querySelectorAll('.content-panel').forEach(panel => {
        panel.classList.remove('active');
    });

    // Remove active class from all nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });

    // Show selected panel
    document.getElementById(panelName + '-panel').classList.add('active');

    // Set active nav item
    event.target.closest('.nav-item').classList.add('active');

    // Reload bots if switching to bots panel
    if (panelName === 'bots' || panelName === 'overview') {
        loadBots();
    }
}

async function loadBots() {
    try {
        const response = await fetch('/api/bots');
        const data = await response.json();

        if (data.success) {
            displayBots(data.bots, 'bots-list');
            displayBots(data.bots, 'bots-management');
            updateStats(data.bots);
        }
    } catch (error) {
        console.error('Error loading bots:', error);
    }
}

function displayBots(bots, containerId) {
    const container = document.getElementById(containerId);

    if (bots.length === 0) {
        container.innerHTML = `
            <div class="terminal-window" style="grid-column: 1 / -1;">
                <div class="terminal-body" style="text-align: center; padding: 40px;">
                    <p style="color: var(--primary-cyan); font-size: 18px;">
                        No bots deployed yet. Click <span style="color: var(--primary-green);">🚀 DEPLOY BOT</span> to get started!
                    </p>
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = bots.map(bot => `
        <div class="bot-card" data-bot-id="${bot.id}">
            <div class="bot-card-header">
                <h3 class="bot-name">🤖 @${bot.bot_username}</h3>
            </div>
            <div class="bot-info">
                <div class="bot-info-item">
                    <span class="bot-info-label">Telegram:</span>
                    <span class="bot-info-value" id="telegram-status-${bot.id}">
                        🟡 Setting up...
                    </span>
                </div>
                <div class="bot-info-item">
                    <span class="bot-info-label">IP Address:</span>
                    <span class="bot-info-value">${bot.ip_address}</span>
                </div>
                <div class="bot-info-item">
                    <span class="bot-info-label">Deployed:</span>
                    <span class="bot-info-value">${new Date(bot.created_at).toLocaleDateString()}</span>
                </div>
            </div>
            <div class="bot-actions" id="actions-${bot.id}">
                <button class="btn-small btn-logs" onclick="viewBotLogs(${bot.id})">
                    📜 LOGS
                </button>
                <button class="btn-small btn-delete" onclick="confirmDeleteBot(${bot.id}, '${bot.bot_name}')">
                    🗑️ DELETE
                </button>
            </div>
        </div>
    `).join('');

    // Check Telegram status for each bot
    bots.forEach(bot => checkBotStatus(bot.id, bot.bot_username));
}

function updateStats(bots) {
    const activeBots = bots.filter(b => b.status === 'running').length;
    const totalBots = bots.length;
    const totalMessages = bots.reduce((sum, b) => sum + (b.message_count || 0), 0);

    document.getElementById('active-bots').textContent = activeBots;
    document.getElementById('total-bots').textContent = totalBots;
    document.getElementById('messages').textContent = totalMessages;
}

async function deployBot(event) {
    event.preventDefault();

    const progressDiv = document.getElementById('deploy-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const messageEl = document.getElementById('deploy-message');
    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');

    // Get form data - only telegram token
    const botData = {
        telegram_token: document.getElementById('telegram-token').value
    };

    // Show progress
    progressDiv.style.display = 'block';
    submitBtn.disabled = true;
    messageEl.style.display = 'none';

    try {
        // Simulate progress
        let progress = 0;
        const progressInterval = setInterval(() => {
            if (progress < 90) {
                progress += Math.random() * 10;
                progressFill.style.width = Math.min(progress, 90) + '%';
            }
        }, 500);

        progressText.textContent = '🌊 Creating droplet...';

        const response = await fetch('/api/deploy', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(botData)
        });

        clearInterval(progressInterval);
        const data = await response.json();

        if (data.success) {
            progressFill.style.width = '100%';
            progressText.textContent = '✅ Deployment complete!';

            showMessage(messageEl, 'success', `
                ✓ Bot deployed successfully!<br>
                <strong>Bot:</strong> @${data.bot_username}<br>
                <strong>IP:</strong> ${data.ip_address}<br>
                <strong>Status:</strong> Ready to use!
            `);

            form.reset();
            setTimeout(() => {
                progressDiv.style.display = 'none';
                loadBots();
            }, 3000);
        } else {
            progressFill.style.width = '0%';
            progressDiv.style.display = 'none';
            showMessage(messageEl, 'error', '✗ Deployment failed: ' + (data.error || data.message));
        }
    } catch (error) {
        progressDiv.style.display = 'none';
        showMessage(messageEl, 'error', '✗ Connection error: ' + error.message);
        console.error('Deploy error:', error);
    } finally {
        submitBtn.disabled = false;
    }
}

async function confirmDeleteBot(botId, botName) {
    if (confirm(`Are you sure you want to delete bot "${botName}"?\n\nThis will permanently delete the bot and its data.`)) {
        await deleteBot(botId);
    }
}

async function deleteBot(botId) {
    try {
        const response = await fetch(`/api/bots/${botId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            alert('✓ Bot deleted successfully');
            loadBots();
        } else {
            alert('✗ Failed to delete bot');
        }
    } catch (error) {
        alert('✗ Connection error');
        console.error('Delete error:', error);
    }
}

function viewBotLogs(botId) {
    // Switch to logs panel
    document.getElementById('logs-panel').classList.add('active');
    document.getElementById('overview-panel').classList.remove('active');

    // Select the bot in the dropdown
    document.getElementById('log-bot-select').value = botId;

    // Load logs
    loadLogs();
}

async function populateBotSelects() {
    try {
        const response = await fetch('/api/bots');
        const data = await response.json();

        if (data.success) {
            const select = document.getElementById('log-bot-select');
            select.innerHTML = '<option value="">-- Select a bot --</option>' +
                data.bots.map(bot => `
                    <option value="${bot.id}">
                        ${bot.bot_name} (@${bot.bot_username})
                    </option>
                `).join('');
        }
    } catch (error) {
        console.error('Error loading bot list:', error);
    }
}

async function loadLogs() {
    const botId = document.getElementById('log-bot-select').value;
    const logsContent = document.getElementById('logs-content');

    if (!botId) {
        logsContent.textContent = 'Select a bot to view logs...';
        return;
    }

    logsContent.textContent = '⏳ Loading logs...';

    try {
        const response = await fetch(`/api/logs/${botId}`);
        const data = await response.json();

        if (data.success) {
            logsContent.textContent = data.logs || 'No logs available';
            // Auto-scroll to bottom
            logsContent.scrollTop = logsContent.scrollHeight;
        } else {
            logsContent.textContent = '✗ Failed to load logs: ' + data.message;
        }
    } catch (error) {
        logsContent.textContent = '✗ Connection error';
        console.error('Logs error:', error);
    }
}

async function logout() {
    try {
        await fetch('/api/logout', { method: 'POST' });
        window.location.href = '/';
    } catch (error) {
        console.error('Logout error:', error);
    }
}

async function saveSettings() {
    const openrouterKey = document.getElementById('settings-openrouter').value.trim();

    if (!openrouterKey) {
        alert('⚠️ OpenRouter API key is required');
        return;
    }

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                openrouter_key: openrouterKey
            })
        });

        const data = await response.json();

        if (data.success) {
            alert('✅ API key saved successfully!');
            // Clear field for security
            document.getElementById('settings-openrouter').value = '';
        } else {
            alert('❌ ' + (data.message || 'Failed to save API key'));
        }
    } catch (error) {
        alert('❌ Connection error');
        console.error('Settings error:', error);
    }
}

function deleteAccount() {
    if (confirm('⚠️ WARNING: This will permanently delete your account and all bots!\n\nAre you absolutely sure?')) {
        if (confirm('This action cannot be undone. Continue?')) {
            alert('⚠️ Account deletion coming soon!');
        }
    }
}

function showMessage(element, type, message) {
    element.innerHTML = message;
    element.className = 'message ' + type;
    element.style.display = 'block';
}

function subscribeToDeploy() {
    // Show the beautiful payment modal instead of ugly prompt
    document.getElementById('dashboard-payment-modal').style.display = 'flex';
}

function closeDashboardPaymentModal() {
    document.getElementById('dashboard-payment-modal').style.display = 'none';
}

// Close modal if clicked outside
window.onclick = function(event) {
    const modal = document.getElementById('dashboard-payment-modal');
    if (event.target === modal) {
        closeDashboardPaymentModal();
    }
}

async function dashboardCreateCheckout(event) {
    event.preventDefault();

    const email = document.getElementById('dashboard-payment-email').value;
    const messageEl = document.getElementById('dashboard-payment-modal-message');
    const submitBtn = event.target.querySelector('button[type="submit"]');

    submitBtn.disabled = true;
    submitBtn.textContent = 'PROCESSING...';

    try {
        const response = await fetch('/api/payment/create-checkout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email })
        });

        const data = await response.json();

        if (data.success) {
            // Store email for post-payment
            sessionStorage.setItem('payment_email', email);

            // Redirect to Dodo checkout
            window.location.href = data.checkout_url;
        } else {
            showMessage(messageEl, 'error', '✗ ' + data.message);
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<span class="btn-glow"></span>CONTINUE TO PAYMENT';
        }
    } catch (error) {
        showMessage(messageEl, 'error', '✗ Connection error');
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<span class="btn-glow"></span>CONTINUE TO PAYMENT';
        console.error('Payment error:', error);
    }
}

async function checkBotStatus(botId, botUsername) {
    try {
        console.log(`[Bot ${botId}] Checking Telegram status...`);
        const response = await fetch(`/api/bots/${botId}/status`);
        const data = await response.json();

        console.log(`[Bot ${botId}] Status response:`, data);

        const statusElement = document.getElementById(`telegram-status-${botId}`);
        const actionsElement = document.getElementById(`actions-${botId}`);

        if (!statusElement) {
            console.warn(`[Bot ${botId}] Status element not found, stopping checks`);
            return;
        }

        if (data.success) {
            const status = data.status;
            console.log(`[Bot ${botId}] Current status: ${status}, Telegram ready: ${data.telegram_ready}`);

            if (status === 'ready') {
                // Telegram is connected and ready!
                statusElement.innerHTML = '🟢 Ready!';
                statusElement.style.color = 'var(--primary-green)';
                console.log(`[Bot ${botId}] ✅ Telegram is ready!`);

                // Add test button if not already present
                if (actionsElement && !actionsElement.querySelector('.btn-test')) {
                    const testBtn = `<button class="btn-small btn-test" onclick="window.open('https://t.me/${botUsername}', '_blank')" style="background: var(--primary-cyan); color: var(--bg-dark);">
                        💬 TEST BOT
                    </button>`;
                    actionsElement.insertAdjacentHTML('afterbegin', testBtn);
                    console.log(`[Bot ${botId}] Added TEST BOT button`);
                }
                // Stop checking - bot is ready!
            } else if (status === 'initializing') {
                statusElement.textContent = '🟡 Initializing...';
                statusElement.style.color = '#ffbd2e';
                console.log(`[Bot ${botId}] Service active, waiting for Telegram... (checking again in 5s)`);
                // Check again in 5 seconds - service is running but Telegram not ready yet
                setTimeout(() => checkBotStatus(botId, botUsername), 5000);
            } else {
                // Still deploying
                statusElement.textContent = '🟡 Setting up...';
                statusElement.style.color = '#ffbd2e';
                console.log(`[Bot ${botId}] VPS still deploying... (checking again in 10s)`);
                // Check again in 10 seconds - VPS still being set up
                setTimeout(() => checkBotStatus(botId, botUsername), 10000);
            }
        } else {
            console.error(`[Bot ${botId}] Status check failed:`, data.message);
        }
    } catch (error) {
        console.error(`[Bot ${botId}] Status check error:`, error);
        const statusElement = document.getElementById(`telegram-status-${botId}`);
        if (statusElement) {
            statusElement.textContent = '⚠️ Checking...';
            statusElement.style.color = 'var(--primary-cyan)';
            // Retry in 10 seconds on error
            console.log(`[Bot ${botId}] Error occurred, retrying in 10s`);
            setTimeout(() => checkBotStatus(botId, botUsername), 10000);
        }
    }
}
