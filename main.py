import asyncio
from bot.bot import bot
from bot.exceptions import BotException

x = {'v': True}
while x['v']:
    try:
        print("Starting bot", x)
        bot.infinity_polling()
    except KeyboardInterrupt:
        x['v'] = False
    except BotException as e:
        print(e)
        print("reboot")
    except Exception as e:
        print(e)
        print("Base excetion, dead")
        x['v'] = False
# auth_qr()
