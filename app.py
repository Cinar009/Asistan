# ----------------------------------------------------
# Asistan Projesi V12.2 - FAZ 5.3 (NİHAİ SÜRÜM)
# (Tüm Sohbetler DB'de + Tam God Mode Panel)
# (Tüm Hatalar ve Girintileme Düzeltildi)
# ----------------------------------------------------

import os
import atexit
import google.generativeai as genai
# Gerekli tüm Flask modülleri
from flask import Flask, request, jsonify, render_template, Response, session, redirect, url_for, flash
from functools import wraps 
from dotenv import load_dotenv
import traceback 
import random
import json
import time
from datetime import datetime
import pytz
import requests
import psycopg
from psycopg.rows import dict_row
import math
from werkzeug.security import generate_password_hash, check_password_hash

# .env dosyasındaki API anahtarlarını yükle
load_dotenv()

# Flask web uygulamasını başlat
app = Flask(__name__)

# --- OTURUM (SESSION) İÇİN GİZLİ ANAHTAR ---
app.secret_key = os.getenv("SECRET_KEY")
if not app.secret_key:
    print("!!! KRİTİK HATA: SECRET_KEY bulunamadı! .env dosyanızı kontrol edin.")
    app.secret_key = 'gecici_bir_anahtar_lutfen_degistir_bunu' 

# --- VERİTABANI KODLARI (PostgreSQL) ---
DATABASE_URL = os.getenv("DATABASE_URL") 
if not DATABASE_URL:
    print("!!! KRİTİK HATA: DATABASE_URL bulunamadı! .env dosyanızı veya Render ayarlarınızı kontrol edin.")

def get_db_connection():
    try:
        conn = psycopg.connect(DATABASE_URL)
        return conn
    except psycopg.OperationalError as e:
        print(f"Veritabanı bağlantı HATASI: {e}")
        return None

