import telebot
from flask import Flask, request
import uuid

BOT_TOKEN = '8565233233:AAEoRhxYdXKqc_amgPKV4uiXkIPANkTjIhs'
CURRENCY_NAME = '$'
CHANNEL_LINK = 't.me/fondsir'
CHANNEL_ID = -1003158741026
REFERRAL_REWARD = 1.5
ADMIN_ID = 8121478086  # Замените на ID администратора
WITHDRAWAL_MIN = 10

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

users_db = {}
withdrawal_requests = [] # Список запросов на вывод
admins = [ADMIN_ID] # Список админов

def generate_referral_code():
    return str(uuid.uuid4())

def get_user_balance(user_id):
    return users_db.get(user_id, {}).get('balance', 0)

def update_user_balance(user_id, amount):
    if user_id not in users_db:
        users_db[user_id] = {'balance': 0, 'subscribed': False, 'referral_code': generate_referral_code()}
    users_db[user_id]['balance'] += amount
    return users_db[user_id]['balance']

def check_subscription(user_id):
    try:
        member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        status = member.status
        return status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

def create_subscription_keyboard():
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(text="Я ПОДПИСАЛСЯ", callback_data="check_sub"))
    return keyboard

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id not in users_db:
        users_db[user_id] = {'balance': 0, 'subscribed': False, 'referral_code': generate_referral_code(), 'pending_referral': None}

    if not check_subscription(user_id):
        bot.reply_to(message, f"Привет! Подпишитесь на канал {CHANNEL_LINK}, чтобы использовать бота.", reply_markup=create_subscription_keyboard())
        return

    balance = get_user_balance(user_id)
    referral_code = users_db[user_id]['referral_code']
    referral_link = f"t.me/freemoney_tgrobot?start={referral_code}"

    # Создаем кнопку "Подать заявку на вывод"
    withdraw_keyboard = telebot.types.InlineKeyboardMarkup()
    withdraw_keyboard.add(telebot.types.InlineKeyboardButton(text="Подать заявку на вывод", callback_data="withdraw"))

    # Отправляем приветственное сообщение с балансом, реферальной ссылкой и кнопкой вывода
    bot.reply_to(message, f"Привет! Твой баланс: {balance} {CURRENCY_NAME}.\nТвоя реферальная ссылка: {referral_link}", reply_markup=withdraw_keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def handle_check_sub(call):
     user_id = call.from_user.id
     if check_subscription(user_id):
        bot.answer_callback_query(call.id, "Спасибо за подписку!", show_alert=True)
        users_db[user_id]['subscribed'] = True
        balance = get_user_balance(user_id)
        # Создаем кнопку "Подать заявку на вывод"
        withdraw_keyboard = telebot.types.InlineKeyboardMarkup()
        withdraw_keyboard.add(telebot.types.InlineKeyboardButton(text="Подать заявку на вывод", callback_data="withdraw"))

        bot.send_message(user_id, f"Теперь у тебя есть доступ! Твой баланс: {balance} {CURRENCY_NAME}.", reply_markup=withdraw_keyboard)

        # Проверяем, есть ли ожидающий реферрал и начисляем
        if 'pending_referral' in users_db[user_id] and users_db[user_id]['pending_referral'] is not None:
            referrer_id = users_db[user_id]['pending_referral']
            update_user_balance(referrer_id, REFERRAL_REWARD)
            bot.send_message(referrer_id, f"По вашей реферальной ссылке зарегистрировался и подписался новый пользователь. Вам начислено {REFERRAL_REWARD} {CURRENCY_NAME}.")
            users_db[user_id]['pending_referral'] = None # Очищаем
     else:
        bot.answer_callback_query(call.id, "Вы все еще не подписаны.", show_alert=True)

@bot.message_handler(func=lambda message: message.text.startswith('/start '))
def handle_start_command(message):
    user_id = message.from_user.id
    referral_code = message.text.split()[1]

    referrer_id = None
    for user, data in users_db.items():
        if data.get('referral_code') == referral_code:
            referrer_id = user
            break

    if referrer_id and user_id != referrer_id and user_id not in users_db:
        users_db[user_id] = {'balance': 0, 'subscribed': False, 'referral_code': generate_referral_code(), 'pending_referral': referrer_id}
        #Важно! Не даем награду сразу, пока человек не подписался
        send_welcome(message)
    else:
        send_welcome(message)

@bot.message_handler(commands=['referral'])
def referral_menu(message):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(text="Вывести", callback_data="withdraw"))
    keyboard.add(telebot.types.InlineKeyboardButton(text="Моя статистика", callback_data="stats"))
    bot.reply_to(message, "Выберите действие:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "withdraw") #Обработчик кнопки withdraw
def withdraw_request(call):
    user_id = call.from_user.id
    balance = get_user_balance(user_id)
    if balance < WITHDRAWAL_MIN:
        bot.answer_callback_query(call.id, f"Минимальная сумма для вывода: {WITHDRAWAL_MIN} {CURRENCY_NAME}", show_alert=True) #Если меньше 10
        return

    withdrawal_requests.append(user_id)
    admin_keyboard = telebot.types.InlineKeyboardMarkup()
    admin_keyboard.add(telebot.types.InlineKeyboardButton(text="Одобрить", callback_data=f"approve_{user_id}"))
    admin_keyboard.add(telebot.types.InlineKeyboardButton(text="Отказать", callback_data=f"reject_{user_id}"))
    bot.send_message(ADMIN_ID, f"Запрос на вывод от {user_id}, сумма: {balance} {CURRENCY_NAME}", reply_markup=admin_keyboard)
    bot.send_message(user_id, "Ваш запрос на вывод отправлен администратору.") #Уведомление

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def handle_withdrawal_action(call):
    action, user_id = call.data.split("_")
    user_id = int(user_id)
    balance = get_user_balance(user_id) #получаем баланс запрашивающего

    if action == "approve":
        # Здесь должна быть логика списания средств и отправки пользователю
        update_user_balance(user_id, -balance) #Обнуляем баланс после подтверждения
        bot.send_message(user_id, f"Ваш запрос на вывод {balance} {CURRENCY_NAME} одобрен.")
        bot.send_message(ADMIN_ID, f"Вывод для {user_id} одобрен.")

    elif action == "reject":
        bot.send_message(user_id, "Ваш запрос на вывод отклонен.")
        bot.send_message(ADMIN_ID, f"Вывод для {user_id} отклонен.")

    if user_id in withdrawal_requests:
        withdrawal_requests.remove(user_id)

@bot.callback_query_handler(func=lambda call: call.data == "stats")
def show_stats(call):
    user_id = call.from_user.id
    balance = get_user_balance(user_id)
    bot.answer_callback_query(call.id, f"Ваш баланс: {balance} {CURRENCY_NAME}", show_alert=True)

# Новые функции для админ-панели
def is_admin(user_id):
    return user_id in admins

@bot.message_handler(commands=['admpan'])
def admin_panel(message):
    if is_admin(message.from_user.id):
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton(text="Рассылка", callback_data="broadcast"))
        keyboard.add(telebot.types.InlineKeyboardButton(text="Заявки на вывод", callback_data="view_withdrawals"))
        keyboard.add(telebot.types.InlineKeyboardButton(text="Назначить админа", callback_data="add_admin"))
        keyboard.add(telebot.types.InlineKeyboardButton(text="Выдать валюту", callback_data="give_currency"))
        bot.reply_to(message, "Админ-панель:", reply_markup=keyboard)
    else:
        bot.reply_to(message, "У вас нет прав для доступа к админ-панели.")

