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
    check_tokens_fun = all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])
    if check_tokens_fun:
        logger.info('All tokens exist')
    if not check_tokens_fun:
        logger.critical('No, tokens')
        raise Exception('No, tokens')


def send_message(bot, message):
    """Function for sending message."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logger.debug('Message sent')


def get_api_answer(timestamp):
    """Function for getting api answer."""
    params = {'from_date': timestamp}
    try:
        homework = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
        status_code = homework.status_code
        if status_code != HTTPStatus.OK:
            raise Exception('Wrong response')
        return homework.json()
    except requests.exceptions.RequestException:
        raise Exception('Request Exception')


def check_response(response):
    """Function for checking response."""
    if not isinstance(response, dict):
        logger.error('Wrong type')
        raise TypeError('Wrong type')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        logger.error('Wrong type')
        raise TypeError('Wrong type')


def parse_status(homework):
    """Function for parsing status."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError('Undefined status homework')
    if homework_name is None:
        raise KeyError('Name field is empty')
    if homework_status is None:
        raise KeyError('Status field is empty')
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
            if response:
                homeworks_list = response['homeworks']

                if homeworks_list != previous_status:
                    bot = Bot(token=TELEGRAM_TOKEN)
                    homework, *other = homeworks_list
                    status_homework = parse_status(homework)
                    send_message(bot, status_homework)
                if homeworks_list is None:
                    logger.info('List is empty')
                try:
                    bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=status_homework)
                    logger.debug('Message was sent second time')
                except TelegramError as e:
                    logger.error(f'Error {e}')
                except Exception as e:
                    logger.error(f'Error {e}')
                previous_status = homeworks_list

        except Exception as error:
            logging.error(f'Error during main loop: {error}')

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
