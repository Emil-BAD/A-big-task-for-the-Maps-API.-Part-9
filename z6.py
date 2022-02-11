import pygame
import requests
import sys
import os

import math

from distance import lonlat_distance
from geo import reverse_geocode
from bis import find_business

# это не готовое решение. Здесь лишь примеры реализации некоторой функциональности из задач урока.

# Подобранные константы для поведения карты.
LAT_STEP = 0.002  # Шаги при движении карты по широте и долготе
LON_STEP = 0.002
API_KEY = "40d1649f-0493-4b70-98ba-98533de7710b"
coord_to_geo_x = 0.0000428  # Пропорции пиксельных и географических координат.
coord_to_geo_y = 0.0000428
screen = None


def ll(x, y):
    return "{0},{1}".format(x, y)


# Структура для хранения результатов поиска:
# координаты объекта, его название и почтовый индекс, если есть.

class SearchResult(object):
    def __init__(self, point, address, postal_code=None):
        self.point = point
        self.address = address
        self.postal_code = postal_code


# Параметры отображения карты:
# координаты, масштаб, найденные объекты и т.д.

class MapParams(object):
    # Параметры по умолчанию.
    def __init__(self):
        try:
            self.lat = float(sys.argv[1])  # Координаты центра карты на старте.
            self.lon = float(sys.argv[2])
        except (IndexError, ValueError):
            print("Не верные координаты (аргументы)")
            exit()
        self.zoom = 15  # Масштаб карты на старте.
        self.type = "map"  # Тип карты на старте.

        self.search_result = None  # Найденный объект для отображения на карте.
        self.use_postal_code = False

    # Преобразование координат в параметр ll
    def ll(self):
        return ll(self.lon, self.lat)

    # Обновление параметров карты по нажатой клавише.
    def update(self, event):
        if event.key == pygame.K_PAGEUP and self.zoom < 19:  # PG_UP
            self.zoom += 1
        elif event.key == pygame.K_PAGEDOWN and self.zoom > 2:  # PG_DOWN
            self.zoom -= 1
        elif event.key == pygame.K_LEFT:  # LEFT_ARROW
            self.lon -= LON_STEP * math.pow(2, 15 - self.zoom)
        elif event.key == pygame.K_RIGHT:  # RIGHT_ARROW
            self.lon += LON_STEP * math.pow(2, 15 - self.zoom)
        elif event.key == pygame.K_UP and self.lat < 85:  # UP_ARROW
            self.lat += LAT_STEP * math.pow(2, 15 - self.zoom)
        elif event.key == pygame.K_DOWN and self.lat > -85:  # DOWN_ARROW
            self.lat -= LAT_STEP * math.pow(2, 15 - self.zoom)
        elif event.key == pygame.K_1:  # 1
            self.type = "map"
        elif event.key == pygame.K_2:  # 2
            self.type = "sat"
        elif event.key == pygame.K_3:  # 3
            self.type = "sat,skl"
        elif event.key == pygame.K_DELETE:  # DELETE
            self.search_result = None
        elif event.key == pygame.K_TAB:  # TAB
            try:
                self.lon, self.lat = get_coordinates(input_field())  # Enter
                self.add_reverse_toponym_search(True, (self.lon, self.lat))
            except (IndexError, RuntimeError):
                print('Не правильное название')

        if self.lon > 180: self.lon -= 360
        if self.lon < -180: self.lon += 360
        if self.lat > 70: self.lat = 70
        if self.lat < -70: self.lat = -70

    # Преобразование экранных координат в географические.
    def screen_to_geo(self, pos):
        dy = 225 - pos[1]
        dx = pos[0] - 300
        lx = self.lon + dx * coord_to_geo_x * math.pow(2, 15 - self.zoom)
        ly = self.lat + dy * coord_to_geo_y * math.cos(math.radians(self.lat)) * math.pow(2,
                                                                                          15 - self.zoom)
        return lx, ly

    # Добавить результат геопоиска на карту.
    def add_reverse_toponym_search(self, flag_that_there_are_readymade_coordinates, pos):
        if not flag_that_there_are_readymade_coordinates:
            point = self.screen_to_geo(pos)
            toponym = reverse_geocode(ll(point[0], point[1]))
        else:
            point = pos
            toponym = reverse_geocode(ll(pos[0], pos[1]))
        self.search_result = SearchResult(
            point,
            toponym["metaDataProperty"]["GeocoderMetaData"]["text"] if toponym else None,
            toponym["metaDataProperty"]["GeocoderMetaData"]["Address"].get(
                "postal_code") if toponym else None)


