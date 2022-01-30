
import requests
import time
import requests
import colorama
import webbrowser
import os
import json
from dateutil import parser
from db import db as dbase
import datetime
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler

# Красота в консоли
bg_re = colorama.Back.RESET
bg_y = colorama.Back.LIGHTYELLOW_EX
fg_b = colorama.Fore.BLACK
fg_r = colorama.Fore.LIGHTRED_EX
fg_re = colorama.Fore.RESET
fg_m = colorama.Fore.LIGHTMAGENTA_EX
fg_g = colorama.Fore.LIGHTGREEN_EX

user_agent = 'JobHunter v0.1'

config = {}
auth_code = ''
emails = []

def greeting():
    data = {
        (0, 1, 2, 3, 4, 5): "Доброй ночи",
        (6, 7, 8, 9, 10, 11): "Доброе утро",
        (12, 13, 14, 15, 16, 17): "Добрый день",
        (18, 19, 20, 21, 22, 23): "Добрый вечер"
    }
    h = datetime.datetime.today().hour
    for hrs in data:
        if h in hrs:
            return data[hrs]

def load_config():
    """
    Загрузка конфига
    """
    global config
    if os.path.exists('config.json'):
        with open('config.json','r') as cnfg:
            config = json.load(cnfg)
            if "access_token" not in config:
                first_run()
            if 'expires_in' in config:
                if config['expires_in'] < time.time():
                    refresh_token()

def log_str(text):
    now = time.strftime('%d.%m.%Y : %H:%M')
    print(
        f'{bg_y}{fg_b}{now}{bg_re}{fg_re} | {text}'
    )

def first_run():
    '''
    При первом запуске, даем права приложению на доступ к учетной записи и получаем токен.
    Проверял на винде, открывается браузер для получения авторизации
    '''
    # Отработка GET запроса и вылавливание authorization_code
    class http_handler(BaseHTTPRequestHandler):
        def do_GET(self):
            global auth_code
            self.send_response(200)
            auth_code = self.path[15:]
    auth_params = f'response_type=code&client_id={config["client_id"]}'
    url = 'https://hh.ru/oauth/authorize?' + auth_params
    # Открываем в браузере авторизацию
    webbrowser.open_new_tab(url)
    # Поднимаем локальный сервер
    http = HTTPServer(
        ('', 8080),
        RequestHandlerClass=http_handler)
    # Ловим authorization_code
    while auth_code == '':
        http.handle_request()
        time.sleep(.5)
    payload = {
        'grant_type': 'authorization_code',
        'client_id': config["client_id"],
        'client_secret': config["client_secret"],
        'code': auth_code
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    token_response = requests.post(
        'https://hh.ru/oauth/token',
        params=payload,
        headers=headers
    ).json()
    ts = int(time.time())
    token_response.pop('token_type')
    token_response['expires_in'] += ts
    update_config(token_response)

def refresh_token():
    """
    Получение нового токена
    """
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'user-agent': user_agent
    }
    payload = {
        'grant_type': 'refresh_token',
        'refresh_token':config['refresh_token']
    }
    res = requests.post(
        'https://hh.ru/oauth/token',
        headers=headers,
        params=payload
        ).json()
    update_config(res)

def update_config(json_data):
    config.update(json_data)
    json.dump(config, open('config.json', 'w'))

def get_json(url):
    try:
        while True:
            if 'access_token' not in config:
                result = requests.get(url).json()
            else:
                if config['expires_in'] < int(time.time()):
                    refresh_token()
                headers = {
                    'user-agent': user_agent,
                    'Authorization':f'Bearer {config["access_token"]}'
                }
                result = requests.get(url,headers=headers).json()

            if 'errors' not in result:
                return result
            else:
                print(result['errors'][0]['value'])
                if result['errors'][0]['value'] == 'captcha_required':
                    print(result['errors'][0]['captcha_url'])
                    print(requests.get(
                        result['errors'][0]['captcha_url']).text)
                time.sleep(10)

    except Exception as e:
        print('Get json error: ', e)
        return {}

def start_negotiate(vac_id, resume_id='16959caaff099e17fc0039ed1f364437586257',msg=''):
    """
    Даем отклик с сопроводительным письмом
    """
    if os.path.exists('message') and msg=='':
        with open('message','r',encoding='utf-8') as f:
            msg = f.read()
            msg.replace('%greeting%', greeting())
    headers = {
        'Content-Type': 'multipart/form-data',
        'user-agent': user_agent,
        'Authorization': f'Bearer {config["access_token"]}'
    }
    payload = {
        'vacancy_id': vac_id,
        'resume_id': resume_id,
        'message': msg
    }
    res = requests.post(
        'https://api.hh.ru/negotiations',
        headers=headers,
        params=payload
    )
    log_str(res.text)
    return res.status_code==201

def get_vacancy(vac_id):
    """
    Получение подробностей по вакансии
    """
    url = f'https://api.hh.ru/vacancies/{vac_id}'
    return get_json(url)

def check_keyword(keyword,vac):
    """
    Проверка наличия слова в теле факансии
    """
    kw = keyword.lower()
    if kw not in vac['name'].lower() and kw not in vac['advanced']['description'].lower():
        return False
    else:
        return True

def get_vacancies(text='', area=[]):
    vac_list = []
    if len(area) > 0:
        area_str = '&area='+'&area='.join([str(i) for i in area])
    else:
        area_str = ''
    url = f'https://api.hh.ru/vacancies?period=1&per_page=100{area_str}'
    if text != '':
        url += f'&text={text}'
    result = get_json(url)
    pages = result['pages']
    vac_list.extend(result['items'])

    # Получаем список вакансий
    for page in range(1, pages+1):
        print(f'Loading page {page}',end='\r')
        url += f'&page={page}'
        result = requests.get(url).json()
        vac_list.extend(result['items'])

    vac_list = list(filter(lambda x: 'python' in x['name'].lower(), vac_list))
    # Получаем дополнительные сведения по вакансиям
    for i in range(len(vac_list)):
        vac = vac_list[i]
        print(f'Loaded total:{fg_g}{i+1}/{len(vac_list)}{fg_re} current: {vac["id"]}', end='\r')
        if db.check_new_vacancy(vac['id']):
            vac_list[i]['advanced'] = get_vacancy(vac["id"])
            log_str(
                f'{vac_list[i]["id"]} : {fg_g}"{vac_list[i]["name"]}"{fg_re} ' +
                f'Работодатель: {fg_m}{vac_list[i]["employer"]["name"]}{fg_re}'
                )
            vac_list[i]['rank'] = 'Developer'
            rank = {
                'Junior' : check_keyword('junior', vac),
                'Middle' : check_keyword('middle', vac),
                'Senior' : check_keyword('senior', vac)
            }
            if any(rank.values()):
                vac_list[i]['rank'] = '/'.join([k for k,v in rank.items() if v])
            published = parser.parse(vac['published_at']).timestamp()
            # Вакансия свежая, отправляем отклик и пишем в базу
            positive = start_negotiate(vac['id'])
            if positive:
                db.add_vacancy(
                    (
                        vac['id'],
                        vac['employer']['id'],
                        int(published),
                        vac_list[i]['rank'] 
                    )
                )

def main():
    while True:
        get_vacancies(text='python', area=[2,145])
        emails.clear()
        time.sleep(30)

db = dbase()
load_config()
if all(
    (
    'access_token' in config,
    'refresh_token' in config, 
    'client_id' in config, 
    'client_secret' in config
    )
):
    # main()
    try:
        main()
    except Exception as e:
        print(e)