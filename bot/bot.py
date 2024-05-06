import telebot
import config, telebot, asyncio
from orm.models import User, Distribs
from sqlalchemy.orm import Session
from pyrogram import Client

from orm.db import engine
from user.user import TgUser
from bot.history import HistoryController
from bot.menu import start_menu, MenuNames, user_mgnmt_menu, user_delete_confirm_menu, distrib_mgnmt_menu, distrib_edit_menu, distrib_send_menu, distrib_delete_confirm_menu

bot = telebot.TeleBot(config.BOT_TOKEN)

history = HistoryController()

def get_dialogs_bounds(user_id, dialogs: list):
    page = history.get_page_n(user_id)
    length = len(dialogs)
    if page*10 >= length:
        return [(page-1)*10, length]
    return [(page-1)*10, page*10]

def menu(user: telebot.types.User):
    is_admin = user.id in config.admin_id
    if not is_admin:
        with Session(autoflush=False, bind=engine) as db:
            users = db.query(User).all()
            users_ids = [v.id for v in users]
            if user.id not in users_ids:
                print("Попытка доступа незарегистрированного пользователя", user.id)
                return
        
    history.init_user(user.id)
    print(history.history)
    bot.send_message(user.id, "Выберите пункт меню:", reply_markup=start_menu(is_admin))

def get_chats(cl: Client):
    for dialog in cl.get_dialogs():
        print(dialog.chat.title or dialog.chat.first_name)

@bot.message_handler(["start", "menu"])
def start(message: telebot.types.Message):
    menu(message.from_user)

@bot.message_handler(["cancel"])
def cancel(message: telebot.types.Message):
    menu(message.from_user)

@bot.message_handler(["token"])
def getsession(message: telebot.types.Message):
    with Session(autoflush=False, bind=engine) as db:
        user = db.query(User).filter(User.id == message.from_user.id).first()
        if user:
            bot.send_message(message.chat.id, "Токен доступа экспортирован и сохранен")
            async def save_token():
                async with Client(user.username, api_id=user.api_id, api_hash=user.api_hash) as app:
                    st = await app.export_session_string()
                    print(st)
                    user.session_string = st
                    db.commit()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(save_token())

