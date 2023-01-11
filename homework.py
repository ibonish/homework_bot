import telegram
import time
import requests
import logging
import sys
import os
from http import HTTPStatus
from dotenv import load_dotenv
from exeptions import ApiResponseError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)


def check_tokens():
    """Проверка наличия токенов."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    return False


def send_message(bot, message):
    """Отправка сообщения пользователю."""
    try:
        logging.debug(f'Сообщение {message} успешно отправлено.')
        bot.send_message(TELEGRAM_CHAT_ID, message)

    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения {error}')


def get_api_answer(timestamp):
    """Получение ответа от API."""
    logging.info('Запрос к API')
    try:
        response = requests.get(
            url=ENDPOINT,
            params={'from_date': timestamp},
            headers=HEADERS
        )
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')

    if response.status_code != HTTPStatus.OK:
        raise ApiResponseError('Ответ API не возвращает 200')

    return response.json()


def check_response(response):
    """Проверка ответа API."""
    logging.info('Проверка ответа API на корректность')
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарем')
    if 'homeworks' not in response or 'current_date' not in response:
        raise Exception('Нет ключа homeworks в ответе API')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('homeworks не является словарем')
    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы."""
    logging.info('Проводим проверки и извлекаем статус работы')
    if 'homework_name' not in homework:
        raise KeyError('Нет ключа homework_name в ответе API')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус работы - {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсутствует токен. Бот остановлен!'
        logging.critical(message)
        sys.exit(message)

    logging.info('Бот начал работу')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    bot.send_message(TELEGRAM_CHAT_ID, 'Умею работать. Люблю работать.')
    timestamp = int(time.time())
    msg = ''

    while True:
        try:

            response = get_api_answer(timestamp)
            timestamp = response.get(
                'current_date', int(time.time())
            )
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                message = 'Нет изменений'
            if message != msg:
                send_message(bot, message)
                msg = message

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
