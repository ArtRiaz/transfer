from aiogram import Router, F, types
from aiogram.types import Message
from tgbot.filters.admin import AdminFilter
from aiogram.filters import Command
import logging

from infrastructure.database.repo.requests import RequestsRepo

admin_router = Router()
admin_router.message.filter(AdminFilter())

database = [
    6583921306,
    6672506961
]


@admin_router.message(Command("post"))
async def post(message: Message):
    text_to_send = "Ваше сообщение для рассылки."
    for user_id in database:
        try:
            await message.bot.send_message(user_id, text_to_send)
        except Exception as e:
            await message.answer(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
    await message.answer("Post Success")


@admin_router.message(Command("clear"))
async def clear_users_command(message: types.Message, repo: RequestsRepo):
    await repo.users.clear_users()
    await message.answer("✅ All users have been deleted from the database.")