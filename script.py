from datetime import datetime, timedelta
import aiohttp
import pandas as pd
from aiohttp import ClientConnectorError
from pytz import timezone


async def get_content_basket(session: aiohttp.ClientSession, product_id: int | str) -> dict | str:
    num_basket = 1
    try:
        while True:
            vol = str(product_id)[:3 if len(str(product_id)) >= 3 else len(str(product_id))]
            part = str(product_id)[:len(str(product_id)) - 3]
            url_basket_item = f'https://basket-{str(num_basket).zfill(2)}.wb.ru/vol{vol}/part{part}/{product_id}/info/ru/card.json'
            response = await session.get(url=url_basket_item)

            if response.status != 200:
                num_basket += 1
                continue
            break
    except ClientConnectorError:
        return str(product_id)

    content_basket = await response.json()
    return content_basket


async def parsing_response(json_data: dict, list_review: list, product_id: int, content_basket: dict,
                           selected_interval: str, rating: list) -> list:
    moscow_timezone = timezone('Europe/Moscow')
    moscow_time = datetime.now(moscow_timezone)
    time_minus = timedelta(days=0)
    match selected_interval:
        case 'За день':
            time_minus = timedelta(days=1)
        case 'За неделю':
            time_minus = timedelta(days=7)
        case 'За Месяц':
            time_minus = timedelta(days=30)
        case 'За 3 месяца':
            time_minus = timedelta(days=90)
        case 'За 1 час':
            time_minus = timedelta(hours=1)
        case 'За 2 часа':
            time_minus = timedelta(hours=2)
        case 'За 6 часов':
            time_minus = timedelta(hours=6)
        case 'За 12 часов':
            time_minus = timedelta(hours=12)
    new_date = moscow_time - time_minus
    list_negative_feedback = [
        {
            'user_id': x['globalUserId'],
            'name_user': x['wbUserDetails']['name'],
            'text_review': x['text'],
            'date': datetime.strptime(x["createdDate"], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=moscow_timezone),
            'rating': x['productValuation']
        }
        for x in json_data['feedbacks']
        if x['productValuation'] in rating and datetime.strptime(x["createdDate"],
                                                                                               '%Y-%m-%dT%H:%M:%SZ').replace(
            tzinfo=moscow_timezone) > new_date
    ]

    list_negative_feedback = sorted(list_negative_feedback, key=lambda x: x['date'])

    list_review.append({
        'id_product': str(product_id),
        'name_product': content_basket['imt_name'],
        'negative_review': list_negative_feedback
    })

    return list_review


async def get_negative_review(filename: str, selected_interval: str, id_product: str, rating: list) -> list | str:
    if id_product:
        numbers = [id_product]
    else:
        df = pd.read_excel(filename)
        numbers = df.values
    list_review = []

    async with aiohttp.ClientSession() as session:

        for count, id_pr in enumerate(numbers):
            id_pr = id_pr[0] if len(numbers) != 1 else id_pr
            content_basket = await get_content_basket(session=session, product_id=id_pr)
            if isinstance(content_basket, str):
                return content_basket

            num_review = 1
            try:
                while True:
                    url = f'https://feedbacks{num_review}.wb.ru/feedbacks/v1/{content_basket["imt_id"]}'
                    async with session.get(url) as resp:
                        json_data = await resp.json(encoding='utf-8')
                        if not json_data['feedbacks'] and not json_data['feedbackCount']:
                            num_review += 1
                            continue
                        list_review = await parsing_response(selected_interval=selected_interval,
                                                             json_data=json_data, list_review=list_review,
                                                             product_id=id_pr, rating=rating,
                                                             content_basket=content_basket)

                        break
            except ClientConnectorError:
                return str(id_product)

    return list_review


async def start_script(filename: str, selected_interval: str, id_product: str, rating: list) -> list | str:
    list_negative_response = await get_negative_review(filename=filename, selected_interval=selected_interval,
                                                       id_product=id_product, rating=rating)
    return list_negative_response
