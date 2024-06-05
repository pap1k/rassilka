import telebot
import telethon
import config, telebot, asyncio, traceback
from orm.models import User, Distribs
from sqlalchemy.orm import Session
from sqlalchemy import delete

from user.user import auth_qr, create_client, auth_tel
from orm.db import engine
from bot.history import HistoryController
from bot.menu import start_menu, MenuNames, user_mgnmt_menu, user_delete_confirm_menu, distrib_mgnmt_menu, distrib_edit_menu, distrib_send_menu, distrib_delete_confirm_menu, admin_menu, distrib_auto_edit_menu
from bot.exceptions import BotException
from bot.lastdistrib import LastDistrib

bot = telebot.TeleBot(config.BOT_TOKEN, exception_handler=BotException)

history = HistoryController()
lastdist = LastDistrib()

def transform_time_to_sec(time, reverse=False):
    trans = {
        '30m': 1800,
        '40m': 2400,
        '50m': 3000,
        '1h':  3600,
    }
    for k, v in trans.items():
        if k == time or v == time:
            return k if reverse else v
    return 'no'

def get_dialogs_bounds(user_id, dialogs: list):
    page = history.get_page_n(user_id)
    length = len(dialogs)
    if page*10 >= length:
        return [(page-1)*10, length]
    return [(page-1)*10, page*10]

def menu(user: telebot.types.User):
    try:
        is_admin = user.id in config.admin_id
        if not is_admin:
            with Session(autoflush=False, bind=engine) as db:
                dbuser = db.query(User).filter(User.id == user.id).first()
                if not dbuser:
                    print("Попытка доступа незарегистрированного пользователя", user.id)
                    return
                else:
                    async def check_auth():
                        client = create_client(dbuser.username)
                        await client.connect()
                        if await client.is_user_authorized():
                            history.init_user(user.id)
                            await client.disconnect()
                            bot.send_message(user.id, "Выберите пункт меню:", reply_markup=start_menu(is_admin))
                        else:
                            await client.disconnect()
                            bot.send_message(user.id, "Вы не авторизованы. Войдите в приложение с помощью /auth или /authqr")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(check_auth())
        else:
            history.init_user(user.id)
            bot.send_message(user.id, "Выберите пункт админ-меню:", reply_markup=admin_menu())
    except Exception:
        print(traceback.format_exc())

@bot.message_handler(["test"])
def start(message: telebot.types.Message):
     with Session(autoflush=False, bind=engine) as db:
        dbuser = db.query(User).filter(User.id == message.from_user.id).first()
        print(dbuser)

@bot.message_handler(["start", "menu"])
def start(message: telebot.types.Message):
    menu(message.from_user)

@bot.message_handler(["last"])
def get_last(message: telebot.types.Message):
    fname = lastdist.export()
    data = open(fname, "rb").read()
    bot.send_document(message.chat.id, data, visible_file_name="Last_Distribution.txt")

@bot.message_handler(["raise"])
def error(message: telebot.types.Message):
    raise Exception

@bot.message_handler(["sticker"])
def sticker(message: telebot.types.Message):
    bot.reply_to(message, "Теперь отправь стикер")
    bot.register_next_step_handler_by_chat_id(message.chat.id, get_sticker)

def get_sticker(message: telebot.types.Message):
    print(message)
    bot.reply_to(message, "Ок", )

@bot.message_handler(["cancel"])
def cancel(message: telebot.types.Message):
    menu(message.from_user)

@bot.message_handler(["authqr"])
def auth(message: telebot.types.Message):
    with Session(autoflush=False, bind=engine) as db:
        user = db.query(User).filter(User.id == message.from_user.id).first()
        if user:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(auth_qr(user.username, bot, message.chat.id))

