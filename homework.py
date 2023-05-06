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
    check_tokens_fun = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for i in check_tokens_fun:
        if not i:
            logger.critical(f'No, token {i}')
            raise Exception(f'No, token {i}')
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
        logger.error(f'Was expected dict type, {type(response)}')
        raise TypeError(f'Was expected dict type, {type(response)}')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        logger.error(f'Was expected list type, {type(homeworks)}')
        raise TypeError(f'Was expected list type, {type(homeworks)}')


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
    if homework_name and homework_status:
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
            if isinstance(response, dict):
                homeworks_list = response['homeworks']
                homework, *_ = homeworks_list
                if homeworks_list[-1] != previous_status:
                    bot = Bot(token=TELEGRAM_TOKEN)
                    status_homework = parse_status(homework)
                    send_message(bot, status_homework)
                if not homeworks_list:
                    logger.info('List is empty')
                if homeworks_list:
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
