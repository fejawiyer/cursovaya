import numpy as np
import time
import matplotlib.pyplot as plt
from matplotlib import animation


class Model:
    def __init__(self, c_start,
                 x_size=50.0, y_size=50.0, x_steps=50, y_steps=50,
                 t=30,
                 Dx=0.5, Dy=0.5,
                 dx=1, dy=1, dt=0.1,
                 u=0, v=0,
                 slices_freq=1,
                 anim_interval=10, scale=5, repeat_freq=-1,
                 repeat_start_conditions=False, check_stable=True, check_cfl=True,
                 dynamic_wind_u_rule=None, dynamic_wind_v_rule=None, show_wind=True,
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
        self.anim_interval = anim_interval
        self.repeat_start_conditions = repeat_start_conditions
        self.check_cfl = check_cfl
        self.cfl = None
        self.repeat_freq = repeat_freq
        if check_cfl:
            self.cfl = dt * np.max(u) / dx + dt * np.max(v) / dy + 2 * Dx * dt / dx ** 2 + 2 * Dy * dt / dy ** 2
            print(f"CFL:{self.cfl}")
            if self.cfl > 1:
                for i in range(50):
                    print("CFL > 1")
                    print("Уменьшаю dt...")
                    self.dt /= 2
                    print(f"dt={self.dt}")
                    self.cfl = self.dt * np.max(u) / dx + self.dt * np.max(
                        v) / dy + 1 * Dx * self.dt / dx ** 2 + 1 * Dy * self.dt / dy ** 2
                    print(f"CFL={self.cfl}")
                    if self.cfl <= 1:
                        print("Успех!")
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
        self.dynamic_wind_u = False
        self.dynamic_wind_v = False
        self.dynamic_wind_u_rule = dynamic_wind_u_rule
        self.dynamic_wind_v_rule = dynamic_wind_v_rule
        self.conditions = conditions
        self.scale = scale
        self.check_stable = check_stable
        self.c_list = []
        self.wind_list_u = []
        self.wind_list_v = []
        self.fig, self.ax = plt.subplots()
        self.Q = None
        self.im = None
        self.crit_t_u = None
        self.crit_t_v = None
        self.crit_rule_u = None
        self.crit_rule_v = None
        self.wind_bar = None
        self.conc_bar = None
        self.show_wind = show_wind
        self.u_key_iter = 0
        self.v_key_iter = 0
        if self.dynamic_wind_u_rule is not None:
            self.dynamic_wind_u = True
            self.crit_t_u = list(self.dynamic_wind_u_rule.keys())
            self.crit_rule_u = list(self.dynamic_wind_u_rule.values())
        if self.dynamic_wind_v_rule is not None:
            self.dynamic_wind_v = True
            self.crit_t_v = list(self.dynamic_wind_v_rule.keys())
            self.crit_rule_v = list(self.dynamic_wind_v_rule.values())
        self.text = self.ax.text(0.5, 1.05, '', transform=self.ax.transAxes, fontsize=12, ha='center')

    def iterate(self):
        start_time = time.time()
        next_time = 1
        for t in range(self.time_steps):
            cur_time = t*self.dt
            c_new = self.c.copy()
            c_new[1:-1, 1:-1] = self.Dx * (self.c[:-2, 1:-1] - 2 * self.c[1:-1, 1:-1] + self.c[2:, 1:-1]) / self.dx ** 2
            c_new[1:-1, 1:-1] += self.Dy * (
                    self.c[1:-1, :-2] - 2 * self.c[1:-1, 1:-1] + self.c[1:-1, 2:]) / self.dy ** 2
            c_new[1:-1, 1:-1] -= ((self.c[1:-1, 1:-1] - self.c[:-2, 1:-1]) * self.u[1:-1, 1:-1] / (self.dx))
            c_new[1:-1, 1:-1] -= ((self.c[1:-1, 1:-1] - self.c[1:-1, :-2]) * self.v[1:-1, 1:-1] / (self.dy))
            c_new[1:-1, 1:-1] *= self.dt
            c_new[1:-1, 1:-1] += self.c[1:-1, 1:-1]

            if self.conditions == "Neimann":
                c_new[0, :] = c_new[1, :]  # Левая граница
                c_new[-1, :] = c_new[-2, :]  # Правая граница
                c_new[:, 0] = c_new[:, 1]  # Нижняя граница
                c_new[:, -1] = c_new[:, -2]  # Верхняя граница
            else:
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
                print(np.max(self.c))
                print("iter=", t)
                raise Exception("Решение расходится")
            if int(t % self.slices_freq) == 0:
                self.c_list.append(self.c.copy())
                self.wind_list_u.append(self.u)
                self.wind_list_v.append(self.v)

            if self.dynamic_wind_v:
                if self.v_key_iter < len(self.crit_t_v):
                    if t > self.crit_t_v[self.v_key_iter]:
                        self.v = self.crit_rule_v[self.v_key_iter]
                        if self.check_cfl:
                            self.cfl = (self.dt * np.max(self.u) / self.dx +
                                        self.dt * np.max(self.v) / self.dy +
                                        self.Dx * self.dt / self.dx ** 2 +
                                        self.Dy * self.dt / self.dy ** 2)
                            if self.cfl > 1:
                                print(f"Опасность! CFL>1! {self.cfl}")
                                for i in range(1000):
                                    self.dt /= 2
                                    if self.cfl <= 1:
                                        print("Уменьшаю dt...")
                                        print(f"dt={self.dt}")
                                        print(f"CFL={self.cfl}")
                                        break
                        self.v_key_iter += 1

            if self.dynamic_wind_u:
                if self.u_key_iter < len(self.crit_t_u):
                    if t > self.crit_t_u[self.u_key_iter]:
                        self.u = self.crit_rule_u[self.u_key_iter]
                        self.u_key_iter += 1
                        if self.check_cfl:
                            self.cfl = (self.dt * np.max(self.u) / self.dx +
                                        self.dt * np.max(self.v) / self.dy +
                                        self.Dx * self.dt / self.dx ** 2 +
                                        self.Dy * self.dt / self.dy ** 2)
                            if self.cfl > 1:
                                print(f"Опасность! CFL>1! {self.cfl}")
                                for i in range(1000):
                                    self.dt /= 2
                                    if self.cfl <= 1:
                                        print("Уменьшаю dt...")
                                        print(f"dt={self.dt}")
                                        print(f"CFL={self.cfl}")
                                        break
        end_time = time.time()
        print(f"Подсчет элементов занял {end_time - start_time:.5f} секунд.")
        print(f"Смоделировано {self.dt * self.time_steps} секунд")
        print(f"Рассчитано {self.time_steps * self.x_steps * self.y_steps} элементов")
        print(f"Рассчитано {len(self.c_list)} слоёв")

    def draw(self):
        self.im = self.ax.imshow(
            self.c_list[0],
            extent=[0, self.x_size, 0, self.y_size],
            origin='lower',
            cmap='hot',
            vmin=0,
            vmax=np.max(self.c_list))
        if self.show_wind:
            self.Q = self.ax.quiver(self.X, self.Y, self.wind_list_u[0], self.wind_list_v[0], angles='xy', scale_units='xy',
                                    scale=self.scale, cmap='viridis')
            speed = np.sqrt(self.wind_list_u[0] ** 2 + self.wind_list_v[0] ** 2)
            self.wind_bar = plt.colorbar(self.Q, ax=self.ax, label="Скорость ветра")
            self.Q.set_clim(vmin=np.min(speed), vmax=np.max(speed))
        self.conc_bar = plt.colorbar(self.im, ax=self.ax, label='Концентрация')
        ani = animation.FuncAnimation(self.fig, self.__anim, frames=len(self.c_list), interval=self.anim_interval,
                                      blit=False, repeat=self.repeat)
        plt.show()

    def __anim(self, it):
        self.im.set_data(self.c_list[it])
        return self.im,
