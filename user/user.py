from orm.models import User
from pyrogram import Client

class TgUser:
    user: User = None
    app : Client = None

    def __init__(self, username, api_id, api_hash, ) -> None:
        #self.user = user
        self.app = Client(username, api_id=api_id, api_hash=api_hash, in_memory=True, session_string=True)
        #print(self.app.export_session_string())

    async def get_chats(self):
        r = await self.app.get_dialogs()
        print(r)
        for dialog in r:
            print(dialog.chat.title or dialog.chat.first_name)

