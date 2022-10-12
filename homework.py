import os
import requests
import logging
from logging.handlers import RotatingFileHandler
import sys
from telegram import Bot
import time
import settings
import exceptions
from http import HTTPStatus
# from dotenv import dotenv_values
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
# TIMESTAMP = int(time.time())
TIMESTAMP = 0

formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(name)s, %(lineno)d'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter((formatter))
handler = RotatingFileHandler(
    'my_logger.log', maxBytes=50000000, backupCount=5, encoding='utf-8')
handler.setFormatter(formatter)
logger.addHandler(stream_handler)
logger.addHandler(handler)


def send_message(bot, message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logger.info("Сообщение отправлено успешно")
    except Exception:
        logger.error("Cбой при отправке сообщения!")
        raise exceptions.FalilureSendingMessage


def get_api_answer(current_timestamp):
    timestamp = current_timestamp  # or int(time.time())
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code != HTTPStatus.OK:
            logger.error(f'Недоступность эндпоинта!\
                 Код ошибки: {response.status_code}')
            raise exceptions.EndpointInaccessibility
        logger.info('Получение ответа от API Яндекс.Практикума')
    except Exception:
        logger.error('Неизвестный сбой при запросе к эндпоинту!')
        raise exceptions.FailureRequestingEnpoint
    return response.json()


def check_response(response):
    logger.info("Проверка ответа API на корректность")
    homeworks = response['homeworks']
    if not isinstance(response, dict):
        logger.error("Полученный ответ не является словарём!")
        raise exceptions.FailureCorrectnessResponse
    elif "homeworks" not in response or "current_date" not in response:
        logger.error("Отсутствуют ожидаемые ключи в ответе API!")
        raise exceptions.MissingCorrectKeys
    elif not isinstance(homeworks, list):
        logger.error('Ключ "homework" не является списком!')
        raise exceptions.HomeworkNotList
    return homeworks


def parse_status(homework):
    if homework['status'] not in settings.HOMEWORK_STATUSES:
        logger.error("Недокументированный статус домашней работы,\
            обнаруженный в ответе API!")
        raise exceptions.UndocmentedStatusInAPIResponse
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")
    verdict = settings.HOMEWORK_STATUSES[homework_status]
    if verdict != settings.OLD_STATUSES1.get(
            homework_name) is None:
        settings.OLD_STATUSES1[homework_name] = verdict
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    # venv = dotenv_values(".env")
    # if all(venv):
    #     return True
    # return False
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True


def main():
    """Основная логика работы бота."""
    logger.info("---------------------------------------------")
    logger.info("Начало проверки статуса ДЗ!")
    if not check_tokens():
        logger.critical("Отсутствие обязательных переменных\
            окружения во время запуска бота!")
        raise exceptions.MissingEnvironmentVariables
    bot = Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            response = get_api_answer(TIMESTAMP)
            # print(type(response))
            # print(response)
            homeworks = check_response(response)
            # print(type(homeworks[0]))
            # print(homeworks[0])
            if homeworks:
                message = parse_status(homeworks[0])
            elif len(homeworks) == 0:
                logger.debug("Список домашних работ пуст!")
                message = "Список домашних работ пуст!"
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
