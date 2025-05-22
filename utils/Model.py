import numpy as np
import time
import logging
from sympy.utilities.lambdify import lambdify
import sympy as sp
logger = logging.getLogger(__name__)


class Model:
    def __init__(self, c_start,
                 x_size=50.0, y_size=50.0,
                 t=30,
                 Dx=0.5, Dy=0.5,
                 dx=1, dy=1, dt=0.1,
                 u=0, v=0,
                 slices_freq=1,
                 repeat_freq=-1,
                 repeat_start_conditions=False, check_stable=True, check_cfl=True,
                 conditions="Dirihle"):
        self.x_size = x_size
        self.y_size = y_size
        self.t = t
        self.Dx = Dx
        self.Dy = Dy
        self.dx = dx
        self.dy = dy
        self.dt = dt
        self.c = c_start
        self.c_start = c_start
        self.repeat_start_conditions = repeat_start_conditions
        self.check_cfl = check_cfl
        self.cfl = None
        self.repeat_freq = repeat_freq
        self.x = np.linspace(0, x_size, int(x_size/dx))
        self.y = np.linspace(0, y_size, int(y_size/dy))
        self.X, self.Y = np.meshgrid(self.x, self.y)
        if isinstance(u, int) or isinstance(u, float):
            self.u = u + 0 * self.X
        elif isinstance(u, dict):
            if isinstance(u.get(0), str):
                self.u = string_function_to_numpy(u.get(0), self.x) + 0 * self.X
            else:
                self.u = float(u.get(0)) + 0 * self.X
            self.u_rules = u
            self.u_times = list(u.keys())
            self.u_next_time = self.u_times[1] if len(self.u_times) > 1 else None
        else:
            self.u = u
        if isinstance(v, int) or isinstance(v, float):
            self.v = v + 0 * self.Y
        elif isinstance(v, dict):
            if isinstance(v.get(0), str):
                self.v = string_function_to_numpy(v.get(0), self.x) + 0 * self.Y
            else:
                self.v = float(v.get(0)) + 0 * self.Y
            self.v_rules = v
            self.v_times = list(v.keys())
            self.v_next_time = self.v_times[1] if len(self.v_times) > 1 else None
        else:
            self.v = v
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
        self.max_conc = np.max(self.c)
        self.slices_freq = slices_freq
        self.time_steps = int(self.t / self.dt)

        logger.info(f"Wind X={self.u}")
        logger.info(f"Wind Y={self.v}")
        self.dynamic_wind_u = False
        self.dynamic_wind_v = False
        self.conditions = conditions
        self.check_stable = check_stable
        self.c_list = []
        self.u_key_iter = 1
        self.v_key_iter = 1

    def iterate(self):
        start_time = time.time()
        next_time = 1
        for t in range(self.time_steps):
            cur_time = t * self.dt
            c_new = self.c.copy()
            c_new[1:-1, 1:-1] = self.Dx * (self.c[:-2, 1:-1] - 2 * self.c[1:-1, 1:-1] + self.c[2:, 1:-1]) / self.dx ** 2
            c_new[1:-1, 1:-1] += self.Dy * (
                    self.c[1:-1, :-2] - 2 * self.c[1:-1, 1:-1] + self.c[1:-1, 2:]) / self.dy ** 2

            if self.v_next_time is not None and t == self.v_next_time:
                if isinstance(self.v_rules.get(self.v_next_time), str):
                    self.v = string_function_to_numpy(self.v_rules.get(self.v_next_time), self.x) + 0 * self.Y
                else:
                    self.v = float(self.v_rules.get(self.v_next_time)) + 0 * self.Y
                if len(self.v_times) > (self.v_key_iter + 1):
                    self.v_next_time = self.v_times[self.v_key_iter + 1]
                else:
                    self.v_next_time = None
                self.v_key_iter += 1

            if self.u_next_time is not None and t == self.u_next_time:
                if isinstance(self.u_rules.get(self.u_next_time), str):
                    self.u = string_function_to_numpy(self.u_rules.get(self.u_next_time), self.x) + 0 * self.Y
                else:
                    self.u = float(self.u_rules.get(self.u_next_time)) + 0 * self.X
                if len(self.u_times) > (self.u_key_iter + 1):
                    self.u_next_time = self.u_times[self.u_key_iter + 1]
                else:
                    self.u_next_time = None
                self.u_key_iter += 1

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

            if self.repeat_start_conditions:
                if self.repeat_freq == -1:
                    if cur_time >= next_time:
                        c_new += self.c_start
                        next_time += 1
                else:
                    if t % self.repeat_freq == 0:
                        c_new += self.c_start

            self.c = c_new
            if np.max(self.c) > self.max_conc and not self.repeat_start_conditions and self.check_stable:
                logger.warning("The solution differs.")
                logger.info(np.max(self.c))
                logger.info("iter=", t)
                raise Exception("Решение расходится")
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
