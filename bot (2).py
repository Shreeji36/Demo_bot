# -*- coding: utf-8 -*-

import os
import threading
import uuid
import asyncio
from flask import Flask
from pyrogram.errors import FloodWait, ChatWriteForbidden
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pymongo import MongoClient
from broadcast import setup_broadcast
from force_sub import is_user_joined_all, send_force_sub

# ================= CONFIG =================
API_ID =   # your api id
API_HASH = "" # your api hash
BOT_TOKEN = "" # your bot token
OWNER_ID =   # your telegram id
MONGO_URI = "" # your mongo db uri

LOG_CHANNEL_ID = # your log channel id
BD_CHANNEL_ID = # your data base channel id for forward check
BOT_ID = None
# =========================================

bot = Client(
    "simple_start_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ---------- DATABASE ----------
mongo = MongoClient(MONGO_URI)
db = mongo["genlink_db"]
links_col = db["links"]
batch_col = db["batch_links"]
ban_col = db["banned_users"]
mod_col = db["moderators"]
config_col = db["config"]
users_col = db["users"]
restart_col = db["restart"]

# ---------- AUTO DELETE ----------
AUTO_DELETE_MINUTES = 30
saved_cfg = config_col.find_one({"_id": "auto_delete_time"})
if saved_cfg:
    AUTO_DELETE_MINUTES = saved_cfg["value"]
AUTO_DELETE_TIME = AUTO_DELETE_MINUTES * 60
# ---------- TEMP STATE ----------
GENLINK_WAIT = set()
BATCH_WAIT = {}
BAN_WAIT = set()
UNBAN_WAIT = set()
MOD_WAIT = set()
REVMOD_WAIT = set()

# ---------- HELPERS ----------
def is_banned(uid):
    return ban_col.find_one({"_id": uid}) is not None

def can_use(uid):
    return uid == OWNER_ID or mod_col.find_one({"_id": uid})

# 🔧 FIXED LOG FUNCTION (ONLY CHANGE)
async def send_log(text):
    try:
        await bot.send_message(LOG_CHANNEL_ID, text)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await bot.send_message(LOG_CHANNEL_ID, text)
    except ChatWriteForbidden:
        print("❌ LOG ERROR: Bot has no permission to write in log channel")
    except Exception as e:
        print("❌ LOG ERROR:", e)



# ---------- BROADCAST ----------
setup_broadcast(
    bot=bot,
    users_col=users_col,
    OWNER_ID=OWNER_ID,
    send_log=send_log
)

# =========================================
async def auto_delete(msg):
    await asyncio.sleep(AUTO_DELETE_TIME)
    try:
        await msg.delete()
    except:
        pass

async def send_autodel_notice(client, chat_id):
    note = await client.send_message(
        chat_id,
        f"» Save these files in your Saved Messages.\n"
        f"» They will be deleted in {AUTO_DELETE_MINUTES} minutes.\n\n"
        f"» Must Join:\n"
        f"1. ⚡️⚡️ @BotifyX_Pro ⚡️⚡️"
    )
    asyncio.create_task(auto_delete(note))


# ---------- START ----------
@bot.on_message(filters.command("start"), group=1)
async def start_cmd(client, message):
    uid = message.from_user.id

    # Save user
    users_col.update_one(
        {"_id": uid},
        {"$set": {"_id": uid}},
        upsert=True
    )

    # Ban check
    if is_banned(uid):
        return

    # 🔒 FORCE SUB (CORRECT WAY)
    joined = await is_user_joined_all(client, uid)
    if not joined:
        await send_force_sub(client, message, send_log)
        return

    # Parse deep-link command
    command = message.command or []

    if len(command) > 1:
        key = command[1]

        # ----- SINGLE FILE -----
        data = links_col.find_one({"_id": key})
        if data:
            msg = await client.copy_message(
                message.chat.id,
                data["chat_id"],
                data["message_id"]
            )
            asyncio.create_task(auto_delete(msg))
            await send_autodel_notice(client, message.chat.id)
            await send_log(f"LINK ACCESSED | USER {uid} | KEY {key}")
            return

        # ----- BATCH FILE -----
        if key.startswith("BATCH_"):
            data = batch_col.find_one({"_id": key})
            if data:
                for mid in range(data["from_id"], data["to_id"] + 1):
                    try:
                        msg = await client.copy_message(
                            message.chat.id,
                            data["chat_id"],
                            mid
                        )
                        asyncio.create_task(auto_delete(msg))
                    except:
                        continue

                await send_autodel_notice(client, message.chat.id)
                await send_log(f"BATCH ACCESSED | USER {uid} | KEY {key}")
                return

# replace welcome message and photo id
    photo_id = "AgACAgUAAxkBAAO6aUqaRSOm2iOBm1wZBrHzO9TATi4AAikOaxtNllhWl7uOeyQ1l5sACAEAAwIAA3kABx4E"

    caption = (
        "<code>WELCOME TO THE ADVANCED  FILE SHARE SYSTEM.\n" # modify welcome message
        "WITH THIS BOT, YOU CAN GET YOUR REQUESTED \n"
        "FILES SECURELY AND ENJOY THEM !! \n"
        "MANAGED BY ~</code> @BotifyX_Pro .\n\n"
        "<blockquote><b>➥ MAINTAINED BY : "
        "<a href='https://t.me/Akuma_Rei_Kami'>Akuma_Rei</a>"
        "</b></blockquote>"
    )

    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➥ 𝐀𝐁𝐎𝐔𝐓", callback_data="about")],
            [
                InlineKeyboardButton("➥ 𝗢𝗪𝗡𝗘𝗥", url="https://t.me/Prince_Vegeta_36"),
                InlineKeyboardButton("➥ 𝐍𝐄𝐓𝐖𝐎𝐑𝐊", url="https://t.me/") # your channel link
            ],
            [InlineKeyboardButton("➥ 𝗖𝗟𝗢𝗦𝗘", callback_data="close_msg")]
        ]
    )

    await message.reply_photo(
        photo=photo_id,
        caption=caption,
        reply_markup=buttons,
        parse_mode=ParseMode.HTML
    )

