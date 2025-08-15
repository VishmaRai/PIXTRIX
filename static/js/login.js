        function togglePassword() {
            const passwordInput = document.getElementById('password');
            const toggleIcon = document.querySelector('.toggle-password path');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                // Change to eye-slash icon (hidden)
                toggleIcon.setAttribute('d', 'M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z');
            } else {
                passwordInput.type = 'password';
                // Change back to eye icon (visible)
                toggleIcon.setAttribute('d', 'M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z');
            }
        }

        // Add typing effect to inputs
        document.querySelectorAll('.form-input').forEach(input => {
            input.addEventListener('input', function() {
                this.style.textShadow = '0 0 5px rgba(0, 255, 0, 0.8)';
                setTimeout(() => {
                    this.style.textShadow = 'none';
                }, 200);
            });
        });

function isEmail(email) {
    // Regular expression for basic email validation
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(String(email).toLowerCase());
}

        // Form validation
        document.getElementById('loginForm').addEventListener('submit', function(e) {
            const email = document.getElementById('email');
            const password = document.getElementById('password');
            const emailError = document.getElementById('email-error');
            const passwordError = document.getElementById('password-error');

            let hasErrors = false;

            // Reset errors
            email.classList.remove('error');
            password.classList.remove('error');
            emailError.style.display = 'none';
            passwordError.style.display = 'none';

            if (email.value.trim() === '') {
                email.classList.add('error');
                emailError.textContent = 'Please enter your email address.';
                emailError.style.display = 'block';
                hasErrors = true;
            } else if (!isEmail(email.value)) {
                email.classList.add('error');
                emailError.textContent = 'Please enter a valid email address.';
                emailError.style.display = 'block';
                hasErrors = true;
            }

            if (password.value.trim() === '') {
                password.classList.add('error');
                passwordError.textContent = 'Please enter your password.';
                passwordError.style.display = 'block';
                hasErrors = true;
            }

            if (hasErrors) {
                e.preventDefault();
            }
        });