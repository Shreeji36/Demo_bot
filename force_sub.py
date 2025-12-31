
# -*- coding: utf-8 -*-

from pyrogram.enums import ChatMemberStatus, ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

FORCE_SUB_CHANNEL_IDS = [
    -1002345678901, # change to your channel ids
    -1002345678902, # change to your channel ids
]

FORCE_SUB_CHANNEL_LINKS = [
    "", # change to your channel links
    "", # change to your channel links
]
# change to your own photo id before uploading it to your telegram bot
FORCE_SUB_PHOTO_ID = "AgACAgUAAxkBAAIGN2lUFZvy2EBSrB7P8aKJz7CIVvBIAAKJC2sbYtegVmmGUAs7QVapAAgBAAMCAAN5AAceBA"


async def is_user_joined_all(client, user_id):
    for channel_id in FORCE_SUB_CHANNEL_IDS:
        try:
            member = await client.get_chat_member(channel_id, user_id)
            if member.status not in (
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.OWNER
            ):
                return False
        except Exception:
            return False
    return True


async def send_force_sub(client, message, send_log):
    await send_log(f"FSUB BLOCKED | USER {message.from_user.id}")

    mention = message.from_user.mention
    text = (
        f"◈ Hᴇʏ {mention} ×\n\n"
        "‼️ AFTER JOINING THE FORCE SUB CHANNELS\n"
        "CLICK **CHECK JOIN** AGAIN\n\n"
        "›› Powered by : "
        "<a href='https://t.me/Prince_Vegeta_36'>𝗖𝗵𝗿𝗼𝗹𝗹𝗼 𝗟𝘂𝗰𝗶𝗹𝗳𝗲𝗿</a>"
    )

    buttons = [
        [InlineKeyboardButton(f"➥ JOIN CHANNEL {i+1}", url=link)]
        for i, link in enumerate(FORCE_SUB_CHANNEL_LINKS)
    ]
    buttons.append(
        [InlineKeyboardButton("🔁 CHECK JOIN", callback_data="check_fsub")]
    )

    await message.reply_photo(
        photo=FORCE_SUB_PHOTO_ID,
        caption=text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML
    )
