import telethon, telebot, qrcode, asyncio, os

qr = qrcode.QRCode()

def gen_qr(token:str):
    qr.clear()
    qr.add_data(token)

def display_url_as_qr(url):
    gen_qr(url)

async def main(client: telethon.TelegramClient, botref: telebot.TeleBot, chat_id: int):
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
    os.remove(fname)
    botref.delete_message(chat_id, msg.message_id)
    botref.send_message(chat_id, "Вы успешно авторизовались")

TELEGRAM_API_ID=28639018
TELEGRAM_API_HASH="f014cc12e32f1f618da532184382c3a7"

def create_client(acc_name: str, loop = None) -> telethon.TelegramClient:
    return telethon.TelegramClient(acc_name, TELEGRAM_API_ID, TELEGRAM_API_HASH, loop=loop, system_version="1.4.2 DistributionxXXL_AMG(OSX/4:1)", device_model="Factory-New Console v0.41")

async def auth_qr(acc_name: str, botref: telebot.TeleBot, chatid: int):
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    client = create_client(acc_name, loop)
    await main(client, botref, chatid)
    #client.loop.run_until_complete(main(client, botref, chatid))
    