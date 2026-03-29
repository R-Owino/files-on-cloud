// sidebar functionality - Only handles delete account modal

const SELECTORS = {
    SIDEBAR: '.sidebar',
    TOGGLE: '.sidebar-toggle',
    EMAIL_CONTAINER: '.user-email-container',
    LOGOUT_SECTION: '.logout-section',
    DROPDOWN_ARROW: '.down-arrow',
    DELETE_ACCOUNT_MODAL: '#deleteAccountModal',
    DELETE_ACCOUNT_BTN: '.delete-account-btn',
    MODAL_CANCEL_BTN: '#deleteModalCancel',
    MODAL_DELETE_BTN: '#deleteModalDelete',
    LOGOUT_BTN: '.logout-btn',
    MOBILE_TOGGLE: '.mobile-menu-toggle',
    SIDEBAR_OVERLAY: '.sidebar-overlay'
};

const API_ENDPOINTS = {
    register: '/register',
    delete_account: '/delete-account',
    logout: '/logout'
};

class SidebarManager {
    constructor() {
        this.sidebar = document.querySelector(SELECTORS.SIDEBAR);
        this.toggle = document.querySelector(SELECTORS.TOGGLE);
        this.emailContainer = document.querySelector(SELECTORS.EMAIL_CONTAINER);
        this.logoutSection = document.querySelector(SELECTORS.LOGOUT_SECTION);
        this.dropdownArrow = document.querySelector(SELECTORS.DROPDOWN_ARROW);
        this.deleteAccountModal = document.querySelector(SELECTORS.DELETE_ACCOUNT_MODAL);
        this.deleteAccountBtn = document.querySelector(SELECTORS.DELETE_ACCOUNT_BTN);
        this.modalCancelBtn = document.querySelector(SELECTORS.MODAL_CANCEL_BTN);
        this.modalDeleteBtn = document.querySelector(SELECTORS.MODAL_DELETE_BTN);
        this.logoutBtn = document.querySelector(SELECTORS.LOGOUT_BTN);
        this.mobileToggle = document.querySelector(SELECTORS.MOBILE_TOGGLE);
        this.sidebarOverlay = document.querySelector(SELECTORS.SIDEBAR_OVERLAY);

        this.initializeEventListeners();

        // Conditionally initialize features based on user type
        if (this.deleteAccountBtn && this.modalCancelBtn && this.modalDeleteBtn) {
            this.initializeDeleteAccount();
        }

        if (this.logoutBtn) {
            this.initializeLogout();
        }

        if (this.mobileToggle) {
            this.mobileToggle.addEventListener('click', () => this.toggleSidebar());
        }

        if (this.sidebarOverlay) {
            this.sidebarOverlay.addEventListener('click', () => this.toggleSidebar());
        }
    }

    initializeEventListeners() {
        if (this.toggle) {
            this.toggle.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }

        if (this.emailContainer) {
            this.emailContainer.addEventListener('click', () => {
                this.handleEmailContainerClick();
            });
        }

        const userIcon = document.querySelector('.user-icon');
        if (userIcon) {
            userIcon.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }

        document.addEventListener('click', (event) => {
            this.handleOutsideClick(event);
        });
    }

    toggleSidebar() {
        if (!this.sidebar) return;

        this.sidebar.classList.toggle('expanded');

        // Mobile-specific behavior
        if (window.innerWidth <= 768) {
            document.body.classList.toggle('sidebar-open');
        }

        // Desktop-specific behavior
        if (window.innerWidth > 768 && this.logoutSection && this.dropdownArrow) {
            this.logoutSection.classList.remove('expanded');
            this.dropdownArrow.classList.remove('active');
        }
    }

    handleEmailContainerClick() {
        if (!this.sidebar || !this.sidebar.classList.contains('expanded')) return;
        if (!this.logoutSection || !this.dropdownArrow) return;

        this.logoutSection.classList.toggle('expanded');
        this.dropdownArrow.classList.toggle('active');
    }

    handleOutsideClick(event) {
        if (!this.emailContainer || !this.logoutSection) return;

        const isClickOutside = !this.emailContainer.contains(event.target) &&
            !this.logoutSection.contains(event.target);

        if (isClickOutside && this.logoutSection && this.dropdownArrow) {
            this.logoutSection.classList.remove('expanded');
            this.dropdownArrow.classList.remove('active');
        }
    }

    initializeDeleteAccount() {
        if (!this.deleteAccountBtn || !this.deleteAccountModal) return;

        this.deleteAccountBtn.addEventListener('click', () => {
            this.deleteAccountModal.classList.add('visible');
        });

        if (this.modalCancelBtn) {
            this.modalCancelBtn.addEventListener('click', () => {
                this.deleteAccountModal.classList.remove('visible');
            });
        }

        if (this.modalDeleteBtn) {
            this.modalDeleteBtn.addEventListener('click', async () => {
                try {
                    this.showToast('Deleting account...');

                    const response = await fetch(API_ENDPOINTS.delete_account, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        }
                    });

                    const data = await response.json();

                    if (response.ok) {
                        this.showToast(data.message);

                        setTimeout(() => {
                            window.location.href = API_ENDPOINTS.register;
                        }, 1500);

                    } else {
                        this.showToast(data.message || 'Failed to delete account');
                        this.deleteAccountModal.classList.remove('visible');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    this.showToast('An unexpected error occurred');
                    this.deleteAccountModal.classList.remove('visible');
                }
            });
        }

        if (this.deleteAccountModal) {
            this.deleteAccountModal.addEventListener('click', (event) => {
                if (event.target === this.deleteAccountModal) {
                    this.deleteAccountModal.classList.remove('visible');
                }
            });
        }
    }

    initializeLogout() {
        if (!this.logoutBtn) return;

        this.logoutBtn.addEventListener('click', async (event) => {
            event.preventDefault();

            this.showToast('Logging out...');

            try {
                const response = await fetch(API_ENDPOINTS.logout, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }
                });

                if (response.ok) {
                    this.showToast('Logged out successfully');
                    setTimeout(() => {
                        window.location.href = response.url;
                    }, 1500);
                } else {
                    this.showToast('Failed to log out');
                }
            } catch (error) {
                console.error('Error:', error);
                this.showToast('An unexpected error occurred');
            }
        });
    }

    showToast(message) {
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            document.body.appendChild(toastContainer);
        }

        const toast = document.createElement('div');
        toast.className = 'toast-notification';
        toast.textContent = message;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('show');
        }, 10);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 400);
        }, 5000);
    }
}

export function initializeSidebar() {
    return new SidebarManager();
}
