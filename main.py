import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
import sqlite3
import threading
import time

BOT_TOKEN = '8708256332:AAFOMWD5QtdsjtS-LCL9PL23mnM0neOrg4k'
ADMIN_IDS = [7283380508]  # Твой ID

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# ==================== БАЗА ДАННЫХ ====================
conn = sqlite3.connect('bot_database.db', check_same_thread=False)
cursor = conn.cursor()

# Создаем таблицы
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 0,
    spent INTEGER DEFAULT 0,
    referrer_id INTEGER,
    refs_count INTEGER DEFAULT 0
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY,
    gifts_given INTEGER DEFAULT 0,
    auto_add_amount INTEGER DEFAULT 0,
    auto_add_interval INTEGER DEFAULT 0
)''')
conn.commit()

# Автоматическое обновление старой БД (если файл не удалили)
try: cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
except: pass
try: cursor.execute("ALTER TABLE users ADD COLUMN refs_count INTEGER DEFAULT 0")
except: pass
conn.commit()

# Инициализация настроек при первом запуске
cursor.execute("SELECT id FROM settings WHERE id = 1")
if not cursor.fetchone():
    cursor.execute("INSERT INTO settings (id, gifts_given, auto_add_amount, auto_add_interval) VALUES (1, 0, 0, 0)")
    conn.commit()

# ==================== СЛОВАРИ ====================
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
GIFTS_KEYS = list(GIFTS.keys())

# ==================== ФУНКЦИЯ-ПРЕДОХРАНИТЕЛЬ ОТ ОШИБОК API ====================
def safe_edit(text, chat_id, message_id, reply_markup=None):
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=reply_markup, parse_mode='HTML')
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" not in str(e):
            print(f"Ошибка редактирования: {e}")

# ==================== ФОНОВЫЙ ПОТОК ДЛЯ АДМИНА ====================
def auto_increment_gifts():
    while True:
        cursor.execute("SELECT auto_add_amount, auto_add_interval FROM settings WHERE id = 1")
        amount, interval = cursor.fetchone()
        if amount > 0 and interval > 0:
            cursor.execute("UPDATE settings SET gifts_given = gifts_given + ? WHERE id = 1", (amount,))
            conn.commit()
            time.sleep(interval)
        else:
            time.sleep(5)

threading.Thread(target=auto_increment_gifts, daemon=True).start()

# ==================== КЛАВИАТУРЫ (ВСЕ В СТОЛБИК) ====================
def main_menu_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🎁 Подарки", callback_data="menu_gifts"))
    kb.add(InlineKeyboardButton("🕹️ Игры", callback_data="menu_games"))
    kb.add(InlineKeyboardButton("👤 Профиль", callback_data="menu_profile"))
    kb.add(InlineKeyboardButton("⭐ Задание", callback_data="menu_tasks"))
    return kb

def gifts_menu_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🌟 НФТ", callback_data="gifts_nft"))
    kb.add(InlineKeyboardButton("🧸 Обычные подарки", callback_data="gifts_regular"))
    kb.add(InlineKeyboardButton("💝 Бесплатные подарки", callback_data="gifts_free"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="menu_main"))
    return kb

def nft_menu_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    for idx, name in enumerate(GIFTS_KEYS):
        kb.add(InlineKeyboardButton(f"{name} - 10⭐", callback_data=f"nft_{idx}"))
    kb.add(InlineKeyboardButton("💝 Бесплатный мишка", callback_data="gifts_free"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="menu_gifts"))
    return kb

def regular_gifts_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("Обычный подарок - 3⭐", callback_data="buy_reg_3"))
    kb.add(InlineKeyboardButton("Подарок с подписью - 8⭐", callback_data="buy_reg_8"))
    kb.add(InlineKeyboardButton("💝 Бесплатный мишка", callback_data="gifts_free"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="menu_gifts"))
    return kb

def games_menu_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🎲 Кубик - 8⭐", callback_data="game_dice"))
    kb.add(InlineKeyboardButton("🎯 Дартс - 8⭐", callback_data="game_darts"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="menu_main"))
    return kb

def profile_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="menu_main"))
    return kb

def free_bear_kb(bot_username, user_id):
    kb = InlineKeyboardMarkup(row_width=1)
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    kb.add(InlineKeyboardButton("📤 Поделиться ссылкой", switch_inline_query=ref_link))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="menu_gifts"))
    return kb

def buy_nft_kb(nft_name):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("Перейти к покупке ⬆️", url=f"https://t.me/Glft_free_nft?text={nft_name}"))
    kb.add(InlineKeyboardButton("Оплатить со звезд ⭐", callback_data=f"pay_balance_{GIFTS_KEYS.index(nft_name)}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="gifts_nft"))
    return kb

# ==================== ХЭНДЛЕРЫ ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Без имени"
    
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id == user_id:
            referrer_id = None
            
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)", (user_id, username, referrer_id))
        if referrer_id:
            cursor.execute("UPDATE users SET refs_count = refs_count + 1 WHERE user_id = ?", (referrer_id,))
        conn.commit()

    send_main_menu(message.chat.id, message.message_id)

@bot.message_handler(commands=['setgifts', 'autoincrement', 'refs'])
def admin_commands(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    cmd = message.text.split()
    if cmd[0] == '/setgifts' and len(cmd) == 2:
        cursor.execute("UPDATE settings SET gifts_given = ? WHERE id = 1", (int(cmd[1]),))
        conn.commit()
        bot.reply_to(message, f"✅ Количество подаренных подарков установлено на {cmd[1]}")
    
    elif cmd[0] == '/autoincrement' and len(cmd) == 3:
        amount = int(cmd[1])
        interval = int(cmd[2])
        cursor.execute("UPDATE settings SET auto_add_amount = ?, auto_add_interval = ? WHERE id = 1", (amount, interval))
        conn.commit()
        bot.reply_to(message, f"✅ Автопополнение включено: +{amount} подарков каждые {interval} секунд.")
        
    elif cmd[0] == '/refs' and len(cmd) == 2:
        user_id = int(cmd[1])
        cursor.execute("SELECT refs_count FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        if res:
            bot.reply_to(message, f"👤 Пользователь {user_id} пригласил {res[0]} рефералов.")
        else:
            bot.reply_to(message, "Пользователь не найден.")

def send_main_menu(chat_id, message_id=None):
    cursor.execute("SELECT gifts_given FROM settings WHERE id = 1")
    gifts_given = cursor.fetchone()[0]
    
    text = (f"🧸 <b>Главное меню</b>\n\n"
            f"🎁 Подарено подарков: <b>{gifts_given}</b>\n\n"
            f"В данном боте вы можете получить бесплатно подарки обычные и NFT.\n"
            f"Для получения звезд выполняйте задания. За задания вы можете получить NFT подарки, а также звезды.\n\n"
            f"Выберите категорию👇")
    bot.send_message(chat_id, text, reply_markup=main_menu_kb())

# ==================== CALLBACK И НАВИГАЦИЯ ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    user_id = call.from_user.id

    if call.data == "menu_main":
        cursor.execute("SELECT gifts_given FROM settings WHERE id = 1")
        gifts_given = cursor.fetchone()[0]
        text = (f"🧸 <b>Главное меню</b>\n\n"
                f"🎁 Подарено подарков: <b>{gifts_given}</b>\n\n"
                f"В данном боте вы можете получить бесплатно подарки обычные и NFT.\n"
                f"Для получения звезд выполняйте задания. За задания вы можете получить NFT подарки, а также звезды.\n\n"
                f"Выберите категорию👇")
        safe_edit(text, chat_id, msg_id, reply_markup=main_menu_kb())

    elif call.data == "menu_gifts":
        safe_edit("🎁 <b>Подарки</b>\n\nВыберите категорию:", chat_id, msg_id, reply_markup=gifts_menu_kb())

    elif call.data == "gifts_nft":
        safe_edit("🌟 <b>Выберите НФТ подарок</b>", chat_id, msg_id, reply_markup=nft_menu_kb())

    elif call.data.startswith("nft_"):
        idx = int(call.data.split("_")[1])
        nft_name = GIFTS_KEYS[idx]
        nft_url = GIFTS[nft_name]
        text = (f"🎁 <b>{nft_name}</b>\n\n"
                f"1️⃣ Нажмите кнопку ниже.\n"
                f"2️⃣ Оплатите платное сообщение.\n"
                f"3️⃣ После оплаты бот автоматически выдаст Вам подарок.\n\n"
                f"⚡ Скриншоты не нужны — подтверждение срабатывает автоматически.")
        
        bot.delete_message(chat_id, msg_id)
        bot.send_photo(chat_id, nft_url, caption=text, reply_markup=buy_nft_kb(nft_name))

    elif call.data == "gifts_regular":
        safe_edit("🧸\nВыберете подарок", chat_id, msg_id, reply_markup=regular_gifts_kb())

    elif call.data == "gifts_free":
        cursor.execute("SELECT refs_count FROM users WHERE user_id = ?", (user_id,))
        refs = cursor.fetchone()
        refs_count = refs[0] if refs else 0
        bears_available = refs_count // 5
        
        text = (f"🧸 <b>БЕСПЛАТНЫЙ МИШКА</b> 🎁\n\n"
                f"Приглашай друзей и получай мишку за каждые 5 рефералов! 🚀\n\n"
                f"🔗 Ваша ссылка:\n<code>https://t.me/{bot.get_me().username}?start={user_id}</code>\n\n"
                f"👥 Приглашено: <b>{refs_count}</b>\n"
                f"🧸 Доступно мишек: <b>{bears_available}</b>")
        
        try:
            safe_edit(text, chat_id, msg_id, reply_markup=free_bear_kb(bot.get_me().username, user_id))
        except:
            bot.delete_message(chat_id, msg_id)
            bot.send_message(chat_id, text, reply_markup=free_bear_kb(bot.get_me().username, user_id))

    elif call.data == "menu_games":
        safe_edit("Тут вы можете выйграть подарок от обычного до нфт", chat_id, msg_id, reply_markup=games_menu_kb())

    elif call.data == "menu_profile":
        cursor.execute("SELECT username, balance, spent FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        if res:
            text = (f"📊 <b>Ваш профиль!</b>\n\n"
                    f"┌ 💡 ID: <code>{user_id}</code>\n"
                    f"├ 👤 Имя: @{res[0]}\n"
                    f"├ ⭐ Баланс: {res[1]}\n"
                    f"└ ⭐ Потрачено звёзд: {res[2]}")
            safe_edit(text, chat_id, msg_id, reply_markup=profile_kb())

    elif call.data == "menu_tasks":
        bot.answer_callback_query(call.id, "В разработке...", show_alert=True)

    # ==== ОПЛАТЫ И ИГРЫ ====
    elif call.data == "buy_reg_3":
        bot.send_invoice(chat_id, title="Обычный подарок", description="Оплата за подарок", 
                         invoice_payload="reg_gift_3", provider_token="", currency="XTR", prices=[LabeledPrice("Цена", 3)])

    elif call.data == "buy_reg_8":
        msg = bot.send_message(chat_id, "✍️ Какую подпись вы хотите добавить подарку?")
        bot.register_next_step_handler(msg, process_gift_signature)

    elif call.data == "game_dice":
        bot.send_invoice(chat_id, title="Игра: Кубик", description="Бросок кубика. Стоимость 8 звезд.", 
                         invoice_payload="game_dice_8", provider_token="", currency="XTR", prices=[LabeledPrice("Ставка", 8)])

    elif call.data == "game_darts":
        bot.send_invoice(chat_id, title="Игра: Дартс", description="Бросок дротика. Стоимость 8 звезд.", 
                         invoice_payload="game_darts_8", provider_token="", currency="XTR", prices=[LabeledPrice("Ставка", 8)])
        
    elif call.data.startswith("pay_balance_"):
        idx = int(call.data.split("_")[2])
        nft_name = GIFTS_KEYS[idx]
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        if res and res[0] >= 10:
            cursor.execute("UPDATE users SET balance = balance - 10, spent = spent + 10 WHERE user_id = ?", (user_id,))
            conn.commit()
            bot.answer_callback_query(call.id, f"Успешно куплено: {nft_name}!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "❌ Недостаточно звезд на внутреннем балансе!", show_alert=True)

    bot.answer_callback_query(call.id) # Закрываем "часики" загрузки на кнопке

def process_gift_signature(message):
    bot.send_invoice(message.chat.id, title="Подарок с подписью", description=f"Подпись: {message.text}", 
                     invoice_payload="reg_gift_8", provider_token="", currency="XTR", prices=[LabeledPrice("Цена", 8)])

# ==================== ОБРАБОТКА ПЛАТЕЖЕЙ TELEGRAM STARS (XTR) ====================
@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    payload = message.successful_payment.invoice_payload
    user_id = message.from_user.id
    amount = message.successful_payment.total_amount
    
    cursor.execute("UPDATE users SET spent = spent + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

    if payload == "reg_gift_3":
        bot.send_message(message.chat.id, "✅ Вы успешно купили Обычный подарок!")
    elif payload == "reg_gift_8":
        bot.send_message(message.chat.id, "✅ Вы успешно купили Подарок с подписью!")
    elif payload == "game_dice_8":
        dice_msg = bot.send_dice(message.chat.id, emoji="🎲")
        time.sleep(3)
        if dice_msg.dice.value in [4, 5, 6]:
            win_amount = 16
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (win_amount, user_id))
            conn.commit()
            bot.send_message(message.chat.id, f"🎉 Вы выиграли! {win_amount}⭐ начислено на внутренний баланс.")
        else:
            bot.send_message(message.chat.id, "😔 Вы проиграли, ничего страшного. Попробуйте еще раз!")
    elif payload == "game_darts_8":
        darts_msg = bot.send_dice(message.chat.id, emoji="🎯")
        time.sleep(3)
        if darts_msg.dice.value in [4, 5, 6]:
            win_amount = 16
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (win_amount, user_id))
            conn.commit()
            bot.send_message(message.chat.id, f"🎯 Точно в цель! {win_amount}⭐ начислено на баланс.")
        else:
            bot.send_message(message.chat.id, "😔 Промах. Попробуйте еще раз!")

if __name__ == "__main__":
    print("Бот запущен!")
    bot.infinity_polling()
    
