# ----------------------------------------------------
# Asistan Projesi V9.1 - HİBRİT BEYİN (Strict/İlham)
# (Kalıcı PostgreSQL + Tam Admin Paneli + Akıllı Araçlar)
# (Girintileme ve Boşluklar Temizlendi)
# ----------------------------------------------------

import os
import atexit
import google.generativeai as genai
# Gerekli tüm Flask modülleri
from flask import Flask, request, jsonify, render_template, Response, session, redirect, url_for, flash
from functools import wraps # Admin Paneli için
from dotenv import load_dotenv
import traceback # Hata ayıklama için
import random    # Rastgele cevap seçmek için
import json      # Veri fışkırtmak için
import time      # Akıcı yazma efekti için
from datetime import datetime # Saat/Tarih aracı için
import pytz # Saat/Tarih aracı için
import requests # Hava durumu için
import psycopg # YENİ TERCÜMAN (PostgreSQL için)
from psycopg.rows import dict_row # Sonuçları sözlük gibi almak için

# .env dosyasındaki API anahtarlarını yükle
load_dotenv()

# Flask web uygulamasını başlat
app = Flask(__name__)

# --- OTURUM (SESSION) İÇİN GİZLİ ANAHTAR ---
app.secret_key = os.getenv("SECRET_KEY")
if not app.secret_key:
    print("!!! KRİTİK HATA: SECRET_KEY bulunamadı! .env dosyanızı kontrol edin.")
    app.secret_key = 'gecici_bir_anahtar_lutfen_degistir_bunu' # Acil durum anahtarı

# --- VERİTABANI KODLARI (PostgreSQL) ---
DATABASE_URL = os.getenv("DATABASE_URL") # Render'dan gizli adresi al
if not DATABASE_URL:
    print("!!! KRİTİK HATA: DATABASE_URL bulunamadı! .env dosyanızı veya Render ayarlarınızı kontrol edin.")

# Veritabanı bağlantısını oluşturma fonksiyonu
def get_db_connection():
    try:
        conn = psycopg.connect(DATABASE_URL)
        return conn
    except psycopg.OperationalError as e:
        print(f"Veritabanı bağlantı HATASI: {e}")
        return None