# Создание карты с соответствующими параметрами.
def load_map(mp):
    map_request = "http://static-maps.yandex.ru/1.x/?ll={ll}&z={z}&l={type}".format(ll=mp.ll(),
                                                                                    z=mp.zoom,
                                                                                    type=mp.type)
    if mp.search_result:
        map_request += "&pt={0},{1},pm2grm".format(mp.search_result.point[0],
                                                   mp.search_result.point[1])

    response = requests.get(map_request)
    if not response:
        print("Ошибка выполнения запроса:")
        print(map_request)
        print("Http статус:", response.status_code, "(", response.reason, ")")
        sys.exit(1)

    # Запишем полученное изображение в файл.
    map_file = "map.png"
    try:
        with open(map_file, "wb") as file:
            file.write(response.content)
    except IOError as ex:
        print("Ошибка записи временного файла:", ex)
        sys.exit(2)

    return map_file


# Создание холста с текстом.
def render_text(text):
    font = pygame.font.Font(None, 30)
    return font.render(text, 1, (100, 0, 100))


def geocode(address):
    geocoder_request = f"http://geocode-maps.yandex.ru/1.x/"
    geocoder_params = {
        "apikey": API_KEY,
        "geocode": address,
        "format": "json"}

    response = requests.get(geocoder_request, params=geocoder_params)

    if response:
        json_response = response.json()
    else:
        raise RuntimeError(
            f"""Ошибка выполнения запроса:
            {geocoder_request}
            Http статус: {response.status_code} ({response.reason})""")

    return json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"] if json_response else None


def get_coordinates(address):
    toponym = geocode(address)
    if not toponym:
        return None, None
    toponym_coordinates = toponym["Point"]["pos"]
    toponym_longitude, toponym_lattitude = toponym_coordinates.split(" ")
    return float(toponym_longitude), float(toponym_lattitude)


def input_field():
    global screen
    font = pygame.font.Font(None, 32)
    clock = pygame.time.Clock()
    input_box = pygame.Rect(100, 100, 140, 32)
    color_active = pygame.Color('Black')
    color = color_active
    text = ''
    run = True
    while run:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:  # Enter
                    run = False
                    return text
                elif event.key == pygame.K_BACKSPACE:  # BACKSPACE
                    text = text[:-1]
                elif event.key == pygame.K_ESCAPE:  # ESCAPE
                    run = False
                else:
                    text += event.unicode
        pygame.draw.rect(screen, pygame.Color('Grey'), input_box)
        txt_surface = font.render(text, True, color)
        width = max(200, txt_surface.get_width() + 10)
        input_box.w = width
        screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))
        pygame.draw.rect(screen, color, input_box, 2)
        pygame.display.flip()
        clock.tick(30)


def main():
    global screen
    # Инициализируем pygame
    pygame.init()
    screen = pygame.display.set_mode((600, 450))
    # Заводим объект, в котором будем хранить все параметры отрисовки карты.
    mp = MapParams()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:  # Выход из программы
                running = False
                break
            elif event.type == pygame.KEYUP:  # Обрабатываем различные нажатые клавиши.
                mp.update(event)
            elif event.type == pygame.MOUSEBUTTONUP:  # Выполняем поиск по клику мышки.
                if event.button == 1:  # LEFT_MOUSE_BUTTON
                    mp.add_reverse_toponym_search(False, event.pos)
            else:
                continue

        # Загружаем карту, используя текущие параметры.
        map_file = load_map(mp)

        # Рисуем картинку, загружаемую из только что созданного файла.
        screen.blit(pygame.image.load(map_file), (0, 0))
        # Переключаем экран и ждем закрытия окна.
        pygame.display.flip()

    pygame.quit()
    # Удаляем за собой файл с изображением.
    os.remove(map_file)


if __name__ == "__main__":
    main()
