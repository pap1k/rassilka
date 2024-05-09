import telebot

class BotException(telebot.ExceptionHandler):
    def handle(info):
        print(info)
        return True