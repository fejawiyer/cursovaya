import json
from math import sqrt
import pathlib
import numpy as np
import time
import logging
from sympy.utilities.lambdify import lambdify
import sympy as sp
logger = logging.getLogger(__name__)


class Model:
    def __init__(self, config_dir: pathlib.Path,
                 sources: dict = None,
                 x_size=50.0, y_size=50.0,
                 t=30,
                 Dx=0.5, Dy=0.5,
                 dx=1, dy=1, dt=0.1,
                 slices_freq=1,
                 check_stable=True, check_cfl=True,
                 conditions="Dirihle",
                 debug=False,):
        self.x_size = x_size
        self.y_size = y_size
        self.t = t
        self.Dx = Dx
        self.Dy = Dy
        self.dx = dx
        self.dy = dy
        self.dt = dt
        self.check_cfl = check_cfl
        self.x = np.linspace(0, x_size, int(x_size/dx))
        self.y = np.linspace(0, y_size, int(y_size/dy))
        self.X, self.Y = np.meshgrid(self.x, self.y)

        self.is_u_float = False
        self.is_u_dict = False
        self.is_v_float = False
        self.is_v_dict = False
        self.sources = sources
        self.n_sources = len(sources)
        self.c = 0*self.X
        self.u, self.v = load_wind_arrays(int(x_size), int(y_size), json_file=config_dir / "wind.json")
        self.max_conc = np.max(self.c)
        self.slices_freq = slices_freq
        self.time_steps = int(self.t / self.dt)
        self.conditions = conditions
        self.check_stable = check_stable
        self.c_list = []
        self.u_key_iter = 1
        self.v_key_iter = 1
        self.log() if debug else None
        logger.info("Modelling start")
        if check_cfl:
            self.cfl = dt * np.max(self.u) / dx + dt * np.max(
                self.v) / dy + 2 * Dx * dt / dx ** 2 + 2 * Dy * dt / dy ** 2
            logger.info(f"CFL:{self.cfl}")
            if self.cfl > 1:
                for i in range(50):
                    logger.info("CFL > 1")
                    logger.info("Reduce dt...")
                    self.dt /= 2
                    logger.info(f"dt={self.dt}")
                    self.cfl = self.dt * np.max(self.u) / dx + self.dt * np.max(
                        self.v) / dy + 1 * Dx * self.dt / dx ** 2 + 1 * Dy * self.dt / dy ** 2
                    logger.info(f"CFL={self.cfl}")
                    if self.cfl <= 1:
                        logger.info("Success")
                        break

    def log(self):
        logger.info(f"Got params: x_size={self.x_size}, y_size={self.y_size}, t={self.t}, Dx={self.Dx}, Dy={self.Dy}")
        logger.info(f"dx={self.dx}, dy={self.dy}, dt={self.dt}")
        logger.info(f"is u wind float={self.is_u_float}")
        logger.info(f"is u wind dict={self.is_u_dict}")
        logger.info(f"is v wind float={self.is_v_float}")
        logger.info(f"is v wind dict={self.is_v_dict}")
        logger.info(f"sources_n={self.n_sources}")
        logger.info(f"slices freq={self.slices_freq}")
        logger.info(f"check stable={self.check_stable}")
        logger.info(f"check cfl={self.check_cfl}")
        logger.info(f"conditions={self.conditions}")
        logger.info(f"sources={self.sources}")

    def iterate(self):
        start_time = time.time()
        for t in range(self.time_steps):
            c_new = self.c.copy()
            c_new[1:-1, 1:-1] = self.Dx * (self.c[:-2, 1:-1] - 2 * self.c[1:-1, 1:-1] + self.c[2:, 1:-1]) / self.dx ** 2
            c_new[1:-1, 1:-1] += self.Dy * (
                    self.c[1:-1, :-2] - 2 * self.c[1:-1, 1:-1] + self.c[1:-1, 2:]) / self.dy ** 2

            # Обработка источников
            try:
                for source_key, source_value in self.sources.items():
                    # Разбираем координаты и параметры источника
                    x, y = map(float, source_key.split(','))
                    concentration, repeat_freq = map(float, source_value.split(','))
                    # Проверяем, нужно ли добавлять источник на этом шаге
                    if t % int(repeat_freq) == 0:
                        # Находим ближайшие индексы к координатам x, y
                        i = np.argmin(np.abs(self.x - x))
                        j = np.argmin(np.abs(self.y - y))

                        # Добавляем концентрацию в указанную точку
                        c_new[i, j] += concentration
            except Exception:
                print("while source except")


            mask_u_pos = self.u[1:-1, 1:-1] > 0
            mask_u_neg = ~mask_u_pos

            # Правосторонняя схема для u > 0
            c_new[1:-1, 1:-1][mask_u_pos] -= ((self.c[1:-1, 1:-1][mask_u_pos] - self.c[:-2, 1:-1][mask_u_pos]) *
                                              self.u[1:-1, 1:-1][mask_u_pos]) / self.dx
            c_new[1:-1, 1:-1][mask_u_neg] -= ((self.c[2:, 1:-1][mask_u_neg] - self.c[1:-1, 1:-1][mask_u_neg]) *
                                              self.u[1:-1, 1:-1][mask_u_neg]) / self.dx

            mask_v_pos = self.v[1:-1, 1:-1] > 0
            mask_v_neg = ~mask_v_pos

            # Правосторонняя схема для v > 0
            c_new[1:-1, 1:-1][mask_v_pos] -= ((self.c[1:-1, 1:-1][mask_v_pos] - self.c[1:-1, :-2][mask_v_pos]) *
                                              self.v[1:-1, 1:-1][mask_v_pos] / self.dy)

            # Левосторонняя схема для v <= 0
            c_new[1:-1, 1:-1][mask_v_neg] -= ((self.c[1:-1, 2:][mask_v_neg] - self.c[1:-1, 1:-1][mask_v_neg]) *
                                              self.v[1:-1, 1:-1][mask_v_neg] / self.dy)

            # Обновление значения с учетом временного шага
            c_new[1:-1, 1:-1] *= self.dt
            c_new[1:-1, 1:-1] += self.c[1:-1, 1:-1]

            if self.conditions == "Dirihle":
                c_new[0, :] = 0  # Левая граница
                c_new[-1, :] = 0  # Правая граница
                c_new[:, 0] = 0  # Нижняя граница
                c_new[:, -1] = 0  # Верхняя граница
            if self.conditions == "Neumann":
                c_new[0, :] = c_new[1, :]  # Левая граница (копируем из соседнего слоя)
                c_new[-1, :] = c_new[-2, :]  # Правая граница
                c_new[:, 0] = c_new[:, 1]  # Нижняя граница
                c_new[:, -1] = c_new[:, -2]  # Верхняя граница
            if self.conditions == "WTF":
                c_new[0, :] = c_new[-2, :]  # Левая граница = предпоследний слой
                c_new[-1, :] = c_new[1, :]  # Правая граница = второй слой
                c_new[:, 0] = c_new[:, -2]  # Нижняя граница = предпоследний слой
                c_new[:, -1] = c_new[:, 1]  # Верхняя граница = второй слой

            self.c = c_new
            if self.check_stable and np.any(self.c < 0):
                raise Exception("Решение расходится")
            if int(t % self.slices_freq) == 0:
                self.c_list.append(self.c.copy())

        end_time = time.time()
        logger.info(f"Time spend {end_time - start_time:.5f} seconds.")
        logger.info(f"Modelled {self.dt * self.time_steps} seconds")
        logger.info(f"Calculated {self.time_steps * len(self.x) * len(self.y)} elements")
        logger.info(f"Calculated {len(self.c_list)} layers")


