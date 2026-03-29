// file display and search functionalities

import { utils } from './utils.js';

export class FileDisplayManager {
    constructor() {

        this.searchInput = document.querySelector('.search-input');
        this.filesContainer = document.getElementById('files-container');
        if (!this.filesContainer) {
            console.error('[FILE] Critical: files-container missing!');
            return;
        }
        this.isSearching = false;
        this.isLoggedIn = window.isLoggedIn || false;
        this.debouncedSearch = utils.debounce(this.handleSearch.bind(this), 300);

        this.initializeEventListeners();
        this.fetchRecentFiles();
    }

    initializeEventListeners() {
        this.searchInput.addEventListener('focus', () => {
            this.searchInput.placeholder = "Type to search...";
        });

        this.searchInput.addEventListener('blur', () => {
            this.searchInput.placeholder = "Search files...";
            if (this.searchInput.value.trim() === '') {
                this.fetchRecentFiles();
            }
        });

        this.searchInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.trim();
            this.debouncedSearch(searchTerm);
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-container')) {
                this.searchInput.classList.remove('active');
                this.searchInput.value = '';
                this.fetchRecentFiles();
            }
        });
    }

    async fetchRecentFiles() {
        try {
            const response = await fetch(`/file-metadata`);
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const data = await response.json();

            // Always display files if they exist, regardless of auth status
            if (!this.isSearching) {
                if (data.files?.length > 0) {
                    this.displayFiles(data.files, data.authenticated);
                } else {
                    const message = this.isLoggedIn
                        ? "No files have been uploaded yet. Upload your first file to get started!"
                        : "No files are available in the catalog yet. Files uploaded by users will appear here."
                    this.showNoFilesMessage(message);
                }
            }
        } catch (error) {
            console.error('Error fetching files:', error);
            if (!this.isSearching) {
                this.showNoFilesMessage("Unable to load files. Please try again later.");
            }
        }
    }

    displayFiles(files, isAuthenticated = false) {
        this.filesContainer.innerHTML = '';
        const columns = Array.from({ length: 3 }, () => {
            const col = document.createElement('div');
            col.className = 'files-column';
            return col;
        });

        files.forEach((file, index) => {
            const columnIndex = Math.floor(index / Math.ceil(files.length / 3));
            const fileItem = this.createFileElement(file, isAuthenticated);
            columns[columnIndex].appendChild(fileItem);
        });

        columns.forEach(col => this.filesContainer.appendChild(col));
        lucide.createIcons();
    }

    async handleSearch(searchTerm) {
        if (searchTerm === '') {
            this.isSearching = false;
            this.fetchRecentFiles();
            return;
        }

        this.isSearching = true;
        try {
            const response = await fetch(`/search-files?search=${encodeURIComponent(searchTerm)}`);
            if (!response.ok) throw new Error('Search failed');

            const data = await response.json();

            if (data.files?.length > 0) {
                this.displayFiles(data.files, data.authenticated || false);
            } else {
                this.showNoFilesMessage(`No files found matching "${searchTerm}". Try a different search term.`);
            }
        } catch (error) {
            console.error('Error during search:', error);
            this.showNoFilesMessage("An error occurred while searching. Please try again.");
        }
    }

    createFileElement(file) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        const icon = utils.getFileIcon(file.file_name);

        fileItem.innerHTML = `
            <i class="file-icon" data-lucide="${icon}"></i>
            <div class="file-details">
                <div class="file-name">${file.file_name}</div>
                <div class="file-size">${(file.size_bytes / 1024 / 1024).toFixed(1)} MB</div>
            </div>
            <div class="file-actions">
                <i class="action-icon download-file" data-file-key="${file.file_key}" data-lucide="download"></i>
                <i class="action-icon delete-file" data-file-key="${file.file_key}" data-lucide="trash-2"></i>
            </div>
        `;

        return fileItem;
    }

    showNoFilesMessage(message) {
        this.filesContainer.innerHTML = `
            <div class="message-container">
                <i data-lucide="inbox" class="message-icon"></i>
                <p class="message-text">${message}</p>
            </div>
        `;
        lucide.createIcons();
    }
}
