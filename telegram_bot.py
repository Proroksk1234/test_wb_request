import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

from script import start_script

logging.basicConfig(level=logging.INFO)

# telegram bot: @Proroksk1234_test_wb_bot
bot = Bot(token='6242941792:AAGNm99POEDicWbI_kxtakhmgK4Qadgoor8')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

buttons_rating = [
    "Рейтинг:1",
    "Рейтинг:2",
    "Рейтинг:3",
    "Рейтинг:4",
    "Рейтинг:1-2",
    "Рейтинг:1-3",
    "Рейтинг:1-4",
    "Рейтинг:2-3",
    "Рейтинг:2-4",
    "Рейтинг:3-4",
]

buttons_day = [
    "За 1 час",
    "За 2 часа",
    "За 6 часов",
    "За 12 часов",
    "За день",
    "За неделю",
    "За месяц",
    "За 3 месяца",
    "Назад",
]

buttons_start = [
    "Введите ID товара",
    "Обновить существующие"
]

dict_rating = {
    "Рейтинг:1": [1],
    "Рейтинг:2": [2],
    "Рейтинг:3": [3],
    "Рейтинг:4": [4],
    "Рейтинг:1-2": [1, 2],
    "Рейтинг:1-3": [1, 2, 3],
    "Рейтинг:1-4": [1, 2, 3, 4],
    "Рейтинг:2-3": [2, 3],
    "Рейтинг:2-4": [2, 3, 4],
    "Рейтинг:3-4": [3, 4]
}


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await update_buttons_start(message=message)


@dp.message_handler(lambda message: message.text in buttons_start)
async def handle_option_selection(message: types.Message):
    selected_option = message.text

    if selected_option == "Введите ID товара":
        await bot.send_message(chat_id=message.chat.id, text=f"Введите ID продукта")
    elif selected_option == "Обновить существующие":
        await update_buttons_rating(message)


@dp.message_handler(
    lambda message: message.text not in buttons_start and message.text not in buttons_rating and message.text not in buttons_day)
async def input_text(message: types.Message) -> None:
    while True:
        if not message.text.isdigit():
            await bot.send_message(chat_id=message.chat.id, text="Введен неверный id")
            break
        with open('settings/id_save.txt', 'w') as file:
            file.write(message.text)
        await update_buttons_rating(message)
        break


@dp.message_handler(lambda message: message.text in ["Назад"])
async def update_buttons_start(message: types.Message):
    new_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = buttons_start
    new_keyboard.add(*buttons)

    await bot.send_message(message.chat.id, "Выберите опцию:", reply_markup=new_keyboard)


async def update_buttons_rating(message: types.Message):
    new_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = buttons_rating
    new_keyboard.add(*buttons)

    await bot.send_message(message.chat.id, "Выберите интересующий вас рейтинг:", reply_markup=new_keyboard)


async def update_buttons_days(message: types.Message):
    new_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = buttons_day
    new_keyboard.add(*buttons)

    await bot.send_message(message.chat.id, "Выберите промежуток:", reply_markup=new_keyboard)


async def send_json(list_negative_response: list, message: types.Message) -> None:
    num_message = 0
    for count, i in enumerate(list_negative_response):
        for ind, x in enumerate(i['negative_review']):
            response = (f"id product: {i['id_product']}\n"
                        f"name_product: {i['name_product']}\n"
                        f"user_id: {x['user_id']}\n"
                        f"username: {x['name_user'] if x['name_user'] else 'Отсутствует информация'}\n"
                        f"rating: {x['rating']}\n"
                        f"text_review: {x['text_review']}\n"
                        f"date: {str(x['date'])[:-6]}")
            await bot.send_message(chat_id=message.chat.id, text=response)
            await asyncio.sleep(3)
            num_message = 1
    if num_message:
        await bot.send_message(chat_id=message.chat.id, text="Обновление завершено")
    else:
        await bot.send_message(chat_id=message.chat.id, text="По вашему запросу ничего не найдено")


@dp.message_handler(lambda message: message.text in buttons_rating)
async def handle_button_rating(message: types.Message):
    with open('settings/save_rating.txt', 'w', encoding='utf-8') as file:
        file.write(message.text)
    await update_buttons_days(message=message)


@dp.message_handler(lambda message: message.text in buttons_day)
async def handle_button_click(message: types.Message):
    selected_interval = message.text
    with open('settings/id_save.txt', 'r', encoding='utf-8') as file:
        id_product = file.read()
    with open('settings/save_rating.txt', 'r', encoding='utf-8') as file_1:
        rating = file_1.read()
    rating_list = dict_rating[rating]
    text_id = f" для продукта c id:{id_product}" if id_product else ''
    await bot.send_message(chat_id=message.chat.id, text=f"Начинаем производить выборку {selected_interval.lower()}"
                                                         f"{text_id} c {rating.lower()}.\nПожалуйста, подождите")

    list_negative_response = await start_script(filename='data/Книга111.xlsx', selected_interval=selected_interval,
                                                id_product=id_product, rating=rating_list)
    if isinstance(list_negative_response, str):
        if id_product:
            await bot.send_message(chat_id=message.chat.id, text=f"Введенного id {id_product} не существует")
        else:
            await bot.send_message(chat_id=message.chat.id,
                                   text=f"В веденных данных в документе присутствует несуществующий id: {list_negative_response}")
    else:
        await send_json(list_negative_response=list_negative_response, message=message)
    with open('settings/id_save.txt', 'w') as file:
        file.write('')
    await update_buttons_start(message=message)


if __name__ == '__main__':
    asyncio.run(executor.start_polling(dp, skip_updates=True))

