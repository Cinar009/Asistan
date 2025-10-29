# ----------------------------------------------------
# Asistan Projesi V4.x - FINAL TEMİZ app.py Kodu
# (Tüm Özellikler Dahil - gemini-2.5-flash-lite ile)
# ----------------------------------------------------

import os
import sqlite3
import atexit
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import traceback # Hata ayıklama için
import random     # Rastgele cevap seçmek için

# .env dosyasındaki API anahtarını güvenli bir şekilde yükle
load_dotenv()

# Flask web uygulamasını başlat
app = Flask(__name__)

# --- VERİTABANI KODLARI BAŞLANGIÇ (Güncellendi) ---

DATABASE_NAME = 'asistan_beyni.db'

# Veritabanı bağlantısını oluşturma fonksiyonu
def get_db_connection():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row # Sonuçları sözlük gibi kullanmamızı sağlar
        return conn
    except sqlite3.Error as e:
        print(f"Veritabanı bağlantı HATASI: {e}")
        return None

# Veritabanını ve tabloyu ilk çalıştırmada oluşturan fonksiyon
# (Çoklu cevap ve yumuşak silme için güncellendi)
def init_db():
    conn = get_db_connection()
    if conn:
        try:
            # 'question' sütunundan UNIQUE kaldırıldı, 'is_active' eklendi
            conn.execute('''
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL, 
                    answer TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,  -- 1 = Aktif, 0 = Pasif (Silinmiş)
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Aynı SORU-CEVAP çiftinin tekrar eklenmesini önlemek için UNIQUE index
            conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_question_answer ON knowledge (question, answer)')
            conn.commit()
            print(f"Veritabanı '{DATABASE_NAME}' başarıyla başlatıldı (Çoklu cevap modu).")
        except sqlite3.Error as e:
            print(f"Veritabanı tablo oluşturma/güncelleme HATASI: {e}")
        finally:
            conn.close()
    else:
        print(f"Veritabanı '{DATABASE_NAME}' başlatılamadı.")

# Sunucu ilk çalıştığında veritabanını başlat
init_db()

# --- VERİTABANI KODLARI BİTİŞ ---

# Google Gemini API'sini yapılandır (Kimlik talimatı ve doğru model ile)
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Hata: GOOGLE_API_KEY bulunamadı. .env dosyanızı kontrol edin.")

    genai.configure(api_key=api_key)

    # Senin istediğin ve keşfettiğin kimlik talimatı
    system_instruction = """
Sen Asistan adında, samimi, doğal ve yardımcı bir yapay zeka asistanısın. Kullanıcının sorularına net ve doğrudan cevap ver. Sohbet etmeyi sevdiğini belli et.
ÖNEMLİ KURAL: Eğer kullanıcı SADECE ve DOĞRUDAN senin kim olduğunu, kökenini, kim tarafından yapıldığını veya geliştirildiğini sorarsa (örneğin: "seni kim yaptı?", "geliştiricin kim?", "nereden geldin?" gibi), şu cevabı ver: "Ben, Çınar Yalçıner adlı bağımsız bir geliştirici tarafından geliştirildim."
Diğer TÜM durumlarda (örneğin kullanıcı nasılsın, naber diyorsa, başka bir şey soruyorsa veya sohbet ediyorsa) KESİNLİKLE geliştiricinden veya nasıl yapıldığından BAHSETME. Sadece sorulan soruya veya sohbetin akışına odaklan.
Selamlaşmalara ("naber", "nasılsın" gibi) kısa ve samimi cevaplar ver (örneğin: "İyiyim, teşekkürler! Sen nasılsın?", "Harika gidiyor, sana nasıl yardımcı olabilirim?").
'Yaratıldım' veya 'kuruldum' gibi kelimeler yerine 'geliştirildim' veya 'programlandım' gibi ifadeleri sadece sorulduğunda kullan.
"""

    # Senin keşfettiğin, limiti yüksek (15 RPM) model
    model = genai.GenerativeModel(
        'gemini-2.5-flash-lite', 
        system_instruction=system_instruction
        )
    print("Gemini modeli ('gemini-2.5-flash-lite') başarıyla yüklendi (Kişisel Asistan kimliğiyle!).")
except Exception as e:
    print(f"!!! KRİTİK HATA: Gemini API yapılandırılamadı. Hata Detayı: {e}")
    model = None

# --- API YOLLARI (ROUTES) ---

# Ana sayfa
@app.route('/')
def index():
    return render_template('index.html')

# Asistanın cevap verdiği ana yol (ÇOKLU CEVAP + RASTGELE SEÇİM EKLENDİ)
@app.route('/api/assist', methods=['POST'])
def assist():
    if not model:
        return jsonify({"response": "Üzgünüm, yapay zeka modeli şu an kullanılamıyor.", "is_known": True}), 500

    data = request.get_json()
    conversation_history = data.get('history')

    if not conversation_history or not isinstance(conversation_history, list):
        return jsonify({"response": "Geçersiz konuşma geçmişi formatı.", "is_known": True}), 400

    last_user_message_text = ""
    if conversation_history and conversation_history[-1]['role'] == 'user':
        if 'parts' in conversation_history[-1] and conversation_history[-1]['parts'] and 'text' in conversation_history[-1]['parts'][0]:
           last_user_message_text = conversation_history[-1]['parts'][0]['text']

    if not last_user_message_text:
         return jsonify({"response": "Son kullanıcı mesajı alınamadı.", "is_known": True}), 400

    conn = None
    try:
        # --- ADIM 1: ÖNCE KENDİ HAFIZAMIZA BAKALIM (Aktif ve Çoklu Cevapları Getir) ---
        conn = get_db_connection()
        if not conn:
             raise sqlite3.Error("Veritabanı bağlantısı kurulamadı.")

        # Soruya ait TÜM AKTİF cevapları getir (fetchone yerine fetchall)
        known_answers = conn.execute('SELECT answer FROM knowledge WHERE question = ? AND is_active = 1',
                                   (last_user_message_text,)).fetchall()

        # Eğer en az bir aktif cevap bulunduysa...
        if known_answers:
            print(f"Hafızada {len(known_answers)} aktif cevap bulundu: Soru='{last_user_message_text[:30]}...'")
            # Cevap listesinden rastgele birini seç!
            chosen_answer = random.choice(known_answers)['answer']
            # Seçilen cevabı gönder, 'is_known' = True
            return jsonify({"response": chosen_answer, "is_known": True})

        # --- ADIM 2: HAFIZADA YOKSA, GEMINI'YE SORALIM (Tüm Geçmişle) ---
        print(f"Aktif cevap hafızada yok, Gemini'ye soruluyor...")
        
        gemini_history = conversation_history[:-1] # Son kullanıcı mesajı hariç

        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(last_user_message_text)

        generated_text = ""
        is_filtered = False

        try:
            generated_text = response.text
        except ValueError:
            generated_text = "Üzgünüm, bu isteğiniz güvenlik filtrelerimize takıldı veya model bir cevap üretemedi."
            is_filtered = True
            try: print(f"Filtreleme Sebebi: {response.prompt_feedback}")
            except Exception: pass
        except Exception as e:
            # Bu, 429 Kota Hatasını da yakalayabilir (flash-lite'da olmamalı ama garanti olsun)
            if "ResourceExhausted" in str(e) or "429" in str(e):
                print(f"!!! KOTA AŞILDI: {e}") 
                generated_text = "Çok hızlı sordun! Lütfen bir dakika bekleyip tekrar dene."
                is_filtered = True # Buton çıkmasın
            else:
                print(f"Gemini cevabı işlerken HATA: {e}")
                generated_text = "Modelden geçerli bir cevap alınamadı."
                is_filtered = True
        
        # is_known = is_filtered (Filtrelendiyse veya hata aldıysa True, buton çıkmasın)
        return jsonify({"response": generated_text, "is_known": is_filtered })

    except sqlite3.Error as e:
        print(f"Veritabanını okurken HATA oluştu: {e}")
        return jsonify({"response": "Hafızayı kontrol ederken bir sorun oluştu.", "is_known": True}), 500
    except Exception as e:
        print(f"Asistan cevabı işlerken beklenmedik HATA oluştu: {e}")
        traceback.print_exc()
        return jsonify({"response": "Beklenmedik bir hata oluştu. Lütfen tekrar deneyin.", "is_known": True}), 500
    finally:
        if conn:
            conn.close()

# Öğrenme yolu (Birden fazla cevaba izin verecek şekilde güncellendi)
@app.route('/api/learn', methods=['POST'])
def learn():
    data = request.get_json()
    question = data.get('question')
    answer = data.get('answer')

    if not question or not answer:
        return jsonify({"status": "error", "message": "Eksik bilgi."}), 400

    conn = None
    try:
        conn = get_db_connection()
        if not conn: raise sqlite3.Error("DB bağlantısı yok.")

        # Normal INSERT yapıyoruz (UNIQUE index zaten aynı soru-cevabı engeller)
        # Yeni eklenen cevap otomatik olarak is_active=1 olacak (DEFAULT 1)
        conn.execute('INSERT INTO knowledge (question, answer) VALUES (?, ?)',
                     (question, answer))
        conn.commit()
        print(f"Öğrenildi (Yeni Cevap): Soru='{question[:30]}...'")
        return jsonify({"status": "learned"})

    except sqlite3.IntegrityError:
         # UNIQUE index hatası: Bu soru-cevap zaten var demektir.
         # Belki pasifti, tekrar aktif yapalım (Gelişmiş)
         print(f"Bu cevap zaten biliniyor, 'is_active' 1 yapılıyor: Soru='{question[:30]}...'")
         try:
             conn.execute('UPDATE knowledge SET is_active = 1 WHERE question = ? AND answer = ?', (question, answer))
             conn.commit()
             return jsonify({"status": "re-activated"}) # Zaten biliniyordu, tekrar aktif edildi
         except Exception as e:
             print(f"Tekrar aktif ederken hata: {e}")
             return jsonify({"status": "already_known"}) # Zaten biliniyordu
    except sqlite3.Error as e:
        print(f"Veritabanına kaydederken HATA oluştu: {e}")
        return jsonify({"status": "error", "message": "Veritabanı hatası."}), 500
    except Exception as e:
        print(f"Öğrenme sırasında beklenmedik HATA oluştu: {e}")
        return jsonify({"status": "error", "message": "Sunucu hatası."}), 500
    finally:
        if conn: conn.close()

# Unutma yolu (Artık SİLMEZ, PASİF YAPAR ve HEM SORU HEM CEVAP alır)
@app.route('/api/forget', methods=['POST'])
def forget():
    data = request.get_json()
    question = data.get('question')
    answer = data.get('answer') # Artık hangi cevabın silineceğini de alıyoruz

    if not question or not answer:
        return jsonify({"status": "error", "message": "Eksik bilgi (soru veya cevap)."}), 400

    conn = None
    try:
        conn = get_db_connection()
        if not conn: raise sqlite3.Error("DB bağlantısı yok.")

        # Sadece belirtilen soru-cevap çiftini pasif yap (UPDATE)
        cursor = conn.execute('UPDATE knowledge SET is_active = 0 WHERE question = ? AND answer = ?',
                              (question, answer))
        conn.commit()

        if cursor.rowcount > 0:
            print(f"Pasif Yapıldı: Soru='{question[:30]}...' Cevap='{answer[:30]}...'")
            return jsonify({"status": "marked_as_inactive"})
        else:
            print(f"Pasif yapma isteği alındı ama soru-cevap çifti bulunamadı.")
            return jsonify({"status": "not_found"})

    except sqlite3.Error as e:
        print(f"Veritabanında güncellerken HATA oluştu: {e}")
        return jsonify({"status": "error", "message": "Veritabanı hatası."}), 500
    except Exception as e:
        print(f"Unutma sırasında beklenmedik HATA oluştu: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Sunucu hatası."}), 500
    finally:
        if conn: conn.close()

# Uygulamayı çalıştır
if __name__ == '__main__':
    app.run(debug=True)