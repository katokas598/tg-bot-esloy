import asyncio
import html
import logging
import re
import time

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import ChatMemberUpdatedFilter, CommandStart, JOIN_TRANSITION
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message, User
from aiogram.client.default import DefaultBotProperties

from config import load_config
from database import Database
from keyboards import admin_menu, back_menu, commands_menu, item_menu, simple_edit_menu, welcome_buttons


COMMAND_RE = re.compile(r"^/[a-zA-Z0-9_]{1,32}$")


class AdminStates(StatesGroup):
    waiting_setting_value = State()
    waiting_command_name = State()
    waiting_command_response = State()
    waiting_command_delete = State()


def display_name(message: Message) -> str:
    user = message.from_user
    if user is None:
        return "друг"
    return user.full_name or user.username or "друг"


def format_welcome(template: str, user: User) -> str:
    mention = f'<a href="tg://user?id={user.id}">{member_name(user)}</a>'
    return html.escape(template).replace("{name}", mention).replace("{user}", mention)


def member_name(user: User) -> str:
    return html.escape(user.full_name or user.username or "друг")


def normalize_command(text: str) -> str | None:
    command = text.strip().split(maxsplit=1)[0].lower()
    if "@" in command:
        command = command.split("@", maxsplit=1)[0]
    if not COMMAND_RE.match(command):
        return None
    return command


