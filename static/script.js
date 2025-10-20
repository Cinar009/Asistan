document.addEventListener('DOMContentLoaded', () => {
    const sendButton = document.getElementById('send-button');
    const promptInput = document.getElementById('prompt-input');
    const responseArea = document.getElementById('response-area');
    const loadingIndicator = document.getElementById('loading');
    const themeToggle = document.getElementById('theme-toggle');

    // --- Gece Modu (Dark Mode) Yönetimi ---
    const applyTheme = (theme) => {
        const root = document.documentElement;
        if (theme === 'dark') {
            root.classList.add('dark');
            themeToggle.querySelector('.material-symbols-rounded').innerText = 'light_mode';
        } else {
            root.classList.remove('dark');
            themeToggle.querySelector('.material-symbols-rounded').innerText = 'dark_mode';
        }
    };
    const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    applyTheme(savedTheme);
    themeToggle.addEventListener('click', () => {
        const newTheme = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
    });
    
    // --- Mesajlaşma Fonksiyonları ---
    const sendMessage = async () => {
        const prompt = promptInput.value.trim();
        if (!prompt) return;
        appendMessage(prompt, 'user');
        promptInput.value = '';
        adjustTextareaHeight();
        loadingIndicator.classList.remove('hidden');
        scrollToBottom();

        try {
            const response = await fetch('/api/assist', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });
            if (!response.ok) throw new Error(`Server error: ${response.status}`);
            const data = await response.json();
            appendMessage(data.response, 'assistant');
        } catch (error) {
            appendMessage('Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.', 'assistant');
            console.error('Hata:', error);
        } finally {
            loadingIndicator.classList.add('hidden');
        }
    };

    const appendMessage = (text, type) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type} message-animate`;
        messageDiv.innerText = text;
        responseArea.appendChild(messageDiv);
        scrollToBottom();
    };
    
    const scrollToBottom = () => {
        responseArea.scrollTop = responseArea.scrollHeight;
    };
    
    const adjustTextareaHeight = () => {
        promptInput.style.height = 'auto';
        const maxHeight = 192; // max-h-48 (Tailwind) = 12rem = 192px
        promptInput.style.height = `${Math.min(promptInput.scrollHeight, maxHeight)}px`;
    };
    
    sendButton.addEventListener('click', sendMessage);
    promptInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    promptInput.addEventListener('input', adjustTextareaHeight);
    scrollToBottom();
});