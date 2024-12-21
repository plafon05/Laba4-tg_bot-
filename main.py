import logging
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp
import asyncio
import random

BOT_TOKEN = "7518084370:AAGVY_Fo1ObQeN6LwPVXXfFbCTrOOOIuz44"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
router = Router()
dp = Dispatcher(storage=storage)
dp.include_router(router)

# Логирование
logging.basicConfig(level=logging.INFO)

# Начальные настройки пользователя
user_settings = {}

def get_user_settings(user_id):
    if user_id not in user_settings:
        user_settings[user_id] = {
            "language": "all",  # "all", "ru", "en"
            "count": 3
        }
    return user_settings[user_id]

# Кнопки меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Поиск публикации по теме"),
            KeyboardButton(text="Поиск по автору"),
            KeyboardButton(text="Поиск по DOI")
        ],
        [
            KeyboardButton(text="Настройки языка публикаций"),
            KeyboardButton(text="Количество выдаваемых публикаций")
        ]
    ],
    resize_keyboard=True
)

# Функция для поиска публикаций через API CrossRef
async def search_publications(query, search_type="query", count=3, language="all"):
    url = "https://api.crossref.org/works"
    params = {search_type: query, "rows": count}
    if language != "all":
        params["filter"] = f"language:{language}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                items = data.get("message", {}).get("items", [])
                return [
                    f"{item.get('title', ['Без названия'])[0]}\n{item.get('URL')}"
                    for item in items
                ]
            return []

# Обработчики команд
@router.message(commands=["start", "help"])
async def send_welcome(message: types.Message):
    await message.answer(
        "Добро пожаловать! Выберите действие из меню.",
        reply_markup=main_menu
    )

@router.message(lambda message: message.text == "Поиск публикации по теме")
async def ask_topic(message: types.Message):
    await message.answer("Введите тему для поиска публикаций:")
    @router.message()
    async def process_topic_search(inner_message: types.Message):
        user_id = inner_message.from_user.id
        settings = get_user_settings(user_id)
        publications = await search_publications(
            query=inner_message.text,
            search_type="query",
            count=settings["count"],
            language=settings["language"]
        )
        if publications:
            await inner_message.answer("\n\n".join(publications))
        else:
            await inner_message.answer("Ничего не найдено по вашей теме.")

@router.message(lambda message: message.text == "Поиск по автору")
async def ask_author(message: types.Message):
    await message.answer("Введите ФИО автора (можно только фамилию):")
    @router.message()
    async def process_author_search(inner_message: types.Message):
        user_id = inner_message.from_user.id
        settings = get_user_settings(user_id)
        publications = await search_publications(
            query=inner_message.text,
            search_type="query.author",
            count=settings["count"],
            language=settings["language"]
        )
        if publications:
            await inner_message.answer("\n\n".join(publications))
        else:
            await inner_message.answer("Ничего не найдено по вашему запросу.")

@router.message(lambda message: message.text == "Поиск по DOI")
async def ask_doi(message: types.Message):
    await message.answer(
        "Введите DOI публикации. DOI (Digital Object Identifier) - это уникальный идентификатор публикации."
    )
    @router.message()
    async def process_doi_search(inner_message: types.Message):
        publications = await search_publications(query=inner_message.text, search_type="query.bibliographic", count=1)
        if publications:
            await inner_message.answer(publications[0])
        else:
            await inner_message.answer("Публикация с таким DOI не найдена.")

@router.message(lambda message: message.text == "Настройки языка публикаций")
async def change_language(message: types.Message):
    language_menu = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Русский"), KeyboardButton(text="Английский")]
        ],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Выберите язык публикаций:", reply_markup=language_menu)
    @router.message()
    async def process_language_selection(inner_message: types.Message):
        user_id = inner_message.from_user.id
        if inner_message.text == "Русский":
            user_settings[user_id]["language"] = "ru"
        elif inner_message.text == "Английский":
            user_settings[user_id]["language"] = "en"
        else:
            user_settings[user_id]["language"] = "all"
        await inner_message.answer("Язык публикаций успешно обновлён.", reply_markup=main_menu)

@router.message(lambda message: message.text == "Количество выдаваемых публикаций")
async def ask_publication_count(message: types.Message):
    await message.answer("Введите количество публикаций, которое вы хотите получать:")
    @router.message()
    async def process_publication_count(inner_message: types.Message):
        user_id = inner_message.from_user.id
        try:
            count = int(inner_message.text)
            user_settings[user_id]["count"] = count
            await inner_message.answer(
                f"Количество выдаваемых публикаций успешно обновлено на {count}.",
                reply_markup=main_menu
            )
        except ValueError:
            await inner_message.answer("Пожалуйста, введите корректное число.")

# Запуск бота
async def main():
    try:
        logging.info("Бот запущен")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

