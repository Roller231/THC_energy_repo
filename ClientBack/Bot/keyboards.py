from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def confirm_address_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data="address_confirm_yes"),
            InlineKeyboardButton(text="Нет", callback_data="address_confirm_no")
        ]
    ])