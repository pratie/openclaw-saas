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

// Auth Modal Functions
function showAuthModal(type) {
    const modal = document.getElementById('auth-modal');
    const title = document.getElementById('auth-modal-title');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    if (type === 'login') {
        title.textContent = 'Login';
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
    } else {
        title.textContent = 'Create Account';
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
    }

    modal.style.display = 'flex';
}

function closeAuthModal() {
    document.getElementById('auth-modal').style.display = 'none';
}

function switchToRegister() {
    showAuthModal('register');
}

function switchToLogin() {
    showAuthModal('login');
}


// Close modal if clicked outside
window.onclick = function(event) {
    const paymentModal = document.getElementById('payment-modal');
    const authModal = document.getElementById('auth-modal');

    if (event.target === paymentModal) {
        closePaymentModal();
    }
    if (event.target === authModal) {
        closeAuthModal();
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

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    // Handle model option clicks
    const modelOptions = document.querySelectorAll('.model-option');
    modelOptions.forEach(option => {
        option.addEventListener('click', function() {
            modelOptions.forEach(opt => opt.classList.remove('selected'));
            this.classList.add('selected');
            this.querySelector('input[type="radio"]').checked = true;
        });
    });

    // Handle channel option clicks
    const channelOptions = document.querySelectorAll('.channel-option');
    channelOptions.forEach(option => {
        option.addEventListener('click', function() {
            channelOptions.forEach(opt => opt.classList.remove('selected'));
            this.classList.add('selected');
            this.querySelector('input[type="radio"]').checked = true;
        });
    });

    // Check for payment success
    const urlParams = new URLSearchParams(window.location.search);
    const paymentSuccess = urlParams.get('payment');

    if (paymentSuccess === 'success') {
        const email = sessionStorage.getItem('payment_email');
        if (email) {
            const regEmailField = document.getElementById('reg-email');
            if (regEmailField) {
                // Pre-fill email in registration form
                regEmailField.value = email;

                // Switch to register modal
                showAuthModal('register');

                // Show success message
                const messageEl = document.getElementById('register-message');
                showMessage(messageEl, 'success', '✓ Payment successful! Complete your registration below.');

                // Clear payment email from storage
                sessionStorage.removeItem('payment_email');
            }
        }
    }
});
