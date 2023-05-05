from dotenv import load_dotenv
from http import HTTPStatus
import logging
from logging.handlers import RotatingFileHandler
import os
from telegram import Bot
import time
import requests
import json


load_dotenv()


PRACTICUM_TOKEN = os.getenv('token_practicum')
TELEGRAM_TOKEN = os.getenv('bot_token')
TELEGRAM_CHAT_ID = os.getenv('chat_id')

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
        return True
    if not check_tokens_fun:
        message_error = 'No, tokens'
        logger.critical(message_error)
        return False


def send_message(bot, message):
    """Function for sending message."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug('Message sent')

    except Exception as error:
        logger.error(f'Message sending error {error}')


def get_api_answer(timestamp):
    """Function for getting api answer."""
    params = {'from_date': timestamp}
    try:
        homework = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
        status_code = homework.status_code
        if status_code != HTTPStatus.OK:
            message_error = 'Wrong response'
            raise Exception(message_error)
        return homework.json()
    except requests.exceptions.RequestException:
        message_error = 'Request Exception'
        raise Exception(message_error)
    except json.JSONDecodeError:
        message_error = 'Problem with json'
        raise Exception(message_error)


def check_response(response):
    """Function for checking response."""
    if type(response) != dict:
        raise TypeError('Wrong type')
    homework_statuses = response.get('homeworks')
    if (type(homework_statuses) != list) or\
            (type(homework_statuses[0]) != dict):
        raise TypeError('Wrong type')
    else:
        return []


def parse_status(homework):
    """Function for parsing status."""
    try:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        result = HOMEWORK_VERDICTS[homework_status]
        if homework_status not in HOMEWORK_VERDICTS:
            raise KeyError(f'Invalid homework status: {homework_status}')
        if homework_name is None:
            raise Exception('Wrong response')
        return f'Изменился статус проверки работы "{homework_name}". {result}'

    except KeyError as error:
        logging.error(f'Error {error}')
        raise Exception(KeyError)


def main():
    """Main function."""
    if not check_tokens():
        exit()
    else:
        previous_status = []
        while True:
            try:
                response = get_api_answer(timestamp)
                check_response(response)
                if response:
                    current_status = response['homeworks']

                    if current_status == previous_status:
                        text = "Status didn't change"
                    elif current_status != previous_status:
                        bot = Bot(token=TELEGRAM_TOKEN)
                        homework = current_status[0]
                        text = parse_status(homework)
                        send_message(bot, text)
                        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)
                        logger.debug('Message was sent second time')
                        raise Exception('error')
                previous_status = current_status

            except Exception as error:
                logging.error(f'Error during main loop: {error}')

            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
