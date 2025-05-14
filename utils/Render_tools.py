import numpy as np
from matplotlib import pyplot as plt, animation, colors
from matplotlib.colors import BoundaryNorm
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.animation import FuncAnimation, PillowWriter
from PyQt5.QtWidgets import QMessageBox
from matplotlib.ticker import FixedLocator


class SaveMPCAnimation:
    def __init__(self, anim_int, repeat, x_size, y_size, mpc,
                 output_file="pollution_animation.gif", progress_bar=None, zoning=False):
        plt.switch_backend('Agg')
        plt.close('all')

        self.fig, self.ax = plt.subplots(figsize=(10, 8))
        self.canvas = FigureCanvasAgg(self.fig)

        self.x_size = x_size
        self.y_size = y_size
        self.mpc = mpc
        self.anim_int = anim_int
        self.repeat = repeat
        self.output_file = output_file
        self.progress_bar = progress_bar
        self.zoning = zoning  # Флаг для гладких зон

        # Загрузка данных
        self.c_list = np.load("model.npz")['res']
        self.total_frames = len(self.c_list)

        # Настройка зон
        self._setup_zones()

        if progress_bar:
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)

    def _setup_zones(self):
        """Настройка зон загрязнения на основе MPC"""
        self.zones = {
            'levels': [0, 0.5, 1.0, 2.0, 5.0],  # В долях от MPC
            'colors': ['#4CAF50', '#FFEB3B', '#FF9800', '#F44336'],
            'labels': [
                'Ниже 0.5 MPC (безопасно)',
                '0.5-1 MPC (допустимо)',
                '1-2 MPC (опасно)',
                'Выше 2 MPC (критично)'
            ]
        }

    def _get_scaled_levels(self):
        """Масштабирование уровней относительно MPC"""
        return [level * self.mpc for level in self.zones['levels']]

    def _setup_axes(self):
        """Настройка осей с ограниченным количеством тиков"""
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

        # Обновление прогресса
        if self.progress_bar:
            progress = int((it + 1) / self.total_frames * 100)
            self.progress_bar.setValue(progress)

        return [self.im]

    def save(self):
        # Настройка осей
        self._setup_axes()

        # Создаем нормализацию и цветовую карту
        scaled_levels = self._get_scaled_levels()
        norm = BoundaryNorm(scaled_levels, len(self.zones['colors']))
        cmap = colors.ListedColormap(self.zones['colors'])

        # Выбираем метод интерполяции
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

        self.ax.set_title(f'Карта загрязнений\nПДК = {self.mpc}')

        # Создаем анимацию
        ani = FuncAnimation(
            self.fig,
            self.update_frame,
            frames=self.total_frames,
            interval=self.anim_int,
            blit=True,
            repeat=self.repeat
        )

        # Сохранение в нужном формате
        if self.output_file.lower().endswith('.gif'):
            self._save_gif(ani)
        elif self.output_file.lower().endswith('.html'):
            self._save_html(ani)
        else:
            raise ValueError("Unsupported file format. Please use .gif or .html")

        plt.close(self.fig)

    def _save_gif(self, ani):
        writer = PillowWriter(fps=1000 / self.anim_int)

        if self.progress_bar:
            writer.frame_count = 0
            original_grab_frame = writer.grab_frame

            def grab_frame_with_progress(**kwargs):
                result = original_grab_frame(**kwargs)
                writer.frame_count += 1
                progress = int(writer.frame_count / self.total_frames * 100)
                self.progress_bar.setValue(progress)
                return result

            writer.grab_frame = grab_frame_with_progress

        try:
            ani.save(self.output_file, writer=writer, dpi=100)
            if self.progress_bar:
                self.progress_bar.setValue(100)
        except Exception as e:
            self.show_error(f"Ошибка при сохранении GIF: {str(e)}")

    def _save_html(self, ani):
        try:
            html = ani.to_jshtml()
            with open(self.output_file, 'w') as f:
                f.write(html)
            if self.progress_bar:
                self.progress_bar.setValue(100)
        except Exception as e:
            self.show_error(f"Ошибка при сохранении HTML: {str(e)}")

    def show_error(self, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Ошибка")
        msg.setInformativeText(message)
        msg.setWindowTitle("Ошибка")
        msg.exec_()

    def show_info(self, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText("Успех")
        msg.setInformativeText(message)
        msg.setWindowTitle("Информация")
        msg.exec_()


class SaveDefaultAnimation:
    def __init__(self, anim_int, repeat, x_size, y_size, output_file="animation.gif",
                 progress_bar=None, zoning=False, update_conc=False):
        plt.switch_backend('Agg')
        plt.close('all')

        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvasAgg(self.fig)

        self.x_size = x_size
        self.y_size = y_size
        self.anim_int = anim_int
        self.repeat = repeat
        self.output_file = output_file
        self.progress_bar = progress_bar
        self.zoning = zoning  # New parameter for interpolation control
        self.update_conc = update_conc  # New parameter for dynamic color scaling

        self.c_list = np.load("model.npz")['res']
        self.total_frames = len(self.c_list)
        self.current_vmax = np.max(self.c_list) if not update_conc else np.max(self.c_list[0])

        if progress_bar:
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)

    def update_frame(self, it):
        if self.update_conc:
            self.current_vmax = np.max(self.c_list[it])
            self.im.set_clim(vmin=0, vmax=self.current_vmax)

        self.im.set_array(self.c_list[it])

        if self.progress_bar:
            progress = int((it + 1) / self.total_frames * 100)
            self.progress_bar.setValue(progress)

        return [self.im]

    def save(self):
        # Set interpolation based on zoning parameter
        interpolation = 'bilinear' if self.zoning else 'nearest'

        self.im = self.ax.imshow(
            self.c_list[0],
            extent=[0, self.x_size, 0, self.y_size],
            origin='lower',
            cmap='hot',
            vmin=0,
            vmax=self.current_vmax,
            interpolation=interpolation)  # Added interpolation parameter

        self.fig.colorbar(self.im, ax=self.ax, label='Концентрация')

        ani = FuncAnimation(
            self.fig,
            self.update_frame,
            frames=self.total_frames,
            interval=self.anim_int,
            blit=True,
            repeat=self.repeat
        )

        if self.output_file.lower().endswith('.gif'):
            self._save_gif(ani)
        elif self.output_file.lower().endswith('.html'):
            self._save_html(ani)
        else:
            raise ValueError("Unsupported file format. Please use .gif or .html")

        plt.close(self.fig)

    def _save_gif(self, ani):
        writer = PillowWriter(fps=1000 / self.anim_int)
        if self.progress_bar:
            writer.frame_count = 0
            original_grab_frame = writer.grab_frame

            def grab_frame_with_progress(**kwargs):
                result = original_grab_frame(**kwargs)
                writer.frame_count += 1
                progress = int(writer.frame_count / self.total_frames * 100)
                self.progress_bar.setValue(progress)
                return result

            writer.grab_frame = grab_frame_with_progress

        ani.save(self.output_file, writer=writer, dpi=100)

    def _save_html(self, ani):
        html = ani.to_jshtml()
        with open(self.output_file, 'w') as f:
            f.write(html)

    def show_error(self, message):
        QMessageBox.critical(None, "Ошибка", message)

    def show_info(self, message):
        QMessageBox.information(None, "Успех", message)