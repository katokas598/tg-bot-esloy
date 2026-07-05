from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import Database


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Приветствие", callback_data="admin:welcome")],
            [InlineKeyboardButton(text="Правила", callback_data="admin:rules")],
            [InlineKeyboardButton(text="Админы", callback_data="admin:admins")],
            [InlineKeyboardButton(text="Discord", callback_data="admin:discord")],
            [InlineKeyboardButton(text="TikTok", callback_data="admin:tiktok")],
            [InlineKeyboardButton(text="Команды", callback_data="admin:commands")],
        ]
    )


def back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="admin:menu")]]
    )


def item_menu(item: str, enabled: bool) -> InlineKeyboardMarkup:
    status = "Выключить" if enabled else "Включить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Изменить", callback_data=f"edit:{item}")],
            [InlineKeyboardButton(text=status, callback_data=f"toggle:{item}")],
            [InlineKeyboardButton(text="Назад", callback_data="admin:menu")],
        ]
    )


def simple_edit_menu(item: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Изменить", callback_data=f"edit:{item}")],
            [InlineKeyboardButton(text="Назад", callback_data="admin:menu")],
        ]
    )


def commands_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Добавить/изменить команду", callback_data="command:add")],
            [InlineKeyboardButton(text="Список команд", callback_data="command:list")],
            [InlineKeyboardButton(text="Удалить команду", callback_data="command:delete")],
            [InlineKeyboardButton(text="Назад", callback_data="admin:menu")],
        ]
    )


def welcome_buttons(db: Database) -> InlineKeyboardMarkup | None:
    rows: list[list[InlineKeyboardButton]] = []

    if db.enabled("rules_enabled"):
        rows.append([InlineKeyboardButton(text="Правила", callback_data="public:rules")])
    if db.enabled("admins_enabled"):
        rows.append([InlineKeyboardButton(text="Админы", callback_data="public:admins")])

    link_row: list[InlineKeyboardButton] = []
    if db.enabled("discord_enabled"):
        link_row.append(InlineKeyboardButton(text="Discord", callback_data="public:discord"))
    if db.enabled("tiktok_enabled"):
        link_row.append(InlineKeyboardButton(text="TikTok", callback_data="public:tiktok"))
    if link_row:
        rows.append(link_row)

    if not rows:
        return None
    return InlineKeyboardMarkup(inline_keyboard=rows)
