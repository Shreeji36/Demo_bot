
# -*- coding: utf-8 -*-

from pyrogram import filters
from pyrogram.errors import FloodWait
import asyncio

def setup_broadcast(bot, users_col, OWNER_ID, send_log):

    @bot.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
    async def broadcast_handler(client, message):

        if not message.reply_to_message:
            await message.reply_text(
                "Reply to any message to broadcast it."
            )
            return

        await send_log("BROADCAST STARTED")

        sent = 0
        failed = 0

        for user in users_col.find({}):
            try:
                await message.reply_to_message.copy(user["_id"])
                sent += 1
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await message.reply_to_message.copy(user["_id"])
                sent += 1
            except Exception:
                failed += 1

        await send_log(
            f"BROADCAST FINISHED | SENT {sent} | FAILED {failed}"
        )

        await message.reply_text(
            f"✅ Broadcast completed.\n\n"
            f"📤 Sent: {sent}\n"
            f"❌ Failed: {failed}"
        )
