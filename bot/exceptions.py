import telebot

class BotException(Exception):
    def handle(info):
        print(info)
        return True