@bot.message_handler(["auth"])
def auth(message: telebot.types.Message):
    def tel_inp(message: telebot.types.Message):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(auth_tel(user.username, bot, message.chat.id, message.text))
    with Session(autoflush=False, bind=engine) as db:
        user = db.query(User).filter(User.id == message.from_user.id).first()
        if user:
            bot.reply_to(message, "Введите номер телефона без проблеов, в формате\n+[код_страны][номер]")
            bot.register_next_step_handler_by_chat_id(message.chat.id, tel_inp)

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
            with Session(autoflush=False, bind=engine) as db:
                distr = db.query(Distribs).filter(Distribs.id == int(pl)).first()
                history.storage[cb.from_user.id]['chats'] = distr.chats
                history.storage[cb.from_user.id]['distribid'] = int(pl)
                bot.send_message(cb.message.chat.id, "Введите текст рассылки или перешлите сообщение\n/cancel для отмены.")
                bot.register_next_step_handler_by_chat_id(cb.message.chat.id, send_distrib_input)
    
    #МЕНЮ РЕДАКТИРОВАНИЯ РАССЫЛКИ
    elif usermenu == MenuNames.distrib_edit:
        [pl, id] = pl.split('--')
        def update_dialogs():
            dialogs = history.storage[cb.from_user.id]['dialogs']
            messageid, chatid = history.storage[cb.from_user.id]['dialogs_id']
            x, y = get_dialogs_bounds(cb.from_user.id, dialogs)
            bot.edit_message_reply_markup(chatid, messageid, reply_markup=distrib_edit_menu(dialogs, x, y, id=id))
        if pl == "next":
            history.next_page(cb.from_user.id)
            update_dialogs()
        elif pl == "prev":
            history.prev_page(cb.from_user.id)
            update_dialogs()
        elif pl == "back":
            history.move_up(cb.from_user.id)
            bot.send_message(cb.message.chat.id, "Выберите рассылку для управления", reply_markup=distrib_mgnmt_menu(cb.from_user.id))
        elif pl == "all":
            d = history.storage[cb.from_user.id]['dialogs']
            for dialog in d:
                dialog[2] = True
            update_dialogs()
        elif pl == "delete":
            history.move_down(cb.from_user.id, MenuNames.distrib_delete_confirm)
            bot.delete_message(cb.message.chat.id, cb.message.id)
            bot.send_message(cb.message.chat.id, "Вы уверены что хотите удалить рассылку?", reply_markup=distrib_delete_confirm_menu(id, id))
        elif pl == "auto":
            history.move_down(cb.from_user.id, MenuNames.distrib_auto_edit)
            bot.delete_message(cb.message.chat.id, cb.message.id)
            history.storage[cb.from_user.id]['auto_id'] = id
            with Session(autoflush=False, bind=engine) as db:
                db_data = db.query(Distribs).filter(Distribs.id == id).first()
                selected = transform_time_to_sec(db_data.auto_period, True)
                history.storage[cb.from_user.id]['auto_period'] = selected
                bot.send_message(cb.message.chat.id, "Настройки авто рассылки", reply_markup=distrib_auto_edit_menu(selected))
        elif pl == "save":
            bot.delete_message(cb.message.chat.id, cb.message.id)
            if 'editing' in history.storage[cb.from_user.id] and history.storage[cb.from_user.id]['editing'] == True:
                history.storage[cb.from_user.id]['editing'] = False
                with Session(autoflush=False, bind=engine) as db:
                    selected_dialogs = filter(lambda v: v[2], history.storage[cb.from_user.id]["dialogs"])
                    chatlist = [str(v[1]) for v in selected_dialogs]
                    dbdistrib = db.query(Distribs).filter(Distribs.id == int(id)).first()
                    print(dbdistrib)
                    dbdistrib.chats = ','.join(chatlist)
                    db.commit()
                    bot.send_message(cb.message.chat.id, "Рассылка успешно обновлена")
                    return menu(cb.from_user)
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
    
    #МЕНЮ НАТСРОЙКИ АВТО ОТПРАВКИ
    elif usermenu == MenuNames.distrib_auto_edit:
        if pl == "ok":
            bot.delete_message(cb.message.chat.id, cb.message.id)
            bot.send_message(cb.message.chat.id, "Введите текст авто рассылки. Не удаляйте сообщение с текстом в будущем.")
            bot.register_next_step_handler_by_chat_id(cb.message.chat.id, save_autodistrib_message_id)
        elif pl == "no":
            bot.delete_message(cb.message.chat.id, cb.message.id)
            with Session(autoflush=False, bind=engine) as db:
                d = db.query(Distribs).filter(Distribs.id == history.storage[cb.from_user.id]['auto_id']).first()
                d.auto_period = 0
                d.auto_message_id = 0
                db.commit()
                menu(cb.from_user)
        else:
            history.storage[cb.from_user.id]['auto_period'] = pl
            bot.edit_message_reply_markup(cb.message.chat.id, cb.message.id, reply_markup=distrib_auto_edit_menu(pl))

    #МЕНЮ УПРАВЛЕНИЯ РАССЫЛКАМИ
    elif usermenu == MenuNames.distrib_mgnmt:
        bot.delete_message(cb.message.chat.id, cb.message.id)
        if pl == "back":
            return menu(cb.from_user)
        elif pl == "new":
            with Session(autoflush=False, bind=engine) as db:
                u = db.query(User).filter(User.id == cb.from_user.id).first()
                async def getdialogs():
                    def titleorfname(ent):
                        if isinstance(ent, telethon.types.Channel) or isinstance(ent, telethon.types.Channel):
                            return ent.title
                        if isinstance(ent, telethon.types.User):
                            return ent.first_name
                    app = create_client(u.username)
                    async with app:
                        tgdialogs = await app.get_dialogs()
                        dialogs =  [[str(titleorfname(dialog.entity)), dialog.id, False] for dialog in tgdialogs]
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
                dbdistrib = db.query(Distribs).filter(Distribs.id == int(id)).first()
                dbdialogs = dbdistrib.chats.split(',')
                
                async def getdialogs():
                    def titleorfname(ent):
                        if isinstance(ent, telethon.types.Channel) or isinstance(ent, telethon.types.Chat):
                            return ent.title
                        if isinstance(ent, telethon.types.User):
                            return ent.first_name
                    app = create_client(u.username)
                    async with app:
                        tgdialogs = await app.get_dialogs()
                        ##SYNC TG AND DB DELETED CHATS
                        tgids = [str(d.id) for d in tgdialogs]
                        newdb = list(filter(lambda v: v in tgids, dbdialogs))
                        dbdistrib.chats = ','.join(newdb)
                        print(dbdistrib.chats)
                        db.commit()
                        #===========
                        newdbdialogs = dbdistrib.chats.split(',')
                        dialogs =  [[str(titleorfname(dialog.entity)), dialog.id, str(dialog.id) in newdbdialogs] for dialog in tgdialogs]
                        #dialogs = sorted(dialogs, key=lambda v: v[2], reverse=True)
                        history.storage[cb.from_user.id]['dialogs'] = dialogs
                        history.move_down(cb.from_user.id, MenuNames.distrib_edit)
                        x, y = get_dialogs_bounds(cb.from_user.id, dialogs)
                        r = bot.send_message(cb.message.chat.id, f"Редактрирвоание рассылки {name}", reply_markup=distrib_edit_menu(dialogs, x, y, delete=True, id=id))
                        history.storage[cb.from_user.id]['dialogs_id'] = [r.message_id, r.chat.id]
                        history.storage[cb.from_user.id]['editing'] = True

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
            msg = "Введите данные пользователяв следющем формате:\n\nTelegram ID\nНазвание (произвольное, уникальное)"
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