def string_function_to_numpy(func_str, x_values):
    """
    Преобразует строковое представление функции в numpy-массив значений.

    Параметры:
    func_str (str): Строковое представление функции, например "cos(x)".
    x_values (np.ndarray): Массив значений x, для которых нужно вычислить функцию.

    Возвращает:
    np.ndarray: Массив значений функции для заданных x.
    """
    # Определяем символьную переменную
    x = sp.symbols('x')

    try:
        # Парсим строку в sympy-выражение
        expr = sp.sympify(func_str)

        # Преобразуем sympy-выражение в функцию, которую можно вычислить с numpy
        func = lambdify(x, expr, modules=['numpy'])

        # Вычисляем значения функции для массива x_values
        y_values = func(x_values)

        return y_values

    except (sp.SympifyError, TypeError) as e:
        raise ValueError(f"Ошибка при обработке функции '{func_str}': {str(e)}")


def load_wind_arrays(size_x, size_y, json_file):
    """
    Создает массивы u и v компонент ветра из wind.json.

    Параметры:
    size_x, size_y - размеры выходных массивов
    json_file - путь к JSON-файлу с данными о ветре

    Возвращает:
    u, v - двумерные numpy массивы компонент ветра
    """
    # Загружаем данные о ветре
    with open(json_file) as f:
        wind_data = json.load(f)

    # Создаем координатные сетки
    x = np.linspace(0, 100, size_x)
    y = np.linspace(0, 100, size_y)
    xx, yy = np.meshgrid(x, y, indexing='ij')

    # Инициализируем массивы u и v
    u = np.zeros((size_x, size_y))
    v = np.zeros((size_x, size_y))

    for wind in wind_data:
        # Координаты начала и конца ветрового вектора
        x0, y0 = wind['start_x'], wind['start_y']
        x1, y1 = wind['end_x'], wind['end_y']
        strength = wind['strength']

        # Вектор направления ветра
        dx = x1 - x0
        dy = y1 - y0
        length = sqrt(dx * dx + dy * dy)

        if length == 0:
            continue

        # Нормализованный вектор направления
        nx = dx / length
        ny = dy / length

        # Влияние на каждую точку сетки
        for i in range(size_x):
            for j in range(size_y):
                # Расстояние от точки до линии ветра
                # Используем проекцию для нахождения ближайшей точки на линии
                px = xx[i, j]
                py = yy[i, j]

                # Вектор от точки до начала линии
                vx = px - x0
                vy = py - y0

                # Проекция вектора v на линию ветра
                proj = (vx * nx + vy * ny) / length
                proj = max(0, min(1, proj))  # Ограничиваем проекцию отрезком

                # Ближайшая точка на линии ветра
                closest_x = x0 + proj * dx
                closest_y = y0 + proj * dy

                # Расстояние от точки до линии
                distance = sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)

                # Влияние ветра (убывает с расстоянием)
                influence = strength * np.exp(-distance / 10.0)

                # Добавляем компоненты ветра
                u[i, j] += nx * influence
                v[i, j] += ny * influence

    return u, v
