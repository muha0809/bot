import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8656639262:AAHw3xIQzZt2FCgkM8khfA_Ko9XpUWnnDGU")

REQUIRED_INVITES = 10
user_invites = {}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🇰🇬 Салам! Бул группага жумуш жарыясын жазуу үчүн 10 адам чакырууңуз керек.\n\n"
        "🇷🇺 Здравствуйте! Чтобы публиковать объявления в этой группе, вам нужно пригласить 10 человек."
    )
    await update.message.reply_text(msg)

async def track_invites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    inviter = message.from_user
    new_members = message.new_chat_members

    if new_members:
        if inviter.id not in user_invites:
            user_invites[inviter.id] = 0
        
        added_count = len([m for m in new_members if not m.is_bot])
        user_invites[inviter.id] += added_count
        
        current_count = user_invites[inviter.id]
        
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
    
    chat_member = await context.bot.get_chat_member(message.chat.id, user_id)
    if chat_member.status in ['creator', 'administrator']:
        return

    invited = user_invites.get(user_id, 0)
    
    if invited < REQUIRED_INVITES:
        try:
            await message.delete()
            warning_msg = (
                f"⚠️ {message.from_user.first_name}, жазуу үчүн кеминде {REQUIRED_INVITES} адам чакырышыңыз керек! "
                f"Азыркы чакырганыңыз: {invited}.\n\n"
                f"⚠️ Чтобы писать в группу, нужно пригласить {REQUIRED_INVITES} человек! "
                f"Вы пригласили: {invited}."
            )
            await context.bot.send_message(chat_id=message.chat_id, text=warning_msg)
        except Exception as e:
            print(f"Каталык пайда болду: {e}")

if name == '__main__':
    print("Бот иштеп жатат...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, track_invites))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, enforce_invite_rule))

    app.run_polling()
