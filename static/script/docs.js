document.addEventListener('DOMContentLoaded', function() {
    const projectTree = document.getElementById('projectTree');
    const markdownContent = document.getElementById('markdownContent');
    const fileName = document.getElementById('fileName');

    const firstFile = document.querySelector('.tree-item');
    if (firstFile) {
        loadFileContent(firstFile.dataset.file);
        firstFile.classList.add('active');
    }

    projectTree.addEventListener('click', async function(e) {
        if (e.target.classList.contains('tree-item')) {
            e.preventDefault();
            
            document.querySelectorAll('.tree-item').forEach(item => {
                item.classList.remove('active');
            });
            
            e.target.classList.add('active');
            loadFileContent(e.target.dataset.file);
        }
    });

    async function loadFileContent(filePath) {
        fileName.textContent = filePath.split('/').pop().slice(0, -3);
        
        try {
            const response = await fetch(`/docs/content/${userId}/${repoId}/${filePath}`);
            const data = await response.json();
            markdownContent.innerHTML = marked.parse(data.content);
            
            document.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
        } catch (error) {
            markdownContent.innerHTML = `<p>Error loading file: ${error.message}</p>`;
        }
    }
});

function initSearch() {
    const searchBox = document.createElement('div');
    searchBox.className = 'search-box';
    searchBox.innerHTML = `
        <input type="text" placeholder="Поиск по документации...">
        <button>Найти</button>
    `;
    document.querySelector('.file-header').appendChild(searchBox);

    searchBox.querySelector('button').addEventListener('click', performSearch);
    searchBox.querySelector('input').addEventListener('keyup', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    function performSearch() {
        const term = searchBox.querySelector('input').value.toLowerCase();
        if (!term) return;

        const content = document.getElementById('markdownContent').textContent.toLowerCase();
        if (content.includes(term)) {
            highlightTerm(term);
        } else {
            alert('Ничего не найдено');
        }
    }

    function highlightTerm(term) {
        const markdownContent = document.getElementById('markdownContent');
        const html = markdownContent.innerHTML;
        const regex = new RegExp(term, 'gi');
        const highlighted = html.replace(regex, match => 
            `<span class="highlight">${match}</span>`
        );
        markdownContent.innerHTML = highlighted;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    initThemeSwitcher();
    initSearch();
    
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });
});