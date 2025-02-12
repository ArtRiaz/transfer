from aiogram import Router, types, Bot, F
from aiogram.filters import CommandStart, Command, StateFilter, CommandObject
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from tgbot.keyboards.inline import start_keyboard_user, start_keyboard, social_keyboard
from aiogram.fsm.context import FSMContext
import asyncio
from email_validator import validate_email, EmailNotValidError
import random
from aiosmtplib import SMTP

from infrastructure.database.repo.requests import RequestsRepo

from aiogram.types import FSInputFile

user_router = Router()

photo = FSInputFile("game_chart.jpg")

caption_pre_sales = ("🚀 Exclusive Early Access – Join the Revolution! 🚀\n"
                     "We are excited to introduce [Coin Name], a groundbreaking cryptocurrency designed to redefine "
                     "the future "
                     "of decentralized finance. This is your opportunity to be part of an innovative ecosystem that "
                     "offers "
                     "security, scalability, and seamless transactions.\n\n "
                     "🔹 Why Invest in [Coin Name]\n"
                     "✅ Advanced Blockchain Technology – Fast, secure, and cost-effective transactions.\n"
                     "✅ Deflationary Mechanism – Limited supply with a smart burn system.\n"
                     "✅ Strong Utility & Real-World Use Cases – Designed for DeFi, gaming, NFTs, and more.\n"
                     "✅ Community-Driven & Transparent – Built for users, governed by the community.\n\n"
                     "🔥 Pre-Sale Details:\n"
                     "📌 Start Date: [Insert Date]\n"
                     "📌 Token Price: [Insert Price]\n"
                     "📌 Bonus for Early Investors: Up to [X]% extra tokens!\n\n"
                     "Join the movement and invest in the future with [Coin Name] today! 🌍💎")

caption = "Get your money, insert your wallet."


class Wallet(StatesGroup):
    email = State()
    code = State()


# Хранилище кодов подтверждения
verification_codes = {}


@user_router.message(CommandStart(deep_link=True))
@user_router.message(CommandStart())
async def start(message: Message, user, repo: RequestsRepo, command: CommandObject):
    referral_id = command.args
    print(type(referral_id))

    # Записываем пользователя в базу
    await repo.users.get_or_create_user(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name or "Unknown",
        language=message.from_user.language_code or "en",
        username=message.from_user.username or "Unknown",
        email=None,  # Email будет добавлен позже
        referral_id=referral_id,  # Если нет реферала, записываем None
    )

    # Если есть реферер (referral_id), увеличиваем его счетчик рефералов
    # if referral_id:
    #     await repo.users.increase_referral_count(referral_id)
    #
    #     # Получаем новое количество рефералов
    #     referral_count = await repo.users.count_referrals(referral_id)

    await message.answer_photo(photo=photo, caption=f"{caption_pre_sales} {referral_id}",
                               reply_markup=start_keyboard_user())


async def reset_state_timer(state: FSMContext, message: types.Message):
    """Устанавливает таймер для сброса состояния"""
    await asyncio.sleep(120)  # Подождать 2 минуту
    if not await state.get_state():  # Проверить, что состояние все еще активно
        return
    await state.clear()  # Сброс состояния
    await message.answer("Время ожидания истекло, регистрация отменена.\n"
                         " Нажми на команду /start")


# Функция отправки email
async def send_verification_email(email: str, code: str):
    message = f"""
    Subject: Email Verification Code\n
    Your verification code is: {code}
    """

    async with SMTP(hostname='smtp.gmail.com', port=587) as smtp:
        await smtp.login('asriazantsev22@gmail.com', 'oflc xsij tfnd uifd')
        await smtp.sendmail('asriazantsev22@gmail.com', email, message)


@user_router.callback_query(F.data == "register")
async def whitelist_registration(callback_query: types.CallbackQuery, state: FSMContext, repo: RequestsRepo):
    # Переводим пользователя в состояние ввода email
    await state.set_state(Wallet.email)
    await callback_query.message.answer("Enter your Email")
    await callback_query.answer()
    # Запуск таймера сброса состояния
    await reset_state_timer(state, callback_query.message)


@user_router.message(StateFilter(Wallet.email))
async def name(message: types.Message, state: FSMContext, repo: RequestsRepo):
    email = message.text.strip()

    # Проверяем корректность email
    try:
        validate_email(email, check_deliverability=True)
    except EmailNotValidError:
        await message.answer("❌ Invalid email format. Please enter a valid email (example: user@example.com).")
        return

        # **Проверяем, есть ли такой email в БД**
    email_exists = await repo.users.is_email_exists(email)
    if email_exists:
        await message.answer("❌ This email is already registered. Please enter a different email.")
        return

    # Генерация 6-значного кода
    verification_code = str(random.randint(100000, 999999))
    verification_codes[email] = verification_code

    # Отправка кода на email
    try:
        await send_verification_email(email, verification_code)
        await state.update_data(email=email)
        await state.set_state(Wallet.code)
        await message.answer("📩 A verification code has been sent to your email. Please enter it below:")
    except Exception as e:
        await message.answer(f"⚠️ Failed to send email. Please try again later.\nError: {e}")
        await state.clear()


# Обработка ввода кода
@user_router.message(StateFilter(Wallet.code))
async def process_verification_code(message: types.Message, state: FSMContext, repo: RequestsRepo):
    user_data = await state.get_data()
    email = user_data.get("email")
    user_id = message.from_user.id  # Получаем user_id Telegram пользователя
    user_code = message.text.strip()

    # Проверка кода
    if email in verification_codes and verification_codes[email] == user_code:
        del verification_codes[email]  # Удаляем код после успешного подтверждения

        # Проверяем, зарегистрирован ли пользователь в системе
        user_exists = await repo.users.is_user_exists(user_id)
        if not user_exists:
            await message.answer("❌ You are not registered in the system. Join the whitelist first.")
            await state.clear()
            return

        # Обновляем email в БД
        updated_user = await repo.users.update_user_email(user_id, email)
        if updated_user:
            await message.answer(
                f"✅ Email {email} verified and saved successfully! You will be notified when listing starts."
            )
        else:
            await message.answer("⚠️ Failed to update email. Try again later.")

        # Очищаем состояние FSM
        await state.clear()
    else:
        await message.answer("❌ Invalid code. Please try again.")


@user_router.callback_query(F.data == 'project')
async def project(callback: types.CallbackQuery):
    await callback.message.answer_photo(photo=photo, caption=f"{caption_pre_sales}")
    await callback.message.edit_reply_markup()
    await callback.answer()


@user_router.callback_query(F.data == 'social')
async def social(callback: types.CallbackQuery):
    await callback.message.answer_photo(photo=photo, caption="Our social and media", reply_markup=social_keyboard())
    # await callback.message.edit_reply_markup()
    await callback.answer()
