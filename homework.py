import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv  # , dotenv_values
from telegram import Bot, TelegramError

import exceptions
import settings

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


def send_message(bot, message):
    """Отправляет сообщение о статусе домашней работы."""
    try:
        logging.info("Отправка сообщения")
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        logging.error("Cбой при отправке сообщения!")
        raise TelegramError(f'Ошибка отправки телеграм сообщения: {error}')
    else:
        logging.info("Сообщение отправлено успешно")


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    request_params = {
        'url': ENDPOINT,
        'headers': {'Authorization': f'OAuth {PRACTICUM_TOKEN}'},
        'params': {'from_date': timestamp}
    }
    try:
        logging.info(
                    (
                        'Начинаем подключение к эндпоинту {url}, с параметрами'
                        ' headers = {headers} ;params= {params}.'
                    ).format(**request_params)
        )
        response = requests.get(**request_params)
        if response.status_code != HTTPStatus.OK:
            raise exceptions.EndpointInaccessibility(
                'Ответ сервера не является успешным:'
                f' request params = {request_params};'
                f' http_code = {response.status_code};'
                f' reason = {response.reason}; content = {response.text}'
            )
    except Exception as error:
        logging.error('Неизвестный сбой при запросе к эндпоинту!')
        raise ConnectionError(
            (
                'Во время подключения к эндпоинту {url} произошла'
                ' непредвиденная ошибка: {error}'
                ' headers = {headers}; params = {params};'
            ).format(error=error, **request_params)
        )
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    logging.info("Проверка ответа API на корректность")
    homeworks = response['homeworks']
    if not isinstance(response, dict):
        logging.error("Полученный ответ не является словарём!")
        raise exceptions.FailureCorrectnessResponse
    elif "homeworks" not in response or "current_date" not in response:
        logging.error("Отсутствуют ожидаемые ключи в ответе API!")
        raise exceptions.MissingCorrectKeys
    elif not isinstance(homeworks, list):
        logging.error('Ключ "homework" не является списком!')
        raise exceptions.HomeworkNotList
    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы из ответа API-сервиса."""
    if homework['status'] not in settings.HOMEWORK_STATUSES:
        logging.error("Недокументированный статус домашней работы,\
            обнаруженный в ответе API!")
        raise exceptions.UndocmentedStatusInAPIResponse
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")
    verdict = settings.HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения для работы программы."""
    # venv = dotenv_values(".env")
    # if all(venv):
    #     return True
    # return False
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    return False


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.INFO,
        format=(
            '%(asctime)s [%(levelname)s] - '
            '(%(filename)s).%(funcName)s:%(lineno)d - %(message)s'
        ),
        handlers=[
            logging.FileHandler('my_logger.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info("---------------------------------------------")
    logging.info("Начало проверки статуса ДЗ!")
    if not check_tokens():
        message = (
            'Отсутсвуют обязательные переменные окружения: PRACTICUM_TOKEN,'
            ' TELEGRAM_TOKEN, TELEGRAM_CHAT_ID.'
            ' Программа принудительно остановлена.'
        )
        logging.critical(message)
        sys.exit(message)
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    current_report: dict = {'name': '', 'output': ''}
    prev_report: dict = current_report.copy()
    try:
        response = get_api_answer(current_timestamp)
        current_timestamp = response.get('current_date', current_timestamp)
        new_homeworks = check_response(response)
        if new_homeworks:
            current_report['name'] = new_homeworks[0]['homework_name']
            current_report['output'] = parse_status(new_homeworks[0])
        else:
            current_report['output'] = (
                f'За период от {current_timestamp} до настоящего момента'
                ' домашних работ нет.'
            )
        if current_report != prev_report:
            send_message(bot, current_report)
            prev_report = current_report.copy()
        else:
            logging.debug('В ответе нет новых статусов.')
    except Exception as error:
        message = f'Сбой в работе программы: {error}'
        current_report['output'] = message
        logging.error(message, exc_info=True)
        if current_report != prev_report:
            send_message(bot, current_report)
            prev_report = current_report.copy()
    finally:
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