# ---------- SET AUTO DELETE ----------
@bot.on_message(filters.command("setdeltime"))
async def set_delete_time(client, message):
    global AUTO_DELETE_TIME, AUTO_DELETE_MINUTES

    if message.from_user.id != OWNER_ID:
        return

    if len(message.command) != 2 or not message.command[1].isdigit():
        await message.reply_text(
            "Usage:\n/setdeltime <minutes>\n\nExample:\n/setdeltime 30"
        )
        return

    AUTO_DELETE_MINUTES = int(message.command[1])
    AUTO_DELETE_TIME = AUTO_DELETE_MINUTES * 60  # convert to seconds

    config_col.update_one(
        {"_id": "auto_delete_time"},
        {"$set": {"value": AUTO_DELETE_MINUTES}},
        upsert=True
    )

    await message.reply_text(
        f"✅ Auto delete time set to {AUTO_DELETE_MINUTES} minutes."
    )

    await send_log(
        f"DELETE TIME SET | {AUTO_DELETE_MINUTES} minutes | BY {message.from_user.id}"
    )


# ---------- GENLINK ----------
@bot.on_message(filters.command("genlink"))
async def genlink_cmd(client, message):
    if not can_use(message.from_user.id):
        return
    GENLINK_WAIT.add(message.from_user.id)
    await message.reply_text("<blockquote>Send A Message For To Get Your Shareable Link</blockquote>")

# ---------- BATCH ----------
@bot.on_message(filters.command("batch"))
async def batch_cmd(client, message):
    if not can_use(message.from_user.id):
        return
    BATCH_WAIT[message.from_user.id] = {"step": "first"}
    await message.reply_text(
        "<blockquote>Forward The Batch First Message From your Batch Channel (With Forward Tag)..</blockquote>"
    )

# ---------- BAN ----------
@bot.on_message(filters.command("ban"))
async def ban_cmd(client, message):
    if not can_use(message.from_user.id):
        return
    BAN_WAIT.add(message.from_user.id)
    await message.reply_text("<blockquote>send the user id</blockquote>")

