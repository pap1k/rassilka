from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from orm.models import User, Distribs
from sqlalchemy.orm import Session
from orm.db import engine

class MenuNames:
    main = "main"
    users_mgnmt = "users"
    users_delete_confirm = "users_del_yesno"
    distrib_delete_confirm = "distrib_del_yesno"
    distrib_mgnmt = "distribs"
    distrib_edit = "distrib_edit"
    distrib_send_menu = "distrib_send_menu"

def start_menu(is_admin: bool) -> InlineKeyboardMarkup:
    mk = InlineKeyboardMarkup()
    mk.add(InlineKeyboardButton("Выполнить рассылку", callback_data=f"menu:{MenuNames.distrib_send_menu}"))
    if is_admin:
        mk.add(InlineKeyboardButton("[A] Управление пользователями", callback_data=f"menu:{MenuNames.users_mgnmt}"))
    mk.add(InlineKeyboardButton("Управление рассылками", callback_data=f"menu:{MenuNames.distrib_mgnmt}"))
    return mk

def admin_menu() -> InlineKeyboardMarkup:
    mk = InlineKeyboardMarkup()
    mk.add(InlineKeyboardButton("[A] Управление пользователями", callback_data=f"menu:{MenuNames.users_mgnmt}"))
    return mk

def distrib_send_menu(userid, page=1) -> InlineKeyboardMarkup:
    mk = InlineKeyboardMarkup()
    lim = 10
    with Session(autoflush=False, bind=engine) as db:
        distrs = db.query(Distribs).filter(Distribs.belong_to == userid).limit(lim).offset((page-1)*lim).all()
        for dist in distrs:
            mk.add(InlineKeyboardButton(dist.name, callback_data=f"{MenuNames.distrib_mgnmt}:{dist.id}"))
    mk.add(InlineKeyboardButton("< Главное меню", callback_data=f"{MenuNames.distrib_mgnmt}:back"))
    return mk

def distrib_mgnmt_menu(userid, page=1) -> InlineKeyboardMarkup:
    mk = InlineKeyboardMarkup()
    mk.add(InlineKeyboardButton("> Создать рассылку", callback_data=f"{MenuNames.distrib_mgnmt}:new"))
    lim = 10
    with Session(autoflush=False, bind=engine) as db:
        distrs = db.query(Distribs).filter(Distribs.belong_to == userid).limit(lim).offset((page-1)*lim).all()
        for dist in distrs:
            mk.add(InlineKeyboardButton(dist.name, callback_data=f"{MenuNames.distrib_mgnmt}:{dist.id}-{dist.name}"))
    if page >= 1 and len(distrs) == 10:
        mk.add(InlineKeyboardButton(">> Страница вперед", callback_data=f"{MenuNames.distrib_mgnmt}:next"))
    if page > 1:
        mk.add(InlineKeyboardButton("<< Страница назад", callback_data=f"{MenuNames.distrib_mgnmt}:prev"))
    mk.add(InlineKeyboardButton("< Главное меню", callback_data=f"{MenuNames.distrib_mgnmt}:back"))
    return mk

def user_mgnmt_menu(page=1) -> InlineKeyboardMarkup:
    mk = InlineKeyboardMarkup()
    mk.add(InlineKeyboardButton("> Добавить нового", callback_data=f"{MenuNames.users_mgnmt}:new"))
    lim = 10
    with Session(autoflush=False, bind=engine) as db:
        users = db.query(User).limit(lim).offset((page-1)*lim).all()
        for user in users:
            mk.add(InlineKeyboardButton(user.username, callback_data=f"{MenuNames.users_mgnmt}:{user.id}-{user.username}"))
    if page >= 1 and len(users) == 10:
        mk.add(InlineKeyboardButton(">> Страница вперед", callback_data=f"{MenuNames.users_mgnmt}:next"))
    if page > 1:
        mk.add(InlineKeyboardButton("<< Страница назад", callback_data=f"{MenuNames.users_mgnmt}:prev"))
    mk.add(InlineKeyboardButton("< Главное меню", callback_data=f"{MenuNames.users_mgnmt}:back"))
    return mk

def distrib_delete_confirm_menu(username, distid) -> InlineKeyboardMarkup:
    mk = InlineKeyboardMarkup()
    mk.add(InlineKeyboardButton("Да", callback_data=f"{MenuNames.distrib_delete_confirm}:{distid}-yes"))
    mk.add(InlineKeyboardButton("Нет", callback_data=f"{MenuNames.distrib_delete_confirm}:{distid}-no"))
    return mk

def user_delete_confirm_menu(username, userid) -> InlineKeyboardMarkup:
    mk = InlineKeyboardMarkup()
    mk.add(InlineKeyboardButton("Да", callback_data=f"{MenuNames.users_delete_confirm}:{userid}-yes"))
    mk.add(InlineKeyboardButton("Нет", callback_data=f"{MenuNames.users_delete_confirm}:{userid}-no"))
    return mk

def distrib_edit_menu(chatlist: list[list[str, int, bool]], x, y, delete = False, id=0) -> InlineKeyboardMarkup:
    mk = InlineKeyboardMarkup()
    for chat in chatlist[x:y]:
        status = "🟢" if chat[2] else "🔴"
        mk.add(InlineKeyboardButton(status+" "+chat[0], callback_data=f"{MenuNames.distrib_mgnmt}:{chat[1]}--{id}"))
    if y < len(chatlist):
        mk.add(InlineKeyboardButton(">> Страница вперед", callback_data=f"{MenuNames.distrib_mgnmt}:next--{id}"))
    if x != 0:
        mk.add(InlineKeyboardButton("<< Страница назад", callback_data=f"{MenuNames.distrib_mgnmt}:prev--{id}"))
    mk.add(InlineKeyboardButton("👌 Выбрать все", callback_data=f"{MenuNames.distrib_mgnmt}:all--{id}"))
    mk.add(InlineKeyboardButton("Сохранить", callback_data=f"{MenuNames.distrib_mgnmt}:save--{id}"))
    if delete:
        mk.add(InlineKeyboardButton("Удалить", callback_data=f"{MenuNames.distrib_mgnmt}:delete--{id}"))
    mk.add(InlineKeyboardButton("< Управления рассылками", callback_data=f"{MenuNames.distrib_mgnmt}:back--{id}"))
    return mk
