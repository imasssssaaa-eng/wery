import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, InputMediaPhoto
import sqlite3, threading, time

print("⚙️ Запуск скрипта... Загрузка библиотек")
BOT_TOKEN = '8708256332:AAFOMWD5QtdsjtS-LCL9PL23mnM0neOrg4k'
ADMIN_IDS = [7283380508]  # Твой ID

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
BOT_USERNAME = bot.get_me().username

# Блокировка для защиты от краша базы данных при одновременной загрузке фото (альбомов)
db_lock = threading.Lock()

print("⚙️ Подключение к базе данных...")
conn = sqlite3.connect('bot_database.db', check_same_thread=False)
cursor = conn.cursor()

with db_lock:
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 0, spent INTEGER DEFAULT 0, referrer_id INTEGER, refs_count INTEGER DEFAULT 0, joined_date TEXT);
        CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, gifts_given INTEGER DEFAULT 0, auto_add_amount INTEGER DEFAULT 0, auto_add_interval INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS task_applications (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, photos TEXT, status TEXT DEFAULT 'pending');
        CREATE TABLE IF NOT EXISTS join_requests (user_id INTEGER PRIMARY KEY);
    ''')

    for col in ["username TEXT", "refs_count INTEGER DEFAULT 0", "spent INTEGER DEFAULT 0", "joined_date TEXT"]:
        try: cursor.execute(f"ALTER TABLE users ADD COLUMN {col}")
        except sqlite3.OperationalError: pass

    cursor.execute("INSERT OR IGNORE INTO settings (id, gifts_given, auto_add_amount, auto_add_interval) VALUES (1, 0, 0, 0)")
    conn.commit()
print("⚙️ База данных готова.")

GIFTS = {
    "🎭 Маска": "https://ibb.co/hx6dgvj6", "💼 Рюкзак": "https://ibb.co/SX64sfWh", "📅 Календарь": "https://ibb.co/9mNGyLsk",
    "🍭 Лолипоп": "https://ibb.co/3YpBsrgT", "🦩 Фламинго": "https://ibb.co/DPgbPFtV", "🥥 Кокос": "https://ibb.co/LdB5r5ty",
    "🥚 Яйцо": "https://ibb.co/HLjCQzqM", "🍦 Мороженое": "https://ibb.co/vB00C0y", "💩 Какашка": "https://ibb.co/Rp35KTpp",
    "🧁 Кекс": "https://ibb.co/nN6DF5HL", "🍀 Клевер": "https://ibb.co/20kG7Gpc", "🫙 Банка": "https://ibb.co/CNCGH6t",
    "🐍 Змея": "https://ibb.co/bMgXKh4m", "🍸 Коктейль": "https://ibb.co/xSx5TG33", "🕯 Свеча": "https://ibb.co/wZ4yPSD2",
    "🐒 Обезьяна": "https://ibb.co/tMjcdPGw", "🍄 Гриб": "https://ibb.co/1tCmj7zH", "🌸 Цветок": "https://ibb.co/yP3T8z3",
    "🎃 Тыква": "https://ibb.co/DfDWW87L", "👁 Глаз": "https://ibb.co/xqHhPsNp", "🧹 Метла": "https://ibb.co/4wrZmkwb",
    "🍜 Рамен": "https://ibb.co/mCQ1BrNV", "🗽 Свобода": "https://ibb.co/yFPjnGPg", "🧦 Носок": "https://ibb.co/JR8xGJyZ",
    "🐶 Редо": "https://ibb.co/6dyp5hz", "👜 Сетка": "https://ibb.co/tpDNL70Q", "⌚ Часы": "https://ibb.co/6RcbmsFv",
    "🚬 Сигара": "https://ibb.co/WvsnSYDk", "⛑ Шлем": "https://ibb.co/N2dMtGMH", "🧢 Кепка": "https://ibb.co/cKw8L5F0",
    "🍑 Персик": "https://ibb.co/BKGb64tK", "🐸 Лягушка": "https://ibb.co/0y65bHb2", "👳 Папаха": "https://ibb.co/Df4W9W0F",
    "🗿 Статуя Дурова": "https://ibb.co/DgmxvyB3", "💪 Бицепс": "https://ibb.co/WW2G5bjZ", "🤵 Оскар": "https://ibb.co/pBqQLDGq",
    "🧴 Духи": "https://ibb.co/Xk4985Zk", "📦 UFC": "https://ibb.co/DHz0p9fQ"
}
GIFTS_KEYS, user_photo_uploads = list(GIFTS.keys()), {}

def safe_edit(call, text, kb=None):
    try:
        if call.message.content_type == 'photo':
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, text, reply_markup=kb)
        else: bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception: pass

def get_kb(buttons, row_width=1):
    kb = InlineKeyboardMarkup(row_width=row_width)
    for text, data in buttons:
        if data.startswith("url:"): kb.add(InlineKeyboardButton(text, url=data[4:]))
        elif data.startswith("switch:"): kb.add(InlineKeyboardButton(text, switch_inline_query=data[7:]))
        else: kb.add(InlineKeyboardButton(text, callback_data=data))
    return kb

def auto_increment_gifts():
    while True:
        try:
            amount, interval = cursor.execute("SELECT auto_add_amount, auto_add_interval FROM settings WHERE id = 1").fetchone()
            if amount > 0 and interval > 0:
                with db_lock:
                    cursor.execute("UPDATE settings SET gifts_given = gifts_given + ? WHERE id = 1", (amount,))
                    conn.commit()
                time.sleep(interval)
            else: time.sleep(5)
        except Exception: time.sleep(5)

threading.Thread(target=auto_increment_gifts, daemon=True).start()

def send_main_menu(chat_id):
    gifts = cursor.execute("SELECT gifts_given FROM settings WHERE id = 1").fetchone()[0]
    text = (f"🧸 <b>Главное меню</b>\n\n🎁 Подарено подарков: <b>{gifts:,}</b>\n\nВ данном боте вы можете получить бесплатно подарки обычные и NFT.\nДля получения звезд выполняйте задания. За задания вы можете получить NFT подарки, а также звезды.\n\nВыберите категорию👇")
    bot.send_message(chat_id, text, reply_markup=get_kb([("🎁 Подарки", "menu_gifts"), ("🕹️ Игры", "menu_games"), ("👤 Профиль", "menu_profile"), ("⭐ Задание", "menu_tasks")]))

@bot.chat_join_request_handler()
def handle_join_request(message):
    try:
        with db_lock:
            cursor.execute("INSERT OR IGNORE INTO join_requests (user_id) VALUES (?)", (message.from_user.id,))
            conn.commit()
    except Exception: pass

@bot.message_handler(commands=['start'])
def start_cmd(message):
    u_id, u_name = message.from_user.id, message.from_user.username or "Без имени"
    args = message.text.split()
    ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != u_id else None
    
    if not cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (u_id,)).fetchone():
        with db_lock:
            cursor.execute("INSERT INTO users (user_id, username, referrer_id, balance, joined_date) VALUES (?, ?, ?, 0, date('now'))", (u_id, u_name, ref_id))
            if ref_id:
                cursor.execute("UPDATE users SET refs_count = refs_count + 1 WHERE user_id = ?", (ref_id,))
                try: bot.send_message(ref_id, "🎉 По вашей ссылке зарегистрировался новый пользователь! +1 к счетчику рефералов.")
                except: pass
            conn.commit()

    if not cursor.execute("SELECT user_id FROM join_requests WHERE user_id = ?", (u_id,)).fetchone():
        text = "⛔️ Вы должны быть подписанными на все каналы и выполнить задания!\n❗️ НЕ НУЖНО ждать принятия Вашей заявки в канал(ы)"
        return bot.send_message(message.chat.id, text, reply_markup=get_kb([("Спонсор", "url:https://t.me/+YLnbvrb46HA4Y2Uy"), ("✅Проверить", "check_sub")]))
    send_main_menu(message.chat.id)

@bot.message_handler(commands=['setgifts', 'autoincrement', 'refs', 'apps', 'approve', 'reject', 'users', 'список'])
def admin_commands(message):
    if message.from_user.id not in ADMIN_IDS: return
    cmd = message.text.split()
    command = cmd[0].lower()

    try:
        if command == '/список':
            text = ("🛠 <b>Список админ-команд:</b>\n\n🔸 <code>/users</code> — Статистика пользователей (за сегодня и за все время)\n🔸 <code>/setgifts [число]</code> — Установить количество подаренных подарков\n🔸 <code>/autoincrement [количество] [секунды]</code> — Включить автонакрутку подарков\n🔸 <code>/refs [ID]</code> — Посмотреть количество рефералов у пользователя\n🔸 <code>/apps</code> — Проверить новую заявку на задание (модерация)\n🔸 <code>/approve [ID заявки]</code> — Одобрить заявку (выдает 50 ⭐)\n🔸 <code>/reject [ID заявки] [Причина]</code> — Отклонить заявку\n🔸 <code>/список</code> — Показать это меню")
            bot.reply_to(message, text)
        elif command == '/users':
            t_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            d_users = cursor.execute("SELECT COUNT(*) FROM users WHERE joined_date = date('now')").fetchone()[0]
            bot.reply_to(message, f"👥 <b>Список пользователей в боте</b>\n\n📅 За сегодня: <b>{d_users:,}</b>\n🌍 За все время: <b>{t_users:,}</b>")
        elif command == '/setgifts' and len(cmd) == 2 and cmd[1].isdigit():
            with db_lock:
                cursor.execute("UPDATE settings SET gifts_given = ? WHERE id = 1", (int(cmd[1]),))
                conn.commit()
            bot.reply_to(message, f"✅ Количество подаренных подарков установлено на {cmd[1]}")
        elif command == '/autoincrement' and len(cmd) == 3 and cmd[1].isdigit() and cmd[2].isdigit():
            with db_lock:
                cursor.execute("UPDATE settings SET auto_add_amount=?, auto_add_interval=? WHERE id=1", (int(cmd[1]), int(cmd[2])))
                conn.commit()
            bot.reply_to(message, f"✅ Автопополнение включено: +{cmd[1]} подарков каждые {cmd[2]} секунд.")
        elif command == '/refs' and len(cmd) == 2 and cmd[1].isdigit():
            res = cursor.execute("SELECT refs_count FROM users WHERE user_id = ?", (int(cmd[1]),)).fetchone()
            bot.reply_to(message, f"👤 Пользователь {cmd[1]} пригласил {res[0]} рефералов." if res else "Пользователь не найден.")
        elif command == '/apps':
            app = cursor.execute("SELECT id, user_id, photos FROM task_applications WHERE status = 'pending' LIMIT 1").fetchone()
            if not app: return bot.reply_to(message, "📭 Нет новых заявок на модерацию.")
            bot.send_media_group(message.chat.id, [InputMediaPhoto(media=p) for p in app[2].split(',')])
            bot.send_message(message.chat.id, f"📝 <b>Заявка #{app[0]}</b> от пользователя <code>{app[1]}</code>\n\n✅ Одобрить: <code>/approve {app[0]}</code>\n❌ Отклонить: <code>/reject {app[0]} Причина отказа</code>")
        elif command == '/approve' and len(cmd) == 2 and cmd[1].isdigit():
            u_id = cursor.execute("SELECT user_id FROM task_applications WHERE id=? AND status='pending'", (int(cmd[1]),)).fetchone()
            if u_id:
                with db_lock:
                    cursor.execute("UPDATE task_applications SET status='approved' WHERE id=?", (int(cmd[1]),))
                    cursor.execute("UPDATE users SET balance = balance + 50 WHERE user_id = ?", (u_id[0],))
                    conn.commit()
                bot.reply_to(message, f"✅ Заявка #{cmd[1]} одобрена. Начислено 50 ⭐.")
                try: bot.send_message(u_id[0], "🎉 Ваша заявка по заданию одобрена! На ваш баланс начислено <b>50 ⭐</b>.")
                except: pass
            else: bot.reply_to(message, "Заявка не найдена или уже обработана.")
        elif command == '/reject' and len(cmd) >= 3 and cmd[1].isdigit():
            u_id = cursor.execute("SELECT user_id FROM task_applications WHERE id=? AND status='pending'", (int(cmd[1]),)).fetchone()
            if u_id:
                with db_lock:
                    cursor.execute("UPDATE task_applications SET status='rejected' WHERE id=?", (int(cmd[1]),))
                    conn.commit()
                bot.reply_to(message, f"❌ Заявка #{cmd[1]} отклонена.")
                try: bot.send_message(u_id[0], f"❌ Ваша заявка по заданию была отклонена модератором.\n\n<b>Причина:</b> {' '.join(cmd[2:])}")
                except: pass
            else: bot.reply_to(message, "Заявка не найдена или уже обработана.")
        else: bot.reply_to(message, "❌ <b>Команда введена неправильно!</b> Используйте /список")
    except Exception as e: bot.reply_to(message, f"⚠️ Ошибка: {e}")

@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout_query(pre_checkout_query):
    try:
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    except Exception: pass

@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    try:
        bot.send_message(message.chat.id, "✅ Оплата прошла успешно! Ваш подарок/услуга успешно получены.")
    except Exception: pass

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid, cid, mid, d = call.from_user.id, call.message.chat.id, call.message.message_id, call.data

    if d == "check_sub":
        if cursor.execute("SELECT user_id FROM join_requests WHERE user_id = ?", (uid,)).fetchone():
            bot.delete_message(cid, mid)
            send_main_menu(cid)
        else: bot.answer_callback_query(call.id, "❌ Вы не подписаны на каналы или не выполнили задания", show_alert=True)
    elif d == "menu_main":
        user_photo_uploads.pop(uid, None)
        gifts = cursor.execute("SELECT gifts_given FROM settings WHERE id = 1").fetchone()[0]
        text = f"🧸 <b>Главное меню</b>\n\n🎁 Подарено подарков: <b>{gifts:,}</b>\n\nВ данном боте вы можете получить бесплатно подарки обычные и NFT.\nДля получения звезд выполняйте задания. За задания вы можете получить NFT подарки, а также звезды.\n\nВыберите категорию👇"
        safe_edit(call, text, get_kb([("🎁 Подарки", "menu_gifts"), ("🕹️ Игры", "menu_games"), ("👤 Профиль", "menu_profile"), ("⭐ Задание", "menu_tasks")]))
    elif d == "menu_gifts":
        safe_edit(call, "🎁 <b>Подарки</b>\n\nВыберите категорию:", get_kb([("🌟 НФТ", "gifts_nft"), ("🧸 Обычные подарки", "gifts_regular"), ("💝 Бесплатные подарки", "gifts_free"), ("🔙 Назад", "menu_main")]))
    elif d == "gifts_nft":
        btns = [(f"{name} - 10⭐", f"nft_{i}") for i, name in enumerate(GIFTS_KEYS)] + [("💝 Бесплатный мишка", "gifts_free"), ("🔙 Назад", "menu_gifts")]
        safe_edit(call, "🌟 <b>Выберите НФТ подарок</b>", get_kb(btns))
    elif d.startswith("nft_"):
        idx = int(d.split("_")[1])
        name = GIFTS_KEYS[idx]
        text = f"🎁 <b>{name}</b>\n\n1️⃣ Нажмите кнопку ниже.\n2️⃣ Оплатите платное сообщение.\n3️⃣ После оплаты бот автоматически выдаст Вам подарок.\n\n⚡ Скриншоты не нужны — подтверждение срабатывает автоматически."
        bot.delete_message(cid, mid)
        bot.send_photo(cid, GIFTS[name], caption=text, reply_markup=get_kb([("Перейти к покупке ⬆️", f"url:https://t.me/Glft_free_nft?text={name}"), ("Оплатить со звезд ⭐", f"pay_balance_{idx}"), ("🔙 Назад", "gifts_nft")]))
    elif d == "gifts_regular":
        safe_edit(call, "🧸\nВыберете подарок", get_kb([("Обычный подарок - 3⭐", "buy_reg_3"), ("Подарок с подписью - 8⭐", "buy_reg_8"), ("💝 Бесплатный мишка", "gifts_free"), ("🔙 Назад", "menu_gifts")]))
    elif d == "gifts_free":
        refs = cursor.execute("SELECT refs_count FROM users WHERE user_id = ?", (uid,)).fetchone()[0]
        text = f"🧸 <b>БЕСПЛАТНЫЙ МИШКА</b> 🎁\n\nПриглашай друзей и получай мишку за каждые 5 рефералов! 🚀\n\n🔗 Ваша ссылка:\n<code>https://t.me/{BOT_USERNAME}?start={uid}</code>\n\n👥 Приглашено: <b>{refs}</b>\n🧸 Доступно мишек: <b>{refs // 5}</b>"
        safe_edit(call, text, get_kb([("📤 Поделиться ссылкой", f"url:https://t.me/share/url?url=https://t.me/{BOT_USERNAME}?start={uid}&text=Заходи%20и%20забирай%20подарки!"), ("🔙 Назад", "menu_gifts")]))
    elif d == "menu_games":
        safe_edit(call, "Тут вы можете выйграть подарок от обычного до нфт", get_kb([("🎲 Кубик - 8⭐", "game_dice"), ("🎯 Дартс - 8⭐", "game_darts"), ("🔙 Назад", "menu_main")]))
    elif d == "menu_profile":
        u = cursor.execute("SELECT username, balance, spent FROM users WHERE user_id = ?", (uid,)).fetchone()
        if u: safe_edit(call, f"📊 <b>Ваш профиль!</b>\n\n┌ 💡 ID: <code>{uid}</code>\n├ 👤 Имя: @{u[0]}\n├ ⭐ Баланс: {u[1]:,}\n└ ⭐ Потрачено звёзд: {u[2]:,}", get_kb([("🔙 Назад", "menu_main")]))
    elif d == "menu_tasks":
        text = "📱 <b>Задание: Комментарии в TikTok</b>\n\n🎁 Награда: +50 ⭐\n\n📝 <b>Что нужно сделать:</b>\n   1️⃣ Откройте TikTok\n   2️⃣ Найдите любое видео в ленте\n   3️⃣ Напишите ровно 10 комментариев под разными видео с этим текстом:\n\n      <code>durov_play_bot реально дарит подарки, проверено</code>\n<i>(можно нажать скопируется)</i>\n\n   4️⃣ Поставьте ❤️ лайк под каждым комментарием\n   5️⃣ Сделайте 10 скриншотов (комментарий + лайк)\n   6️⃣ Отправьте все 10 фото сюда подряд\n\n⏳ После проверки звёзды придут в течение 24 часов"
        safe_edit(call, text, get_kb([("✅ Я выполнил", "task_completed"), ("🔙 Назад", "menu_main")]))
    elif d == "task_completed":
        user_photo_uploads[uid] = []
        bot.delete_message(cid, mid)
        bot.send_message(cid, "📸 Теперь отправь 10 скриншотов (фото) твоих комментариев по одному.")
    elif d in ["buy_reg_3", "game_dice", "game_darts"]:
        payload, price, desc, title = {"buy_reg_3": ("reg_gift_3", 3, "Оплата за подарок", "Обычный подарок"), "game_dice": ("game_dice_8", 8, "Бросок кубика. Стоимость 8 звезд.", "Игра: Кубик"), "game_darts": ("game_darts_8", 8, "Бросок дротика. Стоимость 8 звезд.", "Игра: Дартс")}[d]
        bot.send_invoice(cid, title=title, description=desc, invoice_payload=payload, provider_token="", currency="XTR", prices=[LabeledPrice("Цена", price)])
    elif d == "buy_reg_8":
        msg = bot.send_message(cid, "✍️ Какую подпись вы хотите добавить подарку?")
        bot.register_next_step_handler(msg, lambda m: bot.send_invoice(m.chat.id, title="Подарок с подписью", description=f"Подпись: {m.text}", invoice_payload="reg_gift_8", provider_token="", currency="XTR", prices=[LabeledPrice("Цена", 8)]))
    elif d.startswith("pay_balance_"):
        name = GIFTS_KEYS[int(d.split('_')[2])]
        bal = cursor.execute("SELECT balance FROM users WHERE user_id = ?", (uid,)).fetchone()
        if bal and bal[0] >= 10:
            with db_lock:
                cursor.execute("UPDATE users SET balance = balance - 10, spent = spent + 10 WHERE user_id = ?", (uid,))
                conn.commit()
            bot.answer_callback_query(call.id, f"Успешно куплено: {name}!", show_alert=True)
        else: bot.answer_callback_query(call.id, "❌ Недостаточно звезд на внутреннем балансе!", show_alert=True)
    try: bot.answer_callback_query(call.id)
    except: pass

@bot.message_handler(content_types=['photo'])
def handle_photos(message):
    uid = message.from_user.id
    if uid in user_photo_uploads:
        user_photo_uploads[uid].append(message.photo[-1].file_id)
        if len(user_photo_uploads[uid]) >= 10:
            # Безопасно извлекаем, чтобы избежать конфликтов при мгновенной отправке альбома
            photos = user_photo_uploads.pop(uid, None)
            if photos: 
                photos_str = ','.join(photos[:10])
                try:
                    with db_lock:
                        cursor.execute("INSERT INTO task_applications (user_id, photos) VALUES (?, ?)", (uid, photos_str))
                        conn.commit()
                    bot.send_message(message.chat.id, "✅ Все 10 скриншотов получены и отправлены на проверку модераторам!")
                except Exception as e:
                    print("Ошибка БД при сохранении фото:", e)

bot.infinity_polling()
