"""Telegram menus and replies.

/start shows the buttons.
A search button asks for a value. The next message is passed to find_car in cars.py.
The statistics buttons print counts that load_cars already prepared.

The last function, unknown_text, must stay last. It answers any other text
with "open /start", so it must not run before a real search.
"""

from datetime import timezone
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from cars import find_car

router = Router()

# A Telegram message is rejected above 4096 characters. Stay under that.
TELEGRAM_LIMIT = 4000

PROMPTS = {
    "plate": "Надішліть номерний знак. Пробіли й латиниця підходять: <code>AE9157CX</code>.",
    "body": "Надішліть номер кузова або VIN.",
    "chassis": "Надішліть номер шасі.",
    "engine": "Надішліть номер двигуна.",
    "brand": "Надішліть марку і модель, наприклад <code>KIA SORENTO</code>.",
}

WELCOME = (
    "<b>Перевірка транспорту в розшуку</b>\n"
    "Дані відкритого переліку МВС України.\n"
    "Оберіть, за чим шукати, або відкрийте статистику."
)

HELP = (
    "<b>Як користуватися</b>\n"
    "Натисніть кнопку і надішліть значення:\n"
    "• номерний знак\n"
    "• номер кузова\n"
    "• номер шасі\n"
    "• номер двигуна\n"
    "• марку і модель\n\n"
    "Пошук точний. Пробіли, дефіси, регістр і схожі латинські літери на номері не заважають.\n"
    "Команда /start відкриває меню."
)

NOT_FOUND = "У розшуку такого транспорту немає."
USE_MENU = "Оберіть тип пошуку в меню: /start"
EMPTY_QUERY = "Надішліть непорожнє значення."
STATS_INTRO = "Оберіть зведення по відкритому переліку."
UNKNOWN_FIELD = "Цей тип пошуку більше не підтримується. Відкрийте /start."


class SearchState(StatesGroup):
    # The bot is waiting for a plate, VIN, or other value.
    # The button id ("plate", "body", ...) is saved next to this state.
    waiting_query = State()


def main_menu():
    # Each inner list is one row. A button sends callback_data, not its label.
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Номерний знак", callback_data="search:plate")],
            [InlineKeyboardButton(text="Номер кузова", callback_data="search:body")],
            [InlineKeyboardButton(text="Номер шасі", callback_data="search:chassis")],
            [InlineKeyboardButton(text="Номер двигуна", callback_data="search:engine")],
            [InlineKeyboardButton(text="Марка і модель", callback_data="search:brand")],
            [InlineKeyboardButton(text="Статистика", callback_data="stats:menu")],
        ]
    )


def stats_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="За типом", callback_data="stats:types")],
            [InlineKeyboardButton(text="Топ марки", callback_data="stats:brands")],
            [InlineKeyboardButton(text="Останні викрадення", callback_data="stats:recent")],
            [InlineKeyboardButton(text="Назад", callback_data="menu:back")],
        ]
    )


def back_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="menu:back")],
        ]
    )


def records_word(count):
    # Ukrainian has three plural forms: 1 запис, 2 записи, 5 записів.
    # 11–14 use the same form as 5, so they are handled before the last digit.
    remainder_100 = abs(count) % 100
    remainder_10 = remainder_100 % 10
    if 11 <= remainder_100 <= 14:
        return "записів"
    if remainder_10 == 1:
        return "запис"
    if 2 <= remainder_10 <= 4:
        return "записи"
    return "записів"


def need_model(total):
    return (
        "За цією маркою в розшуку " + str(total) + " " + records_word(total) + ". "
        "Уточніть модель, наприклад <code>KIA SORENTO</code>."
    )


def found_header(total, shown):
    if total > shown:
        return "Знайдено " + str(total) + " " + records_word(total) + ". Показано перші " + str(shown) + "."
    if total == 1:
        return "Знайдено 1 запис у розшуку."
    return "Знайдено " + str(total) + " " + records_word(total) + "."


def format_date(value):
    # The file stores a UTC timestamp. The card shows that calendar day as ДД.ММ.РРРР.
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc)
    return value.strftime("%d.%m.%Y")


def format_car(car):
    # Skip empty fields. A trailer often has no engine number.
    # escape() keeps "<" or "&" in a police-unit name from breaking the message.
    lines = ["<b>У розшуку</b>"]
    rows = [
        ("Номерний знак", car.plate),
        ("Марка", car.brand),
        ("Модель", car.model),
        ("Тип", car.car_type),
        ("Колір", car.color),
        ("Кузов", car.body_number),
        ("Шасі", car.chassis_number),
        ("Двигун", car.engine_number),
        ("Дата викрадення", format_date(car.seizure_date)),
        ("Дата внесення", format_date(car.insert_date)),
        ("Підрозділ", car.organ_unit),
    ]
    for label, value in rows:
        if value:
            lines.append("<b>" + label + ":</b> " + escape(value))
    return "\n".join(lines)


def format_search(result):
    parts = [found_header(result.total, len(result.cars))]
    for car in result.cars:
        parts.append(format_car(car))
    return "\n\n".join(parts)


