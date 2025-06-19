// Переключение темы
document.querySelector('.theme-toggle').addEventListener('click', function() {
    document.body.classList.toggle('light-theme');
    const icon = this.querySelector('i');
    if (document.body.classList.contains('light-theme')) {
        icon.classList.remove('fa-moon');
        icon.classList.add('fa-sun');
    } else {
        icon.classList.remove('fa-sun');
        icon.classList.add('fa-moon');
    }
});

// Анимация при скролле
window.addEventListener('scroll', function() {
    const scrollPosition = window.scrollY;
    const hero = document.querySelector('.hero');
    hero.style.backgroundPositionY = `${scrollPosition * 0.5}px`;
});

const loginModal = document.getElementById('loginModal');
const registerModal = document.getElementById('registerModal');

document.addEventListener('DOMContentLoaded', function() {
    const repoModal = document.getElementById('repoModal');
    const closeButtons = document.querySelectorAll('.close-modal');

    const showRegister = document.getElementById('showRegister');
    const showLogin = document.getElementById('showLogin');

    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const repoForm = document.getElementById('repoForm');
    
    const optionLink = document.getElementById('optionLink');
    const optionZip = document.getElementById('optionZip');
    const repoLinkGroup = document.querySelector('.repo-link-group');
    const repoFileGroup = document.querySelector('.repo-file-group');

    document.querySelectorAll('.password-toggle').forEach(toggle => {
        toggle.addEventListener('click', function() {
            const input = this.parentElement.querySelector('input');
            const icon = this.querySelector('i');
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });
    showRegister.addEventListener('click', (e) => {
        e.preventDefault();
        closeModal(loginModal);
        openModal(registerModal);
    });
    showLogin.addEventListener('click', (e) => {
        e.preventDefault();
        closeModal(registerModal);
        openModal(loginModal);
    });
    
    closeButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            closeModal(modal);
        });
    });
    
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            closeModal(e.target);
        }
    });
    
    // Валидация формы регистрации
    const regEmail = document.getElementById('regEmail');
    const regUsername = document.getElementById('regUsername');
    const regPassword = document.getElementById('regPassword');
    const regConfirmPassword = document.getElementById('regConfirmPassword');
    const emailError = document.getElementById('emailError');
    const usernameError = document.getElementById('usernameError');
    const passwordError = document.getElementById('passwordError');
    
    const strengthBar = document.querySelector('.strength-bar');
    const strengthText = document.querySelector('.strength-text');
    regPassword.addEventListener('input', function() {
        const password = this.value;
        let strength = 0;
        
        const hasUpper = /[A-Z]/.test(password);
        const hasLower = /[a-z]/.test(password);
        const hasNumber = /[0-9]/.test(password);
        const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
        const hasLength = password.length >= 8;

        if (hasUpper) strength++;
        if (hasLower) strength++;
        if (hasNumber) strength++;
        if (hasSpecial) strength++;
        if (hasLength) strength++;
        
        const width = (strength / 5) * 100;
        strengthBar.style.width = `${width}%`;
        
        if (strength <= 1) {
            strengthBar.style.backgroundColor = '#ff4757';
            strengthText.textContent = 'Сложность: слабый';
        } else if (strength <= 3) {
            strengthBar.style.backgroundColor = '#ffa502';
            strengthText.textContent = 'Сложность: средний';
        } else {
            strengthBar.style.backgroundColor = '#2ed573';
            strengthText.textContent = 'Сложность: сильный';
        }
    });
    
    // Валидация email
    regEmail.addEventListener('blur', function() {
        const email = this.value.trim();
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        
        if (!email) {
            emailError.textContent = 'Поле обязательно для заполнения';
        } else if (!emailRegex.test(email)) {
            emailError.textContent = 'Введите корректный email';
        } else {
            emailError.textContent = '';
        }
    });
    
    // Валидация никнейма
    regUsername.addEventListener('blur', function() {
        const username = this.value.trim();
        const usernameRegex = /^[a-zA-Z0-9_]{3,20}$/;
        
        if (!username) {
            usernameError.textContent = 'Поле обязательно для заполнения';
        } else if (!usernameRegex.test(username)) {
            usernameError.textContent = 'Никнейм должен содержать 3-20 символов (буквы, цифры, _)';
        } else {
            usernameError.textContent = '';
        }
    });
    
    // Валидация подтверждения пароля
    regConfirmPassword.addEventListener('blur', function() {
        if (this.value !== regPassword.value) {
            passwordError.textContent = 'Пароли не совпадают';
        } else {
            passwordError.textContent = '';
        }
    });
    
    // Отправка формы регистрации
    registerForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        regEmail.dispatchEvent(new Event('blur'));
        regUsername.dispatchEvent(new Event('blur'));
        regPassword.dispatchEvent(new Event('input'));
        regConfirmPassword.dispatchEvent(new Event('blur'));
        
        const errors = document.querySelectorAll('.error-message');
        let hasErrors = false;
        
        errors.forEach(error => {
            if (error.textContent !== '') {
                hasErrors = true;
            }
        });
        
        const requirements = document.querySelectorAll('.password-requirements li.valid');
        if (requirements.length < 5) {
            passwordError.textContent = 'Пароль не соответствует требованиям';
            hasErrors = true;
        }
        
        if (!hasErrors) {
            showMainLoader(true);
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData.entries());

            try {
                const response = await fetch('/auth/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        username: data.username,
                        email: data.email,
                        password: data.password,
                        password_confirm: data.c_password
                    })
                });
                
                const result = await response.json();
                
                if (!response.ok) {
                    showNotification(result.message || 'Ошибка регистрации пользователя', 'error');
                    return;
                }
                
                saveTokens(result.tokens);
                showNotification('Успешный вход');
                connectGitHub();
            } catch (error) {
                showNotification(error.message || 'Ошибка регистрации пользователя', 'error');
                showMainLoader(false);
            } finally {
                showMainLoader(false);
                closeModal(registerModal);
                this.reset();
            }
        }
    });
    
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        showMainLoader(true);
        const formData = new FormData(e.target);
        const loginValue = formData.get('loginUsername');
        const password = formData.get('loginPassword');

        const isEmail = loginValue.includes('@');
        
        try {
            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    [isEmail ? 'email' : 'username']: loginValue,
                    password: password
                }),
            });

            const result = await response.json();
            
            if (!response.ok) {
                showNotification(result.message || "Ошибка авторизации пользователя", 'error');
                showMainLoader(false);
                return;
            }

            saveTokens(result);
            showNotification("Успешный вход");
            updateAuthState();
            connectGitHub();
        } catch (error) {
            showNotification(error.message || "Ошибка авторизации пользователя", 'error');
            showMainLoader(false);
        } finally {
            showMainLoader(false);
            closeModal(loginModal);
            this.reset();
        }
    });

    
    optionLink.addEventListener('click', function() {
        optionLink.classList.add('active');
        optionZip.classList.remove('active');
        repoLinkGroup.style.display = 'block';
        repoFileGroup.style.display = 'none';
        repoUrl.setAttribute('required', '');
        repoFile.removeAttribute('required');
    });
    optionZip.addEventListener('click', function() {
        optionZip.classList.add('active');
        optionLink.classList.remove('active');
        repoFileGroup.style.display = 'block';
        repoLinkGroup.style.display = 'none';
        repoFile.setAttribute('required', '');
        repoUrl.removeAttribute('required');
    });
    
    // Валидация URL GitHub
    const repoUrl = document.getElementById('repoUrl');
    const urlError = document.getElementById('urlError');
    
    repoUrl.addEventListener('blur', function() {
        const url = this.value.trim();
        const githubRegex = /^(https?:\/\/)?(www\.)?github\.com\/([a-zA-Z0-9_-]+)\/([a-zA-Z0-9_.-]+)(\.git)?(\/)?$|^git@github\.com:([a-zA-Z0-9_-]+)\/([a-zA-Z0-9_.-]+)\.git$/;
        
        if (!url) {
            urlError.textContent = 'Поле обязательно для заполнения';
        } else if (!githubRegex.test(url)) {
            urlError.textContent = 'Введите корректную ссылку на GitHub репозиторий';
        } else {
            urlError.textContent = '';
        }
    });
    
    // Обработка загрузки файла
    const repoFile = document.getElementById('repoFile');
    const fileLabel = document.querySelector('.file-label');
    const fileText = document.querySelector('.file-text');
    const fileInfo = document.querySelector('.file-info');
    const fileError = document.getElementById('fileError');
    
    repoFile.addEventListener('change', function() {
        if (this.files.length > 0) {
            const file = this.files[0];
            
            // Проверка размера (100 МБ)
            if (file.size > 100 * 1024 * 1024) {
                fileError.textContent = 'Файл слишком большой (макс. 100 МБ)';
                fileLabel.style.borderColor = 'var(--neon-accent)';
                return;
            }
            
            // Проверка расширения
            const validExtensions = ['.zip', '.rar', '.7zip'];
            const fileName = file.name.toLowerCase();
            const isValid = validExtensions.some(ext => fileName.endsWith(ext));
            
            if (!isValid) {
                fileError.textContent = 'Поддерживаются только ZIP, RAR и 7ZIP архивы';
                fileLabel.style.borderColor = 'var(--neon-accent)';
                return;
            }
            
            fileError.textContent = '';
            fileLabel.style.borderColor = 'var(--secondary-color)';
            fileText.textContent = file.name;
            fileInfo.textContent = `${(file.size / (1024 * 1024)).toFixed(2)} МБ`;
        }
    });
    
    repoForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const tokens = getTokens();
        if (!tokens.access_token) {
            showNotification("Для данного действия требуется авторизация", "error");
            return;
        }

        let isValid = true;
        
        if (optionLink.classList.contains('active')) {
            repoUrl.dispatchEvent(new Event('blur'));
            if (urlError.textContent !== '') {
                isValid = false;
            }
            
            const gitStatus = await checkStatusGithub();
            if (!gitStatus?.linked) {
                showNotification("GitHub аккаунт не подключен или токен недействителен", "error");
                isValid = false;
            }
        } else {
            // Обработка ZIP архива
            if (!repoFile.files.length) {
                fileError.textContent = 'Выберите файл для загрузки';
                isValid = false;
            }
        }
        
        if (isValid) {
            showMainLoader(true);
            try {
                if (optionLink.classList.contains('active')) {
                    await processRepoURL(repoUrl.value);
                } else {
                    const formData = new FormData();
                    formData.append('repoFile', repoFile.files[0]);
                    
                    const response = await fetch('/repos/import', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${tokens.access_token}`
                        },
                        body: formData
                    });
                    
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Ошибка загрузки архива');
                    }
                    
                    const result = await response.json();
                    showNotification("Документация генерируется. Мы уведомим вас, когда она будет готова.", "success", 5000);
                    
                    const socket = await setupWebSocket(result.user_id);
                    await saveGenerationInfo(result.user_id, result.repo_id, "ZIP Archive");
                }
            } catch (error) {
                showNotification(error.message || 'Ошибка обработки архива', 'error');
            } finally {
                showMainLoader(false);
                closeModal(repoModal);
                this.reset();
                fileText.textContent = 'Выберите файл';
                fileInfo.textContent = '';
            }
        }
    });
    
    document.querySelectorAll('#repoBtn').forEach(btn => {
        btn.addEventListener('click', function() {
            openModal(repoModal);
        });
    })
});

async function processRepoURL(repoURL) {
    showMainLoader(true);
    try {
        const tokens = getTokens();
        if (!tokens.access_token) {
            showNotification("Для данного действия требуется авторизация", "error");
            return;
        }

        // Проверка статуса GitHub
        const gitStatus = await checkStatusGithub();
        if (!gitStatus?.linked) {
            showNotification("GitHub аккаунт не подключен или токен недействителен", "error");
            return;
        }

        const response = await fetch('/repos/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${tokens.access_token}`
            },
            body: JSON.stringify({ repo_url: repoURL })
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: "Unknown error" }));
            throw new Error(error.message || "Ошибка обработки репозитория");
        }

        const result = await response.json();
        showNotification("Документация генерируется. Мы уведомим вас, когда она будет готова.", "success", 5000);
        
        const socket = await setupWebSocket(result.user_id);
        await saveGenerationInfo(result.user_id, result.repo_id, repoURL);
        
        return socket;
    } catch (error) {
        console.error('Repository processing error:', error);
        showNotification(error.message || 'Ошибка обработки репозитория', 'error', 10000);
        throw error;
    } finally {
        showMainLoader(false);
    }
}

