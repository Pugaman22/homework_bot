import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv
from requests import RequestException

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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение отправлено.')
    except telegram.error.TelegramError:
        logger.error('Не удалось отправить сообщение.')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload)
        status = response.status_code
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(
                f'Ресурс {ENDPOINT} не доступен. Код ответа API: {status}'
            )
            raise AssertionError
    except RequestException:
        logger.error(f'Ошибка при запросе к ресурсу. {ENDPOINT}')


def check_response(response):
    """Проверка ответа API на корректность документации."""
    if not isinstance(response, dict):
        logger.error('Ответ API не является словарем.')
        raise TypeError('Данные не получены в формате словаря')
    try:
        homework = response.get('homeworks')[0]
        return homework
    except TypeError():
        logger.error('Ответ API не соответствует ожтдаемому.')
        raise TypeError('Данные не получены в формате словаря')


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы.
    В случае успеха, функция возвращает  строку для отправки в Telegram.
    """
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework:
        logger.error(f'отсутствует или пустое поле: {homework_name}')
        raise KeyError
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        logger.error(f'Неизвестный статус: {status}')
        raise KeyError
    verdict = HOMEWORK_VERDICTS.get(status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствует переменная окружения')
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
