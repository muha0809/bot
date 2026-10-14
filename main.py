import os
import json
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
)

BOT_TOKEN = os.environ.get("8656639262:AAHw3xIQzZt2FCgkM8khfA_Ko9XpUWnnDGU")

REQUIRED_INVITES = 10
DATA_FILE = "invites.json"
WARNING_LIFETIME = 15  # эскертүү канча секунддан кийин өчөт

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ---------- Маалыматты файлга сактоо (бот өчүп күйсө да жоголбойт) ----------
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.exception("invites.json окулган жок")
    return {}


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_invites, f)


user_invites = load_data()  # ачкыч: "chat_id:user_id" -> сан


def make_key(chat_id, user_id):
    return f"{chat_id}:{user_id}"


async def delete_later(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


# ---------- /start ----------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🇰🇬 Салам! Бул группага жумуш жарыясын жазуу үчүн "
        f"{REQUIRED_INVITES} адам чакырууңуз керек.\n\n"
        "🇷🇺 Здравствуйте! Чтобы публиковать объявления в этой группе, "
        f"вам нужно пригласить {REQUIRED_INVITES} человек."
    )
    await update.message.reply_text(msg)


# ---------- Чакыруулду эсептөө ----------
async def track_invites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.from_user:
        return

    inviter = message.from_user
    new_members = message.new_chat_members or []

    # Ботторду жана өзү шилтеме менен кошулгандарды санабайбыз
    added = [m for m in new_members if not m.is_bot and m.id != inviter.id]
    if not added:
        return

    key = make_key(message.chat_id, inviter.id)
    user_invites[key] = user_invites.get(key, 0) + len(added)
    save_data()

    current = user_invites[key]
    text = (
        f"🇰🇬 Рахмат, {inviter.first_name}! Сиз {current}/{REQUIRED_INVITES} адам чакырдыңыз.\n"
        f"🇷🇺 Спасибо! Вы пригласили {current}/{REQUIRED_INVITES} человек."
    )
    sent = await message.reply_text(text)
    asyncio.create_task(delete_later(sent, WARNING_LIFETIME))


# ---------- Эрежени көзөмөлдөө ----------
async def enforce_invite_rule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.from_user:
        return

    # Канал атынан же анонимдүү админ жазса - тийбейбиз
    if message.sender_chat:
        return

    user = message.from_user
    if user.is_bot:
        return

    try:
        member = await context.bot.get_chat_member(message.chat_id, user.id)
    except Exception:
        logger.exception("get_chat_member ката берди")
        return

    if member.status in ("creator", "administrator"):
        return

    invited = user_invites.get(make_key(message.chat_id, user.id), 0)
    if invited >= REQUIRED_INVITES:
        return

    try:
        await message.delete()
    except Exception:
        logger.exception("Билдирүү өчүрүлгөн жок (бот админби жана өчүрүү укугу барбы?)")
        return

    warning = (
        f"⚠️ {user.first_name}, жазуу үчүн кеминде {REQUIRED_INVITES} адам чакырышыңыз керек! "
        f"Азыркы чакырганыңыз: {invited}.\n\n"
        f"⚠️ Чтобы писать в группу, нужно пригласить {REQUIRED_INVITES} человек! "
        f"Вы пригласили: {invited}."
    )
    sent = await context.bot.send_message(chat_id=message.chat_id, text=warning)
    asyncio.create_task(delete_later(sent, WARNING_LIFETIME))


if name == '__main__':
    print("Бот иштеп жатат...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, track_invites)
    )
    # Группадагы бардык билдирүүлөр (текст, сүрөт, видео ж.б.), команда жана тейлөө билдирүүлөрүнөн башка
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & ~filters.COMMAND & ~filters.StatusUpdate.ALL,
            enforce_invite_rule,
        )
    )

    app.run_polling()
