from aiogram import Router, F, types, Bot
from aiogram.types import Message
from tgbot.filters.admin import AdminFilter
from aiogram.filters import Command
import logging
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.types import FSInputFile

from infrastructure.database.repo.requests import RequestsRepo

admin_router = Router()
admin_router.message.filter(AdminFilter())


@admin_router.message(Command("post"))
async def broadcast_message(message: types.Message, state: FSMContext):
    """
    Обработчик кнопки "Розсилання". Запрашивает текст и (опционально) фото для рассылки.
    """
    await state.set_state("broadcast")
    await message.answer("Enter the message text for the broadcast. You can also attach an image.\n"
                         "If you want to add a button, use the format:\n"
                         "Message text | Button text | Button URL")


@admin_router.message(StateFilter("broadcast"))
async def process_broadcast_message(message: types.Message, state: FSMContext, repo: RequestsRepo, bot: Bot):
    """
        Обработчик рассылки сообщений всем пользователям из базы данных, с возможностью отправки фото и inline-кнопки.
        """
    # Определяем текст сообщения (из caption, если есть фото)
    text_input = message.caption if message.photo else message.text
    photo = message.photo[-1].file_id if message.photo else None

    if not text_input and not photo:
        await message.answer("Please send text or an image for the broadcast.")
        return

    # Разбираем текст и inline-кнопку
    button = None
    if text_input and " | " in text_input:  # Проверяем, есть ли разделители
        parts = text_input.split(" | ")
        if len(parts) == 3:
            broadcast_text, button_text, button_url = parts
            button = types.InlineKeyboardMarkup(
                inline_keyboard=[[types.InlineKeyboardButton(text=button_text.strip(), url=button_url.strip())]]
            )
        else:
            broadcast_text = text_input  # Если формат неверный, используем весь текст без кнопки
    else:
        broadcast_text = text_input

    try:
        # Получаем всех пользователей из базы данных
        users = await repo.users.count_users()

        if not users:
            await message.answer("The database is empty. There is no one to send the message to.")
            await state.clear()
            return

        success_count = 0
        fail_count = 0

        for user_id, username in users:
            try:
                if photo:  # Если есть фото, отправляем его с подписью и (опционально) кнопкой
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=photo,
                        caption=broadcast_text,
                        reply_markup=button if button else None
                    )
                else:  # Если фото нет, отправляем только текст с (опционально) кнопкой
                    await bot.send_message(
                        chat_id=user_id,
                        text=broadcast_text,
                        reply_markup=button if button else None
                    )

                success_count += 1
            except Exception as e:
                logging.error(f"Failed to send a message to the user {user_id}: {e}")
                fail_count += 1

        await message.answer(
            f"Broadcast completed!\n"
            f"✅ Successful: {success_count}\n"
            f"❌ Failed: {fail_count}"
        )

    except Exception as e:
        logging.error(f"Error during broadcast: {e}")
        await message.answer("An error occurred during the broadcast. Please try again later.")

    await state.clear()


@admin_router.message(Command("clear"))
async def clear_users_command(message: types.Message, repo: RequestsRepo):
    await repo.users.clear_users()
    await message.answer("✅ All users have been deleted from the database.")


@admin_router.message(Command("base"))
async def show_database(message: types.Message, repo: RequestsRepo):
    """Выводит всех пользователей из базы данных"""
    users = await repo.users.get_all_users()

    if not users:
        await message.answer("📂 The database is empty.")
        return

    response = "📊 User Database:\n\n"
    for user in users:
        response += (
            f"👤 ID: {user.user_id}\n"
            f"📛 Name: {user.full_name}\n"
            f"🔗 Username: @{user.username if user.username else 'N/A'}\n"
            f"💰 Transactions: {'✅' if user.transactions else '❌'}\n"
            f"💵 Total Amount: {user.amount_tx / 1_000_000_000:.9f} SOL\n"
            f"🎁 Referral Bonus: {user.referral_bonus / 1_000_000_000:.9f} SOL\n"
            f"👥 Referred Users: {user.refer}\n"
            "------------------------\n"
        )

    await message.answer(response)
