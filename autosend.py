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

def extract_usernames(text):
    pattern = r'@[\w]+'
    usernames = re.findall(pattern, text)
    return usernames

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
        resendcounter = []
        todelete = []
        sent = [] #entity
        resend = []
        errors = {
            "slow": 0,
            "banned": 0,
            "unk": 0,
            "resend": 0
        }
        bot.send_message(distrib.belong_to, f"Выполняю авто рассылку {distrib.name}...")

        #обход удаления сообщений
        @app.on(events.NewMessage)
        async def new_handler(event):
            if event.message.mentioned:
                peer_id = int(event.message.peer_id) 
                if peer_id in resendcounter:
                    resendcounter[peer_id] += 1
                else:
                    resendcounter[peer_id] = 1
                if resendcounter[peer_id] > 3:
                    return print(f"Подписки на каналы (из {peer_id}) превысили лимит, останавливаем эту ерунду")
                ent = await app.get_entity(peer_id)
                if ent in sent:
                    txt = event.message.text
                    chats = extract_usernames(txt)
                    for chat in chats:
                        try:
                            print(f"Подписываемся на канал(из {peer_id} - {resendcounter[peer_id]} попытка): ", chat)
                            await app(telethon.functions.channels.JoinChannelRequest(
                                    channel=chat
                                ))
                            resend.append(ent)
                        except Exception as e:
                            print("Ошибка подписки на канал: ", e)
        ##################

        try:
            chatent = await app.get_entity(distrib.belong_to)
        except Exception:
            for admin in config.admin_id:
                bot.send_message(admin, f"Невозможно выполнить рассылку {distrib.name} с аккаунта {u.username} ({distrib.belong_to}) из-за внутренней ошибки. Авто рассылка деактивирована.")
                
            return None, distrib.id
        
        async def sendToChat(chatid = None, chatentinity = None):
            try:
                if chatid:
                    ent = await app.get_entity(int(chatid))
                else:
                    chatid = chatentinity.id
                    ent = chatentinity
                isresend = False
                if ent in resend:
                    print(distrib.name, "REsending to", chatid)
                    isresend = True
                    errors['resend'] += 1
                else:
                    print(distrib.name, "sending to", chatid)
                    sent.append(chatid)
                
                await app.forward_messages(ent, distrib.auto_message_id, drop_author=True, from_peer=chatent)
                
                if isresend:
                    resend.remove(chatentinity)
                else:
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

        for chatid in distrib.chats.split(','):
            await sendToChat(chatid=chatid)
            await asyncio.sleep(delay)

        await asyncio.sleep(10) #ждем удаления сообщений
        while len(resend) > 0:
            for ent in resend:
                await sendToChat(chatentinity=ent)
            await asyncio.sleep(5) #ждем удаления сообщений
        print(distrib.name, "sending ends")
        bot.send_message(distrib.belong_to, f"Рассылка выполнена. Сообщение успешно доставлено {len(sent)} раз")
        if errors['banned'] + errors['slow'] + errors['unk'] + errors['resend'] > 0:
            txt = f"Но есть нюанс. Всего: {errors['banned'] + errors['slow'] + errors['unk']}\n{errors['slow']} столько чатов со слоу модом \n{errors['banned']} Столько чатов бан/приватные\n{errors['resend']} Столько раз переслали чтобы обойти антифлуд ботов\n{errors['unk']} Столько неопознанных ошибок."

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