# ---------- UNBAN ----------
@bot.on_message(filters.command("unban"))
async def unban_cmd(client, message):
    if not can_use(message.from_user.id):
        return
    UNBAN_WAIT.add(message.from_user.id)
    await message.reply_text("<blockquote>send the user id</blockquote>")

# ---------- MODERATOR ----------
@bot.on_message(filters.command("moderator"))
async def moderator_cmd(client, message):
    if message.from_user.id != OWNER_ID:
        return
    MOD_WAIT.add(message.from_user.id)
    await message.reply_text("<blockquote>send the user id</blockquote>")

# ---------- REMOVE MODERATOR ----------
@bot.on_message(filters.command("revmoderator"))
async def revmoderator_cmd(client, message):
    if message.from_user.id != OWNER_ID:
        return
    REVMOD_WAIT.add(message.from_user.id)
    await message.reply_text("<blockquote>send the user id</blockquote>")

# ---------- PRIVATE HANDLER ----------
@bot.on_message(filters.private & ~filters.regex(r"^/"))
async def private_handler(client, message):
    uid = message.from_user.id

    if uid in MOD_WAIT:
        MOD_WAIT.remove(uid)
        mod_col.insert_one({"_id": int(message.text)})
        await send_log(f"MOD ADDED | {message.text}")
        await message.reply_text("✨ Successfully Added the user")
        return

    if uid in REVMOD_WAIT:
        REVMOD_WAIT.remove(uid)
        mod_col.delete_one({"_id": int(message.text)})
        await send_log(f"MOD REMOVED | {message.text}")
        await message.reply_text("✨ Successfully Removed the user")
        return

    if uid in BAN_WAIT:
        BAN_WAIT.remove(uid)
        ban_col.insert_one({"_id": int(message.text)})
        await send_log(f"USER BANNED | {message.text}")
        await message.reply_text("✨ Successfully Banned the user")
        return

    if uid in UNBAN_WAIT:
        UNBAN_WAIT.remove(uid)
        ban_col.delete_one({"_id": int(message.text)})
        await send_log(f"USER UNBANNED | {message.text}")
        await message.reply_text("✨ Successfully Unbanned the user")
        return

    if uid in GENLINK_WAIT:
        GENLINK_WAIT.remove(uid)

        if message.forward_from_chat and message.forward_from_chat.id == BD_CHANNEL_ID:
            chat_id = message.forward_from_chat.id
            msg_id = message.forward_from_message_id
        else:
            chat_id = message.chat.id
            msg_id = message.id

        key = uuid.uuid4().hex[:12]
        links_col.insert_one({
            "_id": key,
            "chat_id": chat_id,
            "message_id": msg_id
        })

        bot_username = (await client.get_me()).username
        link = f"https://t.me/{bot_username}?start={key}"

        await send_log(f"GENLINK CREATED | {key} | BY {uid}")
        await message.reply_text(
            f"Here is your link:\n\n{link}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(
                    "➥ SHARE URL",
                    url=f"https://t.me/share/url?url={link}"
                )]]
            )
        )
        return

    if uid in BATCH_WAIT:
        if not message.forward_from_chat:
            return

        data = BATCH_WAIT[uid]

        if data["step"] == "first":
            data["chat_id"] = message.forward_from_chat.id
            data["from_id"] = message.forward_from_message_id
            data["step"] = "last"
            await message.reply_text(
                "<blockquote>Forward The Batch Last Message From Your Batch Channel (With Forward Tag)..</blockquote>"
            )
            return

        batch_id = f"BATCH_{uuid.uuid4().hex[:10]}"
        batch_col.insert_one({
            "_id": batch_id,
            "chat_id": data["chat_id"],
            "from_id": data["from_id"],
            "to_id": message.forward_from_message_id
        })

        del BATCH_WAIT[uid]

        bot_username = (await client.get_me()).username
        link = f"https://t.me/{bot_username}?start={batch_id}"

        await send_log(f"BATCH CREATED | {batch_id} | BY {uid}")
        await message.reply_text(
            f"Here is your link:\n\n{link}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(
                    "➥ SHARE URL",
                    url=f"https://t.me/share/url?url={link}"
                )]]
            )
        )
        return
        
