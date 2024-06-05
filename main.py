import asyncio, sys
from bot.bot import bot
from bot.exceptions import BotException

if '-test' in sys.argv:
    bot.infinity_polling()
    quit()

x = {'v': True}
while x['v']:
    try:
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
