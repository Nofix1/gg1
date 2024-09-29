import telebot
from telebot import types
import sqlite3
import random
import time
import datetime
import threading
import json
import os

# ==================== Конфигурация ====================
TOKEN = '7424641182:AAG5Wh77L20nqWdw_zrtzC2jHrKIJbO3bYE'  # Замените на ваш токен
DB_NAME = 'bot_database.db'    # Имя файла базы данных

# ==================== Инициализация Базы Данных ====================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Создание таблицы пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            balance INTEGER DEFAULT 0,
            last_bonus INTEGER DEFAULT 0
        )
    ''')

    # Создание таблицы игр
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            user_id INTEGER PRIMARY KEY,
            mine_count INTEGER,
            bet INTEGER,
            field TEXT,
            current_winnings INTEGER DEFAULT 0,
            opened_indices TEXT
        )
    ''')

    conn.commit()
    conn.close()

# ==================== Работа с Базой Данных ====================
def register_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
        conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'user_id': row[0],
            'wins': row[1],
            'losses': row[2],
            'balance': row[3],
            'last_bonus': row[4]
        }
    return None

def update_user(user_id, **kwargs):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values())
    values.append(user_id)
    query = f'UPDATE users SET {fields} WHERE user_id = ?'
    cursor.execute(query, tuple(values))
    conn.commit()
    conn.close()

def get_top_players(limit=10):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, wins FROM users ORDER BY wins DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_game(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM games WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'user_id': row[0],
            'mine_count': row[1],
            'bet': row[2],
            'field': json.loads(row[3]),
            'current_winnings': row[4],
            'opened_indices': json.loads(row[5])
        }
    return None

def create_game(user_id, mine_count, bet):
    field = ['💎'] * (25 - mine_count) + ['🧨'] * mine_count
    random.shuffle(field)
    opened_indices = []
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO games (user_id, mine_count, bet, field, current_winnings, opened_indices)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, mine_count, bet, json.dumps(field), 0, json.dumps(opened_indices)))
    conn.commit()
    conn.close()

def update_game(user_id, **kwargs):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
    values = []
    for k, v in kwargs.items():
        if isinstance(v, list):
            v = json.dumps(v)
        values.append(v)
    values.append(user_id)
    query = f'UPDATE games SET {fields} WHERE user_id = ?'
    cursor.execute(query, tuple(values))
    conn.commit()
    conn.close()

