


import requests
from geopy.geocoders import Nominatim
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import psycopg2

from Bot.keyboards import confirm_address_keyboard

router = Router()

YANDEX_API_KEY = "4444140b-3c65-4196-99b2-8f4d51133969"

# строка подключения
DATABASE_URL = "postgresql://postgres:141722@localhost:5432/postgres"

# создаём соединение
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True

def save_complaint_to_db(tg_user_id, username, phone, user_address, complaint_text, complaint_address):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO complaints (tg_user_id, username, phone, user_address, complaint_text, complaint_address)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (tg_user_id, username, phone, user_address, complaint_text, complaint_address))


class ComplaintForm(StatesGroup):
    name = State()
    phone = State()
    user_address = State()
    complaint_text = State()
    complaint_locality = State()
    complaint_street = State()
    complaint_house = State()
    complaint_building = State()
    confirm_address = State()

def normalize_address(raw_address: str) -> str:
    replacements = {
        "д.": "дом",
        "д ": "дом ",
        "ул ": "улица ",
        "г ": "город ",
        "/": " корпус ",
    }
    for old, new in replacements.items():
        raw_address = raw_address.replace(old, new)

    if "россия" not in raw_address.lower():
        raw_address += ", Россия"

    return raw_address.strip()


def check_address_yandex(address: str) -> (bool, str | None):
    try:
        print(f"🟡 Проверка адреса через Yandex: {address}")
        url = "https://geocode-maps.yandex.ru/1.x"
        params = {
            "apikey": YANDEX_API_KEY,
            "geocode": address,
            "format": "json",
            "lang": "ru_RU",
            "results": 1,
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        geo_obj = response.json()["response"]["GeoObjectCollection"]["featureMember"]
        if not geo_obj:
            print("🔴 Адрес не найден (Яндекс)")
            return False, None

        full_address = geo_obj[0]["GeoObject"]["metaDataProperty"]["GeocoderMetaData"]["text"]
        print(f"🟢 Найдено (Yandex): {full_address}")

        if "краснодарский край" or "краснодар" or "город краснодар" or "г.краснодар" in full_address.lower():
            return True, full_address

        print("🔴 Адрес найден, но вне Краснодарского края")
        return False, None

    except Exception as e:
        print(f"❌ Ошибка геокодера Яндекс: {e}")
        return False, None


def check_address_nominatim(address: str) -> (bool, str | None):
    try:
        print(f"🟡 Проверка адреса через Nominatim: {address}")
        geolocator = Nominatim(user_agent="myapp")
        location = geolocator.geocode(address, timeout=10)
        if location is None:
            print("🔴 Адрес не найден (Nominatim)")
            return False, None

        full_address = location.address
        print(f"🟢 Найдено (Nominatim): {full_address}")

        if "краснодарский край" in full_address.lower():
            return True, full_address

        return False, None

    except Exception as e:
        print(f"❌ Ошибка геокодера Nominatim: {e}")
        return False, None


@router.message(Command(commands=["start"]))
async def start_complaint(message: Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Оставить анонимно")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Введите ваше имя или нажмите 'Оставить анонимно':", reply_markup=keyboard)
    await state.set_state(ComplaintForm.name)


@router.message(ComplaintForm.name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if name.lower() == "оставить анонимно":
        await state.update_data(name=None)
    else:
        await state.update_data(name=name)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить номер", request_contact=True)],
            [KeyboardButton(text="Оставить анонимно")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Отправьте ваш номер телефона или нажмите 'Оставить анонимно':", reply_markup=keyboard)
    await state.set_state(ComplaintForm.phone)


@router.message(ComplaintForm.phone)
async def process_phone(message: Message, state: FSMContext):
    if message.contact:
        await state.update_data(phone=message.contact.phone_number)
    elif message.text.lower().strip() == "оставить анонимно":
        await state.update_data(phone=None)
    else:
        await message.answer("Пожалуйста, отправьте номер как контакт или нажмите 'Оставить анонимно'.")
        return

    await message.answer("Введите ваш адрес проживания:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ComplaintForm.user_address)


@router.message(ComplaintForm.user_address)
async def process_user_address(message: Message, state: FSMContext):
    await state.update_data(user_address=message.text)
    await message.answer("Введите текст жалобы:")
    await state.set_state(ComplaintForm.complaint_text)


@router.message(ComplaintForm.complaint_text)
async def process_complaint_text(message: Message, state: FSMContext):
    await state.update_data(complaint_text=message.text)
    await message.answer("Укажите населённый пункт (город, село, станица):")
    await state.set_state(ComplaintForm.complaint_locality)


@router.message(ComplaintForm.complaint_locality)
async def process_complaint_locality(message: Message, state: FSMContext):
    await state.update_data(complaint_locality=message.text)
    await message.answer("Укажите улицу:")
    await state.set_state(ComplaintForm.complaint_street)


@router.message(ComplaintForm.complaint_street)
async def process_complaint_street(message: Message, state: FSMContext):
    await state.update_data(complaint_street=message.text)
    await message.answer("Укажите номер дома:")
    await state.set_state(ComplaintForm.complaint_house)


@router.message(ComplaintForm.complaint_house)
async def process_complaint_house(message: Message, state: FSMContext):
    await state.update_data(complaint_house=message.text)
    await message.answer("Укажите корпус (если есть), или напишите '-' если нет:")
    await state.set_state(ComplaintForm.complaint_building)


@router.message(ComplaintForm.complaint_building)
async def process_complaint_building(message: Message, state: FSMContext):
    data = await state.get_data()
    building = message.text.strip()
    await state.update_data(complaint_building=building)

    parts = [
        data["complaint_street"],
        f"дом {data['complaint_house']}",
        data["complaint_locality"]
    ]
    if building and building != "-":
        parts.append(f"корпус {building}")

    full_input = ", ".join(parts)
    formatted_address = normalize_address(full_input)

    is_valid, full_address = check_address_yandex(formatted_address)
    if not is_valid:
        is_valid, full_address = check_address_nominatim(formatted_address)

    if not is_valid:
        await message.answer(
            "❗ Адрес не найден или он не относится к Краснодарскому краю.\n"
            "Попробуйте ввести адрес снова с уточнением.\n"
            "Укажите населённый пункт, улицу и дом (и корпус, если есть)."
        )
        await state.set_state(ComplaintForm.complaint_locality)
        return

    await state.update_data(complaint_address=full_address)

    await message.answer(
        f"Вы указали адрес жалобы:\n<b>{full_address}</b>\n\nВсе верно?",
        reply_markup=confirm_address_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ComplaintForm.confirm_address)


@router.callback_query(F.data.startswith("address_confirm_"))
async def handle_address_confirmation(callback: CallbackQuery, state: FSMContext):
    if callback.data == "address_confirm_yes":
        data = await state.get_data()
        name = data.get("name") or "Аноним"
        phone = data.get("phone") or "Не указан"

        # Сохранение в БД
        save_complaint_to_db(
            tg_user_id=callback.from_user.id,
            username=name,
            phone=phone,
            user_address=data['user_address'],
            complaint_text=data['complaint_text'],
            complaint_address=data['complaint_address']
        )

        summary = (
            f"Жалоба от пользователя:\n"
            f"Имя: {name}\n"
            f"Телефон: {phone}\n"
            f"Tg ID: {callback.from_user.id}\n"
            f"Адрес пользователя: {data['user_address']}\n"
            f"Жалоба: {data['complaint_text']}\n"
            f"Адрес жалобы: {data['complaint_address']}"
        )

        await callback.message.edit_text("Спасибо, ваша жалоба отправлена.\n\n" + summary)
        await state.clear()

    elif callback.data == "address_confirm_no":
        await callback.message.edit_text("Введите адрес жалобы заново:")
        await state.set_state(ComplaintForm.complaint_locality)

    await callback.answer()


