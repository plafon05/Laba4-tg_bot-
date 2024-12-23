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

bot = Bot(token=os.getenv("BOT_TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

language_filter = "любой"
default_publications = 3

class PublicationStates(StatesGroup):
    wait = State()
    waiting_for_num = State()
    waiting_for_topic = State()
    waiting_for_author = State()
    waiting_for_doi = State()
    waiting_for_language = State()



def get_main_keyboard():
    buttons = [
        [KeyboardButton(text="🔍 Поиск публикации по теме")],
        [KeyboardButton(text="👤 Поиск по автору")],
        [KeyboardButton(text="📜 Поиск по DOI")],
        [KeyboardButton(text="🌐 Настройки языка публикаций")],
        [KeyboardButton(text="📊 Количество выдаваемых публикаций")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

@dp.message(CommandStart())
async def send_welcome(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if "num_publications" not in data:
        await state.update_data(num_publications=default_publications)
    welcome_message = (
        "👋 Привет!\n\n"
        "Я бот для поиска научных публикаций.\n"
        "Я помогу вам находить статьи, исследования и данные по следующим критериям:\n"
        "📌 Поиск по теме\n"
        "📌 Поиск по автору\n"
        "📌 Поиск по DOI\n\n"
        "Дополнительно вы можете настроить:\n"
        "🌐 Язык публикаций\n"
        "📊 Количество выводимых публикаций\n\n"
        "💡 Просто выберите действие из меню ниже или введите команду.\n"
        "Давайте начнем! 🚀"
    )
    await message.answer(welcome_message, reply_markup=get_main_keyboard())

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
        else:
            await message.answer("Введите положительное число.")
    except ValueError:
        await message.answer("Введите корректное число.")

@dp.message(lambda message: message.text == "🔍 Поиск публикации по теме")
async def search_by_topic(message: types.Message, state: FSMContext):
    await message.answer("Введите тему, по которой хотите найти публикации:")
    await state.set_state(PublicationStates.waiting_for_topic)

@dp.message(lambda message: message.text == "👤 Поиск по автору")
async def search_by_author(message: types.Message, state: FSMContext):
    await message.answer("Введите имя автора для поиска публикаций:")
    await state.set_state(PublicationStates.waiting_for_author)

@dp.message(lambda message: message.text == "📜 Поиск по DOI")
async def search_by_doi(message: types.Message, state: FSMContext):
    await message.answer("Введите DOI публикации:")
    await state.set_state(PublicationStates.waiting_for_doi)

@dp.message(PublicationStates.waiting_for_doi)
async def handle_doi_input(message: types.Message, state: FSMContext):
    doi = message.text
    result = search_publication_by_doi(doi)
    if result:
        await message.answer("Найдена публикация:")
        await message.answer(result)
    else:
        await message.answer("Не удалось найти публикацию с указанным DOI.")
    await state.clear()

def search_publication_by_doi(doi):
    try:
        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url)
        response.raise_for_status()
        item = response.json().get('message', {})
        return item.get('URL', 'Ссылка не найдена')
    except requests.RequestException:
        return None

@dp.message(lambda message: message.text == "🌐 Настройки языка публикаций")
async def set_language(message: types.Message, state: FSMContext):
    language_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("Русский"), KeyboardButton("Английский"), KeyboardButton("Любой")
    )
    await message.answer("Выберите язык публикаций:", reply_markup=language_keyboard)
    await state.set_state(PublicationStates.waiting_for_language)

@dp.message(PublicationStates.waiting_for_language)
async def handle_language_input(message: types.Message, state: FSMContext):
    language = message.text
    if language in ["Русский", "Английский", "Любой"]:
        await state.update_data(language_filter=language)
        await message.answer(f"Язык публикаций установлен: {language}", reply_markup=get_main_keyboard())
        await state.clear()
    else:
        await message.answer("Неверный выбор. Пожалуйста, выберите язык из предложенных.")

def filter_by_language(item, language_filter):
    if language_filter == "Русский":
        return item.get('language', '').lower() == "ru"
    elif language_filter == "Английский":
        return item.get('language', '').lower() == "en"
    return True

def search_publications_by_topic(topic, limit, language_filter):
    try:
        url = f"https://api.crossref.org/works?query={topic}"
        response = requests.get(url)
        response.raise_for_status()
        items = response.json().get('message', {}).get('items', [])
        return [item.get('URL', 'Ссылка не найдена') for item in items[:limit] if filter_by_language(item, language_filter)]
    except requests.RequestException:
        return []

def search_publications_by_author(author, limit, language_filter):
    try:
        url = f"https://api.crossref.org/works?query.author={author}"
        response = requests.get(url)
        response.raise_for_status()
        items = response.json().get('message', {}).get('items', [])
        return [item.get('URL', 'Ссылка не найдена') for item in items[:limit] if filter_by_language(item, language_filter)]
    except requests.RequestException:
        return []

@dp.message(PublicationStates.waiting_for_topic)
async def handle_topic_input(message: types.Message, state: FSMContext):
    topic = message.text
    data = await state.get_data()
    num_publications = data.get("num_publications", default_publications)
    language_filter = data.get("language_filter", "Любой")
    results = search_publications_by_topic(topic, num_publications, language_filter)
    if results:
        await message.answer(f"Найдено {len(results)} публикаций:")
        for result in results:
            await message.answer(result)
    else:
        await message.answer("Не удалось найти публикации по указанной теме.")
    await state.clear()

@dp.message(PublicationStates.waiting_for_author)
async def handle_author_input(message: types.Message, state: FSMContext):
    author = message.text
    data = await state.get_data()
    num_publications = data.get("num_publications", default_publications)
    language_filter = data.get("language_filter", "Любой")
    results = search_publications_by_author(author, num_publications, language_filter)
    if results:
        await message.answer(f"Найдено {len(results)} публикаций:")
        for result in results:
            await message.answer(result)
    else:
        await message.answer("Не удалось найти публикации по указанному автору.")
    await state.clear()


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())