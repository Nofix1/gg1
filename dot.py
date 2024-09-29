import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, db
import random
import time

# Инициализация Firebase
cred = credentials.Certificate('database-65f4e-firebase-adminsdk-x7hj9-c913ba6a34.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://database-65f4e-default-rtdb.firebaseio.com/'
})

# Инициализация бота
TOKEN = '7424641182:AAG5Wh77L20nqWdw_zrtzC2jHrKIJbO3bYE'  # Замените на ваш токен
bot = telebot.TeleBot(TOKEN)

# Константы
MAIN_MENU = 'main_menu'
PROFILE_MENU = 'profile_menu'
PLAY_MENU = 'play_menu'
DAILY_BONUS = 'daily_bonus'
BACK_BUTTON_TEXT = 'Назад'

# Хелпер для получения пути пользователя
def get_user_path(user_id):
    return f'users/{user_id}'

# Регистрация пользователя
def register_user(user_id):
    user_ref = db.reference(get_user_path(user_id))
    if not user_ref.get():
        user_ref.set({
            'id': user_id,
            'wins': 0,
            'losses': 0,
            'balance': 0,
            'last_bonus': 0
        })

# Обработка команды /start
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    register_user(user_id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_play = types.KeyboardButton("Играть")
    btn_profile = types.KeyboardButton("Профиль")
    btn_top = types.KeyboardButton("Топ Игроков")
    markup.add(btn_play, btn_profile, btn_top)

    bot.send_message(message.chat.id, "Добро пожаловать! Выберите действие:", reply_markup=markup)

# Обработка текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    register_user(user_id)

    if message.text == "Профиль":
        show_profile(message)
    elif message.text == "Ежедневный Бонус":
        give_daily_bonus(message)
    elif message.text == "Играть":
        show_play_menu(message)
    elif message.text == "Топ Игроков":
        show_top_players(message)
    elif message.text.startswith("/mines"):
        handle_mines_game(message)
    else:
        bot.send_message(message.chat.id, "Я не понимаю эту команду. Пожалуйста, используйте меню.", reply_markup=get_main_menu())

# Функция вывода основного меню
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_play = types.KeyboardButton("Играть")
    btn_profile = types.KeyboardButton("Профиль")
    btn_top = types.KeyboardButton("Топ Игроков")
    markup.add(btn_play, btn_profile, btn_top)
    return markup

# Функция отображения профиля
def show_profile(message):
    user_id = message.from_user.id
    user_ref = db.reference(get_user_path(user_id))
    user_data = user_ref.get()

    profile_text = (
        f"Ваш id: {user_data['id']}\n"
        f"Количество Выигранных Игр: {user_data['wins']}\n"
        f"Количество Проигранных Игр: {user_data['losses']}\n"
        f"Баланс Сашко: {user_data['balance']}"
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_bonus = types.KeyboardButton("Ежедневный Бонус")
    btn_back = types.KeyboardButton(BACK_BUTTON_TEXT)
    markup.add(btn_bonus)
    markup.add(btn_back)

    bot.send_message(message.chat.id, profile_text, reply_markup=markup)

# Функция выдачи ежедневного бонуса
def give_daily_bonus(message):
    user_id = message.from_user.id
    user_ref = db.reference(get_user_path(user_id))
    user_data = user_ref.get()

    current_time = int(time.time())
    last_bonus = user_data.get('last_bonus', 0)

    # Проверка, прошло ли 24 часа (86400 секунд)
    if current_time - last_bonus >= 86400:
        bonus = random.randint(1, 10)
        new_balance = user_data.get('balance', 0) + bonus
        user_ref.update({
            'balance': new_balance,
            'last_bonus': current_time
        })
        bot.send_message(message.chat.id, f"🎁 Вы получили {bonus} Сашко!")
    else:
        remaining = 86400 - (current_time - last_bonus)
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        seconds = remaining % 60
        bot.send_message(message.chat.id, f"❌ Ежедневный бонус доступен через {hours}ч {minutes}м {seconds}с.")

# Функция отображения меню выбора игры
def show_play_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_mines = types.KeyboardButton("Mines")
    btn_blackjack = types.KeyboardButton("BlackJack")
    btn_back = types.KeyboardButton(BACK_BUTTON_TEXT)
    markup.add(btn_mines, btn_blackjack)
    markup.add(btn_back)
    bot.send_message(message.chat.id, "Выберите доступную игру:", reply_markup=markup)

# Функция отображения топа игроков
def show_top_players(message):
    users_ref = db.reference('users')
    users = users_ref.order_by_child('wins').limit_to_last(10).get()

    if not users:
        bot.send_message(message.chat.id, "Топ игроков пока пуст.")
        return

    sorted_users = sorted(users.items(), key=lambda x: x[1]['wins'], reverse=True)

    top_text = "🏆 Топ Игроков 🏆\n"
    for idx, (uid, data) in enumerate(sorted_users, start=1):
        top_text += f"{idx}. ID: {uid} - Выигрышей: {data.get('wins',0)}\n"

    bot.send_message(message.chat.id, top_text, reply_markup=get_main_menu())

# Обработка кнопки "Назад"
@bot.message_handler(func=lambda message: message.text == BACK_BUTTON_TEXT)
def handle_back(message):
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=get_main_menu())

# Игра Mines - Начало игры
def handle_mines_game(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    msg = bot.send_message(chat_id, "Выберите количество мин (от 3 до 24):")
    bot.register_next_step_handler(msg, process_mines_quantity)

def process_mines_quantity(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        mines = int(message.text)
        if not 3 <= mines <= 24:
            raise ValueError
    except ValueError:
        msg = bot.send_message(chat_id, "Пожалуйста, введите число от 3 до 24:")
        bot.register_next_step_handler(msg, process_mines_quantity)
        return

    msg = bot.send_message(chat_id, "Введите ставку Сашко (от 1 до 100):")
    bot.register_next_step_handler(msg, lambda m: process_mines_bet(m, mines))

def process_mines_bet(message, mines):
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        bet = int(message.text)
        if not 1 <= bet <= 100:
            raise ValueError
    except ValueError:
        msg = bot.send_message(chat_id, "Пожалуйста, введите число от 1 до 100:")
        bot.register_next_step_handler(msg, lambda m: process_mines_bet(m, mines))
        return

    user_ref = db.reference(get_user_path(user_id))
    user_data = user_ref.get()

    if user_data['balance'] < bet:
        bot.send_message(chat_id, "❌ Недостаточно средств для ставки.")
        return

    # Начало игры: уменьшение баланса на ставку
    user_ref.update({'balance': user_data['balance'] - bet})

    # Создание игрового поля
    total_buttons = 25
    safe_buttons = total_buttons - mines
    bombs = random.sample(range(total_buttons), mines)
    crystals = [i for i in range(total_buttons) if i not in bombs]
    crystals = random.sample(crystals, safe_buttons)

    game_state = {
        'mines': bombs,
        'crystals': crystals,
        'current_win': 0,
        'bet': bet,
        'opened': [],
        'active': True
    }

    game_ref = db.reference(f'games/{user_id}')
    game_ref.set(game_state)

    # Отправка игрового поля
    send_mines_board(chat_id, user_id)

def send_mines_board(chat_id, user_id):
    game_ref = db.reference(f'games/{user_id}')
    game = game_ref.get()

    if not game or not game.get('active', False):
        bot.send_message(chat_id, "Игра не активна.")
        return

    current_win = game.get('current_win', 0)
    text = f"Игра началась!\nТекущий Выйгрыш: {current_win} Сашко"

    markup = types.InlineKeyboardMarkup(row_width=5)
    for i in range(25):
        if i in game.get('opened', []):
            # Отображение открытой коробки
            content = "💎" if i in game['crystals'] else "🧨"
            button = types.InlineKeyboardButton(content, callback_data=f'open_{i}')
        else:
            button = types.InlineKeyboardButton("🎁", callback_data=f'open_{i}')
        markup.add(button)

    # Кнопка остановиться
    stop_button = types.InlineKeyboardButton("Остановиться🛑", callback_data='stop_game')
    markup.add(stop_button)

    bot.send_message(chat_id, text, reply_markup=markup)

# Обработка нажатий кнопок Inline Keyboard
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    data = call.data

    game_ref = db.reference(f'games/{user_id}')
    game = game_ref.get()

    if not game or not game.get('active', False):
        bot.answer_callback_query(call.id, "Игра не активна.")
        return

    if data.startswith('open_'):
        index = int(data.split('_')[1])
        if index in game.get('opened', []):
            bot.answer_callback_query(call.id, "Эта коробка уже открыта.")
            return

        game['opened'].append(index)

        if index in game['mines']:
            # Проигрыш
            game['active'] = False
            game_ref.set(game)
            reveal_field(chat_id, user_id, lost=True)
            update_user_stats(user_id, lost=True)
            bot.answer_callback_query(call.id, "💥 Бах! Вы проиграли!")
            return
        else:
            # Выигрыш
            game['current_win'] += 1
            game_ref.set(game)
            bot.answer_callback_query(call.id, f"💎 Вы нашли кристалл! Текущий выигрыш: {game['current_win']} Сашко")
            # Обновление сообщения с новым выигрышем
            send_mines_board(chat_id, user_id)
    elif data == 'stop_game':
        # Остановка игры
        winnings = game.get('current_win', 0) * game.get('bet',1)
        game['active'] = False
        game_ref.set(game)

        # Добавление выигрыша пользователю
        user_ref = db.reference(get_user_path(user_id))
        user_data = user_ref.get()
        user_ref.update({'balance': user_data['balance'] + winnings, 'wins': user_data.get('wins',0) + 1})

        bot.edit_message_text(
            f"Вы остановились! Вы выиграли {winnings} Сашко.",
            chat_id=chat_id,
            message_id=call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "Неизвестная команда.")

def reveal_field(chat_id, user_id, lost=False):
    game_ref = db.reference(f'games/{user_id}')
    game = game_ref.get()

    markup = types.InlineKeyboardMarkup(row_width=5)
    for i in range(25):
        if i in game['opened']:
            content = "💎" if i in game['crystals'] else "🧨"
        else:
            if lost:
                content = "💎" if i in game['crystals'] else "🧨"
            else:
                content = "🎁"
        button = types.InlineKeyboardButton(content, callback_data='noop')
        markup.add(button)

    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)
    if lost:
        bot.send_message(chat_id, "💥 Вы проиграли! Все бомбы раскрыты.")
    # Очистка игрового поля
    db.reference(f'games/{user_id}').delete()

def update_user_stats(user_id, lost=False):
    user_ref = db.reference(get_user_path(user_id))
    if lost:
        user_ref.update({'losses': db.ServerValue.increment(1)})
    else:
        user_ref.update({'wins': db.ServerValue.increment(1)})

# Запуск бота
bot.polling(none_stop=True)
