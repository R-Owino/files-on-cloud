// handle download and delete operations with authentication checks

import { NotificationManager } from './notifications.js';

export class FileActionHandler {
    constructor(fileDisplayManager) {
        this.fileDisplayManager = fileDisplayManager;
        this.filesContainer = document.getElementById('files-container');
        this.loginUrl = window.loginUrl || '/login';
        this.loginModal = document.getElementById('loginModal');

        // event listener for login button
        const loginBtn = document.getElementById('loginModalLogin');
        if (loginBtn) {
            loginBtn.addEventListener('click', () => {
                window.location.href = this.loginUrl;
            });
        }

        // event listener for close button
        const loginModalClose = document.getElementById('loginModalClose');
        if (loginModalClose) {
            loginModalClose.addEventListener('click', () => {
                this.hideLoginModal();
            });
        }

        // Close modal when clicking outside
        if (this.loginModal) {
            this.loginModal.addEventListener('click', (event) => {
                if (event.target === this.loginModal) {
                    this.hideLoginModal();
                }
            });
        }

        this.initializeEventListeners();
    }

    initializeEventListeners() {
        this.filesContainer.addEventListener('click', async (event) => {
            const downloadIcon = event.target.closest('.download-file');
            const deleteIcon = event.target.closest('.delete-file');

            if (downloadIcon) await this.handleDownload(downloadIcon);
            if (deleteIcon) await this.handleDelete(deleteIcon);
        });
    }

    // Check authentication before performing actions
    requiresAuth(action) {
        if (!window.isLoggedIn) {
            this.showLoginModal();
            return false;
        }
        return true;
    }

    showLoginModal() {
        if (this.loginModal) {
            this.loginModal.classList.add('visible');
        }
    }

    hideLoginModal() {
        if (this.loginModal) {
            this.loginModal.classList.remove('visible');
        }
    }

    async handleDownload(element) {
        if (!this.requiresAuth('download')) return;

        try {
            const fileKey = element.dataset.fileKey;

            const proxyUrl = `/download/${encodeURIComponent(fileKey)}`;

            window.location.href = proxyUrl;

            NotificationManager.showSuccess('Download started!');
        } catch (error) {
            console.error('Download error:', error);
            NotificationManager.showError('Failed to download file. Please try again later.');
        }
    }

    async handleDelete(element) {
        if (!this.requiresAuth('delete')) return;

        const fileKey = element.dataset.fileKey;
        if (!fileKey) {
            NotificationManager.showError('File key missing');
            return;
        }

        try {
            const shouldDelete = await NotificationManager.showConfirmationDialog(
                'Are you sure you want to delete this file? This action cannot be undone.',
                'Delete',
                'Cancel'
            );

            if (!shouldDelete) {
                NotificationManager.showToast('File deletion canceled.', 'error');
                return;
            }

            const response = await fetch(
                `/delete?file_key=${encodeURIComponent(fileKey)}`,
                { method: 'DELETE' }
            );

            if (response.ok) {
                // Invalidate cache after successful deletion
                await this.invalidateFileMetadataCache();

                // Force refresh the file list to show changes immediately
                await this.fileDisplayManager.fetchRecentFiles();

                NotificationManager.showSuccess('File deleted successfully!');
            } else {
                const errorData = await response.json();
                NotificationManager.showError(`Failed to delete file: ${errorData.error}`);
            }
        } catch (error) {
            console.error('Delete request error:', error);
            NotificationManager.showError(`An error occurred: ${error.message}`);
        }
    }

    /**
     * Invalidate the file metadata cache after successful file delete
     * Ensures the dashboard shows updated file lists immediately
     */
    async invalidateFileMetadataCache() {
        try {
            const response = await fetch('/file-metadata/invalidate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok) {
                console.log('File metadata cache invalidated successfully after deletion');
            } else {
                console.warn('Failed to invalidate cache after deletion, but deletion was successful');
            }
        } catch (error) {
            console.warn('Cache invalidation failed after deletion:', error.message);
        }
    }
}
