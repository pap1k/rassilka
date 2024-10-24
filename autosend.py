import telethon, time, json, asyncio, telebot, config, sys, re
from orm.models import User, Distribs
from sqlalchemy.orm import Session
from orm.db import engine
from user.user import create_client
from telethon import events

def get_current_delay():
    try:
        with open(config.SEND_DELAY_FILE, 'r') as f:
            cur = f.read()
            return float(cur)
    except:
        with open(config.SEND_DELAY_FILE, 'w') as f:
            f.write(str(config.SEND_DELAY))
        return get_current_delay()

bot = telebot.TeleBot(config.BOT_TOKEN)

def extract_login_and_link(text):
    pattern = r'@(\w+)(?:\s*\((https?://[^\s]+)\))?'
    
    matches = re.findall(pattern, text)
    
    result = ""
    for match in matches:
        login = match[0]
        link = match[1] if match[1] else None
        
        if login == "chat" and link:
            result = login
        elif login != "chat":
            result = login
    
    return result

async def sender(distrib: Distribs, u: User, delay: float):
    try:
        app = create_client(u.username)
        await app.connect()
        if not await app.is_user_authorized():
            raise Exception
    except Exception:

        for admin in config.admin_id:
            if u:
                bot.send_message(admin, f"Невозможно выполнить рассылку {distrib.name} так как пользователь {u.username}({distrib.belong_to}) не авторизован или заблокирован. Авто рассылка деактивирована")
            else:
                bot.send_message(admin, f"Невозможно выполнить рассылку {distrib.name} так как пользователь, которому она принадлежит({distrib.belong_to}) удален из базы бота. Авто рассылка деактивирована")
        return None, distrib.id
    
    async with app:
        resub = {}
        todelete = []
        sent = [] #entity
        errors = {
            "slow": 0,
            "banned": 0,
            "unk": 0,
            "subs": 0
        }
        bot.send_message(distrib.belong_to, f"Выполняю авто рассылку {distrib.name}...")

        #обход удаления сообщений
        @app.on(events.NewMessage)
        async def new_handler(event):
            if event.message.mentioned:
                print(event.message.text)
                peer_id = int(event.message.peer_id.channel_id) 
                if peer_id in resub:
                    resub[peer_id] += 1
                else:
                    resub[peer_id] = 1
                if resub[peer_id] > 3:
                    return print(f"Подписки на каналы (из {peer_id}) превысили лимит, останавливаем эту ерунду")
                ent = await app.get_entity(peer_id)
                if ent in sent:
                    txt = event.message.text
                    chats = extract_login_and_link(txt)
                    for chat in chats:
                        try:
                            print(f"Подписываемся на канал(из {peer_id} - {resub[peer_id]} попытка): ", chat)
                            await app(telethon.functions.channels.JoinChannelRequest(
                                    channel=chat
                                ))
                            errors["subs"] += 1
                        except Exception as e:
                            print("Ошибка подписки на канал: ", e)
        ##################

        try:
            chatent = await app.get_entity(distrib.belong_to)
        except Exception:
            for admin in config.admin_id:
                bot.send_message(admin, f"Невозможно выполнить рассылку {distrib.name} с аккаунта {u.username} ({distrib.belong_to}) из-за внутренней ошибки. Авто рассылка деактивирована.")
                
            return None, distrib.id
        

        for chatid in distrib.chats.split(','):
            try:
                ent = await app.get_entity(int(chatid))
                print(distrib.name, "sending to", chatid)
                await app.forward_messages(ent, distrib.auto_message_id, drop_author=True, from_peer=chatent)
                sent.append(ent)
                        
            except telethon.errors.rpcerrorlist.SlowModeWaitError:
                errors['slow']
            except telethon.errors.rpcerrorlist.ChannelPrivateError:
                errors['banned']
                todelete.append(chatid)
            except Exception as e:
                print("BASE", e)
                todelete.append(chatid)
                errors['unk']
            await asyncio.sleep(delay)

        await asyncio.sleep(10) #ждем удаления сообщений
        print(distrib.name, "sending ends")
        bot.send_message(distrib.belong_to, f"Рассылка выполнена. Сообщение успешно доставлено {len(sent)} раз")
        errorscount = errors['banned'] + errors['slow'] + errors['unk'] + errors['subs']
        print("info sent, errors: ", errorscount)
        if errorscount > 0:
            txt = f"Но есть нюансы. Всего: {errorscount} столько чатов со слоу модом \n{errors['banned']} Столько чатов бан/приватные\n{errors['subs']} На столько каналов подписались\n{errors['unk']} Столько неопознанных ошибок."
            print("report txt\n", txt)
            newids = distrib.chats.split(',')
            newids = list(filter(lambda x: x not in todelete, newids))
            txt += f"\n\nИз рассылки атоматически удалены столько чатов - {len(todelete)}"
            bot.send_message(distrib.belong_to, txt)

            return True, [str(distrib.id), ','.join(newids)]
        return True, [str(distrib.id), None]
        
    
async def auto_runner():
    sent = {}
    try:
        data = open("sent_data.txt", 'r').read()
        sent = json.loads(data)
        print(sent)
    except Exception:
        pass

    print(f"[AUTO] Starting")
    while True:
        tasks = []
        with Session(autoflush=False, bind=engine) as db:
            distribs = db.query(Distribs).filter(Distribs.auto_period != 0).all()
            print(f"[AUTO] Got db info ({len(distribs)})")
            for distrib in distribs:
                if str(distrib.id) in sent:
                    print(sent[str(distrib.id)], type(sent[str(distrib.id)]), distrib.auto_period, type(distrib.auto_period))
                    if distrib.auto_period == 'no':
                        distrib.auto_period = 0
                        db.commit()
                    if float(sent[str(distrib.id)]) + float(distrib.auto_period) > time.time() and "-test" not in sys.argv:
                        print("Skip")
                        continue
                u = db.query(User).filter(User.id == distrib.belong_to).first()
                tasks.append(asyncio.create_task(sender(distrib, u, get_current_delay())))
        
        for task in tasks:
            ok, payload = await task
            if ok:
                sent[payload[0]] = time.time()
                if payload[1]:
                    with Session(autoflush=False, bind=engine) as db:
                        distrib = db.query(Distribs).filter(Distribs.id == int(payload[0])).first()
                        distrib.chats = payload[1]
            else:
                try:
                    with Session(autoflush=False, bind=engine) as db:
                        distrib = db.query(Distribs).filter(Distribs.id == payload).first()
                        distrib.auto_period = 0
                        distrib.auto_message_id = 0
                        db.commit()
                except Exception:
                    print("Не удалось подключиться к базе")

        print("[AUTO] All checked")
        open("sent_data.txt", 'w').write(json.dumps(sent))
        await asyncio.sleep(3*60)


asyncio.run(auto_runner())