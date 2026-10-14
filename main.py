import os
import json
import asyncio
import logging
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

BOT_TOKEN = "8735100963:AAFOGPFUQqGTETyXpV0x_aQemGfbslJCY_s"

REQUIRED_INVITES = 10
DATA_FILE = "invites.json"
WARNING_LIFETIME = 15

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- Веб-сервер (Render үчүн порт талабын аткаруу) ----------
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# ---------- Маалыматты файлга сактоо ----------
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Файлды окууда ката: {e}")
    return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Файлга жазууда ката: {e}")

user_invites = load_data()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🇰🇬 Салам! Бул группага жумуш жарыясын жазуу үчүн 10 адам чакырууңуз керек.\n\n"
        "🇷🇺 Здравствуйте! Чтобы публиковать объявления в этой группе, нужно пригласить 10 человек."
    )
    await update.message.reply_text(msg)

async def track_invites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    inviter = message.from_user
    new_members = message.new_chat_members

    if new_members and inviter:
        user_id_str = str(inviter.id)
        if user_id_str not in user_invites:
            user_invites[user_id_str] = 0
        
        added_count = len([m for m in new_members if not m.is_bot])
        user_invites[user_id_str] += added_count
        save_data(user_invites)
        
        current_count = user_invites[user_id_str]
        
        welcome_text = (
            f"🇰🇬 Кош келиңиз, {inviter.first_name}! Сиз {current_count}/{REQUIRED_INVITES} адам чакырдыңыз.\n"
            f"🇷🇺 Добро пожаловать! Вы пригласили {current_count}/{REQUIRED_INVITES} человек."
        )
        await message.reply_text(welcome_text)

async def enforce_invite_rule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.from_user:
        return
    
    user_id = message.from_user.id
    user_id_str = str(user_id)
    
    try:
        chat_member = await context.bot.get_chat_member(message.chat.id, user_id)
        if chat_member.status in ['creator', 'administrator']:
            return
    except Exception:
        pass

    invited = user_invites.get(user_id_str, 0)
    
    if invited < REQUIRED_INVITES:
        try:
            await message.delete()
            warning_msg = (
                f"⚠️ {message.from_user.first_name}, жазуу үчүн кеминде {REQUIRED_INVITES} адам чакырышыңыз керек! "
                f"Азыркы чакырганыңыз: {invited}.\n\n"
                f"⚠️ Чтобы писать в группу, нужно пригласить {REQUIRED_INVITES} человек! "
                f"Вы пригласили: {invited}."
            )
            sent_msg = await context.bot.send_message(chat_id=message.chat_id, text=warning_msg)
            
            async def delete_warning():
                await asyncio.sleep(WARNING_LIFETIME)
                try:
                    await sent_msg.delete()
                except:
                    pass
            
            asyncio.create_task(delete_warning())
            
        except Exception as e:
            logger.error(f"Каталык пайда болду: {e}")

if __name__ == '__main__':
    logger.info("Веб-сервер ишке кирүүдө...")
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

    logger.info("Бот иштеп жатат...")
    
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, track_invites))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, enforce_invite_rule))

    app.run_polling()
