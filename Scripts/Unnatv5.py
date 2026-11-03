import os
import time
import random
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

START_TIME = time.time()
BOT_TOKENS = []
OWNER_ID = None

FLOWER_EMOJIS = ["🌸", "🌻", "🌹", "🌷", "🌺", "🌼", "💐", "💮"]
FLAG_EMOJIS = ["🇮🇳", "🏴‍☠️", "🚩", "🎌", "🏴", "🏳️‍🌈", "🇦🇷", "🇧🇷"]
TIME_EMOJIS = ["🕛", "🕒", "🕕", "🕘", "⏱️", "⏰", "⏲️", "⏳"]
EMO_POOL = ['😭', '❤', '😣', '🥰', '😂', '🤣', '🤡', '💀', '✌', '😁', '😎', '🥶', '😈', '👿', '😏', '🔥', '⚡', '✨']
STAR_EMOJIS = ["⭐", "🌟", "✨", "💫", "🌠", "⚡", "🔥", "💎"]

FLWRNC_LIST = [f"⋆˙.{random.choice(FLOWER_EMOJIS)}*.{{target}}.*{random.choice(FLOWER_EMOJIS)}.˙⋆ [Line {i}]" for i in range(1, 26)]
FLAGNC_LIST = [f"⋆⊱༻{random.choice(FLAG_EMOJIS)}༺⊰⋆ {{target}} {random.choice(FLAG_EMOJIS)} [Line {i}] ⋆⊱༻{random.choice(FLAG_EMOJIS)}༺⊰⋆" for i in range(1, 26)]
TIMENC_LIST = [f"{{target}} ╰┈➤ˎˊ{random.choice(TIME_EMOJIS)}˗ Time-Line-{i}" for i in range(1, 26)]
FNC_LIST = [f"────{random.choice(STAR_EMOJIS)} {{index}} ──── ⚡ {{target}} ⚡ ────{random.choice(STAR_EMOJIS)} ────" for i in range(1, 36)]

ncmix_raidtext = [
    " 𝘾𝙃𝙐𝘿𝘼𝙄 𝙆𝙃𝘼𝘼 ", " 𝙇𝙐𝙉𝘿 𝙆𝙃𝘼𝘼 ", " 𝙏𝙀𝙍𝘼 𝘾𝙃𝙐𝘿𝘼𝙄 𝘽𝙔 𝙐𝙉𝙉𝘼𝙏 ", 
    " 𝙂𝙐𝙇𝘼𝘼𝙈𝙄 𝙆𝙍 𝙍𝙉𝘿𝙔𝙆𝙀 𝙋𝙄𝙇𝙇𝙀 ", " 𝙏𝘼𝙏𝙏𝙀 𝙏𝙈𝙆𝘾 ", " 𝙃𝙀𝙇𝙇 𝙎𝙊𝙉𝘼 𝙂𝙊𝘿 ", 
    " 𝙐𝙏𝙃𝘼𝙆 𝘽𝘼𝙄𝙏𝙃𝘼𝙆 𝙇𝘼𝙂𝘼 𝙍𝙉𝘿𝙔𝙆𝙀 ", " 𝙏𝙈𝙆𝘾 𝙍𝙀YYYY", " 𝘽𝙃𝙀𝙉 𝘾𝙃𝓤𝘿𝘼 𝘼𝙋𝙉𝙄 "
]

def load_panel_config():
    global BOT_TOKENS, OWNER_ID
    if os.path.exists("scripts/tokens.txt"):
        with open("scripts/tokens.txt", "r") as f:
            content = f.read().strip()
            if content:
                BOT_TOKENS = [t.strip() for t in content.split(",") if t.strip()]
    OWNER_ID = os.environ.get("OWNER_ID", "123456789")

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu_text = (
        "ᴛɪɴʏ ᴍᴇɴᴜ | ᴜɴɴᴀᴛ | ꜱᴏɴᴀ ᴠ𝟻 ⚡\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📌 [ ɴᴄ ꜱᴇᴄᴛɪᴏɴꜱ ]\n"
        "• `!ncemo <text>`\n• `!ncmix <target>`\n• `!timenc <text>`\n• `!flwr <text>`\n• `!flag <text>`\n• `!fnc <text>`\n\n"
        "🌪️ [ ꜱʟɪᴅᴇ & ꜱᴘᴀᴍ ]\n"
        "• `!slidespm <text>`\n• `!spm <text>`\n\n"
        "⚙️ [ ꜱᴇᴛᴛɪɴɢꜱ ]\n"
        "• `!ping` | `!runtime` | `!stop all`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "❤ ᴘᴏᴡᴇʀᴇᴅ ʙʏ ᴜɴɴᴀᴛ | ꜱᴏɴᴀ ⚡"
    )
    await update.message.reply_text(menu_text, parse_mode="Markdown", reply_to_message_id=update.message.message_id)

async def handle_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if text.startswith("!ncmix"):
        target = text.replace("!ncmix", "").strip() or "UNNAT"
        selected_emoji = random.choice(EMO_POOL)
        selected_raid = random.choice(ncmix_raidtext).format(target=target)
        generated_nc = f"✩₊˚.⋆{selected_emoji}⋆⁺₊✧{target} {selected_raid} ✩₊˚.⋆{selected_emoji}⋆⁺₊✧"
        response = f"🟠 **ᴜɴɴᴀᴛ | ꜱᴏɴᴀ ʙᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ.........**\n🟢 **@{context.bot.username}**\n\n🔄 `{generated_nc}`"
        await update.message.reply_text(response, parse_mode="Markdown", reply_to_message_id=update.message.message_id)
    elif text.startswith("!ncemo"):
        target = text.replace("!ncemo", "").strip() or "UNNAT"
        e1, e2 = random.choice(EMO_POOL), random.choice(EMO_POOL)
        await update.message.reply_text(f"🌀 `{e1} {target} {e2} 💫`", parse_mode="Markdown", reply_to_message_id=update.message.message_id)
    elif text.startswith("!timenc"):
        target = text.replace("!timenc", "").strip() or "UNNAT"
        now_str = datetime.now().strftime("%H:%M:%S:%f")[:-3]
        template = random.choice(TIMENC_LIST).format(target=target)
        await update.message.reply_text(f"⏳ `{template} | {now_str}`", parse_mode="Markdown", reply_to_message_id=update.message.message_id)
    elif text.startswith("!flwr"):
        target = text.replace("!flwr", "").strip() or "UNNAT"
        await update.message.reply_text(f"🌸 `{random.choice(FLWRNC_LIST).format(target=target)}`", parse_mode="Markdown", reply_to_message_id=update.message.message_id)
    elif text.startswith("!flag"):
        target = text.replace("!flag", "").strip() or "UNNAT"
        await update.message.reply_text(f"🇮🇳 `{random.choice(FLAGNC_LIST).format(target=target)}`", parse_mode="Markdown", reply_to_message_id=update.message.message_id)
    elif text.startswith("!spm"):
        payload = text.split(" ", 1)[1] if " " in text else "Spam Payload"
        await update.message.reply_text(f"🔥 `{payload}`", parse_mode="Markdown", reply_to_message_id=update.message.message_id)

def main():
    load_panel_config()
    if not BOT_TOKENS:
        return
    app = ApplicationBuilder().token(BOT_TOKENS[0]).build()
    app.add_handler(CommandHandler("start", menu_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_commands))
    app.run_polling()

if __name__ == "__main__":
    main()
