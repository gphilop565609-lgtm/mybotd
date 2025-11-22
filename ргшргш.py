import telebot
from telebot import types

# Замените на свой API-ключ Telegram бота
BOT_TOKEN = "8300485475:AAFWJBhXprvRlUiyz84g1coN_67hxWFfBqE"
# Замените на ID ваших каналов и ссылки на них
CHANNEL_ID_1 = "-1003158741026"
CHANNEL_LINK_1 = "https://t.me/fondsir"  # Замените!
CHANNEL_ID_2 = "-1003360504067"
CHANNEL_LINK_2 = "https://t.me/+nF6S_Obu2S8yNTZk"  # Замените!

bot = telebot.TeleBot(BOT_TOKEN)


def check_subscription(user_id, channel_id):
    """Проверяет, подписан ли пользователь на канал."""
    try:
        chat_member = bot.get_chat_member(channel_id, user_id)
        status = chat_member.status
        return status in ['member', 'administrator', 'creator']
    except telebot.apihelper.ApiTelegramException as e:
        if e.description == 'User not found':
            return None  # Пользователь не найден в канале
        else:
            return False  # Произошла другая ошибка при проверке


@bot.message_handler(commands=['start'])
def start(message):
    """Обработчик команды /start."""
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("КАНАЛ 1", url=CHANNEL_LINK_1)
    btn2 = types.InlineKeyboardButton("КАНАЛ 2", url=CHANNEL_LINK_2)
    btn3 = types.InlineKeyboardButton("Я ПОДПИСАЛСЯ", callback_data='check_subscription')
    markup.add(btn1, btn2)
    markup.add(btn3)
    bot.send_message(message.chat.id, "Подпишитесь на каналы, чтобы продолжить:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    """Обработчик всех callback-запросов."""
    user_id = call.from_user.id
    if call.data == 'check_subscription':
        is_subscribed_1 = check_subscription(user_id, CHANNEL_ID_1)
        is_subscribed_2 = check_subscription(user_id, CHANNEL_ID_2)
        if is_subscribed_1 and is_subscribed_2:
            bot.answer_callback_query(call.id, "Спасибо за подписку!")
            # Здесь можно добавить дальнейшие действия после подтверждения подписки
            bot.send_message(call.message.chat.id, "Вы успешно подписались на все каналы!")  # Пример ответа после подписки
        else:
            bot.answer_callback_query(call.id, "Вы не подписаны на все каналы. Пожалуйста, подпишитесь и попробуйте снова.")


if __name__ == '__main__': #Добавлена проверка, чтобы бот запускался, только когда скрипт запускается напрямую
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Произошла ошибка: {e}")