def delete_game(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM games WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# ==================== Инициализация Бота ====================
bot = telebot.TeleBot(TOKEN)

# Инициализация базы данных при запуске скрипта
init_db()

# ==================== Хэндлеры Команд ====================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    register_user(user_id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_play = types.KeyboardButton("Играть")
    btn_profile = types.KeyboardButton("Профиль")
    btn_top = types.KeyboardButton("Топ Игроков")
    markup.add(btn_play, btn_profile, btn_top)

    bot.send_message(
        message.chat.id,
        "Добро пожаловать! Выберите действие:",
        reply_markup=markup
    )

# ==================== Хэндлеры Текстовых Сообщений ====================

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
    elif message.text.lower() == "назад":
        show_main_menu(message)
    elif message.text.lower() in ["mines", "майнс", "mines"]:
        start_mines_game(message)
    else:
        bot.send_message(
            message.chat.id,
            "Я не понимаю эту команду. Пожалуйста, используйте меню.",
            reply_markup=get_main_menu()
        )

# ==================== Функции Основных Меню ====================

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_play = types.KeyboardButton("Играть")
    btn_profile = types.KeyboardButton("Профиль")
    btn_top = types.KeyboardButton("Топ Игроков")
    markup.add(btn_play, btn_profile, btn_top)
    return markup

def show_main_menu(message):
    markup = get_main_menu()
    bot.send_message(
        message.chat.id,
        "Главное меню:",
        reply_markup=markup
    )

def show_profile(message):
    user_id = message.from_user.id
    user = get_user(user_id)

    profile_text = (
        f"📄 **Профиль**\n"
        f"**Ваш ID:** {user['user_id']}\n"
        f"**Количество Выигранных Игр:** {user['wins']}\n"
        f"**Количество Проигранных Игр:** {user['losses']}\n"
        f"**Баланс Сашко:** {user['balance']}\n"
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_bonus = types.KeyboardButton("Ежедневный Бонус")
    btn_back = types.KeyboardButton("Назад")
    markup.add(btn_bonus, btn_back)

    bot.send_message(
        message.chat.id,
        profile_text,
        parse_mode="Markdown",
        reply_markup=markup
    )

def give_daily_bonus(message):
    user_id = message.from_user.id
    user = get_user(user_id)

    current_timestamp = int(time.time())
    last_bonus = user['last_bonus']
    seconds_in_day = 86400

    if current_timestamp - last_bonus >= seconds_in_day:
        bonus = random.randint(1, 10)
        new_balance = user['balance'] + bonus
        update_user(user_id, balance=new_balance, last_bonus=current_timestamp)
        bot.send_message(
            message.chat.id,
            f"🎁 Вы получили **{bonus} Сашко**!",
            parse_mode="Markdown"
        )
    else:
        remaining = seconds_in_day - (current_timestamp - last_bonus)
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        seconds = remaining % 60
        bot.send_message(
            message.chat.id,
            f"⏳ Ежедневный бонус доступен через **{hours}ч {minutes}м {seconds}с**.",
            parse_mode="Markdown"
        )

def show_play_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_mines = types.KeyboardButton("Mines")
    btn_blackjack = types.KeyboardButton("BlackJack")
    btn_back = types.KeyboardButton("Назад")
    markup.add(btn_mines, btn_blackjack)
    markup.add(btn_back)
    bot.send_message(
        message.chat.id,
        "🎲 **Выберите доступную игру:**",
        parse_mode="Markdown",
        reply_markup=markup
    )

def show_top_players(message):
    top_players = get_top_players()

    if not top_players:
        bot.send_message(
            message.chat.id,
            "🏅 Топ игроков пока пуст."
        )
        return

    top_text = "🏆 **Топ Игроков 🏆**\n\n"
    for idx, (uid, wins) in enumerate(top_players, start=1):
        top_text += f"{idx}. **ID:** {uid} - **Выигрышей:** {wins}\n"

    bot.send_message(
        message.chat.id,
        top_text,
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )

# ==================== Игра Mines ====================

def start_mines_game(message):
    user_id = message.from_user.id

    # Проверка, не находится ли пользователь уже в игре
    if get_game(user_id):
        bot.send_message(
            message.chat.id,
            "❌ Вы уже в процессе игры Mines. Завершите текущую игру перед началом новой."
        )
        return

    msg = bot.send_message(
        message.chat.id,
        "🧨 **Игра Mines**\n\nВыберите количество мин (от **3** до **24**):",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_mines_quantity)

def process_mines_quantity(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        mine_count = int(message.text)
        if not 3 <= mine_count <= 24:
            raise ValueError
    except ValueError:
        msg = bot.send_message(
            chat_id,
            "❌ Недопустимое количество мин. Пожалуйста, введите число от **3** до **24**.",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_mines_quantity)
        return

    msg = bot.send_message(
        chat_id,
        "💰 Введите вашу ставку (от **1** до **100** Сашко):",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, lambda m: process_mines_bet(m, mine_count))

def process_mines_bet(message, mine_count):
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        bet = int(message.text)
        if not 1 <= bet <= 100:
            raise ValueError
    except ValueError:
        msg = bot.send_message(
            chat_id,
            "❌ Недопустимая ставка. Пожалуйста, введите число от **1** до **100**.",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, lambda m: process_mines_bet(m, mine_count))
        return

    user = get_user(user_id)
    if user['balance'] < bet:
        bot.send_message(
            chat_id,
            "❌ Недостаточно средств для ставки."
        )
        return

    # Вычитание ставки из баланса
    update_user(user_id, balance=user['balance'] - bet)

    # Создание игровой сессии
    create_game(user_id, mine_count, bet)

    # Отправка игрового поля
    send_mines_board(chat_id, user_id)

def send_mines_board(chat_id, user_id):
    game = get_game(user_id)
    if not game:
        bot.send_message(
            chat_id,
            "❌ Ошибка игры. Пожалуйста, попробуйте снова."
        )
        return

    current_winnings = game['current_winnings']
    bet = game['bet']

    text = f"🧨 **Игра Mines Началась!**\n\n**Текущий Выигрыш:** {current_winnings} Сашко"

    markup = types.InlineKeyboardMarkup(row_width=5)
    for i in range(25):
        if i in game['opened_indices']:
            content = game['field'][i]
        else:
            content = "🎁"
        # Callback data содержит user_id и индекс кнопки
        callback_data = f"{user_id}:{i}"
        button = types.InlineKeyboardButton(content, callback_data=callback_data)
        markup.add(button)

    # Добавление кнопки "Остановиться🛑" в конце
    stop_button = types.InlineKeyboardButton("🛑 Остановиться", callback_data=f"{user_id}:stop")
    markup.add(stop_button)

    bot.send_message(
        chat_id,
        text,
        parse_mode="Markdown",
        reply_markup=markup
    )

# ==================== Обработка Callback Запросов ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        data = call.data.split(':')
        user_id = int(data[0])
        action = data[1]
    except (IndexError, ValueError):
        bot.answer_callback_query(call.id, "❌ Некорректные данные.")
        return

    # Проверка, что действие инициировано тем же пользователем
    if call.from_user.id != user_id:
        bot.answer_callback_query(call.id, "❌ Это не ваша игра.")
        return

    game = get_game(user_id)
    if not game:
        bot.answer_callback_query(call.id, "❌ Вы не участвуете в активной игре.")
        return

    chat_id = call.message.chat.id

    if action == 'stop':
        # Завершение игры победой
        winnings = game['current_winnings'] * game['bet']
        update_user(user_id, balance=get_user(user_id)['balance'] + winnings, wins=get_user(user_id)['wins'] + 1)
        delete_game(user_id)

        bot.edit_message_text(
            f"✅ Вы остановились и забрали **{winnings} Сашко**.",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=None
        )
        bot.answer_callback_query(call.id, "✅ Игра завершена.")
        return

    try:
        index = int(action)
    except ValueError:
        bot.answer_callback_query(call.id, "❌ Некорректные данные.")
        return

    if index < 0 or index >= 25:
        bot.answer_callback_query(call.id, "❌ Некорректный индекс.")
        return

    if index in game['opened_indices']:
        bot.answer_callback_query(call.id, "❌ Эта коробка уже открыта.")
        return

    # Обновление состояния игры
    game['opened_indices'].append(index)
    update_game(user_id, opened_indices=game['opened_indices'])

    if game['field'][index] == '🧨':
        # Проигрыш
        update_user(user_id, losses=get_user(user_id)['losses'] + 1)
        delete_game(user_id)

        # Раскрытие всего поля
        reveal_field(chat_id, game)

        bot.answer_callback_query(call.id, "💥 Вы наткнулись на мину! Вы проиграли.")
    else:
        # Выигрыш
        game['current_winnings'] += 1
        update_game(user_id, current_winnings=game['current_winnings'])
        bot.answer_callback_query(call.id, f"💎 Вы нашли кристалл! Текущий выручка: {game['current_winnings']} Сашко.")

        # Проверка на все кристаллы
        total_crystals = 25 - game['mine_count']
        if game['current_winnings'] == total_crystals:
            # Победа
            winnings = game['current_winnings'] * game['bet']
            update_user(user_id, balance=get_user(user_id)['balance'] + winnings, wins=get_user(user_id)['wins'] + 1)
            delete_game(user_id)

            # Обновление игрового поля с раскрытием всех кристаллов
            reveal_field(chat_id, game, won=True)

            bot.edit_message_text(
                f"🎉 Поздравляем! Вы собрали все кристаллы и выиграли **{winnings} Сашко**!",
                chat_id=chat_id,
                message_id=call.message.message_id,
                parse_mode="Markdown",
                reply_markup=None
            )
            bot.answer_callback_query(call.id, "🎉 Вы выиграли!")
            return

        # Обновление игрового поля
        edit_game_message(call.message, game)

def edit_game_message(message, game):
    chat_id = message.chat.id
    current_winnings = game['current_winnings']

    markup = types.InlineKeyboardMarkup(row_width=5)
    for i in range(25):
        if i in game['opened_indices']:
            content = game['field'][i]
        else:
            content = "🎁"
        callback_data = f"{game['user_id']}:{i}"
        button = types.InlineKeyboardButton(content, callback_data=callback_data)
        markup.add(button)

    stop_button = types.InlineKeyboardButton("🛑 Остановиться", callback_data=f"{game['user_id']}:stop")
    markup.add(stop_button)

    bot.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=message.message_id,
        reply_markup=markup
    )

    # Обновление текста сообщения
    bot.edit_message_text(
        f"🧨 **Игра Mines**\n\n**Текущий Выигрыш:** {current_winnings} Сашко",
        chat_id=chat_id,
        message_id=message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )

def reveal_field(chat_id, game, won=False):
    markup = types.InlineKeyboardMarkup(row_width=5)
    for i in range(25):
        content = game['field'][i]
        button = types.InlineKeyboardButton(content, callback_data='noop')  # Никаких действий
        markup.add(button)

    if won:
        text = f"🎉 Поздравляем! Вы выиграли **{game['current_winnings'] * game['bet']} Сашко**!"
    else:
        text = "💥 Вы проиграли! Все минаты раскрыты."

    bot.edit_message_text(
        text,
        chat_id=chat_id,
        message_id=bot.get_updates()[-1].message.message_id,  # Получение последнего сообщения
        parse_mode="Markdown",
        reply_markup=markup
    )

# ==================== Запуск Бота ====================
def run_bot():
    print("Бот запущен и работает...")
    bot.infinity_polling()

if __name__ == "__main__":
    run_bot()
    
