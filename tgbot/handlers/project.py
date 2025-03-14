from aiogram import Router, types, Bot, F
from aiogram.filters import CommandStart, Command, StateFilter, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message
from tgbot.keyboards.inline import back

from aiogram.types import FSInputFile

project_router = Router()

photo = FSInputFile("game_chart.jpg")


@project_router.callback_query(F.data == 'project')
async def project(callback: types.CallbackQuery):
    text = ("🔥 Game Chart – Where Myth Meets Web3!\n\n"
            "Game Chart combines Japanese mythology, gaming, and blockchain, creating an interactive world where fate "
            "and strategy collide. Enter the realm of Oni, challenge your luck, and become part of the legend.\n"
            "👹 Early challengers reap the greatest rewards! Don’t miss your chance to get ahead.\n\n"
            "🚀 Join the whitelist now!")
    await callback.message.answer_photo(photo=photo, caption=f"{text}", reply_markup=back())
    await callback.message.delete()
    await callback.answer()
