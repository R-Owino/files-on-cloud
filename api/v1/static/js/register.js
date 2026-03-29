document.addEventListener('DOMContentLoaded', function () {
    const emailInput = document.getElementById('email');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const togglePassword = document.querySelector('.toggle-password');
    const passwordField = document.querySelector('#password');
    const validationFeedback = document.querySelector('.email-validation-feedback');
    const requirementsDiv = document.getElementById('password-requirements');
    const form = document.querySelector('form');
    const inputGroups = document.querySelectorAll('.input-group');

    // Add active class to input groups on focus
    inputGroups.forEach(group => {
        const input = group.querySelector('input');

        input.addEventListener('focus', () => {
            group.classList.add('active');
        });

        input.addEventListener('blur', () => {
            if (!input.value) {
                group.classList.remove('active');
            }
        });

        // Keep active class if input has value
        if (input.value) {
            group.classList.add('active');
        }
    });

    // password visibility toggle
    if (togglePassword && passwordField) {
        togglePassword.addEventListener('click', function () {
            const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordField.setAttribute('type', type);

            this.classList.toggle('password-visible');
        });
    }

    // handle email validation display
    emailInput.addEventListener('focus', () => {
        validationFeedback.style.display = 'block';
        setTimeout(() => validationFeedback.classList.add('visible'), 10);
    });

    emailInput.addEventListener('blur', (e) => {
        if (!e.relatedTarget?.closest('.email-validation-feedback')) {
            validationFeedback.classList.remove('visible');
            setTimeout(() => {
                if (!validationFeedback.classList.contains('visible')) {
                    validationFeedback.style.display = 'none';
                }
            }, 300);
        }
    });

    // handle password requirements display
    passwordInput.addEventListener('focus', () => {
        requirementsDiv.style.display = 'block';
    });

    passwordInput.addEventListener('blur', (e) => {
        if (!e.relatedTarget?.closest('.password-requirements')) {
            requirementsDiv.style.display = 'none';
        }
    });

    // form submission and validation
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(e.target);

        try {
            const response = await fetch(`/register`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.success && data.redirect_url) {
              window.location.href = data.redirect_url;
            } else {
                // const data = await response.json();

                if (response.status === 409) {
                    showToast(data.message);
                } else {
                    showToast(data.message);
                }
            }

        } catch (error) {
            console.error('Registration error:', error);
            showToast('An error occurred. Please try again.');
        }
    });

    function showToast(message) {
        const toast = document.getElementById('errorToast');
        toast.textContent = message;
        toast.style.display = 'block';
        toast.style.animation = 'none';
        void toast.offsetWidth;
        toast.style.animation = 'slideIn 0.5s, fadeOut 0.5s 2.5s';

        toast.addEventListener('animationend', (e) => {
            if (e.animationName === 'fadeOut') {
                toast.style.display = 'none';
            }
        });
    }

    // email validation patterns
    const emailPatterns = {
        format: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
        domain: /\.(com|net|org|edu|gov|mil|info|io|co|[a-z]{2})$/i,
        length: (email) => email.length >= 5 && email.length <= 50,
        special: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
    };

    function validateEmail(email) {
        const results = {
            format: emailPatterns.format.test(email),
            domain: emailPatterns.domain.test(email),
            length: emailPatterns.length(email),
            special: emailPatterns.special.test(email)
        };

        return {
            isValid: Object.values(results).every(Boolean),
            results
        };
    }

    function updateValidationUI(validationResults) {
        Object.entries(validationResults.results).forEach(([check, isValid]) => {
            const element = document.querySelector(`[data-check="${check}"]`);
            element.classList.remove('valid', 'invalid');
            element.classList.add(isValid ? 'valid' : 'invalid');
        });

        emailInput.classList.remove('valid-email', 'invalid-email');
        if (validationResults.isValid) {
            emailInput.classList.add('valid-email');
        } else if (emailInput.value) {
            emailInput.classList.add('invalid-email');
        }
    }

    // Email validation event listeners
    emailInput.addEventListener('focus', () => {
        validationFeedback.classList.add('visible');
    });

    emailInput.addEventListener('input', (e) => {
        const validationResults = validateEmail(e.target.value);
        updateValidationUI(validationResults);
    });

    // Check password requirements as the user types
    passwordInput.addEventListener('input', () => {
        const password = passwordInput.value;

        const requirements = {
            'length-check': password.length >= 8,
            'uppercase-check': /[A-Z]/.test(password),
            'lowercase-check': /[a-z]/.test(password),
            'number-check': /\d/.test(password),
            'special-check': /[!@#$%^&*(),.?":{}|<>]/.test(password)
        };

        for (const [id, passes] of Object.entries(requirements)) {
            const element = document.getElementById(id);
            if (passes) {
                element.classList.add('requirement-met');
            } else {
                element.classList.remove('requirement-met');
            }
        }
    });

    // Trigger input event to initialize validation states
    if (emailInput.value) {
        emailInput.dispatchEvent(new Event('input'));
    }

    if (passwordInput.value) {
        passwordInput.dispatchEvent(new Event('input'));
    }

    // Validate all requirements before form submission
    form.addEventListener('submit', (e) => {
        const password = passwordInput.value;
        const allRequirementsMet =
            password.length >= 8 &&
            /[A-Z]/.test(password) &&
            /[a-z]/.test(password) &&
            /\d/.test(password) &&
            /[!@#$%^&*(),.?":{}|<>]/.test(password);

        if (!allRequirementsMet) {
            e.preventDefault();
            requirementsDiv.style.display = 'block';
            showToast('Please ensure all password requirements are met.');
            passwordInput.focus();
        }

        const emailValidation = validateEmail(emailInput.value);
        if (!emailValidation.isValid) {
            e.preventDefault();
            validationFeedback.classList.add('visible');
            showToast('Please enter a valid email address.');
            emailInput.focus();
        }
    });
});
