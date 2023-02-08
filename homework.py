import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions

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


def check_tokens() -> bool:
    """Check if all tokens are present."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message) -> None:
    """Send message in telegram."""
    try:
        logging.info('Отправки статуса в telegram')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError as error:
        raise exceptions.TelegramError(f'Статус не отправлен: {error}')
    else:
        logging.info('Статус отправлен')


def get_api_answer(timestamp):
    """
    Adjust the API request and view the list of homework.
    Also check that the endpoint returns status 200.
    """
    nowtime = timestamp or int(time.time())
    params_request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': nowtime},
    }
    try:
        logging.info(
            'Начало запроса: url = {url},'
            'headers = {headers},'
            'params = {params}'.format(**params_request))
        homework_statuses = requests.get(**params_request)
        if homework_statuses.status_code != HTTPStatus.OK:
            raise exceptions.InvalidResponseCode(
                'Ответ API не возвращает 200, '
                f'ошибка: {homework_statuses.status_code}'
                f'причина: {homework_statuses.reason}'
                f'текст: {homework_statuses.text}')
        return homework_statuses.json()
    except Exception as error:
        message = ('API не возвращает 200. Запрос: {url}, {headers}, {params}.'
                   ).format(**params_request)
        raise exceptions.WrongResponseCode(message, error)


def check_response(response) -> list:
    """Сhecks the API response against the documentation."""
    logging.debug('Начало проверки')
    if not isinstance(response, dict):
        raise TypeError('Ошибка в типе ответа API')
    if 'homeworks' not in response or 'current_date' not in response:
        raise exceptions.EmptyResponseFromAPI('Пустой ответ от API')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise KeyError('Homeworks не является списком')
    return homeworks


def parse_status(homework) -> str:
    """
    Retrieves the status of a specific job from the database.
    and sends the result to Telegram.
    """
    if 'homework_name' not in homework:
        raise KeyError('В ответе отсутсвует ключ homework_name')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус работы - {homework_status}')
    return(
        'Изменился статус проверки работы "{homework_name}" {verdict}'
    ).format(
        homework_name=homework_name,
        verdict=HOMEWORK_VERDICTS[homework_status]
    )


def main():
    """The main logic of the bot."""
    if not check_tokens():
        logging.critical('Отсутствует необходимое кол-во'
                         ' токенов')
        sys.exit('Отсутсвуют токены')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    report = {
        'name': '',
        'output': ''
    }
    prev_report = report.copy()

    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get(
                'current_data', timestamp)
            new_homeworks = check_response(response)
            if new_homeworks:
                homework = new_homeworks[0]
                report['name'] = homework.get('homework_name')
                report['output'] = homework.get('status')
            else:
                report['output'] = 'Нет новых статусов работ.'
            if report != prev_report:
                send = f' {report["name"]}, {report["output"]}'
                send_message(bot, send)
                prev_report = report.copy()
            else:
                logging.debug('Статус не поменялся')
        except exceptions.NotForSending as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            report['output'] = message
            logging.error(message)
            if report != prev_report:
                send_message(bot, message)
                prev_report = report.copy
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename='main.log',
        format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
    )
    main()
