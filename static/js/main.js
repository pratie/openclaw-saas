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

// Payment Modal Functions
function showPaymentModal() {
    document.getElementById('payment-modal').style.display = 'flex';
}

function closePaymentModal() {
    document.getElementById('payment-modal').style.display = 'none';
}

// Close modal if clicked outside
window.onclick = function(event) {
    const modal = document.getElementById('payment-modal');
    if (event.target === modal) {
        closePaymentModal();
    }
}

async function createCheckout(event) {
    event.preventDefault();

    const email = document.getElementById('payment-email').value;
    const messageEl = document.getElementById('payment-modal-message');
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
            // Store email in sessionStorage for post-payment registration
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

// Check for payment success on page load
window.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const paymentSuccess = urlParams.get('payment');

    if (paymentSuccess === 'success') {
        const email = sessionStorage.getItem('payment_email');
        if (email) {
            // Pre-fill email in registration form
            document.getElementById('reg-email').value = email;

            // Switch to register tab
            const registerTab = document.querySelectorAll('.tab')[1];
            registerTab.click();

            // Show success message
            const messageEl = document.getElementById('register-message');
            showMessage(messageEl, 'success', '✓ Payment successful! Complete your registration below.');

            // Clear payment email from storage
            sessionStorage.removeItem('payment_email');
        }
    }
});
