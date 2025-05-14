import numpy as np
from matplotlib import pyplot as plt, animation, colors
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import MultipleLocator, FixedLocator


class MPCPlot:
    def __init__(self, anim_int, repeat, x_size, y_size, mpc, zoning=False):
        plt.switch_backend('Qt5Agg')
        plt.close('all')

        self.fig = plt.figure(figsize=(10, 8))
        self.ax = self.fig.add_subplot(111)

        self.anim_int = anim_int
        self.repeat = repeat
        self.x_size = x_size
        self.y_size = y_size
        self.mpc = mpc  # Предельно допустимая концентрация
        self.zoning = zoning  # Флаг для гладких зон

        data = np.load("model.npz")
        self.c_list = data['res']

        self._setup_zones()

        self.ani = None
        self.im = None
        self.cbar = None

    def _setup_zones(self):
        self.zones = {
            'levels': [0, 0.5, 1.0, 2.0, 5.0],  # В долях от ПДК
            'colors': ['#4CAF50', '#FFEB3B', '#FF9800', '#F44336'],
            'labels': [
                'Ниже 0.5 ПДК',
                '0.5-1 ПДК',
                '1-2 ПДК',
                'Выше 2 ПДК'
            ]
        }

    def _get_scaled_levels(self):
        return [level * self.mpc for level in self.zones['levels']]

    def _setup_axes(self):
        # Настройка осей с ограничением количества тиков (максимум 10)
        max_ticks = 10
        x_ticks = np.linspace(0, self.x_size, min(max_ticks, self.x_size))
        y_ticks = np.linspace(0, self.y_size, min(max_ticks, self.y_size))

        self.ax.xaxis.set_major_locator(FixedLocator(x_ticks))
        self.ax.yaxis.set_major_locator(FixedLocator(y_ticks))

        # Добавляем сетку
        self.ax.grid(which='major', color='black', linestyle=':', alpha=0.3)
        self.ax.set_xlabel('X координата, м')
        self.ax.set_ylabel('Y координата, м')

    def update_frame(self, it):
        current_data = self.c_list[it]

        if self.zoning:
            # Для гладких зон используем интерполяцию
            self.im.set_array(current_data)
        else:
            # Для пиксельного отображения
            self.im.set_data(current_data)

        # Обновляем линию MPC
        if hasattr(self, 'mpc_line'):
            self.mpc_line.remove()
        self.mpc_line = self.ax.contour(
            current_data,
            levels=[self.mpc],
            colors=['white'],
            linewidths=2,
            linestyles='dashed',
            extent=[0, self.x_size, 0, self.y_size])

        self.ax.set_title(f'Карта загрязнений (шаг {it + 1}/{len(self.c_list)})\nПДК = {self.mpc}')
        return self.im,

    def draw(self):
        self.ax.clear()

        # Настройка осей
        self._setup_axes()

        # Создаем нормализацию и цветовую карту
        scaled_levels = self._get_scaled_levels()
        norm = BoundaryNorm(scaled_levels, len(self.zones['colors']))
        cmap = colors.ListedColormap(self.zones['colors'])

        # Выбираем метод интерполяции в зависимости от флага zoning
        interpolation = 'bilinear' if self.zoning else 'nearest'

        # Отображаем данные
        self.im = self.ax.imshow(
            self.c_list[0],
            extent=[0, self.x_size, 0, self.y_size],
            origin='lower',
            cmap=cmap,
            norm=norm,
            interpolation=interpolation)

        # Добавляем цветовую шкалу
        if self.cbar:
            self.cbar.remove()

        self.cbar = self.fig.colorbar(
            self.im,
            ax=self.ax,
            boundaries=scaled_levels,
            spacing='proportional',
            label=f'Концентрация (ПДК = {self.mpc})')

        # Настраиваем метки цветовой шкалы
        tick_positions = [(scaled_levels[i] + scaled_levels[i + 1]) / 2 for i in range(len(scaled_levels) - 1)]
        self.cbar.set_ticks(tick_positions)
        self.cbar.set_ticklabels(self.zones['labels'])

        # Добавляем линию MPC для первого кадра
        self.mpc_line = self.ax.contour(
            self.c_list[0],
            levels=[self.mpc],
            colors=['white'],
            linewidths=2,
            linestyles='dashed',
            extent=[0, self.x_size, 0, self.y_size])

        self.ax.set_title(f'Карта загрязнений (шаг 1/{len(self.c_list)})\nПДК = {self.mpc}')

        # Создаем анимацию
        self.ani = animation.FuncAnimation(
            self.fig,
            self.update_frame,
            frames=len(self.c_list),
            interval=self.anim_int,
            blit=False,
            repeat=self.repeat,
            cache_frame_data=False)

        plt.tight_layout()
        plt.draw()
        plt.show(block=False)
        self.fig._ani = self.ani


class DefaultPlot:
    def __init__(self, anim_int, repeat, x_size, y_size, update_conc=False, zoning=False):
        plt.switch_backend('Qt5Agg')
        plt.close('all')

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111)

        self.anim_int = anim_int
        self.repeat = repeat
        self.x_size = x_size
        self.y_size = y_size
        self.update_conc = update_conc
        self.zoning = zoning  # Store the zoning parameter

        data = np.load("model.npz")
        self.c_list = data['res']
        self.ani = None
        self.im = None

    def update_frame(self, it):
        if self.update_conc:
            self.im.set_clim(vmin=0, vmax=np.max(self.c_list[it]))
        self.im.set_data(self.c_list[it])
        return self.im,

    def draw(self):
        self.ax.clear()
        vmax = np.max(self.c_list[0]) if self.update_conc else np.max(self.c_list)

        # Set interpolation based on zoning parameter
        interpolation = 'bilinear' if self.zoning else 'nearest'

        self.im = self.ax.imshow(
            self.c_list[0],
            extent=[0, self.x_size, 0, self.y_size],
            origin='lower',
            cmap='hot',
            vmin=0,
            vmax=vmax,
            interpolation=interpolation)  # Add interpolation parameter

        self.fig.colorbar(self.im, ax=self.ax, label='Концентрация')

        self.ani = animation.FuncAnimation(
            self.fig,
            self.update_frame,
            frames=len(self.c_list),
            interval=self.anim_int,
            blit=False,
            repeat=False,
            cache_frame_data=False)

        plt.draw()
        plt.show(block=False)

        self.fig._ani = self.ani  # Защита от сборщика мусора