# Veritabanını ve tabloyu ilk çalıştırmada oluşturan fonksiyon (V9.1 GÜNCELLENDİ)
def init_db():
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # Ana Tablo
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS knowledge (
                        id SERIAL PRIMARY KEY,
                        question TEXT NOT NULL, 
                        answer TEXT NOT NULL,
                        is_active INTEGER DEFAULT 1,
                        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                # Aynı SORU-CEVAP çiftinin tekrar eklenmesini önlemek için UNIQUE index
                cur.execute('''
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_question_answer 
                    ON knowledge (question, answer)
                ''')

                # --- YENİ V9.1: 'is_strict' Sütununu Ekle ---
                try:
                    # 'is_strict' sütununu ekle (varsayılan: 0, yani "İlham Al")
                    cur.execute('''
                        ALTER TABLE knowledge
                        ADD COLUMN is_strict INTEGER DEFAULT 0
                    ''')
                    print("V9.1: 'is_strict' sütunu başarıyla eklendi.")
                    # Sütun yeni eklendiği için commit edilmesi gerekiyor
                    conn.commit()
                except psycopg.errors.DuplicateColumn:
                    # Hata vermez, sütun zaten varsa atlar
                    print("V9.1: 'is_strict' sütunu zaten mevcut, atlanıyor.")
                    conn.rollback() # Mevcut işlemi geri al ki devam edebilelim
                except Exception as e:
                    print(f"V9.1 'is_strict' eklenirken HATA: {e}")
                    conn.rollback() # Hata olursa geri al
                # --- V9.1 Bitiş ---

                # Geri kalan (ilk iki execute) işlemlerini commit et
                conn.commit() 
                print(f"Kalıcı PostgreSQL veritabanı başarıyla başlatıldı (V9.1 Hibrit Beyin).")
        except psycopg.Error as e:
            print(f"Veritabanı tablo oluşturma/güncelleme HATASI: {e}")
            conn.rollback() # Hata olursa tüm işlemleri geri al
        finally:
            conn.close()
    else:
        print(f"Kalıcı PostgreSQL veritabanına bağlanılamadı.")

init_db()
# --- VERİTABANI KODLARI BİTİŞ ---

# --- API YAPILANDIRMASI (Weather Key Eklendi) ---
try:
    google_api_key = os.getenv("GOOGLE_API_KEY")
    weather_api_key = os.getenv("WEATHER_API_KEY") # Hava durumu anahtarı
    if not google_api_key: raise ValueError("Hata: GOOGLE_API_KEY bulunamadı...")
    if not weather_api_key: print("UYARI: WEATHER_API_KEY bulunamadı. Hava durumu özelliği çalışmayacak.")
        
    genai.configure(api_key=google_api_key)
    system_instruction = """
Sen Asistan adında, samimi, doğal ve yardımcı bir yapay zeka asistanısın. Kullanıcının sorularına net ve doğrudan cevap ver. Sohbet etmeyi sevdiğini belli et.
ÖNEMLİ KURAL: Eğer kullanıcı SADECE ve DOĞRUDAN senin kim olduğunu, kökenini, kim tarafından yapıldığını veya geliştirildiğini sorarsa (örneğin: "seni kim yaptı?", "geliştiricin kim?", "nereden geldin?" gibi), şu cevabı ver: "Ben, Çınar Yalçıner adlı bağımsız bir geliştirici tarafından geliştirildim."
Diğer TÜM durumlarda (örneğin kullanıcı nasılsın, naber diyorsa, başka bir şey soruyorsa veya sohbet ediyorsa) KESİNLİKLE geliştiricinden veya nasıl yapıldığından BAHSETME. Sadece sorulan soruya veya sohbetin akışına odaklan.
Selamlaşmalara ("naber", "nasılsın" gibi) kısa ve samimi cevaplar ver (örneğin: "İyiyim, teşekkürler! Sen nasılsın?", "Harika gidiyor, sana nasıl yardımcı olabilirim?").
'Yaratıldım' veya 'kuruldum' gibi kelimeler yerine 'geliştirildim' veya 'programlandım' gibi ifadeleri sadece sorulduğunda kullan.
"""
    model = genai.GenerativeModel( 'gemini-2.5-flash-lite', system_instruction=system_instruction )
    print("Gemini modeli ('gemini-2.5-flash-lite') başarıyla yüklendi (Kişisel Asistan kimliğiyle!).")
except Exception as e:
    print(f"!!! KRİTİK HATA: Gemini API yapılandırılamadı. Hata Detayı: {e}")
    model = None
# --- API YAPILANDIRMASI BİTİŞ ---

# --- HAVA DURUMU ARACI ---
def get_weather(city_name):
    if not weather_api_key: return "Üzgünüm, hava durumu servisine şu an erişemiyorum (API anahtarı eksik)."
    try:
        base_url = "http://api.openweathermap.org/data/2.5/weather"; params = { "q": city_name, "appid": weather_api_key, "units": "metric", "lang": "tr" }; response = requests.get(base_url, params=params, timeout=5); response.raise_for_status() 
        data = response.json(); description = data['weather'][0]['description']; temp = round(data['main']['temp']); city_display = data['name']
        return f"{city_display} için hava durumu şu an {temp}°C derece ve {description}."
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 401: return "Hava durumu servisi için kimlik doğrulanamadı. (API Anahtarı hatası)"
        if err.response.status_code == 404: return f"Üzgünüm, '{city_name}' adında bir şehir bulamadım."
        else: return f"Hava durumu servisine bağlanırken bir hata oluştu (Kod: {err.response.status_code})."
    except requests.exceptions.RequestException as e: print(f"Hava durumu API'sine bağlanırken hata: {e}"); return "Hava durumu servisine şu anda ulaşılamıyor."
    except Exception as e: print(f"Hava durumu JSON işlerken hata: {e}"); return "Hava durumu bilgisi alınamadı."
# --- ARAÇ BİTTİ ---

# --- API YOLLARI (ROUTES) ---

@app.route('/')
def index():
    return render_template('index.html')

# --- YENİ V9.1 - Hafızayı "İlham Kaynağı" Yapan Fonksiyon ---
def generate_response_stream(history):
    if not model:
        yield f"data: {json.dumps({'error': 'Yapay zeka modeli şu an kullanılamıyor.', 'is_known': True})}\n\n"
        yield "data: [DONE]\n\n"; return

    last_user_message_text = ""
    if history and history[-1]['role'] == 'user':
        if 'parts' in history[-1] and history[-1]['parts'] and 'text' in history[-1]['parts'][0]:
            last_user_message_text = history[-1]['parts'][0]['text']
    if not last_user_message_text:
        yield f"data: {json.dumps({'error': 'Son kullanıcı mesajı alınamadı.', 'is_known': True})}\n\n"
        yield "data: [DONE]\n\n"; return

    conn = None
    known_answer_context = None # V9.0: Hafızadaki cevabı saklamak için yeni değişken
    
    try:
        lower_prompt = last_user_message_text.lower()
        
        # --- ARAÇ 1: SAAT/TARİH KONTROLÜ ---
        time_keywords = ['saat kaç', 'saat', 'zaman', 'tarih ne', 'bugünün tarihi', 'ayın kaçı', 'bugün günlerden ne']
        if any(keyword in lower_prompt for keyword in time_keywords):
            print("Saat/Tarih aracı tetiklendi.")
            tz_istanbul = pytz.timezone('Europe/Istanbul'); now = datetime.now(tz_istanbul)
            if 'tarih' in lower_prompt or 'ayın kaçı' in lower_prompt: chosen_answer = f"Elbette, bugün {now.strftime('%d.%m.%Y')}."
            elif 'günlerden ne' in lower_prompt: chosen_answer = f"Bugün günlerden {now.strftime('%A')}, {now.strftime('%d.%m.%Y')}."
            elif 'saat' in lower_prompt or 'zaman' in lower_prompt: chosen_answer = f"Tabii, şu an saat {now.strftime('%H:%M')}."
            else: chosen_answer = f"Elbette, tarih {now.strftime('%d.%m.%Y')} ve saat {now.strftime('%H:%M')}."
            for char in chosen_answer: yield f"data: {json.dumps({'response_chunk': char, 'is_known': True})}\n\n"; time.sleep(0.01)
            yield "data: [DONE]\n\n"; return
        
        # --- ARAÇ 2: HAVA DURUMU KONTROLÜ (Akıllı Versiyon) ---
        weather_keywords = ['hava durumu', 'hava nasıl', 'kaç derece']
        if any(keyword in lower_prompt for keyword in weather_keywords):
            print("Hava durumu aracı tetiklendi. Şehir adı Gemini'ye soruluyor...")
            city_extraction_prompt = f"Kullanıcının şu cümlesinden bir şehir adı çıkar: '{last_user_message_text}'. Sadece şehrin adını yaz. Eğer şehir adı yoksa 'None' yaz. Şehir adını cümlenin içinden çıkar, ekleme yapma."
            city_response = model.generate_content(city_extraction_prompt)
            city_name = city_response.text.strip().replace("'", "").replace('"', "").replace(".","")
            
            if city_name and city_name.lower() != 'none' and len(city_name) > 2:
                print(f"Gemini tarafından şehir bulundu: {city_name}")
                weather_report = get_weather(city_name)
            else:
                print("Gemini şehir adı bulamadı. Kullanıcıya sorulacak.")
                weather_report = "Elbette, hangi şehir için hava durumu bilgisi istersiniz?"

            for char in weather_report:
                yield f"data: {json.dumps({'response_chunk': char, 'is_known': True})}\n\n"
                time.sleep(0.01)
            yield "data: [DONE]\n\n"; return
        # --- ARAÇLAR BİTTİ ---

        # --- ADIM 3: HAFIZA KONTROLÜ (V9.1 HİBRİT BEYİN GÜNCELLEMESİ) ---
        conn = get_db_connection()
        if not conn: raise psycopg.Error("Veritabanı bağlantısı kurulamadı.")
        
        known_answers = [] # Boş liste olarak başlat
        with conn.cursor(row_factory=dict_row) as cur:
            # V9.1: 'is_strict' sütununu da çek
            cur.execute('SELECT answer, is_strict FROM knowledge WHERE question = %s AND is_active = 1', (last_user_message_text,))
            known_answers = cur.fetchall()
        
        if known_answers:
            # Birden fazla cevap varsa birini rastgele seç
            chosen_answer_data = random.choice(known_answers)
            
            # --- V9.1: HİBRİT BEYİN KONTROLÜ ---
            if chosen_answer_data and chosen_answer_data['is_strict'] == 1:
                # 'Birebir Oku' işaretliyse, V2.0 gibi direkt fışkırt ve bitir
                print(f"V9.1: Hafızada 'Birebir Oku' (strict) cevap bulundu. Direkt gönderiliyor.")
                chosen_answer_text = chosen_answer_data['answer']
                for char in chosen_answer_text: 
                    yield f"data: {json.dumps({'response_chunk': char, 'is_known': True})}\n\n"; 
                    time.sleep(0.01)
                yield "data: [DONE]\n\n"; 
                return # <<< ÖNEMLİ: Fonksiyonu burada bitir
            elif chosen_answer_data:
                # 'Birebir Oku' işaretli DEĞİLSE, V9.0 gibi ilham al
                print(f"V9.1: Hafızada 'İlham Al' (non-strict) cevap bulundu. İlham kaynağı olarak kullanılacak.")
                known_answer_context = chosen_answer_data['answer']
                # ... ve ADIM 4'e (Gemini'ye Sorma) devam et...
        
        # --- ADIM 4: GEMINI'YE SORMA (V9.0 GÜNCELLEMESİ) ---
        
        final_prompt_to_gemini = "" # V9.0: Gemini'ye gidecek son komut

        if known_answer_context:
            # Hafızada bir şey bulduysak, "ilham komutunu" oluştur:
            print(f"V9.0: Gemini'ye hafızadan ilham alarak soruluyor...")
            final_prompt_to_gemini = f"""Kullanıcı sana şunu sordu: "{last_user_message_text}"

Benim (Asistan'ın) hafızamda bu konuyla ilgili önceden kaydedilmiş şöyle bir bilgi var:
"{known_answer_context}"

LÜTFEN, bu bilgiyi kullanarak (doğruluğunu esas alarak) ama birebir kopyalamadan, daha doğal, akıcı ve gerekirse güncel bir dille cevap ver. 
Cevabın, sadece kullanıcının sorusuna doğrudan bir yanıt olsun."""
        
        else:
            # Hafızada bir şey bulamadıysak, soruyu normal sor:
            print(f"Aktif cevap hafızada yok, Gemini'ye soruluyor (streaming)...")
            final_prompt_to_gemini = last_user_message_text

        # Gemini ile sohbeti başlat ve komutu gönder
        gemini_history = history[:-1]; chat = model.start_chat(history=gemini_history)
        response_stream = chat.send_message(final_prompt_to_gemini, stream=True)
        
        for chunk in response_stream:
            try:
                if chunk.text:
                    # Gelen cevap YENİ bir cevap olduğu için is_known: False gönderiyoruz.
                    for char in chunk.text: 
                        yield f"data: {json.dumps({'response_chunk': char, 'is_known': False})}\n\n"; 
                        time.sleep(0.01) # Akıcılık için küçük bir gecikme
            except ValueError:
                yield f"data: {json.dumps({'error': 'Üzgünüm, bu isteğiniz güvenlik filtrelerimize takıldı.', 'is_known': True})}\n\n"; break
            except Exception as e: 
                print(f"Stream chunk işlerken hata: {e}")
                
        yield "data: [DONE]\n\n" # Her durumda stream'i bitir

    except google.api_core.exceptions.ResourceExhausted as e:
        print(f"!!! KOTA AŞILDI: {e}"); error_message = "Çok hızlı sordun! Lütfen biraz bekleyip tekrar dene."
        yield f"data: {json.dumps({'error': error_message, 'is_known': True})}\n\n"; yield "data: [DONE]\n\n"
    except psycopg.Error as e:
        print(f"Veritabanını okurken HATA oluştu: {e}")
        yield f"data: {json.dumps({'error': 'Hafızayı kontrol ederken bir sorun oluştu.', 'is_known': True})}\n\n"; yield "data: [DONE]\n\n"
    except Exception as e:
        print(f"Asistan cevabı işlerken beklenmedik HATA oluştu: {e}"); traceback.print_exc()
        yield f"data: {json.dumps({'error': 'Beklenmedik bir hata oluştu.', 'is_known': True})}\n\n"; yield "data: [DONE]\n\n"
    finally:
        if conn:
            conn.close()
# --- V9.1 Fonksiyon Bitişi ---

# /api/assist rotası
@app.route('/api/assist', methods=['POST'])
def assist():
    data = request.get_json()
    conversation_history = data.get('history')
    return Response(generate_response_stream(conversation_history), mimetype='text/event-stream')

# Öğrenme yolu (/api/learn) (V9.1 GÜNCELLENDİ)
@app.route('/api/learn', methods=['POST'])
def learn():
    data = request.get_json(); question = data.get('question'); answer = data.get('answer')
    if not question or not answer: return jsonify({"status": "error", "message": "Eksik bilgi."}), 400
    conn = None
    try:
        conn = get_db_connection();
        if not conn: raise psycopg.Error("DB bağlantısı yok.")
        with conn.cursor() as cur:
            # V9.1: Yeni kayıtlar varsayılan olarak 'ilham al' (is_strict=0) modunda eklenir
            cur.execute('INSERT INTO knowledge (question, answer, is_active, is_strict) VALUES (%s, %s, 1, 0)', (question, answer))
        conn.commit(); print(f"Öğrenildi: Soru='{question[:30]}...' (V9.1 non-strict)")
        return jsonify({"status": "learned"})
    except psycopg.errors.UniqueViolation as e:
        print(f"Bu cevap zaten biliniyor: Soru='{question[:30]}...'")
        try:
            with conn.cursor() as cur:
                # Zaten biliniyorsa, onu 'Aktif' yapalım
                cur.execute('UPDATE knowledge SET is_active = 1 WHERE question = %s AND answer = %s', (question, answer))
            conn.commit(); return jsonify({"status": "re-activated"})
        except Exception as e: print(f"Tekrar aktif ederken hata: {e}"); return jsonify({"status": "already_known"})
    except psycopg.Error as e:
        print(f"Veritabanına kaydederken HATA oluştu: {e}"); return jsonify({"status": "error", "message": "Veritabanı hatası."}), 500
    except Exception as e:
        print(f"Öğrenme sırasında HATA oluştu: {e}"); return jsonify({"status": "error", "message": "Sunucu hatası."}), 500
    finally:
        if conn: conn.close()

# Unutma yolu (/api/forget) (V9.1 GÜNCELLENDİ)
@app.route('/api/forget', methods=['POST'])
def forget():
    data = request.get_json(); question = data.get('question'); answer = data.get('answer')
    if not question or not answer: return jsonify({"status": "error", "message": "Eksik bilgi."}), 400
    
    conn = None
    try:
        conn = get_db_connection();
        if not conn: raise psycopg.Error("DB bağlantısı yok.")
        
        with conn.cursor() as cur:
            cur.execute('SELECT id, is_active FROM knowledge WHERE question = %s AND answer = %s', (question, answer))
            existing_entry = cur.fetchone()

            if existing_entry:
                if existing_entry[1] == 1: # Zaten aktifse
                    cur.execute('UPDATE knowledge SET is_active = 0 WHERE id = %s', (existing_entry[0],))
                    conn.commit()
                    print(f"Pasif Yapıldı (Mevcuttu): Soru='{question[:30]}...'")
                    return jsonify({"status": "marked_as_inactive"})
                else:
                    print(f"Zaten Pasif: Soru='{question[:30]}...'")
                    return jsonify({"status": "already_inactive"})
            else:
                # YENİ MANTIK: Kayıt veritabanında HİÇ yoktu. 'Pasif' (is_active = 0) olarak EKLE.
                # V9.1: 'is_strict' = 0 olarak ekle (ilham al)
                cur.execute('INSERT INTO knowledge (question, answer, is_active, is_strict) VALUES (%s, %s, 0, 0)', 
                            (question, answer))
                conn.commit()
                print(f"Hatalı Olarak Öğrenildi (Yeni Eklendi): Soru='{question[:30]}...'")
                return jsonify({"status": "learned_as_inactive"})

    except psycopg.Error as e:
        print(f"Veritabanında unutma/ekleme sırasında HATA oluştu: {e}"); 
        return jsonify({"status": "error", "message": "Veritabanı hatası."}), 500
    except Exception as e:
        print(f"Unutma sırasında HATA oluştu: {e}"); traceback.print_exc(); 
        return jsonify({"status": "error", "message": "Sunucu hatası."}), 500
    finally:
        if conn: conn.close()

# --- ADMİN PANELİ YOLLARI BAŞLANGIÇ ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Bu sayfayı görmek için giriş yapmalısınız.')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
def admin_index():
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_logged_in' in session:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        password_attempt = request.form.get('password')
        admin_password = os.getenv("ADMIN_PASSWORD")
        if not admin_password:
            flash('Hata: Sunucu tarafında ADMIN_PASSWORD ayarlanmamış.')
            return redirect(url_for('admin_login'))
        if password_attempt == admin_password:
            session['admin_logged_in'] = True
            session.permanent = True 
            print("Admin girişi başarılı!")
            return redirect(url_for('admin_dashboard'))
        else:
            print(f"Admin girişi başarısız.")
            flash('Yanlış şifre!')
            return redirect(url_for('admin_login'))
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Başarıyla çıkış yaptınız.')
    return redirect(url_for('admin_login'))

# --- Admin Dashboard (V7.2 İstatistikli ve V9.1 GÜNCELLENDİ) ---
@app.route('/admin/dashboard')
@login_required 
def admin_dashboard():
    conn = None
    all_knowledge = []
    stats = {'total': 0, 'active': 0, 'inactive': 0} 
    try:
        conn = get_db_connection()
        if not conn:
            flash('Hata: Veritabanı bağlantısı kurulamadı.', 'error')
            return render_template('admin_dashboard.html', knowledge=all_knowledge, stats=stats)

        with conn.cursor(row_factory=dict_row) as cur:
            # İstatistikleri Çek
            cur.execute('''
                SELECT 
                    COUNT(*) AS total,
                    COUNT(CASE WHEN is_active = 1 THEN 1 END) AS active,
                    COUNT(CASE WHEN is_active = 0 THEN 1 END) AS inactive
                FROM knowledge
            ''')
            stats = cur.fetchone()
            
            # Ana Veriyi Çek (V9.1: 'is_strict' sütununu da al)
            cur.execute('''
                SELECT id, question, answer, is_active, is_strict, timestamp,
                       TO_CHAR(timestamp, 'DD.MM.YYYY HH24:MI') AS formatted_timestamp
                FROM knowledge 
                ORDER BY timestamp DESC
            ''')
            all_knowledge = cur.fetchall()
        
        return render_template('admin_dashboard.html', knowledge=all_knowledge, stats=stats)

    except Exception as e:
        print(f"Admin dashboard hatası: {e}")
        traceback.print_exc()
        flash(f'Veritabanından veri çekerken bir hata oluştu: {e}', 'error')
        return render_template('admin_dashboard.html', knowledge=all_knowledge, stats=stats)
    finally:
        if conn:
            conn.close()
    
# Durumu Aktif/Pasif Yap
@app.route('/admin/toggle/<int:id>')
@login_required 
def admin_toggle_active(id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            flash('Hata: Veritabanı bağlantısı kurulamadı.', 'error')
            return redirect(url_for('admin_dashboard'))
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('SELECT is_active FROM knowledge WHERE id = %s', (id,))
            item = cur.fetchone()
            if item:
                new_status = 1 - item['is_active'] 
                cur.execute('UPDATE knowledge SET is_active = %s WHERE id = %s', (new_status, id))
                conn.commit()
                status_text = "Aktif" if new_status == 1 else "Pasif"
                flash(f"ID {id} numaralı cevabın durumu '{status_text}' olarak güncellendi.", 'success')
                print(f"Admin: ID {id} durumu değiştirildi -> {status_text}")
            else:
                flash(f'Hata: ID {id} numaralı cevap bulunamadı.', 'error')
    except Exception as e:
        print(f"Admin toggle hatası: {e}")
        traceback.print_exc()
        flash(f'Bir hata oluştu: {e}', 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('admin_dashboard'))

# Kaydı Düzenle (V9.1 GÜNCELLENDİ)
@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@login_required 
def admin_edit(id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            flash('Hata: Veritabanı bağlantısı kurulamadı.', 'error')
            return redirect(url_for('admin_dashboard'))

        with conn.cursor(row_factory=dict_row) as cur:
            # --- POST (Formu Kaydetme) ---
            if request.method == 'POST':
                new_question = request.form.get('question')
                new_answer = request.form.get('answer')
                # V9.1 Checkbox değerini al
                is_strict_val = 1 if request.form.get('is_strict') == 'on' else 0 

                if not new_question or not new_answer:
                    flash('Soru ve Cevap alanları boş bırakılamaz.', 'error')
                    cur.execute('SELECT * FROM knowledge WHERE id = %s', (id,))
                    item = cur.fetchone()
                    return render_template('admin_edit.html', item=item)

                # V9.1: Veritabanını 'is_strict' ile GÜNCELLE
                cur.execute('UPDATE knowledge SET question = %s, answer = %s, is_strict = %s WHERE id = %s',
                            (new_question, new_answer, is_strict_val, id))
                conn.commit()

                flash(f"ID {id} numaralı kayıt başarıyla güncellendi.", 'success')
                print(f"Admin: ID {id} düzenlendi.")
                return redirect(url_for('admin_dashboard')) 

            # --- GET (Formu Gösterme) ---
            # V9.1: 'is_strict' dahil tüm verileri çek
            cur.execute('SELECT * FROM knowledge WHERE id = %s', (id,))
            item = cur.fetchone()
            
            if item:
                return render_template('admin_edit.html', item=item)
            else:
                flash(f'Hata: ID {id} numaralı cevap bulunamadı.', 'error')
                return redirect(url_for('admin_dashboard'))

    except Exception as e:
        print(f"Admin edit hatası: {e}")
        traceback.print_exc()
        flash(f'Bir hata oluştu: {e}', 'error')
        return redirect(url_for('admin_dashboard'))
    finally:
        if conn:
            conn.close()

# Yeni Kayıt Ekle (V9.1 GÜNCELLENDİ)
@app.route('/admin/add', methods=['GET', 'POST'])
@login_required 
def admin_add():
    if request.method == 'POST':
        question = request.form.get('question')
        answer = request.form.get('answer')
        # V9.1 Checkbox değerini al
        is_strict_val = 1 if request.form.get('is_strict') == 'on' else 0 
        
        if not question or not answer:
            flash('Soru ve Cevap alanları boş bırakılamaz.', 'error')
            return render_template('admin_add.html') 

        conn = None
        try:
            conn = get_db_connection()
            if not conn:
                flash('Hata: Veritabanı bağlantısı kurulamadı.', 'error')
                return render_template('admin_add.html')

            with conn.cursor() as cur:
                # V9.1: Yeni kaydı 'is_strict' değeriyle ekle
                cur.execute(
                    'INSERT INTO knowledge (question, answer, is_active, is_strict) VALUES (%s, %s, 1, %s)',
                    (question, answer, is_strict_val)
                )
                conn.commit()
            
            flash(f"Yeni kayıt başarıyla hafızaya eklendi.", 'success')
            print(f"Admin: Yeni kayıt eklendi -> Soru='{question[:30]}...' (Strict: {is_strict_val})")
            return redirect(url_for('admin_dashboard')) 

        except psycopg.errors.UniqueViolation as e:
            flash(f'Hata: Bu soru ve cevap çifti zaten hafızada mevcut.', 'error')
            conn.rollback() # Hatayı geri al
            return render_template('admin_add.html') 
        except Exception as e:
            print(f"Admin add hatası: {e}")
            traceback.print_exc()
            conn.rollback() # Hatayı geri al
            flash(f'Bir hata oluştu: {e}', 'error')
            return render_template('admin_add.html') 
        finally:
            if conn:
                conn.close()

    # GET (Formu Gösterme)
    return render_template('admin_add.html')

# --- ADMİN PANELİ YOLLARI BİTİŞ ---

# --- YENİ V9.2 - Kaydı Kalıcı Olarak Silme ---
@app.route('/admin/delete/<int:id>')
@login_required # Sadece adminler erişebilir
def admin_delete(id):
    # Bu tehlikeli bir işlem olduğu için, formdan gelen bir onayı
    # (normalde POST ile yaparız) biz JavaScript ile (Adım 2'de) halledeceğiz.

    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            flash('Hata: Veritabanı bağlantısı kurulamadı.', 'error')
            return redirect(url_for('admin_dashboard'))

        with conn.cursor() as cur:
            # Kaydı TAMAMEN SİL
            cur.execute('DELETE FROM knowledge WHERE id = %s', (id,))
            conn.commit()

        flash(f"ID {id} numaralı kayıt başarıyla ve kalıcı olarak silindi.", 'success')
        print(f"Admin: ID {id} kalıcı olarak SİLİNDİ.")

    except Exception as e:
        print(f"Admin delete hatası: {e}")
        traceback.print_exc()
        flash(f'Bir hata oluştu: {e}', 'error')
    finally:
        if conn:
            conn.close()

    # İşlem bitince ana panele geri dön
    return redirect(url_for('admin_dashboard'))
# --- V9.2 Bitiş ---

# Uygulamayı çalıştır
if __name__ == '__main__':
    app.run(debug=True, threaded=True)