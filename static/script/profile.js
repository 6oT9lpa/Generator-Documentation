async function deleteRepo(repoId) {
    if (!confirm('Вы уверены, что хотите удалить этот репозиторий? Документация также будет удалена.')) {
        return;
    }

    const tokens = getTokens();
    if (!tokens.access_token) {
        showNotification("Для удаления требуется авторизация", "error");
        return;
    }

    try {
        const response = await fetch(`/profile/delete_repos/${repoId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${tokens.access_token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || "Ошибка при удалении");
        }

        // Плавное удаление элемента из DOM
        const repoElement = document.querySelector(`.repo-item button[onclick="deleteRepo('${repoId}')"]`)?.closest('.repo-item');
        if (repoElement) {
            repoElement.style.transition = 'all 0.3s ease';
            repoElement.style.opacity = '0';
            repoElement.style.height = '0';
            repoElement.style.margin = '0';
            repoElement.style.padding = '0';
            repoElement.style.overflow = 'hidden';
            
            setTimeout(() => {
                repoElement.remove();
                updateStats();
            }, 300);
        }

        showNotification("Репозиторий успешно удален", "success");
    } catch (error) {
        console.error("Delete error:", error);
        showNotification(error.message || "Ошибка при удалении репозитория", "error");
    }
}

function updateStats() {
    const repoCount = document.querySelectorAll('.repo-item').length;
    const statCards = document.querySelectorAll('.stat-card p');
    if (statCards.length > 0) {
        statCards[0].textContent = repoCount;
    }
}