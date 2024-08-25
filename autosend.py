import telethon, time, json, asyncio, telebot, config
from orm.models import User, Distribs
from sqlalchemy.orm import Session
from orm.db import engine
from user.user import create_client

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

async def sender(distrib: Distribs, u: User):
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
        todelete = []
        errors_slow = 0
        errors_banned = 0
        errors_unk = 0
        total = 0
        bot.send_message(distrib.belong_to, f"Выполняю авто рассылку {distrib.name}...")
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

                total += 1
            except telethon.errors.rpcerrorlist.SlowModeWaitError:
                errors_slow += 1
            except telethon.errors.rpcerrorlist.ChannelPrivateError:
                errors_banned += 1
                todelete.append(chatid)
            except Exception as e:
                print("BASE", e)
                todelete.append(chatid)
                errors_unk += 1
            await asyncio.sleep(get_current_delay())
        print(distrib.name, "sending ends")
        bot.send_message(distrib.belong_to, f"Рассылка выполнена. Сообщение успешно доставлено {total} раз")
        if errors_banned + errors_slow + errors_unk > 0:
            txt = f"Есть ошибки. Всего: {errors_banned + errors_slow + errors_unk}\n{errors_slow} столько чатов со слоу модом \n{errors_banned} Столько чатов бан/приватные\n{errors_unk} Столько неопознанных ошибок."

            newids = distrib.chats.split(',')
            newids = list(filter(lambda x: x not in todelete, newids))
            txt += f"Из рассылки атоматически удалены столько чатов - {len(todelete)}"
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
                    if float(sent[str(distrib.id)]) + float(distrib.auto_period) > time.time():
                        print("Skip")
                        continue
                u = db.query(User).filter(User.id == distrib.belong_to).first()
                tasks.append(asyncio.create_task(sender(distrib, u)))
        
        for task in tasks:
            ok, payload = await task
            if ok:
                sent[payload[0]] = time.time()
                if payload[1]:
                    with Session(autoflush=False, bind=engine) as db:
                        distrib = db.query(Distribs).filter(Distribs.id == payload).first()
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