# Veritabanını ve tabloyu ilk çalıştırmada oluşturan fonksiyon (V12.1 DÜZELTİLDİ)
def init_db():
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                
                # --- V1.0 - V9.1 Tablosu (Hafıza) ---
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS knowledge (
                        id SERIAL PRIMARY KEY, question TEXT NOT NULL, answer TEXT NOT NULL,
                        is_active INTEGER DEFAULT 1, timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_question_answer ON knowledge (question, answer)')
                print("V9.1: 'knowledge' tablosu kontrol edildi/oluşturuldu.")
                
                # --- YENİ V12.0: Kullanıcı Yönetim Tabloları ---
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY, email TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL, is_active INTEGER DEFAULT 1,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                print("V12.0: 'users' tablosu kontrol edildi/oluşturuldu.")

                cur.execute('''
                    CREATE TABLE IF NOT EXISTS chats (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        chat_title TEXT NOT NULL,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                print("V12.0: 'chats' tablosu kontrol edildi/oluşturuldu.")

                cur.execute('''
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id SERIAL PRIMARY KEY,
                        chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
                        role TEXT NOT NULL, content TEXT NOT NULL,
                        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                print("V12.0: 'chat_messages' tablosu kontrol edildi/oluşturuldu.")
                
                # --- V12.1 DÜZELTMESİ: ANA TABLOLARI ÖNCE COMMIT ET (Kaydet) ---
                conn.commit()
                print("V12.1: Ana tablolar (knowledge, users, chats, messages) başarıyla commit edildi.")
                
                # --- V9.1: 'is_strict' Sütununu AYRI BİR İŞLEMDE Ekle ---
                try:
                    cur.execute('ALTER TABLE knowledge ADD COLUMN is_strict INTEGER DEFAULT 0')
                    print("V9.1: 'is_strict' sütunu başarıyla eklendi.")
                    conn.commit() 
                except psycopg.errors.DuplicateColumn:
                    print("V9.1: 'is_strict' sütunu zaten mevcut, atlanıyor.")
                    conn.rollback() 
                except Exception as e:
                    print(f"V9.1 'is_strict' eklenirken HATA: {e}")
                    conn.rollback() 
                
                print(f"Kalıcı PostgreSQL veritabanı başarıyla başlatıldı (V12.1 Kullanıcı Altyapısı).")
        
        except psycopg.Error as e:
            print(f"Veritabanı tablo oluşturma/güncelleme HATASI: {e}")
            conn.rollback() 
        finally:
            conn.close()
    else:
        print(f"Kalıcı PostgreSQL veritabanına bağlanılamadı.")

init_db()
# --- VERİTABANI KODLARI BİTİŞ ---

# --- API YAPILANDIRMASI ---
try:
    google_api_key = os.getenv("GOOGLE_API_KEY")
    weather_api_key = os.getenv("WEATHER_API_KEY") 
    if not google_api_key: raise ValueError("Hata: GOOGLE_API_KEY bulunamadı...")
    if not weather_api_key: print("UYARI: WEATHER_API_KEY bulunamadı. Hava durumu özelliği çalışmayacak.")
        
    genai.configure(api_key=google_api_key)
    system_instruction = """
Sen Asistan adında, samimi, doğal ve yardımcı bir yapay zeka asistanısın. Kullanıcının sorularına net ve doğrudan cevap ver. Sohbet etmeyi sevdiğini belli et.
ÖNEMLİ KURAL: Eğer kullanıcı SADECE ve DOĞRUDAN senin kim olduğunu, kökenini, kim tarafından yapıldığını veya geliştirildiğini sorarsa (örneğin: "seni kim yaptı?", "geliştiricin kim?", "nereden geldin?" gibi), şu cevabı ver: "Ben, Çınar Yalçıner adlı bağımsız bir geliştirici tarafından geliştirildim."
Diğer TÜM durumlarda (örneğin kullanıcı nasılsın, naber diyorsa, başka bir şey soruyorsa veya sohbet ediyorsa) KESİNLİKLE geliştiricinden veya nasıl yapıldığından BAHSETME. Sadece sorulan soruya veya sohbetin akışına odaklan.
"""
    model = genai.GenerativeModel( 'gemini-2.5-flash-lite', system_instruction=system_instruction )
    print("Gemini modeli ('gemini-2.5-flash-lite') başarıyla yüklendi (Kişisel Asistan kimliğiyle!).")
except Exception as e:
    print(f"!!! KRİTİK HATA: Gemini API yapılandırılamadı. Hata Detayı: {e}")
    model = None
# --- API YAPILANDIRMASI BİTİŞ ---

# --- ARAÇLAR ---
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
# --- ARAÇLAR BİTTİ ---


# --- KULLANICI GİRİŞ DECORATOR'Ü (V12.2 GÜVENLİK DÜZELTMELİ) ---
def user_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Bilet (session) var mı?
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({"error": "Yetkisiz Erişim. Lütfen giriş yapın."}), 401
            flash('Bu sayfayı görmek için lütfen giriş yapın.', 'error')
            return redirect(url_for('login'))
        
        # 2. (YENİ) Bilet HÂLÂ GEÇERLİ Mİ? (Veritabanını kontrol et)
        conn = None
        try:
            conn = get_db_connection()
            if not conn:
                flash('Veritabanı hatası, giriş durumu doğrulanamadı.', 'error')
                return redirect(url_for('login'))

            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute('SELECT is_active FROM users WHERE id = %s', (session['user_id'],))
                user_status = cur.fetchone()
            
            # 3. Kullanıcı silinmişse veya DONDURULMUŞSA...
            if user_status is None or user_status['is_active'] == 0:
                # Dondurulan kullanıcının biletini (session) iptal et
                session.pop('user_id', None)
                session.pop('user_email', None)
                
                if request.path.startswith('/api/'):
                    return jsonify({"error": "Hesabınız dondurulmuştur. Lütfen çıkış yapın."}), 401
                flash('Hesabınız bir yönetici tarafından donduruldu.', 'error')
                return redirect(url_for('login'))

        except Exception as e:
            print(f"user_login_required decorator HATA: {e}")
            traceback.print_exc()
            flash('Oturum doğrulanırken bir hata oluştu.', 'error')
            return redirect(url_for('login'))
        finally:
            if conn:
                conn.close()

        # Her şey yolundaysa, kullanıcıyı içeri al
        return f(*args, **kwargs)
    return decorated_function
# --- Bitiş ---

# --- ANA SAYFA VE KULLANICI SİSTEMİ ---
@app.route('/')
@user_login_required  
def index():
    user_email = session.get('user_email', 'Kullanıcı')
    return render_template('index.html', user_email=user_email)
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            flash('Lütfen tüm alanları doldurun.', 'error')
            return redirect(url_for('login'))
        conn = None
        try:
            conn = get_db_connection()
            if not conn:
                flash('Veritabanı bağlantı hatası.', 'error')
                return redirect(url_for('login'))
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute('SELECT * FROM users WHERE email = %s', (email,))
                user = cur.fetchone()
            if user is None:
                flash('Bu e-postaya kayıtlı bir kullanıcı bulunamadı.', 'error')
                return redirect(url_for('login'))
            if not check_password_hash(user['password_hash'], password):
                flash('Girdiğiniz şifre yanlış.', 'error')
                return redirect(url_for('login'))
            if user['is_active'] == 0:
                flash('Hesabınız bir yönetici tarafından dondurulmuştur.', 'error')
                return redirect(url_for('login'))
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            print(f"Kullanıcı girişi başarılı: {user['email']} (ID: {user['id']})")
            return redirect(url_for('index'))
        except Exception as e:
            print(f"Giriş sırasında HATA: {e}")
            traceback.print_exc()
            flash(f'Beklenmedik bir hata oluştu: {e}', 'error')
            return redirect(url_for('login'))
        finally:
            if conn:
                conn.close()
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if not email or not password or not confirm_password:
            flash('Lütfen tüm alanları doldurun.', 'error')
            return redirect(url_for('register'))
        if password != confirm_password:
            flash('Girdiğiniz şifreler uyuşmuyor.', 'error')
            return redirect(url_for('register'))
        password_hash = generate_password_hash(password)
        conn = None
        try:
            conn = get_db_connection()
            if not conn:
                flash('Veritabanı bağlantı hatası, lütfen tekrar deneyin.', 'error')
                return redirect(url_for('register'))
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO users (email, password_hash) VALUES (%s, %s)',
                    (email, password_hash)
                )
                conn.commit()
            flash('Hesabınız başarıyla oluşturuldu! Şimdi giriş yapabilirsiniz.', 'success')
            return redirect(url_for('login')) 
        except psycopg.errors.UniqueViolation as e:
            flash('Bu e-posta adresi zaten kayıtlı.', 'error')
            conn.rollback()
            return redirect(url_for('register'))
        except Exception as e:
            print(f"Kayıt sırasında HATA: {e}")
            traceback.print_exc()
            conn.rollback()
            flash(f'Beklenmedik bir hata oluştu: {e}', 'error')
            return redirect(url_for('register'))
        finally:
            if conn:
                conn.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_email', None)
    flash('Başarıyla çıkış yaptınız.', 'success')
    return redirect(url_for('login'))
# --- KULLANICI SİSTEMİ BİTİŞ ---

# --- ASİSTAN ANA API YOLLARI ---

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
    known_answer_context = None 
    
    try:
        lower_prompt = last_user_message_text.lower()
        
        # ARAÇ 1: SAAT/TARİH
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
        
        # ARAÇ 2: HAVA DURUMU
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

        # ADIM 3: HAFIZA KONTROLÜ (V9.1 HİBRİT BEYİN)
        conn = get_db_connection()
        if not conn: raise psycopg.Error("Veritabanı bağlantısı kurulamadı.")
        
        known_answers = [] 
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('SELECT answer, is_strict FROM knowledge WHERE question = %s AND is_active = 1', (last_user_message_text,))
            known_answers = cur.fetchall()
        
        if known_answers:
            chosen_answer_data = random.choice(known_answers)
            if chosen_answer_data and chosen_answer_data['is_strict'] == 1:
                print(f"V9.1: Hafızada 'Birebir Oku' (strict) cevap bulundu. Direkt gönderiliyor.")
                chosen_answer_text = chosen_answer_data['answer']
                for char in chosen_answer_text: 
                    yield f"data: {json.dumps({'response_chunk': char, 'is_known': True})}\n\n"; 
                    time.sleep(0.01)
                yield "data: [DONE]\n\n"; 
                return
            elif chosen_answer_data:
                print(f"V9.1: Hafızada 'İlham Al' (non-strict) cevap bulundu. İlham kaynağı olarak kullanılacak.")
                known_answer_context = chosen_answer_data['answer']
        
        # ADIM 4: GEMINI'YE SORMA
        final_prompt_to_gemini = "" 
        if known_answer_context:
            print(f"V9.0: Gemini'ye hafızadan ilham alarak soruluyor...")
            final_prompt_to_gemini = f"""Kullanıcı sana şunu sordu: "{last_user_message_text}"
Benim (Asistan'ın) hafızamda bu konuyla ilgili önceden kaydedilmiş şöyle bir bilgi var:
"{known_answer_context}"
LÜTFEN, bu bilgiyi kullanarak (doğruluğunu esas alarak) ama birebir kopyalamadan, daha doğal, akıcı ve gerekirse güncel bir dille cevap ver. 
Cevabın, sadece kullanıcının sorusuna doğrudan bir yanıt olsun."""
        else:
            print(f"Aktif cevap hafızada yok, Gemini'ye soruluyor (streaming)...")
            final_prompt_to_gemini = last_user_message_text

        gemini_history = history[:-1]; chat = model.start_chat(history=gemini_history)
        response_stream = chat.send_message(final_prompt_to_gemini, stream=True)
        
        for chunk in response_stream:
            try:
                if chunk.text:
                    for char in chunk.text: 
                        yield f"data: {json.dumps({'response_chunk': char, 'is_known': False})}\n\n"; 
                        time.sleep(0.01) 
            except ValueError:
                yield f"data: {json.dumps({'error': 'Üzgünüm, bu isteğiniz güvenlik filtrelerimize takıldı.', 'is_known': True})}\n\n"; break
            except Exception as e: 
                print(f"Stream chunk işlerken hata: {e}")
        yield "data: [DONE]\n\n" 
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

# /api/assist rotası
@app.route('/api/assist', methods=['POST'])
@user_login_required 
def assist():
    data = request.get_json()
    conversation_history = data.get('history')
    return Response(generate_response_stream(conversation_history), mimetype='text/event-stream')

# --- V12.0 - FAZ 4.2: Sohbetleri Veritabanından Çekme ---
@app.route('/api/get_chats', methods=['GET'])
@user_login_required
def get_chats():
    user_id = session['user_id']
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Veritabanı bağlantı hatası."}), 500
        
        chats_response = {}
        active_chat_id = None
        
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                'SELECT * FROM chats WHERE user_id = %s ORDER BY updated_at DESC',
                (user_id,)
            )
            user_chats = cur.fetchall()
            
            if not user_chats:
                print(f"V12.0: Kullanıcı {user_id} için sohbet bulunamadı, yeni sohbet oluşturuluyor.")
                new_title = "Yeni Sohbet"
                cur.execute(
                    'INSERT INTO chats (user_id, chat_title, updated_at) VALUES (%s, %s, CURRENT_TIMESTAMP) RETURNING id, chat_title',
                    (user_id, new_title)
                )
                new_chat = cur.fetchone()
                conn.commit()
                
                chat_id_str = f"db_{new_chat['id']}"
                chats_response[chat_id_str] = {
                    'db_id': new_chat['id'],
                    'title': new_chat['chat_title'],
                    'history': [] 
                }
                active_chat_id = chat_id_str
            
            else:
                print(f"V12.0: Kullanıcı {user_id} için {len(user_chats)} adet sohbet bulundu.")
                for i, chat in enumerate(user_chats):
                    chat_id_str = f"db_{chat['id']}" 
                    if i == 0:
                        active_chat_id = chat_id_str 
                    
                    cur.execute(
                        'SELECT role, content FROM chat_messages WHERE chat_id = %s ORDER BY timestamp ASC',
                        (chat['id'],)
                    )
                    messages = cur.fetchall()
                    
                    history_list = []
                    for msg in messages:
                        history_list.append({
                            'role': msg['role'],
                            'parts': [{'text': msg['content']}]
                        })
                    
                    chats_response[chat_id_str] = {
                        'db_id': chat['id'],
                        'title': chat['chat_title'],
                        'history': history_list
                    }

        return jsonify({"chats": chats_response, "active_chat_id": active_chat_id})

    except Exception as e:
        print(f"/api/get_chats HATA: {e}")
        traceback.print_exc()
        if conn: conn.rollback()
        return jsonify({"error": "Sohbetler alınırken bir hata oluştu."}), 500
    finally:
        if conn:
            conn.close()
