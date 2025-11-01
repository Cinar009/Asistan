// ----------------------------------------------------
// Asistan Projesi V5.2 - FINAL TEMİZ script.js Kodu
// (Tüm Fonksiyonlar DAHİL!)
// ----------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    console.log("--- DOM Yüklendi, V5.2 Final Script Başlatılıyor ---");

    // HTML Elementlerini Seçme
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const menuToggleButton = document.getElementById('menu-toggle-button');
    const newChatButton = document.getElementById('new-chat-button');
    const chatList = document.getElementById('chat-list');
    const responseArea = document.getElementById('response-area');
    const promptInput = document.getElementById('prompt-input');
    const sendButton = document.getElementById('send-button');
    const loadingIndicator = document.getElementById('loading');
    const themeToggle = document.getElementById('theme-toggle');

    // Element Kontrolleri
    const checkElement = (el, name) => { if (!el) console.error(`${name} elementi HTML'de bulunamadı! ID'yi kontrol et.`); return el; };
    checkElement(sidebar, "Sidebar"); checkElement(sidebarOverlay, "Sidebar overlay"); checkElement(menuToggleButton, "Menü toggle butonu");
    checkElement(newChatButton, "Yeni Sohbet butonu"); checkElement(chatList, "Sohbet listesi alanı"); checkElement(responseArea, "Mesaj alanı");
    checkElement(promptInput, "Giriş kutusu"); checkElement(sendButton, "Gönder butonu"); checkElement(themeToggle, "Tema değiştirme butonu");

    // Global Değişkenler
    let chats = {}; let activeChatId = null;

    // --- Yardımcı Fonksiyonlar ---
    const generateChatId = () => `chat_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    const scrollToBottom = () => { if (responseArea) setTimeout(() => responseArea.scrollTop = responseArea.scrollHeight, 50); };
    const adjustTextareaHeight = () => { if (!promptInput) return; promptInput.style.height = 'auto'; const maxHeight = 160; promptInput.style.height = `${Math.min(promptInput.scrollHeight, maxHeight)}px`; };
    const sanitizeHTML = (str) => { const temp = document.createElement('div'); temp.textContent = str; return temp.innerHTML; };
    const getChatTitle = (history) => { const firstUserMessage = history?.find(m => m.role === 'user'); if (firstUserMessage?.parts?.[0]?.text) { const title = sanitizeHTML(firstUserMessage.parts[0].text.substring(0, 25)); return title ? `${title}...` : "Yeni Sohbet"; } return "Yeni Sohbet"; };

    // --- localStorage Yönetimi ---
    const saveChatsToLocalStorage = () => { try { localStorage.setItem('asistanChats', JSON.stringify(chats)); localStorage.setItem('activeChatId', activeChatId); } catch (e) { console.error("localStorage kaydetme hatası:", e); } };
    const loadChatsFromLocalStorage = () => { try { const savedChats = localStorage.getItem('asistanChats'); chats = savedChats ? JSON.parse(savedChats) : {}; Object.values(chats).forEach(chat => { chat.history = Array.isArray(chat.history) ? chat.history : []; chat.title = chat.title || "İsimsiz Sohbet"; }); activeChatId = localStorage.getItem('activeChatId'); console.log("Sohbetler ve Aktif ID yüklendi."); } catch (e) { console.error("localStorage yükleme hatası:", e); chats = {}; activeChatId = null; } };
    const saveThemeToLocalStorage = (theme) => { try { localStorage.setItem('theme', theme); } catch (e) { console.error("localStorage tema kaydetme hatası:", e); } };
    const loadThemeFromLocalStorage = () => { try { return localStorage.getItem('theme'); } catch (e) { console.error("localStorage tema yükleme hatası:", e); return null; } };

    // --- Arayüz Güncelleme Fonksiyonları ---
    const renderChatList = () => {
        if (!chatList) return; chatList.innerHTML = ''; const sortedChatIds = Object.keys(chats).sort((a, b) => parseInt(b.split('_')[1] || 0) - parseInt(a.split('_')[1] || 0));
        sortedChatIds.forEach(chatId => {
            const chat = chats[chatId]; const listItem = document.createElement('li'); listItem.className = `chat-item group flex items-center justify-between text-sm p-2 rounded hover:bg-[var(--sidebar-hover-bg)] cursor-pointer transition-colors duration-150 ${chatId === activeChatId ? 'active' : ''}`; listItem.dataset.chatId = chatId; const titleSpan = document.createElement('span'); titleSpan.className = 'truncate flex-grow mr-2'; titleSpan.textContent = chat.title;
            titleSpan.addEventListener('click', () => { setActiveChat(chatId); if (window.innerWidth < 1024) closeSidebar(); }); listItem.appendChild(titleSpan); const deleteButton = document.createElement('button'); deleteButton.innerHTML = `<span class="material-symbols-rounded text-xs opacity-60 group-hover:opacity-100 text-red-500 hover:text-red-700">delete</span>`; deleteButton.className = 'delete-chat-button p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 leading-none'; deleteButton.title = 'Sohbeti sil'; deleteButton.dataset.chatId = chatId; deleteButton.addEventListener('click', (e) => { e.stopPropagation(); deleteChat(chatId); }); listItem.appendChild(deleteButton);
            listItem.addEventListener('click', (e) => { if (e.target === listItem || titleSpan.contains(e.target)) { setActiveChat(chatId); if (window.innerWidth < 1024) closeSidebar(); }}); chatList.appendChild(listItem);
        });
    };
    const renderChatMessages = (chatId) => {
        if (!responseArea) return; responseArea.innerHTML = ''; const chat = chats[chatId];
        if (chat?.history?.length > 0) { chat.history.forEach((message) => { appendMessage(message.parts[0].text, message.role === 'user' ? 'user' : 'assistant', null, false); }); }
        else { appendMessage("Merhaba! Ben Asistan...", 'assistant', null, false); }
        scrollToBottom();
    };

    // --- Sohbet Yönetimi ---
    const createNewChat = () => { const newChatId = generateChatId(); chats[newChatId] = { title: "Yeni Sohbet", history: [] }; console.log(`Yeni sohbet oluşturuldu: ${newChatId}`); setActiveChat(newChatId); saveChatsToLocalStorage(); renderChatList(); if (promptInput) promptInput.focus(); };
    const setActiveChat = (chatId) => {
        if (!chats[chatId]) { console.warn(`Aktif sohbet bulunamadı: ${chatId}.`); const chatIds = Object.keys(chats).sort((a, b) => parseInt(b.split('_')[1] || 0) - parseInt(a.split('_')[1] || 0)); if (chatIds.length > 0) activeChatId = chatIds[0]; else { createNewChat(); return; } } else { activeChatId = chatId; }
        localStorage.setItem('activeChatId', activeChatId); console.log(`Aktif sohbet değiştirildi: ${activeChatId}`); renderChatMessages(activeChatId); renderChatList(); if (promptInput) promptInput.focus();
    };
    const deleteChat = (chatIdToDelete) => {
        const chatTitle = chats[chatIdToDelete]?.title || 'Bu'; if (!confirm(`"${chatTitle}" sohbetini silmek istediğinize emin misiniz?`)) { return; }
        console.log(`Sohbet siliniyor: ${chatIdToDelete}`); delete chats[chatIdToDelete];
        if (activeChatId === chatIdToDelete) {
            activeChatId = null; const remainingChatIds = Object.keys(chats).sort((a, b) => parseInt(b.split('_')[1] || 0) - parseInt(a.split('_')[1] || 0));
            if (remainingChatIds.length > 0) { activeChatId = remainingChatIds[0]; } else { createNewChat(); /* save/render createNewChat içinde */ return; }
        }
        saveChatsToLocalStorage(); renderChatList();
        if (activeChatId) { setActiveChat(activeChatId); } else if (Object.keys(chats).length === 0) { if (responseArea) responseArea.innerHTML = ''; appendMessage("Yeni sohbet başlatın.", 'assistant', null, false); }
    };

    // --- Mesaj Gönderme ve Alma (STREAMING) ---
    const sendMessage = async () => {
         if (!activeChatId || !chats[activeChatId]) { console.log("Aktif sohbet yok, yeni oluşturuluyor."); createNewChat(); return; }
         const prompt = promptInput?.value?.trim(); if (!prompt || (sendButton && sendButton.disabled)) return;
        const currentChat = chats[activeChatId]; const userMessage = { role: 'user', parts: [{ text: prompt }] }; currentChat.history.push(userMessage); if (currentChat.history.length === 1 && currentChat.title === "Yeni Sohbet") { currentChat.title = getChatTitle(currentChat.history); renderChatList(); }
        appendMessage(prompt, 'user'); const currentQuestion = prompt; if (promptInput) promptInput.value = ''; adjustTextareaHeight(); if (loadingIndicator) loadingIndicator.classList.remove('hidden'); if (sendButton) sendButton.disabled = true; scrollToBottom();
        const assistantMessageDiv = appendMessage("", 'assistant', null, true); const messageContent = assistantMessageDiv.querySelector('.flex-grow'); if (!messageContent) { console.error("Mesaj içerik alanı bulunamadı!"); return; }
        let fullResponse = ""; let isKnown = false; let errorOccurred = false;
        try {
            const response = await fetch('/api/assist', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ history: currentChat.history }) });
            if (!response.ok) { console.error("Sunucu Hatası:", response.status, response.statusText); throw new Error(`Server error: ${response.status}`); }
            const reader = response.body.getReader(); const decoder = new TextDecoder("utf-8");
            while (true) {
                const { done, value } = await reader.read(); if (done) { console.log("Stream bitti."); break; }
                const chunkText = decoder.decode(value, {stream: true});
                const lines = chunkText.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataPart = line.substring(6); if (dataPart === "[DONE]") { console.log("Stream [DONE] sinyalini aldı."); break; }
                        try {
                            const data = JSON.parse(dataPart);
                            if (data.error) { console.error("Stream HATA:", data.error); fullResponse = data.error; isKnown = data.is_known; errorOccurred = true; break; }
                            if (data.response_chunk) { fullResponse += data.response_chunk; messageContent.innerText = fullResponse; scrollToBottom(); isKnown = data.is_known; }
                        } catch (e) { if (dataPart !== "[DONE]") { console.warn("Geçersiz JSON parçası, atlanıyor:", dataPart, e); } }
                    }
                } if(errorOccurred) break;
            } // while bitti
        } catch (error) { console.error('sendMessage (stream) HATA:', error); messageContent.innerText = 'Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.'; currentChat.history.pop(); errorOccurred = true;
        } finally {
            if (loadingIndicator) loadingIndicator.classList.add('hidden'); if (sendButton) sendButton.disabled = false; scrollToBottom();
            if (!errorOccurred && fullResponse) { const assistantMessage = { role: 'model', parts: [{ text: fullResponse }] }; currentChat.history.push(assistantMessage); saveChatsToLocalStorage(); if (!isKnown) { addResponseButtons(assistantMessageDiv, currentQuestion, fullResponse); } }
            else if (errorOccurred && fullResponse) { const errorMessage = { role: 'model', parts: [{ text: fullResponse }] }; currentChat.history.push(errorMessage); saveChatsToLocalStorage(); }
        }
    };

    // Mesajı sohbet alanına ekleyen fonksiyon
    const appendMessage = (text, type, originalQuestion = null, animate = true) => {
         if (!responseArea) return null; const messageDiv = document.createElement('div'); const messageContent = document.createElement('div'); messageContent.innerText = text; messageContent.className = 'flex-grow min-w-0'; messageDiv.className = `message ${type} flex items-start gap-2`; if (animate) messageDiv.classList.add('message-animate'); messageDiv.appendChild(messageContent);
         responseArea.appendChild(messageDiv);
         if(animate) scrollToBottom();
         return messageDiv;
    };

    // Butonları Mesaja Sonradan Ekleme Fonksiyonu
    const addResponseButtons = (messageDiv, originalQuestion, text) => {
        if (!messageDiv || !originalQuestion || !text) return;
        const buttonsContainer = document.createElement('div'); buttonsContainer.className = 'flex items-center ml-1 sm:ml-2 flex-shrink-0 space-x-1 mt-1 opacity-70 hover:opacity-100 transition-opacity';
        const copyButton = document.createElement('button'); copyButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm">content_copy</span>`; copyButton.className = 'copy-button action-button p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700'; copyButton.title = 'Kopyala';
        const regenerateButton = document.createElement('button'); regenerateButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm">refresh</span>`; regenerateButton.className = 'regenerate-button action-button p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700'; regenerateButton.title = 'Yeniden Üret';
        const likeButton = document.createElement('button'); likeButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm">thumb_up</span>`; likeButton.className = 'like-button action-button p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700'; likeButton.title = 'Hafızaya kaydet';
        const reportButton = document.createElement('button'); reportButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm text-red-500 hover:text-red-700">report</span>`; reportButton.className = 'report-button action-button p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700'; reportButton.title = 'Hatalı bildir/Sil';
        // Kopyala Listener
        copyButton.addEventListener('click', () => { navigator.clipboard.writeText(text).then(() => { copyButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm done-icon text-green-500">done</span>`; copyButton.title = 'Kopyalandı!'; setTimeout(() => { if (copyButton.title === 'Kopyalandı!') { copyButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm">content_copy</span>`; copyButton.title = 'Kopyala'; } }, 2000); }).catch(err => { console.error('Kopyalama hatası:', err); copyButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm error-icon text-red-500">error_outline</span>`; copyButton.title = 'Kopyalanamadı!';}); });
        // Yeniden Üret Listener
        regenerateButton.addEventListener('click', () => { console.log("Yeniden üret tıklandı."); if (activeChatId && chats[activeChatId]) { const currentChat = chats[activeChatId]; if (currentChat.history.length >= 2) { currentChat.history.pop(); currentChat.history.pop(); renderChatMessages(activeChatId); if (promptInput) { promptInput.value = originalQuestion; sendMessage(); } } }});
        // Beğen Listener
        likeButton.addEventListener('click', async () => { likeButton.disabled = true; if(reportButton) reportButton.disabled = true; likeButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm text-green-500">done</span>`; try { const learnResponse = await fetch('/api/learn', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: originalQuestion, answer: text }) }); if (!learnResponse.ok) throw new Error('.'); const learnData = await learnResponse.json(); likeButton.title = (learnData.status === 'already_known') ? 'Zaten biliniyor!' : 'Kaydedildi!'; console.log('Öğrenme sonucu:', learnData.status); } catch (error) { console.error('Öğrenme HATA:', error); likeButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm error-icon text-red-500">error_outline</span>`; likeButton.title = 'Kaydedilemedi!'; setTimeout(() => { if(likeButton && reportButton && !likeButton.disabled) { likeButton.disabled = false; reportButton.disabled = false; likeButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm">thumb_up</span>`; likeButton.title = 'Hafızaya kaydet'; }}, 3000); } });
        // Hata Bildir Listener
        reportButton.addEventListener('click', async () => { reportButton.disabled = true; if(likeButton) likeButton.disabled = true; reportButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm text-orange-500">delete</span>`; try { const forgetResponse = await fetch('/api/forget', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: originalQuestion, answer: text }) }); if (!forgetResponse.ok) throw new Error('.'); console.log('Cevap pasif yapıldı!'); reportButton.title = 'Pasif yapıldı!'; messageDiv.querySelector('.flex-grow').style.opacity = '0.5'; } catch (error) { console.error('Unutma HATA:', error); reportButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm error-icon text-red-500">error_outline</span>`; reportButton.title = 'Silinemedi!'; setTimeout(() => { if(reportButton && likeButton && !reportButton.disabled) { reportButton.disabled = false; likeButton.disabled = false; reportButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm text-red-500 hover:text-red-700">report</span>`; reportButton.title = 'Hatalı bildir/Sil'; }}, 3000); } });
        // Butonları ekle
        buttonsContainer.appendChild(copyButton); buttonsContainer.appendChild(regenerateButton); buttonsContainer.appendChild(likeButton); buttonsContainer.appendChild(reportButton); messageDiv.appendChild(buttonsContainer);
    };

    // --- Gece Modu (Tema) Yönetimi ---
    const applyTheme = (theme) => { const root = document.documentElement; if (theme === 'dark') { root.classList.add('dark'); if (themeToggle) themeToggle.querySelector('.material-symbols-rounded').innerText = 'light_mode'; } else { root.classList.remove('dark'); if (themeToggle) themeToggle.querySelector('.material-symbols-rounded').innerText = 'dark_mode'; } };
    const savedTheme = loadThemeFromLocalStorage() || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); applyTheme(savedTheme);
    if (themeToggle) { themeToggle.addEventListener('click', () => { console.log("--- Tema Butonuna Tıklandı! ---"); const newTheme = document.documentElement.classList.contains('dark') ? 'light' : 'dark'; applyTheme(newTheme); saveThemeToLocalStorage(newTheme); }); }

    // --- Sidebar Yönetimi ---
    const openSidebar = () => { if (sidebar) sidebar.classList.add('open'); if (sidebarOverlay) sidebarOverlay.classList.add('open'); };
    const closeSidebar = () => { if (sidebar) sidebar.classList.remove('open'); if (sidebarOverlay) sidebarOverlay.classList.remove('open'); };
    if (menuToggleButton) { menuToggleButton.addEventListener('click', (e) => { e.stopPropagation(); console.log("--- Menü Toggle Tıklandı! ---"); sidebar?.classList.contains('open') ? closeSidebar() : openSidebar(); }); }
    if (sidebarOverlay) { sidebarOverlay.addEventListener('click', () => { console.log("--- Overlay Tıklandı! ---"); closeSidebar(); }); }

    // --- Başlangıç Ayarları ---
    const initializeApp = () => {
        console.log("Uygulama başlatılıyor..."); loadChatsFromLocalStorage();
        if (!activeChatId || !chats[activeChatId]) { const chatIds = Object.keys(chats); if (chatIds.length > 0) { const latestChatId = chatIds.sort((a, b) => parseInt(b.split('_')[1] || 0) - parseInt(a.split('_')[1] || 0))[0]; activeChatId = latestChatId; } else { const newChatId = generateChatId(); chats[newChatId] = { title: "Yeni Sohbet", history: [] }; activeChatId = newChatId; saveChatsToLocalStorage(); } }
        renderChatList(); if (activeChatId && chats[activeChatId]) { setActiveChat(activeChatId); } else if (Object.keys(chats).length === 0){ if(responseArea) responseArea.innerHTML = ''; appendMessage("Yeni sohbet başlatın.", 'assistant', null, false); }
        console.log("Uygulama başlatma tamamlandı.");
    };

    // --- Olay Dinleyicileri ---
    if (newChatButton) { newChatButton.addEventListener('click', () => { console.log("--- Yeni Sohbet Butonuna Tıklandı! ---"); createNewChat(); if (window.innerWidth < 1024) closeSidebar(); }); }
    if (sendButton) { sendButton.addEventListener('click', sendMessage); }
    if (promptInput) { promptInput.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (sendButton && !sendButton.disabled) sendMessage(); } }); promptInput.addEventListener('input', adjustTextareaHeight); }
    window.addEventListener('resize', scrollToBottom);

    // --- Uygulamayı Başlat ---
    initializeApp();

}); // DOMContentLoaded sonu