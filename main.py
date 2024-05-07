import asyncio
from bot.bot import bot

loop = asyncio.get_event_loop()
loop.create_task(bot.polling(none_stop=True))
loop.run_forever()

# auth_qr()