@bot.callback_query_handler(lambda x: True)
def menu_cb(cb: telebot.types.CallbackQuery):
    usermenu = history.get_current_menu(cb.from_user.id)
    [_, pl] = cb.data.split(':')
    bot.answer_callback_query(cb.id)
    print(history.history[cb.from_user.id])
    #ГЛАВНОЕ МЕНЮ
    if usermenu == MenuNames.main:
        bot.delete_message(cb.message.chat.id, cb.message.id)
        history.move_down(cb.from_user.id, pl)
        if pl == MenuNames.users_mgnmt:
            bot.send_message(cb.message.chat.id, "Нажмите на пользователя чтобы удалить", reply_markup=user_mgnmt_menu())
        elif pl == MenuNames.distrib_mgnmt:
            bot.send_message(cb.message.chat.id, "Выберите рассылку для управления", reply_markup=distrib_mgnmt_menu(cb.from_user.id))
        elif pl == MenuNames.distrib_send_menu:
            bot.send_message(cb.message.chat.id, "Выберите рассылку для выполнения", reply_markup=distrib_send_menu(cb.from_user.id))
        else:
            bot.send_message(cb.message.chat.id, "Произошла ошибка определения нажатой кнопки")
    
    #МЕНЮ ОТПРАВКИ РАССЫЛКИ
    elif usermenu == MenuNames.distrib_send_menu:
        bot.delete_message(cb.message.chat.id, cb.message.id)
        if pl == "back":
            return menu(cb.from_user)
        else:
            history.storage[cb.from_user.id]['chats'] = pl
            bot.send_message(cb.message.chat.id, "Введите текст рассылки или перешлите сообщение\n/cancel для отмены.")
            bot.register_next_step_handler_by_chat_id(cb.message.chat.id, send_distrib_input)
    
    #МЕНЮ РЕДАКТИРОВАНИЯ РАССЫЛКИ
    elif usermenu == MenuNames.distrib_edit:
        def update_dialogs():
            dialogs = history.storage[cb.from_user.id]['dialogs']
            messageid, chatid = history.storage[cb.from_user.id]['dialogs_id']
            x, y = get_dialogs_bounds(cb.from_user.id, dialogs)
            bot.edit_message_reply_markup(chatid, messageid, reply_markup=distrib_edit_menu(dialogs, x, y))
        if pl == "next":
            history.next_page(cb.from_user.id)
            update_dialogs()
        elif pl == "prev":
            history.prev_page(cb.from_user.id)
            update_dialogs()
        elif pl == "back":
            history.move_up(cb.from_user.id)
            bot.send_message(cb.message.chat.id, "Выберите рассылку для управления", reply_markup=distrib_mgnmt_menu(cb.from_user.id))
        elif pl.startswith("delete"):
            [_, id] = pl.split('-')
            history.move_down(cb.from_user.id, MenuNames.distrib_delete_confirm)
            bot.delete_message(cb.message.chat.id, cb.message.id)
            bot.send_message(cb.message.chat.id, "Вы уверены что хотите удалить рассылку?", reply_markup=distrib_delete_confirm_menu(id, id))
        elif pl == "save":
            bot.delete_message(cb.message.chat.id, cb.message.id)
            bot.send_message(cb.message.chat.id, "Введите название новой рассылки, чтобы сохранить ее:")
            bot.register_next_step_handler_by_chat_id(cb.message.chat.id, new_distrib_name_input)
        else:
            chatid = int(pl)
            d = history.storage[cb.from_user.id]['dialogs']
            for dialog in d:
                if dialog[1] == chatid:
                    dialog[2] = not dialog[2]
                    break
            update_dialogs()
    
    #МЕНЮ УПРАВЛЕНИЯ РАССЫЛКАМИ
    elif usermenu == MenuNames.distrib_mgnmt:
        bot.delete_message(cb.message.chat.id, cb.message.id)
        if pl == "back":
            return  menu(cb.from_user)
        elif pl == "new":
            with Session(autoflush=False, bind=engine) as db:
                u = db.query(User).filter(User.id == cb.from_user.id).first()
                async def getdialogs():
                    async with Client(u.username, api_id=u.api_id, api_hash=u.api_hash) as app:
                        dialogs = []
                        async for dialog in app.get_dialogs():
                            dialogs.append([str(dialog.chat.title or dialog.chat.first_name), dialog.chat.id, False])
                        else:
                            history.storage[cb.from_user.id]['dialogs'] = dialogs
                            history.move_down(cb.from_user.id, MenuNames.distrib_edit)
                            x, y = get_dialogs_bounds(cb.from_user.id, dialogs)
                            r = bot.send_message(cb.message.chat.id, "Выберите диалоги для рассылки:", reply_markup=distrib_edit_menu(dialogs, x, y))
                            history.storage[cb.from_user.id]['dialogs_id'] = [r.message_id, r.chat.id]

                bot.send_message(cb.message.chat.id, "Получаю список диалогов, подождите...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(getdialogs())

        elif pl == "next":
            history.next_page(cb.from_user.id)
            bot.send_message(cb.message.chat.id, "Выберите рассылку для управления", reply_markup=distrib_mgnmt_menu(cb.from_user.id, history.get_page_n(cb.from_user.id)))
        elif pl == "prev":
            history.prev_page(cb.from_user.id)
            bot.send_message(cb.message.chat.id, "Выберите рассылку для управления", reply_markup=distrib_mgnmt_menu(cb.from_user.id, history.get_page_n(cb.from_user.id)))
        else:
            [id, name] = pl.split('-')

            with Session(autoflush=False, bind=engine) as db:
                u = db.query(User).filter(User.id == cb.from_user.id).first()
                dbdialogs = db.query(Distribs).filter(Distribs.id == int(id)).first().chats.split(',')

                async def getdialogs():
                    async with Client(u.username, api_id=u.api_id, api_hash=u.api_hash) as app:
                        dialogs = []
                        async for dialog in app.get_dialogs():
                            dialogs.append([str(dialog.chat.title or dialog.chat.first_name), dialog.chat.id, str(dialog.chat.id) in dbdialogs])
                        else:
                            history.storage[cb.from_user.id]['dialogs'] = dialogs
                            history.move_down(cb.from_user.id, MenuNames.distrib_edit)
                            x, y = get_dialogs_bounds(cb.from_user.id, dialogs)
                            r = bot.send_message(cb.message.chat.id, f"Редактрирвоание рассылки {name}", reply_markup=distrib_edit_menu(dialogs, x, y, delete=True, id=id))
                            history.storage[cb.from_user.id]['dialogs_id'] = [r.message_id, r.chat.id]

                bot.send_message(cb.message.chat.id, "Получаю список диалогов, подождите...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(getdialogs())

            #bot.send_message(cb.message.chat.id, f"Вы действительно хотите удалить рассылку {name}?", reply_markup=user_delete_confirm_menu(name, int(id)))
    
    #МЕНЮ УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
    elif usermenu == MenuNames.users_mgnmt:
        bot.delete_message(cb.message.chat.id, cb.message.id)
        if pl == "back":
            return  menu(cb.from_user)
        elif pl == "new":
            msg = "Введите даныне пользователяв следющем формате:\n\nИмя аккаунта (произвольно)\nUSER_ID\nAPI_ID\nAPI_HASH"
            bot.send_message(cb.message.chat.id, msg)
            bot.register_next_step_handler_by_chat_id(cb.message.chat.id, new_user_data_input)
        elif pl == "next":
            history.next_page(cb.from_user.id)
            bot.send_message(cb.message.chat.id, "Нажмите на пользователя чтобы удалить", reply_markup=user_mgnmt_menu(history.get_page_n(cb.from_user.id)))
        elif pl == "prev":
            history.prev_page(cb.from_user.id)
            bot.send_message(cb.message.chat.id, "Нажмите на пользователя чтобы удалить", reply_markup=user_mgnmt_menu(history.get_page_n(cb.from_user.id)))
        else:
            [userid, username] = pl.split('-')
            history.move_down(cb.from_user.id, MenuNames.users_delete_confirm)
            bot.send_message(cb.message.chat.id, f"Вы действительно хотите удалить пользователя {username}?", reply_markup=user_delete_confirm_menu(username, int(userid)))
    
    #МЕНЮ ДА/НЕТ ПРИ УДАЛЕНИИ РАССЫЛКИ
    elif usermenu == MenuNames.distrib_delete_confirm:
        bot.delete_message(cb.message.chat.id, cb.message.id)
        [distribtodelete, yesno] = pl.split("-")
        history.move_up(cb.from_user.id)
        history.move_up(cb.from_user.id)
        if yesno == "yes":
            with Session(autoflush=False, bind=engine) as db:
                print(distribtodelete)
                found = db.query(Distribs).filter(Distribs.id == int(distribtodelete)).first()
                db.delete(found)
                db.commit()
                bot.send_message(cb.message.chat.id, "Рассылка удалена")
        bot.send_message(cb.message.chat.id, "Выберите рассылку для управления", reply_markup=distrib_mgnmt_menu(cb.from_user.id))
    
    #МЕНЮ ДА/НЕТ ПРИ УДАЛЕНИИ ПОЛЬЗОВАТЕЛЯ
    elif usermenu == MenuNames.users_delete_confirm:
        bot.delete_message(cb.message.chat.id, cb.message.id)
        [usertodelete, yesno] = pl.split("-")
        history.move_up(cb.from_user.id)
        if yesno == "yes":
            with Session(autoflush=False, bind=engine) as db:
                found = db.query(User).filter(User.id == int(usertodelete)).first()
                db.delete(found)
                db.commit()
                bot.send_message(cb.message.chat.id, "Пользователь удален")
        bot.send_message(cb.message.chat.id, "Нажмите на пользователя чтобы удалить", reply_markup=user_mgnmt_menu(history.get_page_n(cb.from_user.id)))
    
def send_distrib_input(message: telebot.types.Message):
    if message.text.startswith('/cancel'):
        return menu(message.from_user)
    with Session(autoflush=False, bind=engine) as db:
        u = db.query(User).filter(User.id == message.from_user.id).first()

        async def senddistrib():
            #in_memory=True, session_string=u.session_string
            async with Client(u.username, api_id=u.api_id, api_hash=u.api_hash) as app:
                app.get_dialogs()
                for chatid in history.storage[message.from_user.id]['chats'].split(','):
                    id = int(chatid) if chatid.startswith('-') else chatid
                    x = await app.resolve_peer(id)
                    await app.send_message(chat_id=id, text=message.text)
                else:
                    bot.send_message(message.chat.id, "Рассылка выполнена успешно")

        bot.send_message(message.chat.id, "Выполняю рассылку...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(senddistrib())

def new_distrib_name_input(message: telebot.types.Message):
    with Session(autoflush=False, bind=engine) as db:
        selected_dialogs = filter(lambda v: v[2], history.storage[message.from_user.id]["dialogs"])
        chatlist = [str(v[1]) for v in selected_dialogs]
        print(history.storage[message.from_user.id]["dialogs"], chatlist)
        new = Distribs(name=message.text, belong_to=message.from_user.id, chats=','.join(chatlist))
        db.add(new)
        db.commit()
        bot.send_message(message.chat.id, f"Успешно создана рассылка {message.text}")
        menu(message.from_user)

def new_user_data_input(message: telebot.types.Message):
    try:
        data = message.text.split("\n")
        print(data)
        username = data[0]
        userid = int(data[1])
        apiid = int(data[2])
        apihash = data[3]
    except Exception as ex:
        print(ex)
        return bot.send_message(message.chat.id, "Данные введены в неверном формате. Попробуйте еще раз")
    
    with Session(autoflush=False, bind=engine) as db:
        found = db.query(User).filter(User.id == userid).all()
        if len(found) > 0:
            return bot.send_message(message.chat.id, "Такой пользователь уже зарегистророван")
        
        newuser = User(id=userid, username=username, api_id=apiid, api_hash=apihash)
        db.add(newuser)
        db.commit()

        bot.send_message(message.chat.id, f"Успешно создан пользователь {username}")
        menu(message.from_user)

