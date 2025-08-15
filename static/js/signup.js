// ===== TOAST NOTIFICATION FUNCTIONS =====
function showToast(message, type = 'info') {
    // Remove existing toast if any
    const existingToast = document.querySelector('.toast-notification');
    if (existingToast) {
        existingToast.remove();
    }

    // Create new toast
    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    
    // Add appropriate icon based on type
    const icons = {
        success: '✓',
        error: '✗',
        info: 'ℹ',
        warning: '⚠'
    };
    
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span>${message}</span>
        <button class="close-btn" onclick="this.parentElement.remove()">×</button>
    `;

    document.body.appendChild(toast);

    // Show toast with animation
    setTimeout(() => toast.classList.add('show'), 100);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 400);
        }
    }, 5000);
}

function showModal(message, type = 'info') {
    // Remove existing modal if any
    const existingModal = document.querySelector('.modal-overlay');
    if (existingModal) {
        existingModal.remove();
    }

    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    
    const icons = {
        success: '✓',
        error: '✗',
        info: 'ℹ',
        warning: '⚠'
    };
    
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-icon ${type}">${icons[type]}</div>
            <div class="modal-message">${message}</div>
            <button class="modal-button" onclick="this.closest('.modal-overlay').remove()">OK</button>
        </div>
    `;

    document.body.appendChild(modal);
    
    // Show modal
    setTimeout(() => modal.classList.add('show'), 100);
    
    // Close modal when clicking outside
    modal.addEventListener('click', function(e) {
        if (e.target === this) {
            this.remove();
        }
    });
}

// ===== EXISTING FUNCTIONS =====

// Password visibility toggle
function togglePassword(fieldId) {
    const field = document.getElementById(fieldId);
    const eyeIcon = field.nextElementSibling;
    
    if (field.type === 'password') {
        field.type = 'text';
        eyeIcon.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                <path d="M1 1l22 22"/>
            </svg>
        `;
    } else {
        field.type = 'password';
        eyeIcon.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
            </svg>
        `;
    }
}

// ===== COOLDOWN FUNCTION =====
function startCooldown(btn, seconds) {
    btn.disabled = true;
    btn.classList.remove('loading'); // Ensure loading animation is removed
    let remaining = seconds;
    btn.textContent = `Resend after ${remaining}s`;

    const interval = setInterval(() => {
        remaining--;
        if (remaining > 0) {
            btn.textContent = `Resend after ${remaining}s`;
        } else {
            clearInterval(interval);
            btn.textContent = 'Send Code';
            btn.disabled = false;
        }
    }, 1000);
}

// Send verification code - UPDATED WITH COOLDOWN
async function sendCode() {
    const email = document.getElementById('email').value.trim();
    const btn = document.querySelector('.send-code-btn');
    
    // Clear previous errors
    hideFieldError('email');
    
    // Validate email
    if (!email) {
        showFieldError('email', 'Please enter your Email address first!');
        showToast('Please enter your Email address first!', 'error');
        return;
    }
    
    // Simple email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showFieldError('email', 'Please enter a valid email address');
        showToast('Please enter a valid email address', 'error');
        return;
    }
    
    // Update UI with loading state
    btn.classList.add('loading');
    btn.textContent = 'Sending...';
    btn.disabled = true;
    
    try {
        // Send request to backend
        const response = await fetch('/send_verification_code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email: email })
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            // Success
            showToast(result.message || 'Verification code sent to your email', 'success');
            startCooldown(btn, 60); // Start 60s cooldown
        } else {
            
            // API returned error
            btn.classList.remove('loading');
            btn.textContent = 'Send Code';
            btn.disabled = false; // Re-enable on error
            showFieldError('email', result.message || 'Failed to send code');
            showToast(result.message || 'Failed to send code', 'error');

            // If it's a cooldown error, start the timer on the frontend too
            if (result.message && result.message.toLowerCase().includes('wait')) {
                startCooldown(btn, 60);
            }
        }
    } catch (error) {
        // Network or server error
        console.error('Error sending verification code:', error);
        btn.classList.remove('loading');
        btn.textContent = 'Send Code';
        btn.disabled = false;
        showToast('Failed to connect to server. Please try again.', 'error');
    }
}

// Show field error
function showFieldError(fieldId, message) {
    const field = document.getElementById(fieldId);
    const errorElement = document.getElementById(fieldId + '-error');
    const wrapper = field.closest('.input-wrapper');
    
    if (message) {
        errorElement.textContent = message;
    }
    
    errorElement.style.display = 'block';
    field.classList.add('error');
    if (wrapper) {
        wrapper.classList.add('error');
    }
}

// Hide field error
function hideFieldError(fieldId) {
    const field = document.getElementById(fieldId);
    const errorElement = document.getElementById(fieldId + '-error');
    const wrapper = field.closest('.input-wrapper');
    
    errorElement.style.display = 'none';
    field.classList.remove('error');
    if (wrapper) {
        wrapper.classList.remove('error');
    }
}

// Clear all errors
function clearAllErrors() {
    const fields = ['username', 'email', 'password', 'confirmPassword', 'code'];
    fields.forEach(fieldId => {
        hideFieldError(fieldId);
    });
}

// Form validation - UPDATED WITH TOAST NOTIFICATIONS
document.getElementById('signupForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    clearAllErrors();
    
    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const code = document.getElementById('code').value.trim();
    
    let hasErrors = false;
    
    // Check each field
    if (!username) {
        showFieldError('username', 'Please enter your Username.');
        hasErrors = true;
    }
    
    if (!email) {
        showFieldError('email', 'Please enter your Email address.');
        hasErrors = true;
    }
    
    if (!password) {
        showFieldError('password', 'Please enter your Password.');
        hasErrors = true;
    } else if (password.length < 8) {
        showFieldError('password', 'Password must be at least 8 characters long.');
        hasErrors = true;
    }
    
    if (!confirmPassword) {
        showFieldError('confirmPassword', 'Please re-enter your password for confirmation.');
        hasErrors = true;
    }
    
    if (!code) {
        showFieldError('code', 'Please enter the verification code.');
        hasErrors = true;
    }
    
    // Check password match only if both passwords are filled
    if (password && confirmPassword && password !== confirmPassword) {
        showFieldError('confirmPassword', 'Passwords do not match!');
        hasErrors = true;
    }
    
    if (hasErrors) {
        document.querySelector('.container').classList.add('glitch');
        showToast('Please fix the errors below', 'error');
        setTimeout(() => {
            document.querySelector('.container').classList.remove('glitch');
        }, 300);
        return;
    }
    
    // If no errors, send data to server
    const formData = new FormData(this);
    const submitBtn = this.querySelector('button[type="submit"]');
    
    // Show loading state
    submitBtn.textContent = 'Creating Account...';
    submitBtn.disabled = true;
    
    fetch('/signup', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Success - show modal and redirect
            showModal(data.message, 'success');
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
        } else {
            // Show error toast
            showToast(data.message || 'An error occurred. Please try again.', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('An error occurred. Please try again.', 'error');
    })
    .finally(() => {
        // Reset button
        submitBtn.textContent = 'Create Account';
        submitBtn.disabled = false;
    });
});

// Add input event listeners to clear errors when user starts typing
const inputs = document.querySelectorAll('input');
inputs.forEach(input => {
    input.addEventListener('input', function() {
        if (this.classList.contains('error')) {
            hideFieldError(this.id);
        }
    });
    
    input.addEventListener('focus', function() {
        this.parentElement.classList.add('focused');
    });
    
    input.addEventListener('blur', function() {
        this.parentElement.classList.remove('focused');
    });
});