@bot.callback_query_handler(func=lambda call: call.data == "add_admin")
def add_admin_handler(call):
    # Запрашиваем у админа ID пользователя, которого нужно назначить админом
    bot.send_message(call.from_user.id, "Введите ID пользователя, которого хотите назначить админом:")
    bot.register_next_step_handler(call.message, process_add_admin)

def process_add_admin(message):
    try:
        user_id = int(message.text)
        if user_id not in admins:
            admins.append(user_id)
            bot.send_message(ADMIN_ID, f"Пользователь с ID {user_id} назначен админом.")
            bot.send_message(user_id, "Вы были назначены админом.")
        else:
            bot.send_message(ADMIN_ID, "Этот пользователь уже является админом.")

    except ValueError:
        bot.send_message(ADMIN_ID, "Некорректный ID пользователя. Введите число.")

@bot.callback_query_handler(func=lambda call: call.data == "give_currency")
def give_currency_handler(call):
    # Запрашиваем у админа ID пользователя и количество валюты для выдачи
    bot.send_message(call.from_user.id, "Введите ID пользователя, которому хотите выдать валюту:")
    bot.register_next_step_handler(call.message, process_user_id_for_currency)

def process_user_id_for_currency(message):
    try:
        user_id = int(message.text)
        # Запрашиваем кол-во валюты
        bot.send_message(ADMIN_ID, f"Введите кол-во {CURRENCY_NAME}, которое хотите выдать пользователю с ID {user_id}:")
        bot.register_next_step_handler(message, lambda msg: process_currency_amount(msg, user_id)) # Лямбда функция для передачи user_id

    except ValueError:
        bot.send_message(ADMIN_ID, "Некорректный ID пользователя. Введите число.")

def process_currency_amount(message, user_id):
    try:
        amount = float(message.text) # Получаем кол-во валюты
        update_user_balance(user_id, amount) # Обновляем баланс
        bot.send_message(ADMIN_ID, f"Пользователю с ID {user_id} выдано {amount} {CURRENCY_NAME}.")
        bot.send_message(user_id, f"Вам начислено {amount} {CURRENCY_NAME}.") # Оповещаем пользователя
    except ValueError:
        bot.send_message(ADMIN_ID, "Некорректное количество валюты. Введите число.")

@bot.callback_query_handler(func=lambda call: call.data == "broadcast")
def broadcast_message(call):
    bot.send_message(ADMIN_ID, "Введите текст для рассылки:")
    bot.register_next_step_handler(call.message, process_broadcast_message)

def process_broadcast_message(message):
    broadcast_text = message.text
    for user_id in users_db.keys():
        try:
            bot.send_message(user_id, broadcast_text)
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
    bot.send_message(ADMIN_ID, "Рассылка завершена.")

@bot.callback_query_handler(func=lambda call: call.data == "view_withdrawals")
def view_withdrawals(call):
    if is_admin(call.from_user.id): #Проверка на админа
        if not withdrawal_requests:    #Проверка на сообщения
            bot.send_message(ADMIN_ID, "Заявок на вывод нет.")
            return
        for user_id in withdrawal_requests: #Вывод всех запросов
            balance = get_user_balance(user_id) #Баланс пользователя
            admin_keyboard = telebot.types.InlineKeyboardMarkup()
            admin_keyboard.add(telebot.types.InlineKeyboardButton(text="Одобрить", callback_data=f"approve_{user_id}"))
            admin_keyboard.add(telebot.types.InlineKeyboardButton(text="Отказать", callback_data=f"reject_{user_id}"))
            bot.send_message(ADMIN_ID, f"Запрос на вывод от {user_id}, сумма: {balance} {CURRENCY_NAME}",reply_markup=admin_keyboard) #Отправлят админу сообщения с запросами на вывод

if __name__ == '__main__':
    bot.infinity_polling()
