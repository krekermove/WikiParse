import smtplib
import ssl
from email.header import Header
from email.mime.text import MIMEText
from time import sleep

import requests
from bs4 import BeautifulSoup
from requests import Response

# ----------------- Конфигурация проекта -----------------------
WIKI_URL = "https://en.wikipedia.org/wiki/Deaths_in_August_2025"
USER_AGENT = 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36'
SLEEP_INTERVAL = 300

SENDER_EMAIL = 'ПОЧТА_ОТПРАВИТЕЛЯ'
SENDER_PASSWORD = 'ПАРОЛЬ_ОТ_ПОЧТЫ_ОТПРАВИТЕЛЯ'
RECEIVER_EMAIL = 'ПОЧТА_ПОЛУЧАТЕЛЯ'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
# --------------------------------------------------------------


def get_info_from_wiki(url: str) -> Response | None:
    headers = {
        'User-Agent': USER_AGENT,
    }
    try:
        response = requests.get(url=url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        return response
    except requests.exceptions.RequestException as e:
        print(f'Произошла ошибка при отправке запроса: {e}.')
        return None


def parse_data_from_page(response: Response) -> dict:
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        section = soup.find('section', class_='mf-section-1')
        if not section:
            print("Не удалось найти список умерших людей на странице.")
            return {}
        data = {}
        for el in section.find_all('li'):
            link_el = el.find('a', href=True)
            link_attrs = link_el.attrs
            data[link_attrs['href']] = link_attrs['title'] # Ключем решил сделать ссылку, поскольку имена могут совпасть
        return data
    except Exception as e:
        print(f'При попытке обработать страницу произошла следующая ошибка: {e}.')
        return {}


def get_info_about_person(person, lang='en') -> dict:
    API_URL = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "prop": "langlinks|extracts|info",
        "exintro": True,
        "explaintext": True,
        "redirects": 1,
        "titles": person,
        "inprop": "url",
        "lllang": "ru",
        "llprop": "url",
    }
    headers = {'User-Agent': USER_AGENT}
    try:
        response = requests.get(url=API_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        pages = data['query']['pages']
        page_id = next(iter(pages))

        if page_id == "-1":
            print(f"Страница для '{person}' не найдена.")
            return {}

        return pages[page_id]
    except requests.exceptions.RequestException as e:
        print(f'Произошла ошибка при отправке запроса: {e}.')
        return {}


def collect_info_about_person(person: str, page: dict):
    ru_link = page['langlinks'][0]['url']
    person_data = {
        'name': person,
        'bio': page['extract'],
        'origin_link': page['fullurl'],
    }
    if ru_link:
        pers = page['langlinks'][0]['*']
        ru_page = get_info_about_person(pers, 'ru')
        person_data['ru_link'] = ru_link
        person_data['ru_name'] = pers
        if ru_page:
            person_data['bio'] = ru_page['extract']
    return person_data


def send_email(subject: str, body: str):
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['From'] = Header('Тестовое задание', 'utf-8')
    msg['To'] = Header(RECEIVER_EMAIL, 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print(f"Email успешно отправлен получателю {RECEIVER_EMAIL}.")
    except Exception as e:
        print(f"Ошибка при отправке email: {e}.")

def main_loop():
    person_list = parse_data_from_page(get_info_from_wiki(WIKI_URL))
    while (True):
        print("Поиск новых записей...")
        res = get_info_from_wiki(WIKI_URL)
        if not res:
            sleep(SLEEP_INTERVAL)
            continue
        parsed_data = parse_data_from_page(res)
        for key, value in parsed_data.items():
            if key not in person_list:
                person_list[key] = value
                page = get_info_about_person(value)
                data = collect_info_about_person(value, page)
                body = f"В списке умерших появилась новая запись:\n\n"
                if data['ru_name']:
                    title = f"Новая запись в списке умерших: {data['ru_name']}"
                    body += f"Имя: {data['ru_name']}\n" \
                            f"Ссылка: {data['ru_link']}\n\n" \
                            f"Краткая биография: {data['bio']}"
                else:
                    title = f"Новая запись в списке умерших: {data['name']}"
                    body += f"Имя: {data['name']}\n" \
                            f"Ссылка: {data['origin_link']}\n\n" \
                            f"Краткая биография: {data['bio']}"
                send_email(title, body)
                return 0
        sleep(SLEEP_INTERVAL)


if __name__ == '__main__':
    main_loop()
