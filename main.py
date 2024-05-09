import asyncio
from bot.bot import bot
from bot.exceptions import BotException

x = {'v': True}
while x['v']:
    try:
        print("Starting bot", x)
        loop = asyncio.new_event_loop()
        loop.create_task(bot.polling(none_stop=True))
        loop.run_forever()
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
