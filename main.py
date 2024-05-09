import asyncio
from bot.botfile import bot, create_bot

while True:
    try:
        create_bot()
        bot.infinity_polling(none_stop=True)
    except:
        create_bot()
        print("reboot")
# auth_qr()
