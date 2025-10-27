// ----------------------------------------------------
// Asistan Projesi V4.1 - FINAL TEMİZ script.js Kodu
// (Sohbet Silme Özelliği Eklendi - TAM KOD)
// ----------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    console.log("--- DOM Yüklendi, V4.1 Final Script Başlatılıyor ---");

    // HTML Elementlerini Seçme (Null kontrolü ile)
    const sidebar = document.getElementById('sidebar');
    const newChatButton = document.getElementById('new-chat-button');
    const chatList = document.getElementById('chat-list');
    const responseArea = document.getElementById('response-area');
    const promptInput = document.getElementById('prompt-input');
    const sendButton = document.getElementById('send-button');
    const loadingIndicator = document.getElementById('loading');
    const themeToggle = document.getElementById('theme-toggle');

    // Element Kontrolleri (Başlangıçta bir kez)
    if (!newChatButton) console.error("Yeni Sohbet butonu bulunamadı!");
    if (!chatList) console.error("Sohbet listesi alanı bulunamadı!");
    if (!responseArea) console.error("Mesaj alanı bulunamadı!");
    if (!promptInput) console.error("Giriş kutusu bulunamadı!");
    if (!sendButton) console.error("Gönder butonu bulunamadı!");
    if (!themeToggle) console.error("Tema değiştirme butonu bulunamadı!");

    // Global Değişkenler
    let chats = {};
    let activeChatId = null;

    // --- Yardımcı Fonksiyonlar ---
    const generateChatId = () => `chat_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    const scrollToBottom = () => { if (responseArea) responseArea.scrollTop = responseArea.scrollHeight; };
    const adjustTextareaHeight = () => {
        if (!promptInput) return;
        promptInput.style.height = 'auto'; const maxHeight = 192;
        promptInput.style.height = `${Math.min(promptInput.scrollHeight, maxHeight)}px`;
    };
    const sanitizeHTML = (str) => { const temp = document.createElement('div'); temp.textContent = str; return temp.innerHTML; };
    const getChatTitle = (history) => {
        const firstUserMessage = history?.find(m => m.role === 'user');
        if (firstUserMessage?.parts?.[0]?.text) { const title = sanitizeHTML(firstUserMessage.parts[0].text.substring(0, 25)); return title ? `${title}...` : "Yeni Sohbet"; }
        return "Yeni Sohbet";
    };

    // --- localStorage Yönetimi ---
    const saveChatsToLocalStorage = () => { try { localStorage.setItem('asistanChats', JSON.stringify(chats)); localStorage.setItem('activeChatId', activeChatId); } catch (e) { console.error("localStorage kaydetme hatası:", e); } };
    const loadChatsFromLocalStorage = () => { try { const savedChats = localStorage.getItem('asistanChats'); chats = savedChats ? JSON.parse(savedChats) : {}; Object.values(chats).forEach(chat => { chat.history = Array.isArray(chat.history) ? chat.history : []; chat.title = chat.title || "İsimsiz Sohbet"; }); activeChatId = localStorage.getItem('activeChatId'); console.log("Sohbetler ve Aktif ID yüklendi."); } catch (e) { console.error("localStorage yükleme hatası:", e); chats = {}; activeChatId = null; } };

    // --- Arayüz Güncelleme Fonksiyonları ---
    const renderChatList = () => {
        if (!chatList) return; chatList.innerHTML = '';
        const sortedChatIds = Object.keys(chats).sort((a, b) => parseInt(b.split('_')[1] || 0) - parseInt(a.split('_')[1] || 0));
        sortedChatIds.forEach(chatId => {
            const chat = chats[chatId]; const listItem = document.createElement('li');
            listItem.className = `chat-item group flex items-center justify-between text-sm p-2 rounded hover:bg-[var(--sidebar-hover-bg)] cursor-pointer transition-colors duration-150 ${chatId === activeChatId ? 'active' : ''}`;
            listItem.dataset.chatId = chatId; const titleSpan = document.createElement('span');
            titleSpan.className = 'truncate flex-grow mr-2'; titleSpan.textContent = chat.title;
            titleSpan.addEventListener('click', () => setActiveChat(chatId)); listItem.appendChild(titleSpan);
            const deleteButton = document.createElement('button');
            deleteButton.innerHTML = `<span class="material-symbols-rounded text-xs opacity-60 group-hover:opacity-100 text-red-500 hover:text-red-700">delete</span>`;
            deleteButton.className = 'delete-chat-button p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 leading-none';
            deleteButton.title = 'Sohbeti sil'; deleteButton.dataset.chatId = chatId;
            deleteButton.addEventListener('click', (e) => { e.stopPropagation(); deleteChat(chatId); });
            listItem.appendChild(deleteButton);
            listItem.addEventListener('click', (e) => { if (e.target === listItem || titleSpan.contains(e.target)) setActiveChat(chatId); });
            chatList.appendChild(listItem);
        });
    };
    const renderChatMessages = (chatId) => {
        if (!responseArea) return; responseArea.innerHTML = '';
        const chat = chats[chatId];
        if (chat?.history?.length > 0) { chat.history.forEach((message) => { appendMessage(message.parts[0].text, message.role === 'user' ? 'user' : 'assistant', null, false); }); }
        else { appendMessage("Merhaba! Ben Asistan...", 'assistant', null, false); }
        setTimeout(scrollToBottom, 50);
    };

    // --- Sohbet Yönetimi ---
    const createNewChat = () => {
        const newChatId = generateChatId(); chats[newChatId] = { title: "Yeni Sohbet", history: [] };
        console.log(`Yeni sohbet oluşturuldu: ${newChatId}`); setActiveChat(newChatId); saveChatsToLocalStorage(); renderChatList(); if (promptInput) promptInput.focus();
    };
    const setActiveChat = (chatId) => {
        if (!chats[chatId]) {
             console.warn(`Aktif sohbet bulunamadı: ${chatId}. En yenisi seçiliyor.`);
             const chatIds = Object.keys(chats).sort((a, b) => parseInt(b.split('_')[1] || 0) - parseInt(a.split('_')[1] || 0));
             if (chatIds.length > 0) activeChatId = chatIds[0]; else { createNewChat(); return; }
        } else { activeChatId = chatId; }
        localStorage.setItem('activeChatId', activeChatId); console.log(`Aktif sohbet değiştirildi: ${activeChatId}`);
        renderChatMessages(activeChatId); renderChatList(); if (promptInput) promptInput.focus();
    };
    const deleteChat = (chatIdToDelete) => {
        const chatTitle = chats[chatIdToDelete]?.title || 'Bu';
        if (!confirm(`"${chatTitle}" sohbetini silmek istediğinize emin misiniz?`)) { return; }
        console.log(`Sohbet siliniyor: ${chatIdToDelete}`); delete chats[chatIdToDelete];
        if (activeChatId === chatIdToDelete) {
            activeChatId = null; const remainingChatIds = Object.keys(chats).sort((a, b) => parseInt(b.split('_')[1] || 0) - parseInt(a.split('_')[1] || 0));
            if (remainingChatIds.length > 0) { activeChatId = remainingChatIds[0]; }
            else { createNewChat(); saveChatsToLocalStorage(); renderChatList(); return; }
        }
        saveChatsToLocalStorage(); renderChatList();
        if (activeChatId) { setActiveChat(activeChatId); }
        else if (Object.keys(chats).length === 0) { if (responseArea) responseArea.innerHTML = ''; appendMessage("Yeni sohbet başlatın.", 'assistant', null, false); }
    };

    // --- Mesaj Gönderme ve Alma ---
    const sendMessage = async () => {
         if (!activeChatId || !chats[activeChatId]) { createNewChat(); return; }
         const prompt = promptInput?.value?.trim(); if (!prompt || sendButton?.disabled) return;
        const currentChat = chats[activeChatId]; const userMessage = { role: 'user', parts: [{ text: prompt }] }; currentChat.history.push(userMessage);
        if (currentChat.history.length === 1 && currentChat.title === "Yeni Sohbet") { currentChat.title = getChatTitle(currentChat.history); renderChatList(); }
        appendMessage(prompt, 'user'); const currentQuestion = prompt; if (promptInput) promptInput.value = ''; adjustTextareaHeight();
        if (loadingIndicator) loadingIndicator.classList.remove('hidden'); if (sendButton) sendButton.disabled = true; scrollToBottom();
        try {
            const response = await fetch('/api/assist', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ history: currentChat.history }) });
            if (!response.ok) throw new Error(`Server error: ${response.status}`); const data = await response.json();
            const assistantMessage = { role: 'model', parts: [{ text: data.response }] }; currentChat.history.push(assistantMessage);
            appendMessage(data.response, 'assistant', data.is_known ? null : currentQuestion); saveChatsToLocalStorage();
        } catch (error) { console.error('sendMessage HATA:', error); currentChat.history.pop(); appendMessage('Üzgünüm, bir hata oluştu...', 'assistant', null);
        } finally { if (loadingIndicator) loadingIndicator.classList.add('hidden'); if (sendButton) sendButton.disabled = false; scrollToBottom(); }
    };

    // Mesajı sohbet alanına ekleyen fonksiyon
    const appendMessage = (text, type, originalQuestion = null, animate = true) => {
         if (!responseArea) return; const messageDiv = document.createElement('div'); const messageContent = document.createElement('div');
         messageContent.innerText = text; messageContent.className = 'flex-grow min-w-0'; messageDiv.className = `message ${type} flex items-start gap-2`; if (animate) messageDiv.classList.add('message-animate'); messageDiv.appendChild(messageContent);
        if (type === 'assistant' && originalQuestion) {
            const buttonsContainer = document.createElement('div'); buttonsContainer.className = 'flex flex-col ml-1 sm:ml-2 flex-shrink-0 space-y-1';
            const likeButton = document.createElement('button'); likeButton.innerHTML = `<span class="material-symbols-rounded text-sm sm:text-base opacity-50 hover:opacity-100 transition-opacity">thumb_up</span>`; likeButton.className = 'like-button p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 flex-shrink-0 leading-none'; likeButton.title = 'Hafızaya kaydet';
            const reportButton = document.createElement('button'); reportButton.innerHTML = `<span class="material-symbols-rounded text-sm sm:text-base opacity-50 hover:opacity-100 transition-opacity text-red-500 hover:text-red-700">report</span>`; reportButton.className = 'report-button p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 flex-shrink-0 leading-none'; reportButton.title = 'Hatalı bildir/Sil';
            likeButton.addEventListener('click', async () => {
                likeButton.disabled = true; reportButton.disabled = true; likeButton.innerHTML = `<span class="material-symbols-rounded text-sm sm:text-base text-green-500">done</span>`;
                try {
                    const learnResponse = await fetch('/api/learn', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: originalQuestion, answer: text }) }); if (!learnResponse.ok) throw new Error('Öğrenme isteği başarısız.'); const learnData = await learnResponse.json(); likeButton.title = (learnData.status === 'already_known') ? 'Zaten biliniyor!' : 'Kaydedildi!'; console.log('Öğrenme sonucu:', learnData.status);
                } catch (error) { console.error('Öğrenme HATA:', error); likeButton.innerHTML = `<span class="material-symbols-rounded text-sm sm:text-base error-icon text-red-500">error_outline</span>`; likeButton.title = 'Kaydedilemedi!'; setTimeout(() => { if(likeButton && !likeButton.disabled) { likeButton.disabled = false; if(reportButton) reportButton.disabled = false; likeButton.innerHTML = `<span class="material-symbols-rounded text-sm sm:text-base opacity-50 hover:opacity-100 transition-opacity">thumb_up</span>`; likeButton.title = 'Hafızaya kaydet'; }}, 3000); }
            });
            reportButton.addEventListener('click', async () => {
                reportButton.disabled = true; likeButton.disabled = true; reportButton.innerHTML = `<span class="material-symbols-rounded text-sm sm:text-base text-orange-500">delete</span>`;
                try {
                    const forgetResponse = await fetch('/api/forget', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: originalQuestion, answer: text }) }); if (!forgetResponse.ok) throw new Error('Unutma isteği başarısız.'); console.log('Cevap pasif yapıldı!'); reportButton.title = 'Pasif yapıldı!'; messageContent.style.opacity = '0.5';
                } catch (error) { console.error('Unutma HATA:', error); reportButton.innerHTML = `<span class="material-symbols-rounded text-sm sm:text-base error-icon text-red-500">error_outline</span>`; reportButton.title = 'Silinemedi!'; setTimeout(() => { if(reportButton && !reportButton.disabled) { reportButton.disabled = false; if(likeButton) likeButton.disabled = false; reportButton.innerHTML = `<span class="material-symbols-rounded text-sm sm:text-base opacity-50 hover:opacity-100 transition-opacity text-red-500 hover:text-red-700">report</span>`; reportButton.title = 'Hatalı bildir/Sil'; }}, 3000); }
            });
            buttonsContainer.appendChild(likeButton); buttonsContainer.appendChild(reportButton); messageDiv.appendChild(buttonsContainer);
        }
        responseArea.appendChild(messageDiv);
    };

    // --- Gece Modu (Tema) Yönetimi ---
    const applyTheme = (theme) => {
        const root = document.documentElement; if (theme === 'dark') { root.classList.add('dark'); if (themeToggle) themeToggle.querySelector('.material-symbols-rounded').innerText = 'light_mode'; } else { root.classList.remove('dark'); if (themeToggle) themeToggle.querySelector('.material-symbols-rounded').innerText = 'dark_mode'; }
    };
    const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); applyTheme(savedTheme);
    if (themeToggle) { themeToggle.addEventListener('click', () => { const newTheme = document.documentElement.classList.contains('dark') ? 'light' : 'dark'; applyTheme(newTheme); localStorage.setItem('theme', newTheme); }); }

    // --- Başlangıç Ayarları ---
    const initializeApp = () => {
        console.log("Uygulama başlatılıyor..."); loadChatsFromLocalStorage();
        if (!activeChatId || !chats[activeChatId]) {
            const chatIds = Object.keys(chats);
            if (chatIds.length > 0) { const latestChatId = chatIds.sort((a, b) => parseInt(b.split('_')[1] || 0) - parseInt(a.split('_')[1] || 0))[0]; activeChatId = latestChatId; }
            else { const newChatId = generateChatId(); chats[newChatId] = { title: "Yeni Sohbet", history: [] }; activeChatId = newChatId; saveChatsToLocalStorage(); }
        }
        renderChatList();
        if (activeChatId && chats[activeChatId]) { setActiveChat(activeChatId); }
        else if (Object.keys(chats).length === 0){ if(responseArea) responseArea.innerHTML = ''; appendMessage("Yeni sohbet başlatın.", 'assistant', null, false); }
        console.log("Uygulama başlatma tamamlandı.");
    };

    // --- Olay Dinleyicileri ---
    if (newChatButton) { newChatButton.addEventListener('click', createNewChat); }
    if (sendButton) { sendButton.addEventListener('click', sendMessage); }
    if (promptInput) { promptInput.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (sendButton && !sendButton.disabled) sendMessage(); } }); promptInput.addEventListener('input', adjustTextareaHeight); }
    window.addEventListener('resize', scrollToBottom);

    // --- Uygulamayı Başlat ---
    initializeApp();

}); // DOMContentLoaded sonu