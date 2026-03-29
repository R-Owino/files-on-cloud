
document.addEventListener('DOMContentLoaded', function () {
    const togglePassword = document.querySelector('.toggle-password');
    const passwordField = document.querySelector('#password');
    const form = document.getElementById('loginForm');
    const toast = document.getElementById('errorToast');

    // password visibility toggle
    if (togglePassword && passwordField) {
        togglePassword.addEventListener('click', function () {
            const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordField.setAttribute('type', type);

            this.classList.toggle('password-visible');
        });
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(e.target);

        try {
            const response = await fetch(`/login`, {
                method: 'POST',
                body: formData,
                headers: {
                    'Accept': 'text/html'
                }
            });

            if (response.redirected) {
                window.location.href = response.url;
            } else {
                if (response.status === 400) {
                    toast.textContent = "Email and password are required.";
                } else if (response.status === 401) {
                    toast.textContent = "Invalid credentials.";
                } else if (response.status === 404) {
                    toast.textContent = "User not found. Please check your credentials.";
                } else if (response.status === 500) {
                    toast.textContent = "An unexpected error occurred.";
                } else {
                    toast.textContent = "Login failed. Please try again."
                }

                toast.style.display = 'block';

                setTimeout(() => {
                    toast.style.display = 'none';
                }, 3000);
            }
        } catch (error) {
            console.error('Login error:', error);
            toast.textContent = "Network error. Please try again."
            toast.style.display = 'block';

            setTimeout(() => {
                toast.style.display = 'none';
            }, 3000);
        }
    });
});
