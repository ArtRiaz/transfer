from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


# Keyboards

# New user
def start_keyboard_user():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Join to Whitelist ", callback_data="register")],
        [InlineKeyboardButton(text="🚀 About project ", callback_data="project")],
        [InlineKeyboardButton(text="📲 Social", callback_data="social")]
    ]
    )
    return ikb


def start_keyboard():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Add wallet", callback_data="wallet")]
    ]
    )
    return ikb


def social_keyboard():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Telegram chat", url='https://t.me')],
        [InlineKeyboardButton(text="Telegram channel", url='https://t.me')],
        [InlineKeyboardButton(text="X", url='https://x.com')]
    ])

    return ikb
