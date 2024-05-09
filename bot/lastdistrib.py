from telethon.hints import Entity
import telethon

class OneDistrib:
    chat_id:int = 0
    chat_name: str = 0
    sucess: bool
    reason:str = ""

    def __init__(self, chat_id: int, chat_name: str, success: bool, reason: str) -> None:
        self.chat_id = chat_id
        self.chat_name = chat_name
        self.sucess = success
        self.reason = reason


class LastDistrib:
    distribs: list[OneDistrib] = []

    def __init__(self) -> None:
        self.distribs = []

    def add(self, entity: Entity, success: bool, reason: str = ""):
        title =  ''
        if isinstance(entity, telethon.types.Channel) or isinstance(entity, telethon.types.Chat):
            title = entity.title
        if isinstance(entity, telethon.types.User):
            title = entity.first_name
        self.distribs.append(OneDistrib(entity.id, title, success, reason))

    def export(self) -> str:
        txt = ""
        for dist in self.distribs:
            txt += f"Sent to {dist.chat_name} ({dist.chat_id}) -> {("success" if dist.sucess else "error")} ({dist.reason if dist.reason != "" else "OK"})\n"
        with open("lastdistrib.txt", "w", encoding="utf-8") as f:
            print(txt)
            f.write(txt)
        return "lastdistrib.txt"
    def clear(self):
        self.distribs = []
           