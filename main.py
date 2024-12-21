import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Инициализация бота и диспетчера
bot = Bot(token=os.getenv("BOT_TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Настройки по умолчанию
language_filter = "любой"  # По умолчанию язык "любой"
default_publications = 3  # Количество публикаций по умолчанию

# Состояния FSM
class PublicationStates(StatesGroup):
    wait = State()
    waiting_for_num = State()
    waiting_for_topic = State()
    waiting_for_author = State()
    waiting_for_doi = State()
    waiting_for_language = State()

# Функция для генерации кнопок
def get_main_keyboard():
    buttons = [
        [KeyboardButton(text="🔍 Поиск публикации по теме")],
        [KeyboardButton(text="👤 Поиск по автору")],
        [KeyboardButton(text="📜 Поиск по DOI")],
        [KeyboardButton(text="🌐 Настройки языка публикаций")],
        [KeyboardButton(text="📊 Количество выдаваемых публикаций")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Обработчики сообщений
@dp.message(CommandStart())
async def send_welcome(message: types.Message, state: FSMContext):
    # Устанавливаем количество публикаций по умолчанию, если не установлено
    data = await state.get_data()
    if "num_publications" not in data:
        await state.update_data(num_publications=default_publications)
    await message.answer("Привет! Я бот для поиска научных публикаций. Выберите действие:", reply_markup=get_main_keyboard())

@dp.message(lambda message: message.text == "📊 Количество выдаваемых публикаций")
async def set_num_publications(message: types.Message, state: FSMContext):
    await message.answer("Введите количество публикаций, которое вы хотите получать:")
    await state.set_state(PublicationStates.waiting_for_num)

@dp.message(PublicationStates.waiting_for_num)
async def handle_num_input(message: types.Message, state: FSMContext):
    try:
        num_publications = int(message.text)
        if num_publications > 0:
            await state.update_data(num_publications=num_publications)
            await message.answer(f"Количество публикаций установлено: {num_publications}", reply_markup=get_main_keyboard())
            await state.set_state(PublicationStates.wait)

            data = await state.get_data()
            print(data)
        else:
            await message.answer("Введите положительное число.")
    except ValueError:
        await message.answer("Введите корректное число.")

@dp.message(lambda message: message.text == "🔍 Поиск публикации по теме")
async def search_by_topic(message: types.Message, state: FSMContext):
    await message.answer("Введите тему, по которой хотите найти публикации:")
    await state.set_state(PublicationStates.waiting_for_topic)

@dp.message(PublicationStates.waiting_for_topic)
async def handle_topic_input(message: types.Message, state: FSMContext):
    topic = message.text
    data = await state.get_data()
    # Получаем количество публикаций из состояния
    num_publications = data.get("num_publications", default_publications)
    print(num_publications)
    results = search_publications_by_topic(topic, num_publications)
    if results:
        await message.answer(f"Найдено {len(results)} публикаций:")
        for result in results:
            await message.answer(result)
    else:
        await message.answer("Не удалось найти публикации по указанной теме.")
    await state.clear()

# Функция для настройки языка публикаций
@dp.message(lambda message: message.text == "🌐 Настройки языка публикаций")
async def set_language(message: types.Message, state: FSMContext):
    global language_filter
    language_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("Русский"), KeyboardButton("Английский"), KeyboardButton("Любой")
    )
    await message.answer("Выберите язык публикаций:", reply_markup=language_keyboard)
    await state.set_state(PublicationStates.waiting_for_language)

@dp.message(PublicationStates.waiting_for_language)
async def handle_language_input(message: types.Message, state: FSMContext):
    global language_filter
    language = message.text
    if language in ["Русский", "Английский", "Любой"]:
        language_filter = language
        await message.answer(f"Язык публикаций установлен: {language}", reply_markup=get_main_keyboard())
        await state.clear()
    else:
        await message.answer("Неверный выбор. Пожалуйста, выберите язык из предложенных.")

# Функции поиска через CrossRef API
def search_publications_by_topic(topic, limit):
    try:
        url = f"https://api.crossref.org/works?query={topic}"
        response = requests.get(url)
        response.raise_for_status()
        items = response.json().get('message', {}).get('items', [])
        return [item.get('URL', 'Ссылка не найдена') for item in items[:limit] if filter_by_language(item)]
    except requests.RequestException:
        return []

def filter_by_language(item):
    global language_filter
    if language_filter == "Русский":
        return item.get('language', '').lower() == "ru"
    elif language_filter == "Английский":
        return item.get('language', '').lower() == "en"
    return True

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
