import telethon, time, json, asyncio, telebot, config
from orm.models import User, Distribs
from sqlalchemy.orm import Session
from orm.db import engine
from user.user import create_client


bot = telebot.TeleBot(config.BOT_TOKEN)

async def auto_task():
    sent = {}
    try:
        data = open("sent_data.txt", 'r').read()
        sent = json.loads(data)
        print(sent)
    except Exception:
        pass

    print(f"[AUTO] Starting")
    while True:
        with Session(autoflush=False, bind=engine) as db:
            distribs = db.query(Distribs).filter(Distribs.auto_period != 0).all()
            print(f"[AUTO] Got db info ({len(distribs)})")
            for distrib in distribs:
                if str(distrib.id) in sent:
                    print(sent[str(distrib.id)], type(sent[str(distrib.id)]), distrib.auto_period, type(distrib.auto_period))
                    if sent[str(distrib.id)] + distrib.auto_period > time.time():
                        continue
                u = db.query(User).filter(User.id == distrib.belong_to).first()

                app = create_client(u.username)
                async with app:
                    todelete = []
                    errors_slow = 0
                    errors_banned = 0
                    errors_unk = 0
                    total = 0
                    bot.send_message(distrib.belong_to, f"Выполняю авто рассылку {distrib.name}...")
                    chatent = await app.get_entity(distrib.belong_to)
                    for chatid in distrib.chats.split(','):
                        ent = await app.get_entity(int(chatid))
                        try:
                            print("sending to", chatid)
                            
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
                        await asyncio.sleep(1/80)
                    print("sending ends")
                    sent[str(distrib.id)] = time.time()
                    bot.send_message(distrib.belong_to, f"Рассылка выполнена. Сообщение успешно доставлено {total} раз")
                    if errors_banned + errors_slow + errors_unk > 0:
                        txt = f"Есть ошибки. Всего: {errors_banned + errors_slow + errors_unk}\n{errors_slow} столько чатов со слоу модом \n{errors_banned} Столько чатов бан/приватные\n{errors_unk} Столько неопознанных ошибок."

                        newids = distrib.chats.split(',')
                        newids = list(filter(lambda x: x not in todelete, newids))
                        distrib.chats = ','.join(newids)
                        db.commit()
                        txt += f"Из рассылки атоматически удалены столько чатов - {len(todelete)}"
                        bot.send_message(distrib.belong_to, txt)
        print("[AUTO] All checked")
        open("sent_data.txt", 'w').write(json.dumps(sent))
        await asyncio.sleep(3*60)

loop = asyncio.new_event_loop()
loop.create_task(auto_task())
loop.run_forever()