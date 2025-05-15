import numpy as np
from PyQt5.QtWidgets import QMessageBox
from matplotlib import pyplot as plt
from matplotlib.animation import PillowWriter, FuncAnimation
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.ticker import FixedLocator


class MPCAnimation:
    def __init__(self, anim_int, repeat, x_size, y_size, mpc,
                 output_file=None, progress_bar=None, zoning=False):
        backend = 'Agg' if output_file is not None else 'Qt5Agg'
        plt.switch_backend(backend)
        plt.close('all')

        self.fig, self.ax = plt.subplots(figsize=(10, 8))
        if output_file is not None:
            self.canvas = FigureCanvasAgg(self.fig)

        self.anim_int = anim_int
        self.repeat = repeat
        self.x_size = x_size
        self.y_size = y_size
        self.mpc = mpc
        self.output_file = output_file
        self.progress_bar = progress_bar
        self.zoning = zoning

        self.c_list = np.load("model.npz")['res']
        self.total_frames = len(self.c_list)

        self._setup_zones()

        self.ani = None
        self.im = None
        self.cbar = None
        self.mpc_line = None

        if progress_bar and output_file is not None:
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)

    def _setup_zones(self):
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
        return [level * self.mpc for level in self.zones['levels']]

    def _setup_axes(self):
        max_ticks = 10
        x_ticks = np.linspace(0, self.x_size, min(max_ticks, self.x_size))
        y_ticks = np.linspace(0, self.y_size, min(max_ticks, self.y_size))

        self.ax.xaxis.set_major_locator(FixedLocator(x_ticks))
        self.ax.yaxis.set_major_locator(FixedLocator(y_ticks))

        self.ax.grid(which='major', color='black', linestyle=':', alpha=0.3)
        self.ax.set_xlabel('X координата, м')
        self.ax.set_ylabel('Y координата, м')

    def update_frame(self, it):
        current_data = self.c_list[it]

        if self.zoning:
            self.im.set_array(current_data)
        else:
            self.im.set_data(current_data)

        if hasattr(self, 'mpc_line'):
            self.mpc_line.remove()
        self.mpc_line = self.ax.contour(
            current_data,
            levels=[self.mpc],
            colors=['white'],
            linewidths=2,
            linestyles='dashed',
            extent=[0, self.x_size, 0, self.y_size])

        title = f'Карта загрязнений (шаг {it + 1}/{self.total_frames})\nПДК = {self.mpc}'
        self.ax.set_title(title)

        if self.progress_bar and self.output_file is not None:
            progress = int((it + 1) / self.total_frames * 100)
            self.progress_bar.setValue(progress)

        return [self.im]

    def draw_or_save(self):
        self._setup_axes()

        scaled_levels = self._get_scaled_levels()
        norm = BoundaryNorm(scaled_levels, len(self.zones['colors']))
        cmap = ListedColormap(self.zones['colors'])

        interpolation = 'bilinear' if self.zoning else 'nearest'

        self.im = self.ax.imshow(
            self.c_list[0],
            extent=[0, self.x_size, 0, self.y_size],
            origin='lower',
            cmap=cmap,
            norm=norm,
            interpolation=interpolation)

        if hasattr(self, 'cbar') and self.cbar:
            self.cbar.remove()

        self.cbar = self.fig.colorbar(
            self.im,
            ax=self.ax,
            boundaries=scaled_levels,
            spacing='proportional',
            label=f'Концентрация (ПДК = {self.mpc})')

        tick_positions = [(scaled_levels[i] + scaled_levels[i + 1]) / 2
                          for i in range(len(scaled_levels) - 1)]
        self.cbar.set_ticks(tick_positions)
        self.cbar.set_ticklabels(self.zones['labels'])

        self.mpc_line = self.ax.contour(
            self.c_list[0],
            levels=[self.mpc],
            colors=['white'],
            linewidths=2,
            linestyles='dashed',
            extent=[0, self.x_size, 0, self.y_size])

        self.ax.set_title(f'Карта загрязнений\nПДК = {self.mpc}')

        # Создание анимации
        self.ani = FuncAnimation(
            self.fig,
            self.update_frame,
            frames=self.total_frames,
            interval=self.anim_int,
            blit=True,
            repeat=self.repeat)

        if self.output_file is not None:
            self._save_animation()
        else:
            plt.tight_layout()
            plt.draw()
            plt.show(block=False)
            self.fig._ani = self.ani

    def _save_animation(self):
        try:
            if self.output_file.lower().endswith('.gif'):
                self._save_gif()
            elif self.output_file.lower().endswith('.html'):
                self._save_html()
            else:
                raise ValueError("Unsupported file format. Please use .gif or .html")

            if self.progress_bar:
                self.progress_bar.setValue(100)

        except Exception as e:
            self.show_error(f"Ошибка при сохранении: {str(e)}")
        finally:
            plt.close(self.fig)

    def _save_gif(self):
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

        self.ani.save(self.output_file, writer=writer, dpi=100)

    def _save_html(self):
        html = self.ani.to_jshtml()
        with open(self.output_file, 'w') as f:
            f.write(html)

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


