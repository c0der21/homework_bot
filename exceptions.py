class MissingEnvironmentVariables:
    def __str__(self):
        return "Отсутствие обязательных переменных\
             окружения во время запуска бота!"


class EndpointInaccessibility(Exception):
    def __str__(self):
        return "Недоступность эндпоинта!"


class FailureRequestingEnpoint(Exception):
    def __str__(self):
        return "Неизвестный сбой при запросе к эндпоинту!"


class FailureCorrectnessResponse(Exception):
    def __str__(self):
        return "Неккоректность полученных данных!"


class MissingCorrectKeys(Exception):
    def __str__(self):
        return "Отсутствуют ожидаемые ключи в ответе API!"


class HomeworkNotList(Exception):
    def __str__(self):
        return 'Ключ "homework" не является списком!'


class UndocmentedStatusInAPIResponse(KeyError):
    def __str__(self):
        return 'Недокументированный статус домашней работы,\
             обнаруженный в ответе API!'


class FalilureSendingMessage(Exception):
    def __str__(self):
        return 'Cбой при отправке сообщения!'
