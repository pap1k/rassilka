import asyncio
from pyrogram import Client
from bot.bot import bot
from sqlalchemy.orm import Session
from orm.db import engine

loop = asyncio.get_event_loop()
loop.create_task(bot.polling(none_stop=True))
loop.run_forever()

# app = Client("второй")

# async def main():
#     async with app:
#         # Send a message, Markdown is enabled by default
#         await app.send_message("6505930340", "Hi there! I'm using **Pyrogram**")


# app.run(main())