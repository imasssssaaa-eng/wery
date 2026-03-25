import telebot
from telebot import types
import random

TOKEN = "8708256332:AAFOMWD5QtdsjtS-LCL9PL23mnM0neOrg4k"
WALLET_ADDRESS = "UQAXQKWWH37XPNoIZvpCBOtmAmbR7LpAcMuHKQSKtykoL6eQ"
TON_RATE = 0.013 # 50 звезд = 0.65 TON

bot = telebot.TeleBot(TOKEN)

# Хранилище временных данных (вместо FSM)
user_data = {}

# Главная клавиатура
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("⭐Купить Звезды"))
    return keyboard

# Инлайн кнопка "Купить другу"
def get_friend_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="🎁Купить Другу", callback_data="buy_for_friend"))
    return keyboard

# Выбор оплаты
def get_payment_method_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="TON", callback_data="pay_ton"))
    return keyboard

# Кнопка оплаты (deep link)
def get_pay_url_keyboard(address, nanotons, memo):
    url = f"ton://transfer/{address}?amount={nanotons}&text={memo}"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="👉Оплатить в Приложении", url=url))
    return keyboard

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_data[message.chat.id] = {}
    text = (
        "✨ Добро пожаловать!\n\n"
        "Здесь можно приобрести Telegram звезды без верификации KYC и дешевле чем в приложении.\n\n"
        "❗️Чтобы продолжить, просто введи желаемую сумму покупки (минимум 50 звезд)"
    )
    bot.send_message(message.chat.id, text, reply_markup=get_main_keyboard())

@bot.message_handler(commands=['cancel'])
def cmd_cancel(message):
    user_data[message.chat.id] = {}
    bot.send_message(message.chat.id, "Действие отменено.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "⭐Купить Звезды")
def start_buying(message):
    target_user = message.from_user.username or message.from_user.first_name
    user_data[message.chat.id] = {'target_user': target_user}
    
    text = (
        "🌟 Введите нужное количество звезд (минимум 50, максимум 1000000)\n\n"
        f"👤 Покупка для: @{target_user}"
    )
    msg = bot.send_message(message.chat.id, text, reply_markup=get_friend_keyboard())
    bot.register_next_step_handler(msg, process_amount)

@bot.callback_query_handler(func=lambda call: call.data == "buy_for_friend")
def ask_friend_username(call):
    text = (
        "🙋‍♂️ Введите юзернейм аккаунта, на который будут отправлены звезды.\n\n"
        "Убедитесь, что аккаунт существует.\n\n"
        "Отменить - /cancel"
    )
    msg = bot.send_message(call.message.chat.id, text)
    bot.register_next_step_handler(msg, process_friend_username)
    bot.answer_callback_query(call.id)

def process_friend_username(message):
    if message.text == '/cancel': return cmd_cancel(message)
    
    username = message.text.replace("@", "")
    user_data[message.chat.id]['target_user'] = username
    
    text = (
        "🌟 Введите нужное количество звезд (минимум 50, максимум 1000000)\n\n"
        f"👤 Покупка для: @{username}"
    )
    msg = bot.send_message(message.chat.id, text, reply_markup=get_friend_keyboard())
    bot.register_next_step_handler(msg, process_amount)

def process_amount(message):
    if message.text == '/cancel': return cmd_cancel(message)
    if not message.text.isdigit():
        msg = bot.send_message(message.chat.id, "Пожалуйста, введите только число.")
        bot.register_next_step_handler(msg, process_amount)
        return

    amount = int(message.text)
    if amount < 50 or amount > 1000000:
        msg = bot.send_message(message.chat.id, f"Недопустимое количество ({amount}). Минимум 50, максимум 1000000. Попробуйте еще раз:")
        bot.register_next_step_handler(msg, process_amount)
        return

    user_data[message.chat.id]['stars_amount'] = amount

    text = (
        "⭐️ Выберите способ оплаты:\n\n"
        "❗️Счет действителен 30 минут.\n\n"
        "Оплачивая, вы потдверждаете, что покупаете Telegram Stars/TON для себя или в подарок своим знакомым и НЕ оплачиваете товары на других сайтах/сервисах в пользу незнакомых лиц"
    )
    bot.send_message(message.chat.id, text, reply_markup=get_payment_method_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "pay_ton")
def generate_payment(call):
    data = user_data.get(call.message.chat.id, {})
    stars_amount = data.get("stars_amount")
    target_user = data.get("target_user")
    
    if not stars_amount:
        bot.send_message(call.message.chat.id, "Ошибка сессии. Нажмите /start")
        return

    ton_amount = round(stars_amount * TON_RATE, 2)
    nanotons = int(ton_amount * 1_000_000_000)
    memo = random.randint(1000000000, 9999999999)

    text = (
        f"@{target_user}, Счет действителен 30 минут\n\n"
        f"{stars_amount} Звезд ⭐️ для аккаунта @{target_user}\n\n"
        "Реквизиты для оплаты:\n\n"
        "Сеть: TON\n"
        f"Сумма: {ton_amount}\n"
        f"Адрес: {WALLET_ADDRESS}\n\n"
        f"Добавьте в коммент (memo) к транзакции цифры: {memo}\n\n"
        "‼️ Отправьте точную (!) сумму на указанный адрес. ⚠️ Обязательно указывайте комментарий при переводе, иначе платеж НЕ ЗАСЧИТАЕТСЯ.\n\n"
        "В случае возникновения проблем, обращайтесь в поддержку."
    )
    
    bot.send_message(
        call.message.chat.id, 
        text, 
        reply_markup=get_pay_url_keyboard(WALLET_ADDRESS, nanotons, memo)
    )
    bot.answer_callback_query(call.id)
    # Очищаем данные после генерации счета
    user_data[call.message.chat.id] = {}

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
    
