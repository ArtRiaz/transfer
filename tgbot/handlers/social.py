from aiogram import Router, types, Bot, F
from aiogram.filters import CommandStart, Command, StateFilter, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message
from tgbot.keyboards.inline import social_keyboard

from aiogram.types import FSInputFile

social_router = Router()

photo = FSInputFile("game_chart.jpg")


@social_router.callback_query(F.data == 'social')
async def social(callback: types.CallbackQuery):
    text = ("📢 Stay ahead of the game!\n\n"
            "The Oni are always watching. Stay connected to catch every announcement, update, and special event.\n\n"
            "🔥 Invite your friends and expand the Game Chart community!\n\n"
            "Don’t miss out—subscribe and stay sharp! 👹🚀")
    await callback.message.answer_photo(photo=photo, caption=f"{text}", reply_markup=social_keyboard())
    await callback.message.delete()
    await callback.answer()