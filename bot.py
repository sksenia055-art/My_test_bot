import asyncio
import logging
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

from config import TOKEN, ADMIN_ID, LEVELS
from words import WORDS

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Словарь для хранения данных пользователей
# {user_id: {'level': 'easy', 'direction': 'ru-en', 'score': 0}}
user_data = {}

# Функция для загрузки данных из файла
def load_users():
    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Функция для сохранения данных в файл
def save_user(user_id, data):
    users = load_users()
    users[str(user_id)] = data
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# Загружаем данные при старте
user_data = load_users()


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    # Приветствие с именем пользователя
    await message.reply(f"👋 Привет, {user_name}! Я бот для изучения английского языка.")

    # Сохраняем пользователя если его нет
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {
            'name': user_name,
            'username': message.from_user.username,
            'level': 'easy',
            'direction': 'ru-en',
            'score': 0,
            'joined_date': str(datetime.now())
        }
        save_user(user_id, user_data[str(user_id)])

    # Создаем главное меню
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📚 Учить слова", callback_data="learn"),
        InlineKeyboardButton("⚙️ Уровень", callback_data="level"),
        InlineKeyboardButton("🔄 Направление", callback_data="direction"),
        InlineKeyboardButton("📊 Мой прогресс", callback_data="progress"),
        InlineKeyboardButton("ℹ️ Помощь", callback_data="help"),
        InlineKeyboardButton("👑 Админ", callback_data="admin") if user_id == ADMIN_ID else None
    )

    await message.answer("Выбери действие:", reply_markup=keyboard)

@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    help_text = """
📖 **Как пользоваться ботом:**

1. Нажми "📚 Учить слова" чтобы начать тренировку
2. Выбери уровень сложности в меню "⚙️ Уровень"
3. Выбери направление перевода в меню "🔄 Направление"
4. Следи за прогрессом в "📊 Мой прогресс"

Доступные команды:
/start - Запустить бота
/help - Показать помощь
/stop - Остановить бота
    """
    await message.answer(help_text, parse_mode="Markdown")

@dp.message_handler(commands=['stop'])
async def cmd_stop(message: types.Message):
    await message.answer("👋 До свидания! Чтобы снова начать, нажми /start")