# ---------- PRIVATE HANDLER ----------
@bot.on_callback_query(filters.regex("^check_fsub$"))
async def check_force_sub(client, callback_query):
    joined = await is_user_joined_all(client, callback_query.from_user.id)

    if not joined:
        await callback_query.answer(
            "❌ Join all required channels first!",
            show_alert=True
        )
        return

    await callback_query.message.delete()
    await callback_query.answer("✅ Verified! Access granted.", show_alert=True)

    # Re-run start cleanly
    await start_cmd(client, callback_query.message)

# ---------- ABOUT ----------
@bot.on_callback_query(filters.regex("^about$"))
async def about_callback(client, callback_query):
    about_text = (
        "<code>BOT INFORMATION </code>\n\n"
        "<blockquote>"
        "<b>»» My Name :</b> <a href='https://t.me/MAKIMA_AUTO_APPROVAL_BOT'>𝘔𝘈𝘒𝘐𝘔𝘈 «File_share»</a>\n"
        "<b>»» Developer :</b> @Akuma_Rei_Kami\n"
        "<b>»» Library :</b> <a href='https://docs.pyrogram.org/'>Pyrogram v2</a>\n"
        "<b>»» Language :</b> <a href='https://www.python.org/'>Python 3</a>\n"
        "<b>»» Database :</b> <a href='https://www.mongodb.com/docs/'>MongoDB</a>\n"
        "<b>»» Hosting :</b> <a href='https://render.com/'>Render</a>"
        "</blockquote>"
    )

    buttons = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("➥ BACK", callback_data="back_start"),
            InlineKeyboardButton("➥ CLOSE", callback_data="close_msg")
        ]]
    )

    await callback_query.message.edit_caption(
        caption=about_text,
        reply_markup=buttons,
        parse_mode=ParseMode.HTML
    )
    await callback_query.answer()

# ------------- RESTART_SECTOIN ------------- # add photo id or gif id for restart notification
RESTART_GIF_ID = "CgACAgUAAxkBAAIFhWlTYyz2lswu1zoPW2oGNdtxa47UAAISGgACeHGZVqICASvCmvrNHgQ"

async def broadcast_restart():
    restart_id = uuid.uuid4().hex

    last = restart_col.find_one({"_id": "last"})
    if last and last.get("rid") == restart_id:
        return

    restart_col.update_one(
        {"_id": "last"},
        {"$set": {"rid": restart_id}},
        upsert=True
    )

    caption = (
        "🔄 <code>Bot Restarted Successfully!</code>\n\n"
        "✅ <code>Updates have been applied.</code>\n"
        "🚀 <code>Bot is now online and running smoothly.</code>\n\n"
        "<code>Thank you for your patience.</code>"
    )

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📢 Update Channel", url="https://t.me/BotifyX_Pro"),
                InlineKeyboardButton("🆘 Support", url="https://t.me/BotifyX_support")
            ]
        ]
    )

    # ✅ THIS LOOP MUST BE INSIDE THE FUNCTION
    for user in users_col.find({}):
        if user["_id"] == BOT_ID:
            continue
        try:
            await bot.send_animation(
                chat_id=user["_id"],
                animation=RESTART_GIF_ID,
                caption=caption,
                reply_markup=buttons,
                parse_mode=ParseMode.HTML
            )
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except:
            continue

# ---------- BACK ----------
@bot.on_callback_query(filters.regex("^back_start$"))
async def back_start(client, callback_query):
    msg = callback_query.message
    msg.command = ["start"]
    await msg.delete()
    await start_cmd(client, msg)

# ---------- CLOSE ----------
@bot.on_callback_query(filters.regex("^close_msg$"))
async def close_msg(client, callback_query):
    await callback_query.message.delete()

# ---------- WEB ----------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()

    async def startup():
        global BOT_ID
        me = await bot.get_me()
        BOT_ID = me.id
        await send_log("✅ Bot started successfully")
        await broadcast_restart()

    bot.start()
    bot.loop.run_until_complete(startup())
    idle()














