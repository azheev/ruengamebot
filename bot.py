import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import random
import json
import os

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Загрузка слов из JSON файла
with open('words.json', 'r', encoding='utf-8') as f:
    WORDS = json.load(f)

# Уровни сложности
DIFFICULTY_LEVELS = {
    'beginner': list(WORDS.keys())[:200],
    'intermediate': list(WORDS.keys())[:500],
    'advanced': list(WORDS.keys())
}

# Функция для получения случайного слова
def get_random_word(level):
    return random.choice(DIFFICULTY_LEVELS[level])

# Функция для проверки ответа
def check_answer(russian_word, user_answer):
    correct_answers = WORDS[russian_word]
    for word, synonyms in correct_answers.items():
        if user_answer.lower() == word.lower():
            return True, word, None
        elif user_answer.lower() in [syn.lower() for syn in synonyms]:
            return True, word, user_answer
    return False, list(correct_answers.keys())[0], None

# Функция для сохранения прогресса пользователя
def save_progress(user_id, data):
    with open(f'user_{user_id}_progress.json', 'w') as f:
        json.dump(data, f)

# Функция для загрузки прогресса пользователя
def load_progress(user_id):
    if os.path.exists(f'user_{user_id}_progress.json'):
        with open(f'user_{user_id}_progress.json', 'r') as f:
            return json.load(f)
    return None

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Начать игру", callback_data='start_game')],
        [InlineKeyboardButton("Правила", callback_data='rules')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Добро пожаловать в игру для изучения английских слов! "
        "Выберите действие:",
        reply_markup=reply_markup
    )

# Обработчик для кнопок
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'start_game':
        keyboard = [
            [InlineKeyboardButton("Начальный", callback_data='difficulty_beginner')],
            [InlineKeyboardButton("Средний", callback_data='difficulty_intermediate')],
            [InlineKeyboardButton("Продвинутый", callback_data='difficulty_advanced')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите уровень сложности:", reply_markup=reply_markup)
    elif query.data == 'rules':
        await query.edit_message_text(
            "Правила игры:\n"
            "1. Бот будет давать вам русские слова.\n"
            "2. Ваша задача - написать их английский перевод.\n"
            "3. За каждый правильный ответ вы получаете очко.\n"
            "4. Синонимы также засчитываются как правильный ответ.\n"
            "5. В конце игры вы получите оценку вашего знания английского.\n"
            "Удачи!\n\n"
            "Для начала игры напишите /start"
        )
    elif query.data.startswith('difficulty_'):
        difficulty = query.data.split('_')[1]
        user_id = update.effective_user.id
        context.user_data['difficulty'] = difficulty
        context.user_data['score'] = {'correct': 0, 'total': 0}
        context.user_data['current_word'] = get_random_word(difficulty)
        save_progress(user_id, context.user_data)
        await query.edit_message_text(f"Игра начинается! Переведите слово: {context.user_data['current_word']}")

# Обработчик текстовых сообщений (ответов пользователя)
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if 'current_word' not in context.user_data:
        progress = load_progress(user_id)
        if progress:
            context.user_data.update(progress)
        else:
            await update.message.reply_text("Пожалуйста, начните игру командой /start")
            return

    user_answer = update.message.text
    russian_word = context.user_data['current_word']
    is_correct, correct_word, synonym = check_answer(russian_word, user_answer)
    
    context.user_data['score']['total'] += 1
    if is_correct:
        context.user_data['score']['correct'] += 1
        if synonym:
            response = f"Правильно! '{synonym}' - это синоним слова '{correct_word}'."
        else:
            response = "Правильно!"
    else:
        response = f"Неправильно. Правильный ответ: {correct_word}"
    
    score = context.user_data['score']
    percentage = (score['correct'] / score['total']) * 100
    
    if percentage < 50:
        grade = "неудовлетворительно"
    elif 50 <= percentage < 70:
        grade = "удовлетворительно"
    elif 70 <= percentage < 90:
        grade = "хорошо"
    else:
        grade = "отлично"
    
    response += f"\nВаш счет: {score['correct']}/{score['total']} ({percentage:.1f}%) - {grade}"
    
    context.user_data['current_word'] = get_random_word(context.user_data['difficulty'])
    response += f"\nСледующее слово: {context.user_data['current_word']}"
    
    save_progress(user_id, context.user_data)
    await update.message.reply_text(response)

# Основная функция
def main():
    application = Application.builder().token('7209367762:AAEiGCSeXWrNNsRN_CtuQC12UY_-Gb0D7r8').build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

    application.run_polling()

if __name__ == '__main__':
    main()