@dp.callback_query_handler(lambda c: c.data == 'level')
async def process_level(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    # Создаем кнопки для выбора уровня
    keyboard = InlineKeyboardMarkup(row_width=1)
    for level_id, level_name in LEVELS.items():
        keyboard.add(InlineKeyboardButton(
            level_name,
            callback_data=f"set_level_{level_id}"
        ))
    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu"))

    await bot.send_message(
        user_id,
        "Выбери уровень сложности:",
        reply_markup=keyboard
    )


@dp.callback_query_handler(lambda c: c.data.startswith('set_level_'))
async def set_level(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    level = callback_query.data.replace('set_level_', '')

    if user_id in user_data:
        user_data[user_id]['level'] = level
        save_user(user_id, user_data[user_id])
        await bot.send_message(
            user_id,
            f"✅ Уровень изменен на: {LEVELS[level]}"
        )
    else:
        await bot.send_message(user_id, "❌ Ошибка! Начни с /start")


@dp.callback_query_handler(lambda c: c.data == 'direction')
async def process_direction(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🇷🇺 Русский → 🇬🇧 Английский", callback_data="set_dir_ru-en"),
        InlineKeyboardButton("🇬🇧 Английский → 🇷🇺 Русский", callback_data="set_dir_en-ru"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")
    )

    await bot.send_message(
        user_id,
        "Выбери направление перевода:",
        reply_markup=keyboard
    )


@dp.callback_query_handler(lambda c: c.data.startswith('set_dir_'))
async def set_direction(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    direction = callback_query.data.replace('set_dir_', '')

    if user_id in user_data:
        user_data[user_id]['direction'] = direction
        save_user(user_id, user_data[user_id])

        dir_text = "Русский → Английский" if direction == 'ru-en' else "Английский → Русский"
        await bot.send_message(user_id, f"✅ Направление изменено на: {dir_text}")
    else:
        await bot.send_message(user_id, "❌ Ошибка! Начни с /start")


@dp.callback_query_handler(lambda c: c.data == 'learn')
async def start_learning(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)

    if user_id not in user_data:
        await bot.send_message(user_id, "❌ Сначала нажми /start")
        return

    level = user_data[user_id]['level']
    direction = user_data[user_id]['direction']

    # Берем слова текущего уровня
    words = WORDS[level]

    # Выбираем случайное слово
    import random
    word = random.choice(words)

    # Сохраняем текущее слово для проверки ответа
    user_data[user_id]['current_word'] = word

    if direction == 'ru-en':
        question = word['ru']
        answer = word['en']
    else:
        question = word['en']
        answer = word['ru']

    # Создаем клавиатуру для ответа
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Показать ответ", callback_data="show_answer"),
        InlineKeyboardButton("➡️ Следующее", callback_data="learn"),
        InlineKeyboardButton("🏠 В меню", callback_data="back_to_menu")
    )

    await bot.send_message(
        user_id,
        f"❓ Как переводится слово: **{question}**?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@dp.callback_query_handler(lambda c: c.data == 'show_answer')
async def show_answer(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)

    if user_id in user_data and 'current_word' in user_data[user_id]:
        word = user_data[user_id]['current_word']
        direction = user_data[user_id]['direction']

        if direction == 'ru-en':
            answer = word['en']
        else:
            answer = word['ru']

        # Клавиатура для оценки
        keyboard = InlineKeyboardMarkup(row_width=3)
        keyboard.add(
            InlineKeyboardButton("👍 Знаю", callback_data="score_1"),
            InlineKeyboardButton("🤔 Почти", callback_data="score_0.5"),
            InlineKeyboardButton("👎 Не знаю", callback_data="score_0"),
            InlineKeyboardButton("➡️ Дальше", callback_data="learn"),
            InlineKeyboardButton("🏠 Меню", callback_data="back_to_menu")
        )

        await bot.send_message(
            user_id,
            f"✅ Правильный ответ: **{answer}**\n\nОцени свои знания:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await bot.send_message(user_id, "❌ Начни сначала: /start")


@dp.callback_query_handler(lambda c: c.data.startswith('score_'))
async def process_score(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    score = float(callback_query.data.replace('score_', ''))

    if user_id in user_data:
        user_data[user_id]['score'] = user_data[user_id].get('score', 0) + score
        save_user(user_id, user_data[user_id])

        await bot.send_message(
            user_id,
            f"✅ Оценка сохранена! Твой текущий счет: {user_data[user_id]['score']}"
        )
    else:
        await bot.send_message(user_id, "❌ Ошибка!")


@dp.callback_query_handler(lambda c: c.data == 'progress')
async def show_progress(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)

    if user_id in user_data:
        data = user_data[user_id]
        level_name = LEVELS[data['level']]
        direction = "Русский → Английский" if data['direction'] == 'ru-en' else "Английский → Русский"

        progress_text = f"""
📊 **Твой прогресс:**

👤 Имя: {data['name']}
📈 Счет: {data.get('score', 0)} очков
⚙️ Уровень: {level_name}
🔄 Направление: {direction}
📅 Присоединился: {data.get('joined_date', 'неизвестно')}
        """

        await bot.send_message(user_id, progress_text, parse_mode="Markdown")
    else:
        await bot.send_message(user_id, "❌ Данные не найдены. Нажми /start")


@dp.callback_query_handler(lambda c: c.data == 'back_to_menu')
async def back_to_menu(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📚 Учить слова", callback_data="learn"),
        InlineKeyboardButton("⚙️ Уровень", callback_data="level"),
        InlineKeyboardButton("🔄 Направление", callback_data="direction"),
        InlineKeyboardButton("📊 Мой прогресс", callback_data="progress"),
        InlineKeyboardButton("ℹ️ Помощь", callback_data="help"),
        InlineKeyboardButton("👑 Админ", callback_data="admin") if user_id == ADMIN_ID else None
    )

    await bot.send_message(user_id, "Главное меню:", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == 'admin')
async def admin_panel(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id != ADMIN_ID:
        await bot.send_message(user_id, "❌ У тебя нет прав администратора!")
        return

    users = load_users()
    total_users = len(users)
    active_today = sum(1 for u in users.values()
                       if 'last_active' in u and
                       datetime.fromisoformat(u['last_active']).date() == datetime.now().date())

    admin_text = f"""
👑 **Админ-панель**

👥 Всего пользователей: {total_users}
📊 Активных сегодня: {active_today}

Список пользователей:
"""

    for uid, data in list(users.items())[:10]:  # Покажем первых 10
        admin_text += f"\n- {data['name']} (@{data.get('username', 'нет')}): {data.get('score', 0)} очков"

    await bot.send_message(user_id, admin_text, parse_mode="Markdown")

@dp.message_handler()
async def echo(message: types.Message):
    await message.answer("Я понимаю только команды. Нажми /help")

if __name__ == '__main__':
    print("Бот запущен!")
    executor.start_polling(dp, skip_updates=True)