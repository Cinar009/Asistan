// ----------------------------------------------------
// Asistan Projesi V3.2 - Final script.js Kodu
// (DEBUG Logları Eklendi)
// ----------------------------------------------------

console.log("--- script.js Yüklendi! ---"); // İŞARET FİŞEĞİ 1

document.addEventListener('DOMContentLoaded', () => {

    console.log("--- DOM Yüklendi, event listener'lar ekleniyor... ---"); // İŞARET FİŞEĞİ 2

    const sendButton = document.getElementById('send-button');
    console.log("Send button bulundu mu?", sendButton); // İŞARET FİŞEĞİ 3

    const promptInput = document.getElementById('prompt-input');
    console.log("Prompt input bulundu mu?", promptInput); // İŞARET FİŞEĞİ 4

    const responseArea = document.getElementById('response-area');
    console.log("Response area bulundu mu?", responseArea); // İŞARET FİŞEĞİ 5

    const loadingIndicator = document.getElementById('loading');
    console.log("Loading indicator bulundu mu?", loadingIndicator); // İŞARET FİŞEĞİ 6

    const themeToggle = document.getElementById('theme-toggle');
    console.log("Theme toggle bulundu mu?", themeToggle); // İŞARET FİŞEĞİ 7

    let conversationHistory = []; // Sohbet geçmişini tutar

    // --- Gece Modu Yönetimi ---
    const applyTheme = (theme) => {
        const root = document.documentElement;
        if (theme === 'dark') {
            root.classList.add('dark');
            if (themeToggle) themeToggle.querySelector('.material-symbols-rounded').innerText = 'light_mode';
        } else {
            root.classList.remove('dark');
            if (themeToggle) themeToggle.querySelector('.material-symbols-rounded').innerText = 'dark_mode';
        }
    };
    const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    console.log("Kaydedilmiş veya varsayılan tema:", savedTheme); // İŞARET FİŞEĞİ 8
    applyTheme(savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            console.log("--- Tema Butonuna Tıklandı! ---"); // İŞARET FİŞEĞİ 9
            const newTheme = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
            applyTheme(newTheme);
            localStorage.setItem('theme', newTheme);
        });
    } else {
        console.warn("Tema değiştirme butonu bulunamadı!"); // Uyarı
    }
    // --- Gece Modu Yönetimi Sonu ---

    // --- Mesajlaşma Fonksiyonları ---
    const sendMessage = async () => {
        console.log("--- sendMessage fonksiyonu çalıştı ---"); // İŞARET FİŞEĞİ 10
        const prompt = promptInput ? promptInput.value.trim() : "";
        if (!prompt || (sendButton && sendButton.disabled)) {
            console.log("Mesaj gönderilemedi: Prompt boş veya buton pasif.");
            return;
        }

        conversationHistory.push({ role: 'user', parts: [{ text: prompt }] });
        appendMessage(prompt, 'user');
        const currentQuestion = prompt;
        if (promptInput) promptInput.value = '';
        adjustTextareaHeight();
        if (loadingIndicator) loadingIndicator.classList.remove('hidden');
        if (sendButton) sendButton.disabled = true;
        scrollToBottom();

        console.log("Sunucuya gönderilen geçmiş:", JSON.stringify(conversationHistory)); // İŞARET FİŞEĞİ 11

        try {
            const response = await fetch('/api/assist', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ history: conversationHistory })
            });
            console.log("Sunucu yanıt durumu:", response.status); // İŞARET FİŞEĞİ 12

            if (!response.ok) throw new Error(`Server error: ${response.status}`);
            const data = await response.json();
            console.log("Sunucudan gelen veri:", data); // İŞARET FİŞEĞİ 13

            conversationHistory.push({ role: 'model', parts: [{ text: data.response }] });
            appendMessage(data.response, 'assistant', data.is_known ? null : currentQuestion);

        } catch (error) {
            console.error('sendMessage sırasında HATA:', error); // İŞARET FİŞEĞİ 14 (Hata durumunda)
            conversationHistory.pop();
            appendMessage('Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.', 'assistant', null);
        } finally {
            if (loadingIndicator) loadingIndicator.classList.add('hidden');
            if (sendButton) sendButton.disabled = false;
            scrollToBottom();
        }
    };

    // Mesajı sohbet alanına ekleyen fonksiyon
    const appendMessage = (text, type, originalQuestion = null) => {
        console.log(`appendMessage çağrıldı: type=${type}, text=${text.substring(0, 30)}...`); // İŞARET FİŞEĞİ 15
        if (!responseArea) {
            console.error("responseArea elementi bulunamadı!");
            return;
        }

        const messageDiv = document.createElement('div');
        const messageContent = document.createElement('div');
        messageContent.innerText = text;
        messageContent.className = 'flex-grow';

        messageDiv.className = `message ${type} message-animate flex items-start gap-2`;
        messageDiv.appendChild(messageContent);

        // Butonlar (Sadece Asistan ve Gemini'den gelen cevaplar için)
        if (type === 'assistant' && originalQuestion) {
            console.log("Beğen/Hata Bildir butonları ekleniyor..."); // İŞARET FİŞEĞİ 16
            const buttonsContainer = document.createElement('div');
            buttonsContainer.className = 'flex flex-col ml-1 sm:ml-2 flex-shrink-0 space-y-1';

            const likeButton = document.createElement('button');
            likeButton.innerHTML = `<span class="material-symbols-rounded text-sm sm:text-base opacity-50 hover:opacity-100 transition-opacity">thumb_up</span>`;
            likeButton.className = 'like-button p-1 rounded-full flex-shrink-0 leading-none';
            likeButton.title = 'Bu cevabı Asistan\'ın hafızasına kaydet';

            const reportButton = document.createElement('button');
            reportButton.innerHTML = `<span class="material-symbols-rounded text-sm sm:text-base opacity-50 hover:opacity-100 transition-opacity text-red-500 hover:text-red-700">report</span>`;
            reportButton.className = 'report-button p-1 rounded-full flex-shrink-0 leading-none';
            reportButton.title = 'Bu cevabın hatalı olduğunu bildir ve hafızadan sil';

            likeButton.addEventListener('click', async () => {
                console.log("--- Beğen Butonuna Tıklandı! ---"); // İŞARET FİŞEĞİ 17
                likeButton.disabled = true;
                reportButton.disabled = true;
                likeButton.innerHTML = `<span class="material-symbols-rounded text-sm sm:text-base">done</span>`;
                try {
                    const learnResponse = await fetch('/api/learn', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: originalQuestion, answer: text }) });
                    if (!learnResponse.ok) throw new Error('Öğrenme isteği başarısız.');
                    const learnData = await learnResponse.json();
                    if (learnData.status === 'already_known') { likeButton.title = 'Bu cevap zaten biliniyor!'; } else { likeButton.title = 'Hafızaya kaydedildi!'; }
                    console.log('Öğrenme sonucu:', learnData.status);
                } catch (error) {
                     console.error('Öğrenme sırasında HATA:', error); // İŞARET FİŞEĞİ 18 (Hata durumunda)
                     likeButton.innerHTML = `<span class="material-symbols-rounded text-sm sm:text-base error-icon">error_outline</span>`;
                     likeButton.title = 'Kaydedilemedi!';
                     setTimeout(() => { /* ... (hata sonrası buton resetleme kodu aynı) ... */ }, 3000);
                 }
            });

            reportButton.addEventListener('click', async () => {
                console.log("--- Hata Bildir Butonuna Tıklandı! ---"); // İŞARET FİŞEĞİ 19
                reportButton.disabled = true;
                likeButton.disabled = true;
                reportButton.innerHTML = `<span class="material-symbols-rounded text-sm sm:text-base text-orange-500">delete</span>`;
                try {
                    const forgetResponse = await fetch('/api/forget', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: originalQuestion, answer: text }) });
                    if (!forgetResponse.ok) throw new Error('Unutma isteği başarısız.');
                    console.log('Cevap başarıyla hafızadan silindi!');
                    reportButton.title = 'Hafızadan silindi!';
                } catch (error) {
                     console.error('Unutma sırasında HATA:', error); // İŞARET FİŞEĞİ 20 (Hata durumunda)
                     reportButton.innerHTML = `<span class="material-symbols-rounded text-sm sm:text-base error-icon">error_outline</span>`;
                     reportButton.title = 'Silinemedi!';
                     setTimeout(() => { /* ... (hata sonrası buton resetleme kodu aynı) ... */ }, 3000);
                 }
            });

            buttonsContainer.appendChild(likeButton);
            buttonsContainer.appendChild(reportButton);
            messageDiv.appendChild(buttonsContainer);
        }

        responseArea.appendChild(messageDiv);
        scrollToBottom();
    };

    // Yardımcı fonksiyonlar
    const scrollToBottom = () => { if (responseArea) responseArea.scrollTop = responseArea.scrollHeight; };
    const adjustTextareaHeight = () => {
        if (!promptInput) return;
        promptInput.style.height = 'auto';
        const maxHeight = 192;
        promptInput.style.height = `${Math.min(promptInput.scrollHeight, maxHeight)}px`;
    };

    // Olay Dinleyicileri
    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    } else {
        console.error("Gönder butonu bulunamadı!"); // Hata
    }

    if (promptInput) {
        promptInput.addEventListener('keydown', (e) => {
            // console.log("--- Input'a Tuş Basıldı:", e.key); // Bunu yoruma alalım, çok fazla log üretir
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (sendButton && !sendButton.disabled) sendMessage();
            }
        });
        promptInput.addEventListener('input', adjustTextareaHeight);
    } else {
        console.error("Giriş kutusu bulunamadı!"); // Hata
    }

    // Başlangıç ayarları
    conversationHistory = [];
    scrollToBottom();
    window.addEventListener('resize', scrollToBottom);

    console.log("--- script.js başlatma tamamlandı. ---"); // İŞARET FİŞEĞİ 21
});