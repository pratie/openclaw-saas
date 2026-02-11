// Landing Page JavaScript

function showTab(tabName) {
    // Hide all panels
    document.querySelectorAll('.form-panel').forEach(panel => {
        panel.classList.remove('active');
    });

    // Remove active class from all tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });

    // Show selected panel and activate tab
    document.getElementById(tabName + '-form').classList.add('active');
    event.target.closest('.tab').classList.add('active');
}

async function login(event) {
    event.preventDefault();

    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    const messageEl = document.getElementById('login-message');

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (data.success) {
            showMessage(messageEl, 'success', '✓ Authentication successful! Redirecting...');
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1000);
        } else {
            showMessage(messageEl, 'error', '✗ ' + data.message);
        }
    } catch (error) {
        showMessage(messageEl, 'error', '✗ Connection error');
        console.error('Login error:', error);
    }
}

async function register(event) {
    event.preventDefault();

    const username = document.getElementById('reg-username').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const confirm = document.getElementById('reg-confirm').value;
    const messageEl = document.getElementById('register-message');

    if (password !== confirm) {
        showMessage(messageEl, 'error', '✗ Passwords do not match');
        return;
    }

    if (password.length < 6) {
        showMessage(messageEl, 'error', '✗ Password must be at least 6 characters');
        return;
    }

    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password })
        });

        const data = await response.json();

        if (data.success) {
            showMessage(messageEl, 'success', '✓ Account created! Please login.');
            // Switch to login tab after 2 seconds
            setTimeout(() => {
                document.querySelector('.tab').click();
            }, 2000);
        } else {
            showMessage(messageEl, 'error', '✗ ' + data.message);
        }
    } catch (error) {
        showMessage(messageEl, 'error', '✗ Connection error');
        console.error('Register error:', error);
    }
}

function showMessage(element, type, message) {
    element.textContent = message;
    element.className = 'message ' + type;
    element.style.display = 'block';
}
