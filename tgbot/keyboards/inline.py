from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


# Keyboards


def social_keyboard():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Telegram chat", url='https://t.me')],
        [InlineKeyboardButton(text="Telegram channel", url='https://t.me')],
        [InlineKeyboardButton(text="X", url='https://x.com')],
        [InlineKeyboardButton(text="Website", url='https://example.com')],
        [InlineKeyboardButton(text="◀️ Back Main Menu", callback_data="back")]
    ])

    return ikb


def start_keyboard_after_date():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💲 Buy Token", callback_data="buy_token")],
        [InlineKeyboardButton(text="🚻 Invite a Friends", callback_data="referral")],
        [InlineKeyboardButton(text="🚀 About $ONI ", callback_data="project")],
        [InlineKeyboardButton(text="📲 Social", callback_data="social")]
    ]
    )
    return ikb


def buy_token_keyboard(has_wallet: bool = False) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру с разными кнопками в зависимости от наличия приватного ключа"""

    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔄 Change Wallet" if has_wallet else "💲 Connect your wallet",
                callback_data="connect_wallet"
            )
        ],
        [
            InlineKeyboardButton(text="↔️ Wrap $SOL to $ONI", callback_data="exchange")
        ],
        [InlineKeyboardButton(text="◀️ Back Main Menu", callback_data="back")]
    ])

    return ikb


def referral():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Statistic", callback_data="statistic")],
        [InlineKeyboardButton(text="Create link", callback_data="link")],
        [InlineKeyboardButton(text="◀️ Back Main Menu", callback_data="back")]
    ]
    )
    return ikb


def claim():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Claim Bonus", callback_data="claim_bonus")],
    [InlineKeyboardButton(text="◀️ Back Main Menu", callback_data="back")]]
    )
    return ikb


def back():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back Main Menu", callback_data="back")]]
    )
    return ikb
