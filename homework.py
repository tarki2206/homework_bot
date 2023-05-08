import logging
import os
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv
from telegram import Bot, TelegramError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

timestamp = int(time.time())
payload = {'from_date': timestamp}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('main.log', maxBytes=50000000, backupCount=5)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def check_tokens():
    """Function for checking tokens."""
    check_tokens_fun = {'practicum': PRACTICUM_TOKEN,
                        'telegram': TELEGRAM_TOKEN,
                        'chat_id': TELEGRAM_CHAT_ID}
    for name, token in check_tokens_fun.items():
        if not token:
            logger.critical(f'No, token {name}')
            exit()


def send_message(bot, message):
    """Function for sending message."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logger.debug('Message sent')


def get_api_answer(timestamp):
    """Function for getting api answer."""
    params = {'from_date': timestamp}
    try:
        homework_data = requests.get(
            url=ENDPOINT, headers=HEADERS,
            params=params)
        if homework_data.status_code != HTTPStatus.OK:
            raise Exception(f'Wrong response {homework_data.status_code}')
        return homework_data.json()
    except requests.exceptions.RequestException:
        raise Exception('Request Exception')


def check_response(response):
    """Function for checking response."""
    if not isinstance(response, dict):
        info_message = f'Was expected dict type, {type(response)}'
        logger.error(info_message)
        raise TypeError(info_message)
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        second_info_message = f'Was expected list type, {type(homeworks)}'
        logger.error(second_info_message)
        raise TypeError(second_info_message)


def parse_status(homework):
    """Function for parsing status."""
    keys = {'name': homework.get('homework_name'),
            'status': homework.get('status')}
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    for name, value in keys.items():
        if not value:
            info_message = f'No key {name}'
            logger.error(info_message)
            raise KeyError(info_message)
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError('Undefined status homework')
    if not homework_name:
        raise KeyError('Name field is empty')
    if homework_name and homework_status:
        logger.info('Keys was getting')
        result = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {result}'


def main():
    """Main function."""
    check_tokens()
    previous_status = []
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks_list = response['homeworks']
            homework, *_ = homeworks_list
            status_homework = parse_status(homework)
            if homeworks_list:
                if status_homework != previous_status:
                    bot = Bot(token=TELEGRAM_TOKEN)
                    send_message(bot, status_homework)
                    bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=status_homework)
                    logger.debug('Message was sent second time')
                    previous_status = homeworks_list
        except TelegramError as e:
            logger.error(f'Error {e}')
        except Exception as error:
            logging.error(f'Error during main loop: {error}')

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
