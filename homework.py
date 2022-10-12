import requests
import logging
from logging.handlers import RotatingFileHandler
import sys
from telegram import Bot
import time
import settings
import exceptions
from http import HTTPStatus
from dotenv import dotenv_values


def send_message(bot, message):
    try:
        bot.send_message(settings.TELEGRAM_CHAT_ID, text=message)
        logger.info("Сообщение отправлено успешно")
    except Exception:
        logger.error("Cбой при отправке сообщения!")
        raise exceptions.FalilureSendingMessage


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    try:
        response = requests.get(
            url=settings.ENDPOINT,
            headers=settings.HEADERS,
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
        print(response)
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
    if homework['status'] != settings.OLD_STATUSES.get(
            "homework_name") is None:
        settings.OLD_STATUSES["homework_name"] = homework_status
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return f'Статус проверки работы не изменился "{homework_name}". {verdict}'


def check_tokens():
    venv = dotenv_values(".env")
    if all(venv):
        return True
    return False


def main():
    """Основная логика работы бота."""
    logger.info("---------------------------------------------")
    logger.info("Начало проверки статуса ДЗ!")
    if not check_tokens():
        logger.critical("Отсутствие обязательных переменных\
            окружения во время запуска бота!")
        raise exceptions.MissingEnvironmentVariables
    bot = Bot(token=settings.TELEGRAM_TOKEN)
    while True:
        try:
            response = get_api_answer(settings.TIMESTAMP)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            elif len(homeworks) == 0:
                logger.debug("Список домашних работ пуст!")
                message = "Список домашних работ пуст!"
            send_message(bot, message)
            time.sleep(settings.RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(settings.RETRY_TIME)
        finally:
            time.sleep(settings.RETRY_TIME)


if __name__ == '__main__':
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
    main()
