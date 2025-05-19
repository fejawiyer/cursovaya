import numpy as np
import time
import logging

logger = logging.getLogger(__name__)


class Model:
    def __init__(self, c_start,
                 x_size=50.0, y_size=50.0, x_steps=50, y_steps=50,
                 t=30,
                 Dx=0.5, Dy=0.5,
                 dx=1, dy=1, dt=0.1,
                 u=0, v=0,
                 slices_freq=1,
                 repeat_freq=-1,
                 repeat_start_conditions=False, check_stable=True, check_cfl=True,
                 conditions="Dirihle"):
        self.X = np.linspace(0, int(x_size), int(x_steps))
        self.Y = np.linspace(0, int(y_size), int(y_steps))
        self.x_size = x_size
        self.y_size = y_size
        self.x_steps = x_steps
        self.y_steps = y_steps
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
        logger.info("Modelling start")

        if check_cfl:
            self.cfl = dt * np.max(u) / dx + dt * np.max(v) / dy + 2 * Dx * dt / dx ** 2 + 2 *Dy * dt / dy ** 2
            logger.info(f"CFL:{self.cfl}")
            if self.cfl > 1:
                for i in range(50):
                    logger.info("CFL > 1")
                    logger.info("Reduce dt...")
                    self.dt /= 2
                    logger.info(f"dt={self.dt}")
                    self.cfl = self.dt * np.max(u) / dx + self.dt * np.max(
                        v) / dy + 1 * Dx * self.dt / dx ** 2 + 1 * Dy * self.dt / dy ** 2
                    logger.info(f"CFL={self.cfl}")
                    if self.cfl <= 1:
                        logger.info("Succes")
                        break
        self.max_conc = np.max(self.c)
        self.slices_freq = slices_freq
        self.time_steps = int(self.t / self.dt)
        self.x = np.linspace(0, x_size, x_steps)
        self.y = np.linspace(0, y_size, y_steps)
        self.X, self.Y = np.meshgrid(self.x, self.y)

        if isinstance(u, int) or isinstance(u, float):
            self.u = u + 0 * self.X
        else:
            self.u = u
        if isinstance(v, int) or isinstance(v, float):
            self.v = v + 0 * self.Y
        else:
            self.v = v
        logger.info(f"Wind X={self.u}")
        logger.info(f"Wind Y={self.v}")
        self.dynamic_wind_u = False
        self.dynamic_wind_v = False
        self.conditions = conditions
        self.check_stable = check_stable
        self.c_list = []
        self.Q = None
        self.im = None
        self.crit_t_u = None
        self.crit_t_v = None
        self.crit_rule_u = None
        self.crit_rule_v = None
        self.wind_bar = None
        self.conc_bar = None
        self.u_key_iter = 0
        self.v_key_iter = 0

    def iterate(self):
        start_time = time.time()
        next_time = 1
        for t in range(self.time_steps):
            cur_time = t * self.dt
            c_new = self.c.copy()
            c_new[1:-1, 1:-1] = self.Dx * (self.c[:-2, 1:-1] - 2 * self.c[1:-1, 1:-1] + self.c[2:, 1:-1]) / self.dx ** 2
            c_new[1:-1, 1:-1] += self.Dy * (
                    self.c[1:-1, :-2] - 2 * self.c[1:-1, 1:-1] + self.c[1:-1, 2:]) / self.dy ** 2
            c_new[1:-1, 1:-1] -= ((self.c[1:-1, 1:-1] - self.c[:-2, 1:-1]) * self.u[1:-1, 1:-1] / self.dx)
            c_new[1:-1, 1:-1] -= ((self.c[1:-1, 1:-1] - self.c[1:-1, :-2]) * self.v[1:-1, 1:-1] / self.dy)
            c_new[1:-1, 1:-1] *= self.dt
            c_new[1:-1, 1:-1] += self.c[1:-1, 1:-1]

            if self.conditions == "Dirihle":
                c_new[0, :] = 0  # Левая граница
                c_new[-1, :] = 0  # Правая граница
                c_new[:, 0] = 0  # Нижняя граница
                c_new[:, -1] = 0  # Верхняя граница
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
            if int(t % self.slices_freq) == 0:
                self.c_list.append(self.c.copy())

        end_time = time.time()
        logger.info(f"Time spend {end_time - start_time:.5f} seconds.")
        logger.info(f"Modelled {self.dt * self.time_steps} seconds")
        logger.info(f"Calculated {self.time_steps * self.x_steps * self.y_steps} elements")
        logger.info(f"Calculated {len(self.c_list)} layers")