async function saveGenerationInfo(userId, repoId, repoUrl) {
    const generations = JSON.parse(localStorage.getItem('docGenerations') || '[]');
    generations.push({
        userId,
        repoId,
        repoUrl,
        timestamp: new Date().toISOString(),
        status: 'processing'
    });
    localStorage.setItem('docGenerations', JSON.stringify(generations));
}

async function setupWebSocket(userId) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = `${wsProtocol}${window.location.host}/repos/ws/docs-status/${userId}`;
    
    const socket = new WebSocket(wsUrl);
    
    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.status === 'ready') {
            showNotification(
                `Документация готова! Хотите открыть ее сейчас?`, 
                'success', 
                10000, 
                () => {
                    window.open(data.docs_url, '_blank');
                }
            );
        }
    };
    
    socket.onclose = () => {
        console.log('WebSocket disconnected');
    };
    
    return socket;
}

async function checkStatusGithub() {
    const tokens = getTokens();
    if (!tokens.access_token) {
        return { linked: false };
    }

    try {
        const response = await fetch('/github/status', {
            headers: {
                'Authorization': `Bearer ${tokens.access_token}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.status === 401) {
            clearTokens();
            showNotification("Сессия истекла. Пожалуйста, войдите снова.", "error");
            return { linked: false };
        }

        if (!response.ok) {
            throw new Error("Ошибка получения статуса GitHub");
        }

        return await response.json();
    } catch (error) {
        console.error("GitHub status check error:", error);
        return { linked: false };
    }
}

function showMainLoader(show = true) {
    const loader = document.getElementById('main-loader');
    loader.style.display = show ? 'flex' : 'none';
}

async function connectGitHub() {
    try {
        const token = localStorage.getItem('access_token');
        if (!token) {
            showNotification("Вы должны быть авторизованы", "warning");
            openModal(loginModal);
            return;
        }

        const response = await fetch('/github/auth');
        const data = await response.json();

        const width = 600, height = 600;
        const left = (screen.width - width) / 2;
        const top = (screen.height - height) / 2;
        
        const authWindow = window.open(data.auth_url, 'github_auth', 
            `width=${width},height=${height},top=${top},left=${left}`);
        
        const checkInterval = setInterval(async () => {
            try {
                if (authWindow.closed) {
                    clearInterval(checkInterval);

                    const status = await checkStatusGithub();
                    if (status.linked) {
                        showNotification("GitHub успешно подключен", "success");
                        updateAuthState();
                    }
                }
            } catch (e) {
                clearInterval(checkInterval);
                console.error("Error checking auth window:", e);
            }
        }, 500);
        
    } catch (error) {
        showNotification('Failed to initiate GitHub auth', 'error');
        console.error('Error initiating GitHub auth:', error);
    }
}

async function refreshTokens(refreshToken) {
    try {
        const response = await fetch('/auth/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ refresh_token: refreshToken })
        });

        if (!response.ok) {
            throw new Error("Ошибка обновления токена");
        }

        return await response.json();
    } catch (error) {
        console.error("Token refresh error:", error);
        return null;
    }
}

async function openProfile() {
    const tokens = getTokens();
    
    // Проверка наличия токена
    if (!tokens?.access_token) {
        showNotification("Для просмотра профиля требуется авторизация", "error");
        openModal(loginModal);
        return;
    }

    try {
        let response = await fetch('/auth/me', {
            headers: {
                'Authorization': `Bearer ${tokens.access_token}`
            }
        });

        if (response.status === 401 && tokens.refresh_token) {
            try {
                const newTokens = await refreshTokens(tokens.refresh_token);
                if (!newTokens) {
                    throw new Error("Не удалось обновить токен");
                }
                
                saveTokens(newTokens);
                
                response = await fetch('/auth/me', {
                    headers: {
                        'Authorization': `Bearer ${newTokens.access_token}`
                    }
                });
                
                if (!response.ok) {
                    throw new Error("Ошибка после обновления токена");
                }
            } catch (refreshError) {
                console.error("Token refresh failed:", refreshError);
                clearTokens();
                showNotification("Сессия истекла. Пожалуйста, войдите снова.", "error");
                openModal(loginModal);
                return;
            }
        }
        
        if (!response.ok) {
            throw new Error("Ошибка получения данных пользователя");
        }
        
        const userData = await response.json();
        window.location.href = `/profile?user_id=${userData.id}`;
        
    } catch (error) {
        console.error("Profile error:", error);
        showNotification(error.message || "Ошибка перехода в профиль", "error");
        
        if (error.message.includes("401") || error.message.includes("токен")) {
            openModal(loginModal);
        }
    }
}

document.querySelector('.btn-outline.btn-small:first-of-type').addEventListener('click', function(e) {
    e.preventDefault();
    openModal(document.getElementById('bugReportModal'));
});

document.getElementById('bugReportForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData();
    formData.append('title', document.getElementById('bugTitle').value);
    formData.append('description', document.getElementById('bugDescription').value);
    
    const screenshot = document.getElementById('bugScreenshot').files[0];
    if (screenshot) {
        formData.append('screenshot', screenshot);
    }
    
    try {
        showMainLoader(true);
        const response = await fetch('/api/bug-report', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to submit bug report');
        }
        
        showNotification('Спасибо за ваше сообщение! Мы рассмотрим его в ближайшее время.', 'success');
        closeModal(document.getElementById('bugReportModal'));
        this.reset();
    } catch (error) {
        showNotification('Ошибка при отправке сообщения. Пожалуйста, попробуйте позже.', 'error');
    } finally {
        showMainLoader(false);
    }
});