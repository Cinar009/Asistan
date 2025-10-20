# ----------------------------------------------------
# Asistan Projesi - Güncellenmiş ve Tam app.py Kodu
# ----------------------------------------------------

import os
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# .env dosyasındaki API anahtarını güvenli bir şekilde yükle
load_dotenv()

# Flask web uygulamasını başlat
app = Flask(__name__)

# Google Gemini API'sini yapılandır
# Bu blok, program başlarken API anahtarını kontrol eder
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Hata: GOOGLE_API_KEY bulunamadı. .env dosyanızı kontrol edin.")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-pro')
    print("Gemini modeli başarıyla yüklendi.")
except Exception as e:
    # Eğer API anahtarı veya yapılandırmada bir sorun varsa, terminale yazdır
    print(f"!!! KRİTİK HATA: Gemini API yapılandırılamadı. Hata Detayı: {e}")
    model = None

# Ana sayfa (http://127.0.0.1:5000)
# Bu fonksiyon, templates/index.html dosyasını kullanıcıya gösterir.
@app.route('/')
def index():
    return render_template('index.html')

# Yapay zeka ile konuşacak olan API endpoint'i
@app.route('/api/assist', methods=['POST'])
def assist():
    # Eğer model başlangıçta yüklenemediyse, hata döndür
    if not model:
        return jsonify({"response": "Üzgünüm, yapay zeka modeli şu an kullanılamıyor. Lütfen terminali kontrol edin."}), 500

    # Kullanıcının web sitesinden gönderdiği JSON verisini al
    data = request.get_json()
    user_prompt = data.get('prompt')

    # Eğer kullanıcı boş bir metin gönderdiyse, hata döndür
    if not user_prompt:
        return jsonify({"response": "Lütfen bir metin girin."}), 400

    try:
        # Yapay zekaya kim olduğunu ve nasıl davranması gerektiğini söyleyen komut (prompt)
        full_prompt = f"Senin adın 'Asistan'. Sen akıllı bir dijital yardımcısın. Kullanıcının isteğine net, yardımcı ve samimi bir şekilde cevap ver. Kullanıcının isteği: '{user_prompt}'"
        
        # Modeli çalıştır ve cevabı al
        response = model.generate_content(full_prompt)
        
        # --- GÜVENLİK FİLTRESİ KORUMASI ---
        # Google'ın cevabı güvenlik nedeniyle engelleyip engellemediğini kontrol et
        try:
            generated_text = response.text
        except ValueError:
            # Eğer .text alınamıyorsa, bu genellikle cevabın engellendiği anlamına gelir.
            generated_text = "Üzgünüm, bu isteğiniz güvenlik filtrelerimize takıldı veya model bir cevap üretemedi. Lütfen farklı bir şekilde sormayı deneyin."
        # --- KORUMA BİTTİ ---

        # Başarılı cevabı web sitesine geri gönder
        return jsonify({"response": generated_text})

    except Exception as e:
        # Beklenmedik başka bir hata olursa, detayı terminale yazdır
        print(f"!!! SUNUCUDA BİR HATA OLUŞTU: {e}") 
        # Kullanıcıya genel bir hata mesajı göster
        return jsonify({"response": "Beklenmedik bir hata oluştu. Lütfen tekrar deneyin."}), 500

# Bu kısım, 'flask run' komutunu çalıştırdığımızda uygulamanın başlamasını sağlar
if __name__ == '__main__':
    # debug=True, kodda değişiklik yapıp kaydettiğinizde sunucunun otomatik yeniden başlamasını sağlar
    app.run(debug=True)