def save_autodistrib_message_id(message: telebot.types.Message):
    msg = bot.send_message(message.chat.id, "Подождите, сохраняю...")
    st = history.storage[message.from_user.id]
    with Session(autoflush=False, bind=engine) as db:
        async def save_id(user_id: int):
            u = db.query(User).filter(User.id == user_id).first()
            app = create_client(u.username)
            async with app:
                ent_bot = await app.get_entity(7030989354)
                last_msg = await app.get_messages(ent_bot)
                distr = db.query(Distribs).filter(Distribs.id == st['auto_id']).first()
                distr.auto_period = transform_time_to_sec(st['auto_period'])
                distr.auto_message_id = last_msg.id
                db.commit()
                bot.edit_message_text("Сохранено", msg.chat.id, msg.id)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(save_id(message.from_user.id))
    menu(message.from_user)

def send_distrib_input(message: telebot.types.Message):
    if message.text.startswith('/cancel'):
        return menu(message.from_user)
    with Session(autoflush=False, bind=engine) as db:
        u = db.query(User).filter(User.id == message.from_user.id).first()

        async def senddistrib():
            #in_memory=True, session_string=u.session_string
            app = create_client(u.username)
            async with app:
                lastdist.clear()
                todelete = []
                errors_slow = 0
                errors_banned = 0
                errors_unk = 0
                total = 0
                ent_bot = await app.get_entity(7030989354)
                last_msg = await app.get_messages(ent_bot)
                bot.send_message(message.chat.id, "Выполняю рассылку...")
                for chatid in history.storage[message.from_user.id]['chats'].split(','):
                    try:
                        ent = await app.get_entity(int(chatid))
                        print("sending to", chatid)
                        await app.forward_messages(ent, last_msg, drop_author=True)
                        total += 1
                        lastdist.add(ent, True)
                        #await app.send_message(ent, message.text)
                    except telethon.errors.rpcerrorlist.SlowModeWaitError:
                        errors_slow += 1
                        #todelete.append(chatid)
                        lastdist.add(ent, False, "SlowMode")
                    except telethon.errors.rpcerrorlist.ChannelPrivateError:
                        lastdist.add(ent, False, "Banned/No rights")
                        errors_banned += 1
                        todelete.append(chatid)
                    except telethon.errors.UserBannedInChannelError:
                        lastdist.add(ent, False, "You're banned from sending messages in supergroups/channels")
                        errors_banned += 1
                    except Exception as e:
                        print("BASE", e)
                        lastdist.add(ent, False, "Unkown")
                        todelete.append(chatid)
                        errors_unk += 1
                    await asyncio.sleep(config.SEND_DELAY)
                print("sending ends")
                bot.send_message(message.chat.id, f"Рассылка выполнена. Сообщение успешно доставлено {total} раз")
                if errors_banned + errors_slow + errors_unk > 0:
                    txt = f"Есть ошибки. Всего: {errors_banned + errors_slow + errors_unk}\n{errors_slow} столько чатов со слоу модом \n{errors_banned} Столько чатов бан/приватные\n{errors_unk} Столько неопознанных ошибок."

                    newids = history.storage[message.from_user.id]['chats'].split(',')
                    newids = list(filter(lambda x: x not in todelete, newids))
                    dbdistrib = db.query(Distribs).filter(Distribs.id == history.storage[message.from_user.id]['distribid']).first()
                    if dbdistrib:
                        dbdistrib.chats = ','.join(newids)
                        db.commit()
                        txt += f"Из рассылки атоматически удалены столько чатов - {len(todelete)}"
                    bot.send_message(message.chat.id, txt)

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
        userid = int(data[0])
        username = data[1]
    except Exception as ex:
        print(ex)
        bot.register_next_step_handler_by_chat_id(message.chat.id, new_user_data_input)
        return bot.send_message(message.chat.id, "Данные введены в неверном формате. Попробуйте еще раз")
    
    with Session(autoflush=False, bind=engine) as db:
        found = db.query(User).filter(User.id == userid or User.username == username).all()
        if len(found) > 0:
            return bot.send_message(message.chat.id, "Такой пользователь уже зарегистророван")
        
        newuser = User(id=userid, username=username)
        db.add(newuser)
        db.commit()

        bot.send_message(message.chat.id, f"Успешно создан пользователь {username}")
        menu(message.from_user)

