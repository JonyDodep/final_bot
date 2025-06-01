import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from deep_translator import GoogleTranslator
import speech_recognition as sr
from pydub import AudioSegment
import pytesseract
from PIL import Image

TOKEN = "8098113119:AAHmtZfeo8q9s2ne4uzzEdL-ghW_HW4ccdI"


bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилище выбранных языков по пользователям
user_lang = {}
history = {}

# Кнопки языков
lang_buttons = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton(text="🇬🇧 Английский", callback_data="lang_en"),
        InlineKeyboardButton(text="🇩🇪 Немецкий", callback_data="lang_de"),
    ],
    [
        InlineKeyboardButton(text="🇪🇸 Испанский", callback_data="lang_es"),
        InlineKeyboardButton(text="🇫🇷 Французский", callback_data="lang_fr"),
    ]
])

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Выбери язык перевода:", reply_markup=lang_buttons)

@dp.message(Command('history'))
async def show_history(message: types.Message):
    user_id = message.from_user.id
    user_history = history.get(user_id, [])

    if not user_history:
        await message.answer("У тебя пока нет истории переводов.")
    else:
        # Показываем последние 5 переводов
        last_items = user_history[-5:]
        text = "\n\n".join(f"{i+1}. {item}" for i, item in enumerate(last_items))
        await message.answer(f"🕘 Последние переводы:\n\n{text}")

@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    lang_code = callback.data.split("_")[1]
    user_lang[callback.from_user.id] = lang_code
    await callback.message.answer(f"Выбран язык: {lang_code.upper()}. Теперь отправь текст, голосовое или фото для перевода.")
    await callback.answer()

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    uid = message.from_user.id
    target_lang = user_lang.get(uid)
    if not target_lang:
        await message.answer("Сначала выбери язык через /start")
        return

    file = await bot.download(message.voice.file_id)
    with open('voice.ogg', 'wb') as f:
        f.write(file.read())

# Конвертация ogg в wav
    sound = AudioSegment.from_file('voice.ogg')
    sound.export('voice.wav', format="wav")

    recognizer = sr.Recognizer()
    with sr.AudioFile('voice.wav') as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data, language="ru-RU")
            translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
            user_id = message.from_user.id
            if user_id not in history:
                history[user_id] = []
            history[user_id].append(translated)
            await message.answer(f"Текст из голосового:\n{text}\n\nПеревод:\n{translated}")
            await message.answer("Хочешь перевести ещё? Выбери язык снова:", reply_markup=lang_buttons)
        except Exception as e:
            await message.answer("Не удалось распознать голосовое сообщение.")
            print("Ошибка распознавания:", e)

    # Чистим файлы
    os.remove('voice.ogg')
    os.remove('voice.wav')

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    uid = message.from_user.id
    target_lang = user_lang.get(uid, "en")

    # Получаем самое большое фото
    photo = message.photo[-1]

    # Скачиваем файл через bot.download
    file = await bot.download(photo.file_id)

    # Сохраняем локально
    with open("photo.jpg", "wb") as f:
        f.write(file.read())

    await message.answer("Фото получено! Сейчас попытаюсь извлечь текст...")

    image = Image.open("photo.jpg")
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(image, config=custom_config)
    clean_text = ' '.join(text.strip().splitlines())

    if text.strip():
        translated = GoogleTranslator(source='auto', target=target_lang).translate(clean_text)
        user_id = message.from_user.id
        if user_id not in history:
            history[user_id] = []
        history[user_id].append(translated)
        await message.answer(f"Текст на фото:\n{clean_text}\n\nПеревод:\n{translated}")
        await message.answer("Хочешь перевести ещё? Выбери язык снова:", reply_markup=lang_buttons)
    else:
        await message.answer("Не удалось найти текст на изображении.")

    # Удаляем файл
    os.remove("photo.jpg")

@dp.message(F.text)
async def handle_text(message: types.Message):
    uid = message.from_user.id
    target_lang = user_lang.get(uid)

    if not target_lang:
        await message.answer("Сначала выбери язык через /start")
        return

    try:
        translated = GoogleTranslator(source='auto', target=target_lang).translate(message.text)
        user_id = message.from_user.id
        if user_id not in history:
            history[user_id] = []
        history[user_id].append(translated)
        await message.answer(f"Перевод:\n{translated}")
        await message.answer("Хочешь перевести ещё? Выбери язык снова:", reply_markup=lang_buttons)
    except Exception as e:
        await message.answer("Произошла ошибка при переводе.")
        print("Ошибка:", e)

# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())