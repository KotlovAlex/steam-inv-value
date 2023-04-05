# Импорт необходимых стандартных модулей python.
import json
import codecs
import requests
import time
import datetime

# Импорт констант:
# ----------------------------------------
# profilePath - ссылка на инвентарь по cs:go профиля формата:
# https://steamcommunity.com/inventory/USERID/730/2?l=russian&count=5000
# ex. https://steamcommunity.com/inventory/76561198840043600/730/2?l=russian&count=5000
# ----------------------------------------
# itemPath - ссылка на файл с данными об инвентаре пользователе.
# Файл создается автоматически в ходе выполнения соответстующей функции программы.
# ----------------------------------------
# pricesPath - ссылка на файл с ценами уникальных предметов инвентаря, доступных к продаже.
# Файл создается автоматически в ходе выполнения соответстующей функции программы.
from const import profilePath, itemsPath, pricesPath, logPath

# Вспомогательная функция, генерирующая строку запроса.
# Принимает market_hash_name предмета (атрибут из json файла с данными об предметах в инвентаре).
# Возвращает строку, готовую для отправки http запроса.
def item_url (market_hash_name):
  return f'https://steamcommunity.com/market/priceoverview/?appid=730&market_hash_name={market_hash_name}&currency=5'

# Получение всех предметов аккаунта по ссылке,
# и запись их в файл, в формате json
# Принимает ссылку на инвентарь формата:
# https://steamcommunity.com/inventory/USERID/730/2?l=russian&count=5000
# Ничего не возвращает.
# Выводит в консоль статус запроса.
# При статусе 200 (request get response) создает файл inventory.json,
# в котором отражена вся информация по инвентарю пользователя по cs:go,
# В ином случае выводит в консоль ошибку.
def get_inventory(path):
  response = requests.get(path)
  if response.status_code == 429:
    print('Слишком много запросов')
  elif response.status_code == 200:
    print(response.status_code)
    with open(itemsPath, 'w') as file:
      print(json.dumps(response.json()), file=file)
  else:
    print(f'Ошибка {response.status_code}')
    

# Получение цен всех уникальных предметов,
# которые имеют возможность быть продаными(обменеными)
# Принимает путь в файлу с информацией об предметах инвентаря пользователя.
# Ничего не возвращает.
# Отправляет запросы для получения цен каждого уникального 
# предмета в инвентаре, не являющимя ширпотребом и граффити,
# и доступным к продаже.
# Выводит в консоль название предмета на который отравляет запрос. 
# Задержка между запросами 5 секунд (иначе стим запрещает отправлять запросы), 
# соответственно чем больше предметов, тем долже выполнение функции. 
# В случае возникновения ошибки, сохраняет те цены, 
# которые уже удалось запросить, и завершает работу. 
# В случае работы без ошибок, в результате будет составлен 
# файл с ценами предметов prices.json, формата "название": "цена в рублях".
def get_prices(path):
  try:
    fileObj = codecs.open( path, "r", "utf_8_sig" )
    text = fileObj.read()
    inventory = json.loads(text)
    fileObj.close()

    prices = {}
    iterator = 0

    for item in inventory["descriptions"]:
      consumer = False
      for tag in item["tags"]:
          # Проверка на ширпотреб (что бы не учитывать ширпотреб, и не отправлять лишние запросы)
          if tag["category"] == "Rarity" and tag["localized_tag_name"] == "Ширпотреб":
              consumer = True
              break
          # Проверка на граффити (аналагично ширпортребу)
          if tag["category"] == "Type" and tag["localized_tag_name"] == "Граффити":
              consumer = True
              break
      if consumer:
          continue
      if item['marketable'] == 1:
        print(item['market_hash_name'], iterator)
        response = requests.get(item_url(item['market_hash_name']))
        if response.status_code == 200:
          prices[item['market_name']] =  response.json()['lowest_price']
          iterator += 1
          time.sleep(5)
        elif response.status_code == 429:
          print('Слишком много запросов')
          print(prices)
          with open(pricesPath, "w", encoding='utf-8') as outfile:
            json.dump(prices, outfile)
          return
        elif response.status_code == 502:
          print(f"{item['market_hash_name']}: Bad Gateway")
          iterator += 1
          time.sleep(5)
        else:
          print(f"{item['market_hash_name']}: status_code {response.status_code}")
          iterator += 1
          time.sleep(5)
    print(prices)
    with open(pricesPath, "w", encoding='utf-8') as outfile:
      json.dump(prices, outfile)
    return
  except KeyError:
    with open(pricesPath, "w", encoding='utf-8') as outfile:
      json.dump(prices, outfile)

# Получение суммы стоимостей всех предметов в инветнаре,
# на основе инвентаря, и цен уникальных предметов
# Принимает данные предметов инвентаря, и данные цен уникальных предметов.
# В ходе работы выводит в консоль информацию в формате:
# стоимость текущего предмета, текущая сумма
# Возвращает сумму стоимостей всех предметов в инветнаре.
def get_amount_inventory(inventory, prices):
  summ = 0
  items = []
  names = {}

  fileObj = codecs.open(inventory, "r", "utf_8_sig" )
  text = fileObj.read()
  inventory = json.loads(text)
  fileObj.close()

  fileObj = codecs.open(prices, "r", "utf_8_sig" )
  text = fileObj.read()
  prices = json.loads(text)
  fileObj.close()

  for i in inventory['descriptions']:
    names[i['classid']] = i['market_name']

  for i in inventory['assets']:
    items.append(names[i['classid']])

  for i in items:
    if i in prices:
      summ += float(prices[i][:-5:].replace(',','.'))
      print(f'+{float(prices[i][:-5:].replace(",","."))}, current: {summ}')
  print(summ)
  return summ

# Функция для сохранения логов
# Принимает на вход путь до файла лога, и текущей суммы инвентаря
# На выходе дополняет логирующий файл сегодняшней датой и текущей суммой
def save_log(logPath, amount):
  fileObj = codecs.open(logPath, "r", "utf_8_sig" )
  text = fileObj.read()
  logs = json.loads(text)
  fileObj.close()

  # Получаем текущую дату формата ДД.ММ.ГГГГ
  now = datetime.datetime.now()
  day = now.day if now.day > 9 else f'0{now.day}'
  month = now.month if now.month > 9 else f'0{now.month}'
  today = f'{day}.{month}.{now.year}'

  logs[today] = f'{int(amount)}p'

  str_log = str(logs)

  str_log = str_log.replace("'", '"')
  str_log = str_log.replace(",", ',\n')
  str_log = str_log.replace("{", '{\n ')
  str_log = str_log.replace('"}', '"\n}')

  with open(logPath, 'w', encoding='utf-8') as log:
    print(str_log, file=log)

  



get_inventory(profilePath) # получение данных о предметах в инвентаре
# get_prices(itemsPath) # получение цен уникальных предметов инвентаря (кроме ширпотреба и граффити)
save_log(logPath,get_amount_inventory(itemsPath, pricesPath)) # подсчет стоимости инвентаря, на основе полученых ранее цен, 
                                                              # и запись ее в логи