async def send_admin_menu(message: Message) -> None:
    await message.answer("Админ-панель", reply_markup=admin_menu())


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    db = Database(config.db_path)
    db.init()
    last_welcomes: dict[tuple[int, int], float] = {}

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    async def send_welcome(chat_id: int, user: User) -> None:
        if user.is_bot:
            return

        cache_key = (chat_id, user.id)
        now = time.monotonic()
        if now - last_welcomes.get(cache_key, 0) < 10:
            return
        last_welcomes[cache_key] = now

        text = format_welcome(db.get_setting("welcome_text"), user)
        logging.info("New member detected: chat_id=%s user_id=%s name=%s", chat_id, user.id, user.full_name)
        await bot.send_message(chat_id, text, reply_markup=welcome_buttons(db))

    @dp.message(CommandStart())
    async def start(message: Message) -> None:
        await message.answer("Введите пароль для входа в админ-панель.")

    @dp.message(F.new_chat_members)
    async def new_members(message: Message) -> None:
        for member in message.new_chat_members:
            await send_welcome(message.chat.id, member)

    @dp.chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
    async def member_joined(event: ChatMemberUpdated) -> None:
        await send_welcome(event.chat.id, event.new_chat_member.user)

    @dp.callback_query(F.data == "public:rules")
    async def public_rules(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message:
            await callback.message.answer(db.get_setting("rules_text"))

    @dp.callback_query(F.data == "public:admins")
    async def public_admins(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message:
            await callback.message.answer(db.get_setting("admins_text"))

    @dp.callback_query(F.data == "public:discord")
    async def public_discord(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message:
            await callback.message.answer(db.get_setting("discord_url"))

    @dp.callback_query(F.data == "public:tiktok")
    async def public_tiktok(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message:
            await callback.message.answer(db.get_setting("tiktok_url"))

    @dp.callback_query(F.data == "admin:menu")
    async def admin_panel(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await callback.answer()
        if callback.message:
            await callback.message.edit_text("Админ-панель", reply_markup=admin_menu())

    @dp.callback_query(F.data == "admin:welcome")
    async def welcome_settings(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message:
            await callback.message.edit_text(
                "Текущее приветствие:\n\n"
                f"{db.get_setting('welcome_text')}\n\n"
                "Используйте {name} или {user}, чтобы подставить кликабельное имя участника.",
                reply_markup=simple_edit_menu("welcome_text"),
            )

    @dp.callback_query(F.data == "admin:rules")
    async def rules_settings(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message:
            await callback.message.edit_text(
                f"Правила:\n\n{db.get_setting('rules_text')}",
                reply_markup=item_menu("rules", db.enabled("rules_enabled")),
            )

    @dp.callback_query(F.data == "admin:admins")
    async def admins_settings(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message:
            await callback.message.edit_text(
                f"Админы:\n\n{db.get_setting('admins_text')}",
                reply_markup=item_menu("admins", db.enabled("admins_enabled")),
            )

    @dp.callback_query(F.data == "admin:discord")
    async def discord_settings(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message:
            await callback.message.edit_text(
                f"Discord текст:\n\n{db.get_setting('discord_url')}",
                reply_markup=item_menu("discord", db.enabled("discord_enabled")),
            )

    @dp.callback_query(F.data == "admin:tiktok")
    async def tiktok_settings(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message:
            await callback.message.edit_text(
                f"TikTok текст:\n\n{db.get_setting('tiktok_url')}",
                reply_markup=item_menu("tiktok", db.enabled("tiktok_enabled")),
            )

    @dp.callback_query(F.data.startswith("toggle:"))
    async def toggle_button(callback: CallbackQuery) -> None:
        item = callback.data.split(":", maxsplit=1)[1]
        setting_key = f"{item}_enabled"
        enabled = db.toggle(setting_key)
        await callback.answer("Включено" if enabled else "Выключено")
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=item_menu(item, enabled))

    @dp.callback_query(F.data.startswith("edit:"))
    async def edit_setting(callback: CallbackQuery, state: FSMContext) -> None:
        item = callback.data.split(":", maxsplit=1)[1]
        setting_map = {
            "welcome_text": "welcome_text",
            "rules": "rules_text",
            "admins": "admins_text",
            "discord": "discord_url",
            "tiktok": "tiktok_url",
        }
        setting_key = setting_map[item]
        await state.set_state(AdminStates.waiting_setting_value)
        await state.update_data(setting_key=setting_key)
        await callback.answer()
        if callback.message:
            await callback.message.answer("Отправьте новое значение.", reply_markup=back_menu())

    @dp.callback_query(F.data == "admin:commands")
    async def command_settings(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await callback.answer()
        if callback.message:
            await callback.message.edit_text("Настройка команд", reply_markup=commands_menu())

    @dp.callback_query(F.data == "command:add")
    async def add_command_start(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(AdminStates.waiting_command_name)
        await callback.answer()
        if callback.message:
            await callback.message.answer("Отправьте команду, например /info.", reply_markup=back_menu())

    @dp.callback_query(F.data == "command:list")
    async def list_commands(callback: CallbackQuery) -> None:
        await callback.answer()
        commands = db.list_commands()
        if not commands:
            text = "Команд пока нет."
        else:
            text = "Список команд:\n\n" + "\n".join(f"{item['command']} - {item['response'][:80]}" for item in commands)
        if callback.message:
            await callback.message.answer(text, reply_markup=back_menu())

    @dp.callback_query(F.data == "command:delete")
    async def delete_command_start(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(AdminStates.waiting_command_delete)
        await callback.answer()
        if callback.message:
            await callback.message.answer("Отправьте команду для удаления, например /info.", reply_markup=back_menu())

    @dp.message(AdminStates.waiting_setting_value)
    async def save_setting(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        setting_key = data["setting_key"]
        db.set_setting(setting_key, message.text or "")
        await state.clear()
        await message.answer("Сохранено.", reply_markup=admin_menu())

    @dp.message(AdminStates.waiting_command_name)
    async def save_command_name(message: Message, state: FSMContext) -> None:
        if not message.text:
            await message.answer("Отправьте команду текстом, например /info.")
            return
        command = normalize_command(message.text)
        if command is None:
            await message.answer("Команда должна выглядеть так: /info. Только латинские буквы, цифры и _.")
            return
        await state.update_data(command=command)
        await state.set_state(AdminStates.waiting_command_response)
        await message.answer("Теперь отправьте текст ответа для этой команды.")

    @dp.message(AdminStates.waiting_command_response)
    async def save_command_response(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        command = data["command"]
        db.add_command(command, message.text or "")
        await state.clear()
        await message.answer(f"Команда {command} сохранена.", reply_markup=commands_menu())

    @dp.message(AdminStates.waiting_command_delete)
    async def delete_command(message: Message, state: FSMContext) -> None:
        if not message.text:
            await message.answer("Отправьте команду текстом, например /info.")
            return
        command = normalize_command(message.text)
        if command is None:
            await message.answer("Команда должна выглядеть так: /info.")
            return
        deleted = db.delete_command(command)
        await state.clear()
        await message.answer("Команда удалена." if deleted else "Такой команды нет.", reply_markup=commands_menu())

    @dp.message(F.text)
    async def text_handler(message: Message) -> None:
        text = message.text or ""
        if text.strip() == config.admin_password:
            await send_admin_menu(message)
            return

        if text.startswith("/"):
            command = normalize_command(text)
            if command is None:
                return
            response = db.get_command(command)
            if response is not None:
                await message.answer(response)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
