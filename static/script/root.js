function showNotification(message, type = 'success', duration = 3000, action = null) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    let actionButton = '';
    if (action) {
        actionButton = `<button class="notification-action">Открыть</button>`;
    }
    
    notification.innerHTML = `
        <div class="notification-icon">
            <i class="fas fa-${type === 'success' ? 'check-circle' : 
            type === 'error' ? 'exclamation-circle' : 
            'exclamation-triangle'}"></i>
        </div>
        <div class="notification-message">${message}</div>
        ${actionButton}
    `;
    
    document.body.appendChild(notification);
    
    if (action) {
        notification.querySelector('.notification-action').addEventListener('click', action);
    }
    
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => notification.remove(), 3000);
    }, duration);
}

function saveThemePreference(isLight) {
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
}

async function checkTokenValidity() {
    const tokens = getTokens();
    if (!tokens.access_token) return false;

    try {
        const response = await fetch('/auth/me', {
            headers: {
                'Authorization': `Bearer ${tokens.access_token}`
            }
        });

        if (response.status === 401 && tokens.refresh_token) {
            const newTokens = await refreshTokens(tokens.refresh_token);
            if (newTokens) {
                saveTokens(newTokens);
                return true;
            }
            return false;
        }

        return response.ok;
    } catch (error) {
        console.error('Token check failed:', error);
        return false;
    }
}

function loadThemePreference() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
        const icon = document.querySelector('.theme-toggle i');
        if (icon) {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
        }
    }
}

function setupThemeToggle() {
    const toggle = document.querySelector('.theme-toggle');
    if (toggle) {
        toggle.addEventListener('click', function() {
            const isLight = document.body.classList.toggle('light-theme');
            const icon = this.querySelector('i');
            
            if (isLight) {
                icon.classList.remove('fa-moon');
                icon.classList.add('fa-sun');
            } else {
                icon.classList.remove('fa-sun');
                icon.classList.add('fa-moon');
            }
            
            saveThemePreference(isLight);
        });
    }
}

function saveTokens(tokens) {
    localStorage.setItem('access_token', tokens.access_token);
    if (tokens.refresh_token) {
        localStorage.setItem('refresh_token', tokens.refresh_token);
    }
}

function getTokens() {
    return {
        access_token: localStorage.getItem('access_token'),
        refresh_token: localStorage.getItem('refresh_token')
    }
}

function clearTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.reload();
}

function openModal(modal) {
    document.body.style.overflow = 'hidden';
    modal.classList.add('show');
}

function closeModal(modal) {
    document.body.style.overflow = '';
    modal.classList.remove('show');
}

document.addEventListener('DOMContentLoaded', async () => {
    setupThemeToggle();
    await updateAuthState();
    
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('auth_required') === 'true') {
        const loginModal = document.getElementById('loginModal');
        openModal(loginModal);
    }
});

async function updateAuthState() {
    const isValid = await checkTokenValidity();
    const loginBtn = document.querySelector('.btn-login');
    const registerBtn = document.querySelector('.btn-register');
    const profileBtn = document.querySelector('.btn-profile');

    showMainLoader(true);
    
    if (isValid) {
        const gitStatus = await checkStatusGithub();
        if (!gitStatus?.linked) {
            registerBtn.style.display = "none";
            loginBtn.style.display = "none";
            profileBtn.style.display = "block";
        } else {
            registerBtn.style.display = "none";
            loginBtn.style.display = "none";
            profileBtn.style.display = "block";
        }
        profileBtn?.addEventListener('click', openProfile);
        showMainLoader(false);
    } else {
        profileBtn.style.display = "none";
        loginBtn.style.display = "block";
        registerBtn.style.display = 'block';
        
        const loginModal = document.getElementById('loginModal');
        const registerModal = document.getElementById('registerModal');
        
        loginBtn?.addEventListener('click', () => openModal(loginModal));
        registerBtn?.addEventListener('click', () => openModal(registerModal));
        showMainLoader(false);
    }
}
