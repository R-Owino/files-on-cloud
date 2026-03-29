// main entry point
function initApp() {
    try {
        // Initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    } catch (e) {
        console.error('[MAIN] Icon initialization failed:', e);
    }

    // Initialize sidebar if function exists
    try {
        if (typeof window.initializeSidebar === 'function') {
            window.initializeSidebar();
        }
    } catch (e) {
        console.error('[MAIN] Sidebar initialization failed:', e);
    }

    // Initialize file display
    let fileDisplayManager = null;
    try {
        const filesContainer = document.getElementById('files-container');

        if (filesContainer && typeof window.FileDisplayManager === 'function') {
            fileDisplayManager = new window.FileDisplayManager();
        } else {
            console.warn('[MAIN] FileDisplayManager skipped - container or class missing');
        }
    } catch (e) {
        console.error('[MAIN] FileDisplayManager failed:', e);
    }

    // Initialize file upload
    try {
        const uploadInput = document.getElementById('file-upload');
        if (uploadInput && typeof window.FileUploader === 'function') {
            new window.FileUploader();
        }
    } catch (e) {
        console.error('[MAIN] FileUploader failed:', e);
    }

    // Initialize file actions
    try {
        if (typeof window.FileActionHandler === 'function') {
            new window.FileActionHandler(fileDisplayManager);
        }
    } catch (e) {
        console.error('[MAIN] FileActionHandler failed:', e);
    }
}

try {
    // Import all components
    import('./sidebar.js').then(module => {
        window.initializeSidebar = module.initializeSidebar;
    }).catch(e => console.error('[MAIN] Sidebar import failed:', e));

    import('./fileUpload.js').then(module => {
        window.FileUploader = module.FileUploader;
    }).catch(e => console.error('[MAIN] FileUpload import failed:', e));

    import('./fileDisplay.js').then(module => {
        window.FileDisplayManager = module.FileDisplayManager;
    }).catch(e => console.error('[MAIN] FileDisplay import failed:', e));

    import('./fileActions.js').then(module => {
        window.FileActionHandler = module.FileActionHandler;
    }).catch(e => console.error('[MAIN] FileActions import failed:', e));

    // DOM ready detection
    if (document.readyState !== 'loading') {
        initApp();
    } else {
        document.addEventListener('DOMContentLoaded', initApp);
    }
} catch (e) {
    console.error('[MAIN] Top-level error:', e);
}

// Final fallback in case all DOM methods fail
setTimeout(() => {
    initApp();
}, 1000);
