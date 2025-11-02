// ----------------------------------------------------
// Asistan Projesi V12.0 - Faz 4.3 (NİHAİ SÜRÜM)
// (localStorage TAMAMEN KALDIRILDI)
// (Tüm sohbetler artık Veritabanından Okunuyor ve Yazılıyor)
// ----------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    console.log("--- DOM Yüklendi, V12.0 Faz 4.3 (NİHAİ) Script Başlatılıyor ---");

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
    const logoutButton = document.getElementById('logout-button');

    // Element Kontrolleri...
    
    // Global Değişkenler
    let chats = {}; // Artık sunucudan doldurulacak
    let activeChatId = null; // Artık sunucudan gelecek

    // --- Yardımcı Fonksiyonlar ---
    // (scrollToBottom, adjustTextareaHeight, sanitizeHTML aynı kaldı)
    const scrollToBottom = () => { if (responseArea) setTimeout(() => responseArea.scrollTop = responseArea.scrollHeight, 50); };
    const adjustTextareaHeight = () => { if (!promptInput) return; promptInput.style.height = 'auto'; const maxHeight = 160; promptInput.style.height = `${Math.min(promptInput.scrollHeight, maxHeight)}px`; };
    const sanitizeHTML = (str) => { const temp = document.createElement('div'); temp.textContent = str; return temp.innerHTML; };
    // (getChatTitle artık kullanılmayacak, sunucu başlığı gönderecek)
    // const getChatTitle = (history) => { ... };

    // --- localStorage Yönetimi (TAMAMEN SİLİNDİ) ---
    // const saveChatsToLocalStorage = () => { ... };
    // const loadChatsFromLocalStorage = () => { ... };
    
    // (Tema için localStorage hâlâ duruyor, bu OK)
    const saveThemeToLocalStorage = (theme) => { try { localStorage.setItem('theme', theme); } catch (e) { console.error("localStorage tema kaydetme hatası:", e); } };
    const loadThemeFromLocalStorage = () => { try { return localStorage.getItem('theme'); } catch (e) { console.error("localStorage tema yükleme hatası:", e); return null; } };

    // --- Arayüz Güncelleme Fonksiyonları ---
    const renderChatList = () => {
        if (!chatList) return; 
        chatList.innerHTML = ''; 
        
        // Sunucudan (app.py) gelen chats objesi zaten en yeniden eskiye sıralı
        const sortedChatIds = Object.keys(chats); 

        sortedChatIds.forEach(chatId => {
            const chat = chats[chatId]; 
            const listItem = document.createElement('li'); 
            listItem.className = `chat-item group flex items-center justify-between text-sm p-2 rounded hover:bg-[var(--sidebar-hover-bg)] cursor-pointer transition-colors duration-150 ${chatId === activeChatId ? 'active' : ''}`; 
            listItem.dataset.chatId = chatId; 
            
            const titleSpan = document.createElement('span'); 
            titleSpan.className = 'truncate flex-grow mr-2'; 
            titleSpan.textContent = chat.title; // DB'den gelen başlık
            titleSpan.addEventListener('click', () => { setActiveChat(chatId); if (window.innerWidth < 1024) closeSidebar(); }); 
            listItem.appendChild(titleSpan); 
            
            const deleteButton = document.createElement('button'); 
            deleteButton.innerHTML = `<span class="material-symbols-rounded text-xs opacity-60 group-hover:opacity-100 text-red-500 hover:text-red-700">delete</span>`; 
            deleteButton.className = 'delete-chat-button p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 leading-none'; 
            deleteButton.title = 'Sohbeti sil'; 
            deleteButton.dataset.chatId = chatId; 
            deleteButton.addEventListener('click', (e) => { e.stopPropagation(); deleteChat(chatId); }); // Artık API'yi çağıracak
            listItem.appendChild(deleteButton);
            
            listItem.addEventListener('click', (e) => { if (e.target === listItem || titleSpan.contains(e.target)) { setActiveChat(chatId); if (window.innerWidth < 1024) closeSidebar(); }}); 
            chatList.appendChild(listItem);
        });
    };
    
    const renderChatMessages = (chatId) => {
        if (!responseArea) return; 
        responseArea.innerHTML = ''; 
        const chat = chats[chatId];
        
        if (chat?.history?.length > 0) { 
            chat.history.forEach((message) => { 
                appendMessage(message.parts[0].text, message.role === 'user' ? 'user' : 'assistant', null, false); 
            }); 
        } else { 
            // Veritabanından gelen sohbetin geçmişi (history) boşsa
            appendMessage("Merhaba! Yeni sohbetimize başlayalım mı?", 'assistant', null, false); 
        }
        scrollToBottom();
    };

    // --- YENİ V12.0 - FAZ 4.3: Sohbet Yönetimi (Veritabanı Modu) ---
    
    // (createNewChat fonksiyonu API'yi çağıracak şekilde GÜNCELLENDİ)
    const createNewChat = async () => {
        if (newChatButton.disabled) return; // Zaten tıklanmışsa tekrar basmayı engelle
        newChatButton.disabled = true;
        console.log("Yeni sohbet (DB) oluşturuluyor..."); 
        
        try {
            const response = await fetch('/api/new_chat', { method: 'POST' });
            if (!response.ok) {
                if (response.status === 401) window.location.href = '/login';
                throw new Error('Yeni sohbet oluşturulamadı.');
            }
            const data = await response.json();
            
            const newChatId = data.chat_id;
            chats[newChatId] = data.chat_data; // Yeni sohbeti global 'chats' objesine ekle
            
            console.log(`Yeni sohbet (DB) oluşturuldu: ${newChatId}`); 
            setActiveChat(newChatId); // Yeni sohbeti aktif yap
            renderChatList(); // Sol menüyü yenile
            if (promptInput) promptInput.focus();

        } catch (error) {
            console.error("createNewChat HATA:", error);
            alert("Yeni sohbet oluşturulurken bir hata oluştu.");
        } finally {
            newChatButton.disabled = false;
        }
    };
    
    const setActiveChat = (chatId) => {
        if (!chats[chatId]) { 
            console.error(`Aktif sohbet bulunamadı: ${chatId}. Bu bir hata.`); 
            // /api/get_chats her zaman en az 1 sohbet döndürdüğü için burası olmamalı.
            // Acil durum:
            if (Object.keys(chats).length > 0) {
                activeChatId = Object.keys(chats)[0];
            } else {
                 // Bu, /api/get_chats başarısız oldu demek.
                 // initializeApp'daki hata mesajı zaten gösterilmiştir.
                 return;
            }
        } else { 
            activeChatId = chatId; 
        }
        
        console.log(`Aktif sohbet değiştirildi (DB Modu): ${activeChatId}`); 
        renderChatMessages(activeChatId); 
        renderChatList(); 
        if (promptInput) promptInput.focus();
    };
    
    // (deleteChat fonksiyonu API'yi çağıracak şekilde GÜNCELLENDİ)
    const deleteChat = async (chatIdToDelete) => {
        const chat = chats[chatIdToDelete];
        if (!chat) return;
        
        const chatTitle = chat.title || 'Bu'; 
        if (!confirm(`"${chatTitle}" sohbetini KALICI OLARAK silmek istediğinize emin misiniz?`)) { 
            return; 
        }
        
        console.log(`Sohbet (DB) siliniyor: ${chatIdToDelete} (DB ID: ${chat.db_id})`);
        
        try {
            const response = await fetch('/api/delete_chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_db_id: chat.db_id }) // Gerçek DB ID'sini yolla
            });
            
            if (!response.ok) {
                if (response.status === 401) window.location.href = '/login';
                throw new Error('Sohbet silinemedi.');
            }
            
            // Başarılıysa, arayüzden de sil
            delete chats[chatIdToDelete];
            
            // Eğer silinen sohbet aktif olansa...
            if (activeChatId === chatIdToDelete) {
                activeChatId = null; 
                const remainingChatIds = Object.keys(chats); // (Bunlar zaten sıralı gelmişti)
                
                if (remainingChatIds.length > 0) { 
                    // Kalan sohbetlerden en yenisini (ilkini) aktif yap
                    activeChatId = remainingChatIds[0]; 
                } else { 
                    // Hiç sohbet kalmadıysa, API'den yeni bir tane iste
                    await createNewChat(); 
                    return; 
                }
            }
            
            renderChatList();
            if (activeChatId) { 
                setActiveChat(activeChatId); 
            }

        } catch (error) {
            console.error("deleteChat HATA:", error);
            alert("Sohbet silinirken bir hata oluştu.");
        }
    };

    // --- Mesaj Gönderme ve Alma (STREAMING) (GÜNCELLENDİ) ---
    const sendMessage = async () => {
         if (!activeChatId || !chats[activeChatId]) { 
            console.error("Aktif sohbet yok, gönderilemiyor."); 
            return; 
         }
        const prompt = promptInput?.value?.trim(); 
        if (!prompt || (sendButton && sendButton.disabled)) return;
        
        const currentChat = chats[activeChatId]; 
        const userMessage = { role: 'user', parts: [{ text: prompt }] }; 
        currentChat.history.push(userMessage); // Arayüze geçici olarak ekle
        
        const needsTitleUpdate = (currentChat.history.length === 1 && currentChat.title === "Yeni Sohbet");
        
        appendMessage(prompt, 'user'); 
        const currentQuestion = prompt; 
        if (promptInput) promptInput.value = ''; 
        adjustTextareaHeight(); 
        if (loadingIndicator) loadingIndicator.classList.remove('hidden'); 
        if (sendButton) sendButton.disabled = true; 
        scrollToBottom();
        
        const assistantMessageDiv = appendMessage("", 'assistant', null, true); 
        const messageContent = assistantMessageDiv.querySelector('.flex-grow'); 
        if (!messageContent) { console.error("Mesaj içerik alanı bulunamadı!"); return; }
        
        let fullResponse = ""; 
        let isKnown = false; 
        let errorOccurred = false;
        
        try {
            const response = await fetch('/api/assist', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ history: currentChat.history }) });
            if (!response.ok) { 
                if (response.status === 401) { window.location.href = '/login'; return; }
                console.error("Sunucu Hatası:", response.status, response.statusText); throw new Error(`Server error: ${response.status}`); 
            }
            const reader = response.body.getReader(); const decoder = new TextDecoder("utf-8");
            while (true) {
                const { done, value } = await reader.read(); if (done) { break; }
                const chunkText = decoder.decode(value, {stream: true});
                const lines = chunkText.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataPart = line.substring(6); if (dataPart === "[DONE]") { break; }
                        try {
                            const data = JSON.parse(dataPart);
                            if (data.error) { console.error("Stream HATA:", data.error); fullResponse = data.error; isKnown = data.is_known; errorOccurred = true; break; }
                            if (data.response_chunk) { fullResponse += data.response_chunk; messageContent.innerText = fullResponse; scrollToBottom(); isKnown = data.is_known; }
                        } catch (e) { if (dataPart !== "[DONE]") { console.warn("Geçersiz JSON parçası, atlanıyor:", dataPart, e); } }
                    }
                } if(errorOccurred) break;
            } // while bitti
        } catch (error) { 
            console.error('sendMessage (stream) HATA:', error); 
            messageContent.innerText = 'Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.'; 
            currentChat.history.pop(); // Başarısız olan 'user' mesajını arayüzden geri al
            errorOccurred = true;
        } finally {
            if (loadingIndicator) loadingIndicator.classList.add('hidden'); 
            if (sendButton) sendButton.disabled = false; 
            scrollToBottom();
            
            if (!errorOccurred && fullResponse) { 
                // Mesajı arayüze ekle
                const assistantMessage = { role: 'model', parts: [{ text: fullResponse }] }; 
                currentChat.history.push(assistantMessage); 
                
                // YENİ V12.0 - FAZ 4.3: localStorage'a kaydetmek YERİNE, DB'ye kaydet
                // saveChatsToLocalStorage(); <-- SİLİNDİ
                saveMessagesToDb(currentChat.db_id, prompt, fullResponse, needsTitleUpdate);
                
                if (!isKnown) { addResponseButtons(assistantMessageDiv, currentQuestion, fullResponse); } 
            }
            else if (errorOccurred && fullResponse) { 
                // Hata mesajını arayüze ekle
                const errorMessage = { role: 'model', parts: [{ text: fullResponse }] }; 
                currentChat.history.push(errorMessage); 
                
                // YENİ V12.0 - FAZ 4.3: Hata mesajını da DB'ye kaydet
                // saveChatsToLocalStorage(); <-- SİLİNDİ
                saveMessagesToDb(currentChat.db_id, prompt, fullResponse, needsTitleUpdate);
            }
        }
    };
    
    // YENİ V12.0 - FAZ 4.3: Mesajları Arka Planda DB'ye Kaydetme Fonksiyonu
    const saveMessagesToDb = async (chat_db_id, user_message, model_message, needs_title_update) => {
        console.log(`Sohbet (DB ID: ${chat_db_id}) veritabanına kaydediliyor...`);
        try {
            const response = await fetch('/api/save_messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chat_db_id: chat_db_id,
                    user_message: user_message,
                    model_message: model_message,
                    needs_title_update: needs_title_update
                })
            });
            if (!response.ok) {
                 if (response.status === 401) window.location.href = '/login';
                 throw new Error("Mesajlar DB'ye kaydedilemedi.");
            }
            const data = await response.json();
            
            // Eğer başlık güncellendiyse, sol menüyü (listeyi) yenile
            if (data.new_title) {
                console.log(`Başlık güncellendi: ${data.new_title}`);
                chats[activeChatId].title = data.new_title;
                renderChatList();
            }
            console.log("Mesajlar DB'ye başarıyla kaydedildi.");

        } catch (error) {
            console.error("saveMessagesToDb HATA:", error);
            // Kullanıcıya bir hata göstermek yerine (akışı bozmamak için)
            // sadece konsola hata basabiliriz.
        }
    };

    // (appendMessage fonksiyonu aynı kaldı)
    const appendMessage = (text, type, originalQuestion = null, animate = true) => {
         if (!responseArea) return null; const messageDiv = document.createElement('div'); const messageContent = document.createElement('div'); messageContent.innerText = text; messageContent.className = 'flex-grow min-w-0'; messageDiv.className = `message ${type} flex items-start gap-2`; if (animate) messageDiv.classList.add('message-animate'); messageDiv.appendChild(messageContent);
        responseArea.appendChild(messageDiv);
        if(animate) scrollToBottom();
        return messageDiv;
    };

    // (addResponseButtons fonksiyonu aynı kaldı)
    const addResponseButtons = (messageDiv, originalQuestion, text) => {
        // ... (Kopyala, Yeniden Üret, Beğen, Hata Bildir buton kodları aynı kaldı) ...
        if (!messageDiv || !originalQuestion || !text) return;
        const buttonsContainer = document.createElement('div'); buttonsContainer.className = 'flex items-center ml-1 sm:ml-2 flex-shrink-0 space-x-1 mt-1 opacity-70 hover:opacity-100 transition-opacity';
        const copyButton = document.createElement('button'); copyButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm">content_copy</span>`; copyButton.className = 'copy-button action-button p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700'; copyButton.title = 'Kopyala';
        const regenerateButton = document.createElement('button'); regenerateButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm">refresh</span>`; regenerateButton.className = 'regenerate-button action-button p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700'; regenerateButton.title = 'Yeniden Üret';
        const likeButton = document.createElement('button'); likeButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm">thumb_up</span>`; likeButton.className = 'like-button action-button p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700'; likeButton.title = 'Hafızaya kaydet';
        const reportButton = document.createElement('button'); reportButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm text-red-500 hover:text-red-700">report</span>`; reportButton.className = 'report-button action-button p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700'; reportButton.title = 'Hatalı bildir/Sil';
        copyButton.addEventListener('click', () => { navigator.clipboard.writeText(text).then(() => { copyButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm done-icon text-green-500">done</span>`; copyButton.title = 'Kopyalandı!'; setTimeout(() => { if (copyButton.title === 'Kopyalandı!') { copyButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm">content_copy</span>`; copyButton.title = 'Kopyala'; } }, 2000); }).catch(err => { console.error('Kopyalama hatası:', err); copyButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm error-icon text-red-500">error_outline</span>`; copyButton.title = 'Kopyalanamadı!';}); });
        regenerateButton.addEventListener('click', () => { console.log("Yeniden üret tıklandı."); if (activeChatId && chats[activeChatId]) { const currentChat = chats[activeChatId]; if (currentChat.history.length >= 2) { currentChat.history.pop(); currentChat.history.pop(); renderChatMessages(activeChatId); if (promptInput) { promptInput.value = originalQuestion; sendMessage(); } } }});
        likeButton.addEventListener('click', async () => { likeButton.disabled = true; if(reportButton) reportButton.disabled = true; likeButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm text-green-500">done</span>`; try { const learnResponse = await fetch('/api/learn', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: originalQuestion, answer: text }) }); if (!learnResponse.ok) { if (learnResponse.status === 401) window.location.href = '/login'; throw new Error('.'); } const learnData = await learnResponse.json(); likeButton.title = (learnData.status === 'already_known') ? 'Zaten biliniyor!' : 'Kaydedildi!'; console.log('Öğrenme sonucu:', learnData.status); } catch (error) { console.error('Öğrenme HATA:', error); likeButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm error-icon text-red-500">error_outline</span>`; likeButton.title = 'Kaydedilemedi!'; setTimeout(() => { if(likeButton && reportButton && !likeButton.disabled) { likeButton.disabled = false; reportButton.disabled = false; likeButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm">thumb_up</span>`; likeButton.title = 'Hafızaya kaydet'; }}, 3000); } });
        reportButton.addEventListener('click', async () => { reportButton.disabled = true; if(likeButton) likeButton.disabled = true; reportButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm text-orange-500">delete</span>`; try { const forgetResponse = await fetch('/api/forget', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: originalQuestion, answer: text }) }); if (!forgetResponse.ok) { if (forgetResponse.status === 401) window.location.href = '/login'; throw new Error('.'); } console.log('Cevap pasif yapıldı!'); reportButton.title = 'Pasif yapıldı!'; messageDiv.querySelector('.flex-grow').style.opacity = '0.5'; } catch (error) { console.error('Unutma HATA:', error); reportButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm error-icon text-red-500">error_outline</span>`; reportButton.title = 'Silinemedi!'; setTimeout(() => { if(reportButton && likeButton && !reportButton.disabled) { reportButton.disabled = false; likeButton.disabled = false; reportButton.innerHTML = `<span class="material-symbols-rounded text-xs sm:text-sm text-red-500 hover:text-red-700">report</span>`; reportButton.title = 'Hatalı bildir/Sil'; }}, 3000); } });
        buttonsContainer.appendChild(copyButton); buttonsContainer.appendChild(regenerateButton); buttonsContainer.appendChild(likeButton); buttonsContainer.appendChild(reportButton); messageDiv.appendChild(buttonsContainer);
    };

    // --- Gece Modu (Tema) Yönetimi ---
    // (Bu kod aynı kaldı)
    const applyTheme = (theme) => { const root = document.documentElement; if (theme === 'dark') { root.classList.add('dark'); if (themeToggle) themeToggle.querySelector('.material-symbols-rounded').innerText = 'light_mode'; } else { root.classList.remove('dark'); if (themeToggle) themeToggle.querySelector('.material-symbols-rounded').innerText = 'dark_mode'; } };
    const savedTheme = loadThemeFromLocalStorage() || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); applyTheme(savedTheme);
    if (themeToggle) { themeToggle.addEventListener('click', () => { console.log("--- Tema Butonuna Tıklandı! ---"); const newTheme = document.documentElement.classList.contains('dark') ? 'light' : 'dark'; applyTheme(newTheme); saveThemeToLocalStorage(newTheme); }); }

    // --- Sidebar Yönetimi ---
    // (Bu kod aynı kaldı)
    const openSidebar = () => { if (sidebar) sidebar.classList.add('open'); if (sidebarOverlay) sidebarOverlay.classList.add('open'); };
    const closeSidebar = () => { if (sidebar) sidebar.classList.remove('open'); if (sidebarOverlay) sidebarOverlay.classList.remove('open'); };
    if (menuToggleButton) { menuToggleButton.addEventListener('click', (e) => { e.stopPropagation(); console.log("--- Menü Toggle Tıklandı! ---"); sidebar?.classList.contains('open') ? closeSidebar() : openSidebar(); }); }
    if (sidebarOverlay) { sidebarOverlay.addEventListener('click', () => { console.log("--- Overlay Tıklandı! ---"); closeSidebar(); }); }


    // --- YENİ V12.0 - FAZ 4.2: Sohbetleri Sunucudan Çekme ---
    const loadChatsFromServer = async () => {
        console.log("Sohbetler sunucudan (DB) çekiliyor...");
        try {
            const response = await fetch('/api/get_chats');
            if (!response.ok) {
                if (response.status === 401) { // 401 Yetkisiz
                    window.location.href = '/login'; // Oturum süresi dolmuş, login'e yolla
                    return;
                }
                throw new Error(`Sunucu hatası: ${response.status}`);
            }
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }

            // Global değişkenleri sunucudan gelen veriyle doldur
            chats = data.chats;
            activeChatId = data.active_chat_id;

            console.log("Sohbetler sunucudan başarıyla yüklendi.");
            console.log("Aktif sohbet ID:", activeChatId);

            // Arayüzü güncelle
            renderChatList();
            if (activeChatId && chats[activeChatId]) {
                setActiveChat(activeChatId);
            } else {
                 console.warn("Sunucudan aktif sohbet ID'si gelmedi veya sohbetler boş.");
                 if(responseArea) responseArea.innerHTML = ''; 
                 appendMessage("Sohbet yüklenirken bir hata oluştu veya hiç sohbet yok.", 'assistant', null, false);
            }

        } catch (error) {
            console.error('loadChatsFromServer HATA:', error);
            if(responseArea) responseArea.innerHTML = ''; 
            appendMessage(`Sohbetleriniz yüklenirken kritik bir hata oluştu: ${error.message}`, 'assistant', null, false);
        }
    };

    // --- Başlangıç Ayarları (GÜNCELLENDİ) ---
    const initializeApp = () => {
        console.log("Uygulama başlatılıyor (Veritabanı modu)...");
        // localStorage'dan okumayı BIRAK, sunucudan OKU
        loadChatsFromServer(); 
    };

    // --- Olay Dinleyicileri ---
    if (newChatButton) { newChatButton.addEventListener('click', createNewChat); } // Fonksiyon adı değişti
    if (sendButton) { sendButton.addEventListener('click', sendMessage); }
    if (promptInput) { promptInput.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (sendButton && !sendButton.disabled) sendMessage(); } }); promptInput.addEventListener('input', adjustTextareaHeight); }
    window.addEventListener('resize', scrollToBottom);

    // --- Uygulamayı Başlat ---
    initializeApp();

}); // DOMContentLoaded sonu