class DefaultAnimation:
    def __init__(self, anim_int, repeat, x_size, y_size, output_file=None,
                 progress_bar=None, zoning=False, update_conc=False):
        if output_file is not None:
            plt.switch_backend('Agg')
        else:
            plt.switch_backend('Qt5Agg')

        plt.close('all')

        self.fig, self.ax = plt.subplots()
        if output_file is not None:
            self.canvas = FigureCanvasAgg(self.fig)

        self.x_size = x_size
        self.y_size = y_size
        self.anim_int = anim_int
        self.repeat = repeat
        self.output_file = output_file
        self.progress_bar = progress_bar
        self.zoning = zoning
        self.update_conc = update_conc

        self.c_list = np.load("model.npz")['res']
        self.total_frames = len(self.c_list)
        self.current_vmax = np.max(self.c_list) if not update_conc else np.max(self.c_list[0])
        self.ani = None
        self.im = None

        if progress_bar and output_file is not None:
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)

    def update_frame(self, it):
        if self.update_conc:
            self.current_vmax = np.max(self.c_list[it])
            self.im.set_clim(vmin=0, vmax=self.current_vmax)

        self.im.set_array(self.c_list[it])

        if self.progress_bar and self.output_file is not None:
            progress = int((it + 1) / self.total_frames * 100)
            self.progress_bar.setValue(progress)

        return [self.im]

    def draw_or_save(self):
        interpolation = 'bilinear' if self.zoning else 'nearest'

        self.im = self.ax.imshow(
            self.c_list[0],
            extent=[0, self.x_size, 0, self.y_size],
            origin='lower',
            cmap='hot',
            vmin=0,
            vmax=self.current_vmax,
            interpolation=interpolation)

        self.fig.colorbar(self.im, ax=self.ax, label='Концентрация')

        self.ani = FuncAnimation(
            self.fig,
            self.update_frame,
            frames=self.total_frames,
            interval=self.anim_int,
            blit=True,
            repeat=self.repeat
        )

        if self.output_file is not None:
            self._save_animation()
        else:
            plt.draw()
            plt.show(block=False)
            self.fig._ani = self.ani

    def _save_animation(self):
        if self.output_file.lower().endswith('.gif'):
            self._save_gif()
        elif self.output_file.lower().endswith('.html'):
            self._save_html()
        else:
            raise ValueError("Unsupported file format. Please use .gif or .html")
        plt.close(self.fig)

    def _save_gif(self):
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

        self.ani.save(self.output_file, writer=writer, dpi=100)

    def _save_html(self):
        html = self.ani.to_jshtml()
        with open(self.output_file, 'w') as f:
            f.write(html)

    def show_error(self, message):
        QMessageBox.critical(None, "Ошибка", message)

    def show_info(self, message):
        QMessageBox.information(None, "Успех", message)