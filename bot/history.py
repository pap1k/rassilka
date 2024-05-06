from bot.menu import MenuNames

class HistoryController:

    history:dict[int, str] = {}
    storage: dict[int, dict] = {}

    def __init__(self) -> None:
        self.history = {}

    def init_user(self, user_id:int):
        self.storage[user_id] = {}
        if user_id not in self.history:
            self.history[user_id] = MenuNames.main
        else:
            self.history[user_id] = MenuNames.main

    def move_down(self, user_id: int, menu_name: str):
        if user_id not in self.history:
            self.init_user(user_id)
        self.history[user_id] += "-"+menu_name

    def move_up(self, user_id:int):
        if user_id not in self.history:
            self.init_user(user_id)
        old = self.history[user_id].split('-')
        if len(old) > 1:
            new = '-'.join(old[:-1])
            self.history[user_id] = new

    def get_current_menu(self, user_id:int) -> str:
        if user_id not in self.history:
            self.init_user(user_id)
        old = self.history[user_id].split('-')
        menu = old[-1] if len(old) > 1 else self.history[user_id]
        if ':' in menu:
            return menu.split(':')[0]
        return menu

    def get_page_n(self, user_id:int) -> int:
        if user_id not in self.history:
            self.init_user(user_id)
        old = self.history[user_id]
        if ':' in old:
            page_n = int(old.split(':')[-1])
            return int(page_n)
        return 1

    def next_page(self, user_id:int):
        if user_id not in self.history:
            self.init_user(user_id)
        page_n = self.get_page_n(user_id)
        old = self.history[user_id]
        self.history[user_id] = old.split(':')[0] + ':' + str(page_n+1)

    def prev_page(self, user_id:int):
        if user_id not in self.history:
            self.init_user(user_id)
        page_n = self.get_page_n(user_id)
        old = self.history[user_id]
        self.history[user_id] = old.split(':')[0] + ':' + str(page_n-1)

