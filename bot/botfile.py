import telebot, config

bot = None
def create_bot():
    global bot
    bot = telebot.TeleBot(config.BOT_TOKEN)