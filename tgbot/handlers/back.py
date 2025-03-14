from aiogram import Router, types, Bot, F
from aiogram.filters import CommandStart, Command, StateFilter, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message
from tgbot.keyboards.inline import start_keyboard_after_date
from tgbot.handlers.user import caption_pre_sales
from aiogram.types import FSInputFile

back_router = Router()

photo = FSInputFile("game_chart.jpg")


@back_router.callback_query(F.data == 'back')
async def social(callback: types.CallbackQuery):
    text = caption_pre_sales
    await callback.message.answer_photo(photo=photo, caption=f"{text}", reply_markup=start_keyboard_after_date())
    await callback.message.delete()
    await callback.answer()