def format_type_counts(cars):
    lines = ["<b>За типом транспорту</b>"]
    if len(cars.by_type) == 0:
        lines.append("Немає даних про тип.")
        return "\n".join(lines)
    for name, count in cars.by_type:
        lines.append(escape(name) + " — " + str(count))
    lines.append("")
    lines.append("Разом: " + str(cars.total))
    return "\n".join(lines)


def format_top_brands(cars):
    lines = ["<b>Топ-10 марок</b>"]
    if len(cars.top_brands) == 0:
        lines.append("Марки не вказані.")
        return "\n".join(lines)
    number = 1
    for brand, count in cars.top_brands:
        lines.append(str(number) + ". " + escape(brand) + " — " + str(count))
        number = number + 1
    return "\n".join(lines)


def format_recent(cars):
    lines = ["<b>Останні викрадення</b>"]
    if len(cars.recent) == 0:
        lines.append("Немає дат викрадення.")
        return "\n".join(lines)
    for car in cars.recent:
        date = format_date(car.seizure_date)
        if date is None:
            date = "—"
        if car.plate:
            plate = car.plate
        else:
            plate = "без номера"
        brand_parts = []
        if car.brand:
            brand_parts.append(car.brand)
        if car.model:
            brand_parts.append(car.model)
        if len(brand_parts) == 0:
            brand_model = "марка не вказана"
        else:
            brand_model = " ".join(brand_parts)
        pieces = [date, plate, brand_model]
        if car.car_type:
            pieces.append(car.car_type)
        lines.append(escape(" — ".join(pieces)))
    return "\n".join(lines)


async def answer_callback(callback, text, markup=None):
    message = callback.message
    # A button press on a deleted message has no chat message to reply to.
    if isinstance(message, Message):
        await message.answer(text, reply_markup=markup)
    # Always answer the callback, or Telegram keeps the loading spinner on the button.
    await callback.answer()


@router.message(CommandStart())
async def start(message, state):
    # Drop an unfinished search. The next text should not be treated as a plate.
    await state.clear()
    await message.answer(WELCOME, reply_markup=main_menu())


@router.message(Command("help"))
async def help_command(message):
    await message.answer(HELP, reply_markup=main_menu())


@router.callback_query(F.data.startswith("search:"))
async def choose_field(callback, state):
    # "search:plate" -> "plate"
    field = callback.data.split(":", 1)[1]
    prompt = PROMPTS.get(field)
    if prompt is None:
        await answer_callback(callback, UNKNOWN_FIELD, main_menu())
        return
    await state.set_state(SearchState.waiting_query)
    await state.update_data(field=field)
    await answer_callback(callback, prompt, back_keyboard())


# A leading slash is a command (/start, /help), not a plate or a VIN.
@router.message(SearchState.waiting_query, F.text, ~F.text.startswith("/"))
async def on_query(message, state, cars):
    data = await state.get_data()
    field = data.get("field", "")
    query = message.text.strip()
    prompt = PROMPTS.get(field)
    if prompt is None:
        await state.clear()
        await message.answer(UNKNOWN_FIELD, reply_markup=main_menu())
        return
    if query == "":
        await message.answer(EMPTY_QUERY + "\n\n" + prompt, reply_markup=back_keyboard())
        return

    # Leave the state set, so the next message searches the same field again.
    # The "Назад" button clears it.
    result = find_car(cars, field, query)
    if result.ask_for_model:
        await message.answer(need_model(result.total), reply_markup=back_keyboard())
        return
    if result.total == 0:
        await message.answer(NOT_FOUND, reply_markup=back_keyboard())
        return
    await send_cards(message, result)


async def send_cards(message, result):
    # Five cards with long police-unit names can pass 4096 characters.
    text = format_search(result)
    if len(text) <= TELEGRAM_LIMIT:
        await message.answer(text, reply_markup=back_keyboard())
        return

    await message.answer(found_header(result.total, len(result.cars)))
    cards = []
    for car in result.cars:
        cards.append(format_car(car))
    last_index = len(cards) - 1
    index = 0
    for card in cards:
        if index == last_index:
            await message.answer(card, reply_markup=back_keyboard())
        else:
            await message.answer(card)
        index = index + 1


@router.callback_query(F.data.startswith("stats:"))
async def on_stats(callback, cars):
    # "stats:types" -> "types". The counts were made when the JSON was loaded.
    kind = callback.data.split(":", 1)[1]
    if kind == "menu":
        text = STATS_INTRO
    elif kind == "types":
        text = format_type_counts(cars)
    elif kind == "brands":
        text = format_top_brands(cars)
    elif kind == "recent":
        text = format_recent(cars)
    else:
        text = STATS_INTRO
    await answer_callback(callback, text, stats_menu())


@router.callback_query(F.data == "menu:back")
async def back_to_menu(callback, state):
    await state.clear()
    await answer_callback(callback, WELCOME, main_menu())


@router.message(F.text)
async def unknown_text(message):
    await message.answer(USE_MENU)
