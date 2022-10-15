import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from telegram import Bot

from exceptions import EmptyResponseError, HTTPStatusError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 30
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    try:
        logging.info('Отправляем сообщение.')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError as error:
        logging.error(error)
        return False


def get_api_answer(current_timestamp):
    """Возвращает ответ API в случае успешного запроса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        logging.info('Отправляем запрос к API.')
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            raise HTTPStatusError('Пришел отличный от 200 статус.')
        return homework_statuses.json()

    except Exception as error:
        logging.error(f'API упал: {error}', exc_info=True)
        raise error


def check_response(response):
    """Начинаем проверку корректности ответа API."""
    logging.info('Начинаем проверку корректности ответа API.')
    if not isinstance(response, dict):
        raise TypeError(f'Ответ пришел не с типом данных dict: {response}')

    if 'homeworks' not in response or 'current_date' not in response:
        raise EmptyResponseError(f'Пришел пустой ответ: {response}')

    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise KeyError(f'Домашки не являются типом данных list: {response}')

    logging.info('Ответ API пришел в нужном формате')
    return homeworks


def parse_status(homework):
    """Получаем статус домашки."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError(f'Ключ "homework_name" отсутствует в {homework}')
    if homework_status not in HOMEWORK_STATUSES:
        raise ValueError(f'Статус {homework_status} отсутствует в вердикте')
    verdict = HOMEWORK_STATUSES[homework_status]
    logging.info('Получен статус домашки')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    if not check_tokens():
        no_tokens = (
            'Отсутствует одна из переменных окружения: '
            'PRACTICUM_TOKEN, '
            'TELEGRAM_TOKEN, '
            'TELEGRAM_CHAT_ID')

        logging.critical(no_tokens)
    logging.debug('Бот включен')
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(response['homeworks']) > 0:
                homework = response['homeworks'][0]
                send_message(bot, parse_status(homework))
                logging.info('Сообщение отправлено')
            time.sleep(RETRY_TIME)
            current_timestamp = response.get('current_date', current_timestamp)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
        handlers=[logging.FileHandler('main.log', 'w', 'utf-8'),
                  logging.StreamHandler(sys.stdout)]
    )
    main()
