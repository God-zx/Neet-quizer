import logging
import os
from dotenv import load_dotenv
from telegram import Update, Poll
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    PollAnswerHandler,
    filters,
    ContextTypes,
)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# In-memory storage (user_id -> quiz data)
users = {}  # {user_id: {'title': str, 'desc': str or None, 'questions': [], 'state': 'title'/'desc'/'questions', 'score': 0}}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome to Dev's NEET Quiz Bot! 🚀\n"
        "Commands:\n/create - Naya quiz banao\n/startquiz - Quiz shuru karo (jab questions add ho jaye)"
    )

async def create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    users[user_id] = {
        "title": None,
        "desc": None,
        "questions": [],  # List of {'text': str, 'options': list, 'correct_id': int}
        "state": "title",
        "score": 0,
    }
    await update.message.reply_text("Quiz ka title bhejo (e.g. NEET Biology 2026):")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in users:
        await update.message.reply_text("Pehle /create karo!")
        return

    data = users[user_id]
    state = data["state"]

    if state == "title":
        data["title"] = text
        data["state"] = "desc"
        await update.message.reply_text(
            f"Title set: {text}\n\nAb description bhejo (optional) ya /skip"
        )
        return

    if state == "desc":
        if text.lower() == "/skip":
            data["desc"] = None
        else:
            data["desc"] = text
        data["state"] = "questions"
        await update.message.reply_text(
            "Good! Ab har question ke liye poll bhejo:\n"
            "- Poll type: Quiz\n"
            "- Correct option select karo\n"
            "- Question text + 4 options daalo\n"
            "Jab khatam ho to /done bhejo"
        )
        return

    if text == "/done":
        if not data["questions"]:
            await update.message.reply_text("Koi question nahi add kiya! Pehle poll bhejo.")
            return
        await update.message.reply_text(
            f"Quiz ready! Title: {data['title']}\n"
            f"Questions: {len(data['questions'])}\n"
            "/startquiz se shuru kar sakte ho (DM ya group mein)"
        )
        return

    await update.message.reply_text("Poll bhejo ya /done karo!")

async def handle_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Poll jab user bhejta hai creation mode mein
    if update.message.poll is None:
        return

    user_id = update.effective_user.id
    if user_id not in users or users[user_id]["state"] != "questions":
        return

    poll = update.message.poll
    if poll.type != Poll.QUIZ:
        await update.message.reply_text("Sirf Quiz type poll bhejo!")
        return

    if poll.correct_option_id is None:
        await update.message.reply_text("Correct option select karna bhool gaye poll mein!")
        return

    users[user_id]["questions"].append(
        {
            "text": poll.question,
            "options": poll.options,
            "correct_id": poll.correct_option_id,
        }
    )
    await update.message.reply_text(
        f"Question added! ({len(users[user_id]['questions'])} total)\n"
        "Agla poll bhejo ya /done"
    )

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Jab user quiz ke dauran answer deta hai
    poll_answer = update.poll_answer
    user_id = poll_answer.user.id

    if user_id not in users:
        return

    data = users[user_id]
    # Yahan logic add karo score ke liye (future: current question track karo)
    # Abhi simple: just acknowledge
    await context.bot.send_message(
        chat_id=user_id, text="Answer recorded! (Score update soon...)"
    )

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in users or not users[user_id]["questions"]:
        await update.message.reply_text("Pehle quiz create karo questions ke saath!")
        return

    data = users[user_id]
    await update.message.reply_text(f"Starting {data['title']}... Good luck! 🔥")

    # Send first question as quiz poll
    q = data["questions"][0]  # Abhi sirf first, baad mein loop banao
    await update.message.reply_poll(
        question=q["text"],
        options=[opt.text for opt in q["options"]],
        type=Poll.QUIZ,
        correct_option_id=q["correct_id"],
        is_anonymous=False,  # Group mein visible rahe
    )
    # Future: timer, next question on answer, score track

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create", create))
    application.add_handler(CommandHandler("done", handle_text))  # /done as command
    application.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.POLL, handle_poll))
    application.add_handler(PollAnswerHandler(handle_poll_answer))

    print("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