# --- V12.0 Faz 4.2 Bitiş ---

# --- V12.0 - FAZ 4.3: Sohbetleri Veritabanına Yazma ---
@app.route('/api/new_chat', methods=['POST'])
@user_login_required
def new_chat():
    user_id = session['user_id']
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Veritabanı bağlantı hatası."}), 500
        
        with conn.cursor(row_factory=dict_row) as cur:
            new_title = "Yeni Sohbet"
            cur.execute(
                'INSERT INTO chats (user_id, chat_title, updated_at) VALUES (%s, %s, CURRENT_TIMESTAMP) RETURNING id, chat_title',
                (user_id, new_title)
            )
            new_chat = cur.fetchone()
            conn.commit()
        
        chat_id_str = f"db_{new_chat['id']}"
        print(f"V12.0: Kullanıcı {user_id} için yeni sohbet (ID: {chat_id_str}) DB'de oluşturuldu.")

        return jsonify({
            "chat_id": chat_id_str,
            "chat_data": {
                'db_id': new_chat['id'],
                'title': new_chat['chat_title'],
                'history': []
            }
        })

    except Exception as e:
        print(f"/api/new_chat HATA: {e}")
        traceback.print_exc()
        if conn: conn.rollback()
        return jsonify({"error": "Yeni sohbet oluşturulurken bir hata oluştu."}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/delete_chat', methods=['POST'])
@user_login_required
def delete_chat():
    user_id = session['user_id']
    data = request.get_json()
    chat_db_id = data.get('chat_db_id') 

    if not chat_db_id:
        return jsonify({"error": "Sohbet ID'si eksik."}), 400

    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Veritabanı bağlantı hatası."}), 500
        
        with conn.cursor() as cur:
            cur.execute(
                'DELETE FROM chats WHERE id = %s AND user_id = %s RETURNING id',
                (chat_db_id, user_id)
            )
            deleted_chat = cur.fetchone()
            conn.commit()
        
        if deleted_chat:
            print(f"V12.0: Kullanıcı {user_id}, sohbet (ID: {chat_db_id}) DB'den sildi.")
            return jsonify({"status": "success"})
        else:
            print(f"V12.0: Kullanıcı {user_id}, sohbet (ID: {chat_db_id}) silmeye çalıştı AMA yetkisi yok/sohbet yok.")
            return jsonify({"error": "Sohbet bulunamadı veya silme yetkiniz yok."}), 404

    except Exception as e:
        print(f"/api/delete_chat HATA: {e}")
        traceback.print_exc()
        if conn: conn.rollback()
        return jsonify({"error": "Sohbet silinirken bir hata oluştu."}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/save_messages', methods=['POST'])
@user_login_required
def save_messages():
    user_id = session['user_id']
    data = request.get_json()
    chat_db_id = data.get('chat_db_id')
    user_message = data.get('user_message')
    model_message = data.get('model_message')
    needs_title_update = data.get('needs_title_update', False)

    if not chat_db_id or not user_message or model_message is None:
        return jsonify({"error": "Eksik veri."}), 400

    conn = None
    new_title_to_return = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Veritabanı bağlantı hatası."}), 500
        
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                'SELECT id FROM chats WHERE id = %s AND user_id = %s',
                (chat_db_id, user_id)
            )
            chat = cur.fetchone()

            if not chat:
                return jsonify({"error": "Sohbet bulunamadı veya yazma yetkiniz yok."}), 404
            
            cur.execute(
                'INSERT INTO chat_messages (chat_id, role, content) VALUES (%s, %s, %s)',
                (chat_db_id, 'user', user_message)
            )
            cur.execute(
                'INSERT INTO chat_messages (chat_id, role, content) VALUES (%s, %s, %s)',
                (chat_db_id, 'model', model_message)
            )
            cur.execute(
                'UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = %s',
                (chat_db_id,)
            )

            if needs_title_update:
                new_title = (user_message[:25] + '...') if len(user_message) > 28 else user_message
                cur.execute(
                    'UPDATE chats SET chat_title = %s WHERE id = %s',
                    (new_title, chat_db_id)
                )
                new_title_to_return = new_title
                print(f"V12.0: Sohbet {chat_db_id} başlığı '{new_title}' olarak güncellendi.")

            conn.commit()

        return jsonify({"status": "success", "new_title": new_title_to_return})

    except Exception as e:
        print(f"/api/save_messages HATA: {e}")
        traceback.print_exc()
        if conn: conn.rollback()
        return jsonify({"error": "Mesajlar kaydedilirken bir hata oluştu."}), 500
    finally:
        if conn:
            conn.close()
# --- V12.0 Faz 4.3 Bitiş ---

# Admin'in 'knowledge' tablosunu yönettiği API'lar
@app.route('/api/learn', methods=['POST'])
@user_login_required 
def learn():
    data = request.get_json(); question = data.get('question'); answer = data.get('answer')
    if not question or not answer: return jsonify({"status": "error", "message": "Eksik bilgi."}), 400
    conn = None
    try:
        conn = get_db_connection();
        if not conn: raise psycopg.Error("DB bağlantısı yok.")
        with conn.cursor() as cur:
            cur.execute('INSERT INTO knowledge (question, answer, is_active, is_strict) VALUES (%s, %s, 1, 0)', (question, answer))
        conn.commit(); print(f"Öğrenildi: Soru='{question[:30]}...' (V9.1 non-strict)")
        return jsonify({"status": "learned"})
    except psycopg.errors.UniqueViolation as e:
        print(f"Bu cevap zaten biliniyor: Soru='{question[:30]}...'")
        try:
            with conn.cursor() as cur:
                cur.execute('UPDATE knowledge SET is_active = 1 WHERE question = %s AND answer = %s', (question, answer))
            conn.commit(); return jsonify({"status": "re-activated"})
        except Exception as e: print(f"Tekrar aktif ederken hata: {e}"); return jsonify({"status": "already_known"})
    except psycopg.Error as e:
        print(f"Veritabanına kaydederken HATA oluştu: {e}"); return jsonify({"status": "error", "message": "Veritabanı hatası."}), 500
    except Exception as e:
        print(f"Öğrenme sırasında HATA oluştu: {e}"); return jsonify({"status": "error", "message": "Sunucu hatası."}), 500
    finally:
        if conn: conn.close()

@app.route('/api/forget', methods=['POST'])
@user_login_required 
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
                if existing_entry[1] == 1: 
                    cur.execute('UPDATE knowledge SET is_active = 0 WHERE id = %s', (existing_entry[0],))
                    conn.commit()
                    print(f"Pasif Yapıldı (Mevcuttu): Soru='{question[:30]}...'")
                    return jsonify({"status": "marked_as_inactive"})
                else:
                    print(f"Zaten Pasif: Soru='{question[:30]}...'")
                    return jsonify({"status": "already_inactive"})
            else:
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
# --- ASİSTAN ANA API YOLLARI BİTİŞ ---

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

@app.route('/admin/dashboard')
@login_required 
def admin_dashboard():
    conn = None
    all_knowledge = []
    search_term = request.args.get('search', '').strip() 
    page = request.args.get('page', 1, type=int)        
    ITEMS_PER_PAGE = 20                                 
    offset = (page - 1) * ITEMS_PER_PAGE                
    stats = {'total': 0, 'active': 0, 'inactive': 0}
    total_items_found = 0
    total_pages = 1
    try:
        conn = get_db_connection()
        if not conn:
            flash('Hata: Veritabanı bağlantısı kurulamadı.', 'error')
            return render_template('admin_dashboard.html', knowledge=all_knowledge, stats=stats, 
                                   current_page=page, total_pages=total_pages, search_term=search_term, total_items_found=0)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                SELECT 
                    COUNT(*) AS total,
                    COUNT(CASE WHEN is_active = 1 THEN 1 END) AS active,
                    COUNT(CASE WHEN is_active = 0 THEN 1 END) AS inactive
                FROM knowledge
            ''')
            stats = cur.fetchone()
            base_query = ' FROM knowledge '
            where_clause = ''
            params = [] 
            if search_term:
                where_clause = ' WHERE (question ILIKE %s OR answer ILIKE %s) '
                params.append(f'%{search_term}%')
                params.append(f'%{search_term}%')
            count_query = 'SELECT COUNT(*) AS total_found' + base_query + where_clause
            cur.execute(count_query, tuple(params)) 
            total_items_found = cur.fetchone()['total_found']
            total_pages = math.ceil(total_items_found / ITEMS_PER_PAGE)
            if total_pages == 0: total_pages = 1 
            data_query = '''
                SELECT id, question, answer, is_active, is_strict, timestamp,
                       TO_CHAR(timestamp, 'DD.MM.YYYY HH24:MI') AS formatted_timestamp
            ''' + base_query + where_clause + ' ORDER BY timestamp DESC LIMIT %s OFFSET %s '
            params.append(ITEMS_PER_PAGE)
            params.append(offset)
            cur.execute(data_query, tuple(params))
            all_knowledge = cur.fetchall()
        return render_template('admin_dashboard.html', 
                               knowledge=all_knowledge, 
                               stats=stats,
                               current_page=page, 
                               total_pages=total_pages, 
                               search_term=search_term,
                               total_items_found=total_items_found)
    except Exception as e:
        print(f"Admin dashboard hatası: {e}")
        traceback.print_exc()
        flash(f'Veritabanından veri çekerken bir hata oluştu: {e}', 'error')
        return render_template('admin_dashboard.html', knowledge=all_knowledge, stats=stats, 
                               current_page=page, total_pages=total_pages, search_term=search_term, total_items_found=0)
    finally:
        if conn:
            conn.close()

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
            if request.method == 'POST':
                new_question = request.form.get('question')
                new_answer = request.form.get('answer')
                is_strict_val = 1 if request.form.get('is_strict') == 'on' else 0 
                if not new_question or not new_answer:
                    flash('Soru ve Cevap alanları boş bırakılamaz.', 'error')
                    cur.execute('SELECT * FROM knowledge WHERE id = %s', (id,))
                    item = cur.fetchone()
                    return render_template('admin_edit.html', item=item)
                cur.execute('UPDATE knowledge SET question = %s, answer = %s, is_strict = %s WHERE id = %s',
                            (new_question, new_answer, is_strict_val, id))
                conn.commit()
                flash(f"ID {id} numaralı kayıt başarıyla güncellendi.", 'success')
                print(f"Admin: ID {id} düzenlendi.")
                return redirect(url_for('admin_dashboard')) 
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

@app.route('/admin/add', methods=['GET', 'POST'])
@login_required 
def admin_add():
    if request.method == 'POST':
        question = request.form.get('question')
        answer = request.form.get('answer')
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
            conn.rollback() 
            return render_template('admin_add.html') 
        except Exception as e:
            print(f"Admin add hatası: {e}")
            traceback.print_exc()
            conn.rollback() 
            flash(f'Bir hata oluştu: {e}', 'error')
            return render_template('admin_add.html') 
        finally:
            if conn:
                conn.close()
    return render_template('admin_add.html')

@app.route('/admin/delete/<int:id>')
@login_required 
def admin_delete(id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            flash('Hata: Veritabanı bağlantısı kurulamadı.', 'error')
            return redirect(url_for('admin_dashboard'))
        with conn.cursor() as cur:
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
    return redirect(url_for('admin_dashboard'))

# --- YENİ V12.0 - FAZ 5.1: God Mode Kullanıcı Paneli ---
@app.route('/admin/users')
@login_required 
def admin_users():
    conn = None
    all_users = []
    try:
        conn = get_db_connection()
        if not conn:
            flash('Hata: Veritabanı bağlantısı kurulamadı.', 'error')
            return render_template('admin_users.html', users=all_users)

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, email, is_active, TO_CHAR(created_at, 'DD.MM.YYYY HH24:MI') AS formatted_date FROM users ORDER BY created_at DESC"
            )
            all_users = cur.fetchall()
        
        return render_template('admin_users.html', users=all_users)

    except Exception as e:
        print(f"Admin users hatası: {e}")
        traceback.print_exc()
        flash(f'Bir hata oluştu: {e}', 'error')
        return render_template('admin_users.html', users=all_users)
    finally:
        if conn:
            conn.close()

# --- YENİ V12.0 - FAZ 5.2: Kullanıcıyı Dondur/Aktif Et ---
@app.route('/admin/toggle_user/<int:user_id>')
@login_required 
def admin_toggle_user(user_id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            flash('Hata: Veritabanı bağlantısı kurulamadı.', 'error')
            return redirect(url_for('admin_users'))

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('SELECT is_active FROM users WHERE id = %s', (user_id,))
            user = cur.fetchone()
            
            if user:
                new_status = 1 - user['is_active'] 
                cur.execute('UPDATE users SET is_active = %s WHERE id = %s', (new_status, user_id))
                conn.commit()
                status_text = "Donduruldu" if new_status == 0 else "Aktif Edildi"
                flash(f"Kullanıcı (ID: {user_id}) durumu '{status_text}' olarak güncellendi.", 'success')
                print(f"Admin: Kullanıcı ID {user_id} durumu değiştirildi -> {status_text}")
            else:
                flash(f'Hata: ID {user_id} numaralı kullanıcı bulunamadı.', 'error')

    except Exception as e:
        print(f"Admin toggle_user hatası: {e}")
        traceback.print_exc()
        flash(f'Bir hata oluştu: {e}', 'error')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('admin_users'))

# --- YENİ V12.0 - FAZ 5.3: God Mode Sohbet Görüntüleyici ---
@app.route('/admin/view_chats/<int:user_id>')
@login_required # Sadece Adminler erişebilir
def admin_view_chats(user_id):
    conn = None
    user = None
    chats_list = [] # Kullanıcının sohbetlerini ve mesajlarını tutacak liste
    try:
        conn = get_db_connection()
        if not conn:
            flash('Hata: Veritabanı bağlantısı kurulamadı.', 'error')
            return redirect(url_for('admin_users'))

        with conn.cursor(row_factory=dict_row) as cur:
            
            # 1. Hangi kullanıcıya baktığımızı bulalım
            cur.execute('SELECT id, email FROM users WHERE id = %s', (user_id,))
            user = cur.fetchone()
            
            if not user:
                flash(f'Hata: ID {user_id} numaralı kullanıcı bulunamadı.', 'error')
                return redirect(url_for('admin_users'))
            
            # 2. O kullanıcının tüm sohbetlerini çek (en yeniden eskiye)
            cur.execute(
                'SELECT id, chat_title, updated_at FROM chats WHERE user_id = %s ORDER BY updated_at DESC',
                (user_id,)
            )
            chats = cur.fetchall()
            
            # 3. Her sohbetin içine o sohbete ait mesajları doldur
            for chat in chats:
                cur.execute(
                    '''
                    SELECT role, content, TO_CHAR(timestamp, 'DD.MM.YY HH24:MI') AS formatted_time 
                    FROM chat_messages 
                    WHERE chat_id = %s ORDER BY timestamp ASC
                    ''',
                    (chat['id'],)
                )
                messages = cur.fetchall()
                # 'chat' sözlüğüne (dict) yeni bir 'messages' anahtarı ekle
                chat['messages'] = messages
                chats_list.append(chat)
        
        # Verileri (user bilgisi ve chats_list) yeni HTML sayfamıza gönder
        return render_template('admin_view_chats.html', user=user, chats_list=chats_list)

    except Exception as e:
        print(f"Admin view_chats hatası: {e}")
        traceback.print_exc()
        flash(f'Bir hata oluştu: {e}', 'error')
        return redirect(url_for('admin_users'))
    finally:
        if conn:
            conn.close()
# --- ADMİN PANELİ YOLLARI BİTİŞ ---

# ... (admin_view_chats() fonksiyonu burada biter) ...

# --- YENİ V12.0 - FAZ 5.4: God Mode Şifre Sıfırlama ---
@app.route('/admin/reset_password/<int:user_id>', methods=['GET', 'POST'])
@login_required # Sadece Adminler erişebilir
def admin_reset_password(user_id):
    conn = None
    user = None
    try:
        conn = get_db_connection()
        if not conn:
            flash('Hata: Veritabanı bağlantısı kurulamadı.', 'error')
            return redirect(url_for('admin_users'))

        with conn.cursor(row_factory=dict_row) as cur:

            # --- POST (Formu Kaydetme) ---
            if request.method == 'POST':
                new_password = request.form.get('new_password')

                if not new_password or len(new_password) < 6:
                    flash('Şifre en az 6 karakter olmalıdır.', 'error')
                    # Hata olursa, formu tekrar göstermek için user bilgisini tekrar çekmemiz lazım
                    cur.execute('SELECT id, email FROM users WHERE id = %s', (user_id,))
                    user = cur.fetchone()
                    if not user: return redirect(url_for('admin_users')) # Kullanıcı yoksa geri at
                    return render_template('admin_reset_password.html', user=user)

                # YENİ ŞİFREYİ GÜVENLE HASH'LE
                password_hash = generate_password_hash(new_password)

                # Kullanıcının şifresini veritabanında GÜNCELLE
                cur.execute('UPDATE users SET password_hash = %s WHERE id = %s',
                            (password_hash, user_id))
                conn.commit()

                flash(f"Kullanıcının (ID: {user_id}) şifresi başarıyla güncellendi.", 'success')
                print(f"Admin: Kullanıcı ID {user_id} şifresi sıfırlandı.")
                return redirect(url_for('admin_users')) # Kullanıcı listesine geri dön

            # --- GET (Formu Gösterme) ---
            # Veritabanından o ID'ye ait kullanıcıyı bul (sadece e-postayı göstermek için)
            cur.execute('SELECT id, email FROM users WHERE id = %s', (user_id,))
            user = cur.fetchone()

            if user:
                # 'admin_reset_password.html' sayfasını o user verisiyle doldur
                return render_template('admin_reset_password.html', user=user)
            else:
                flash(f'Hata: ID {user_id} numaralı kullanıcı bulunamadı.', 'error')
                return redirect(url_for('admin_users'))

    except Exception as e:
        print(f"Admin reset_password hatası: {e}")
        traceback.print_exc()
        flash(f'Bir hata oluştu: {e}', 'error')
        return redirect(url_for('admin_users'))
    finally:
        if conn:
            conn.close()
# --- V12.0 Faz 5.4 Bitiş ---

# --- ADMİN PANELİ YOLLARI BİTİŞ ---

# Uygulamayı çalıştır
if __name__ == '__main__':
    app.run(debug=True, threaded=True)