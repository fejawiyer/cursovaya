import multiprocessing
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PyQt5.QtWidgets import QMessageBox
from matplotlib import pyplot as plt
from matplotlib.animation import PillowWriter, FuncAnimation
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.figure import Figure
from matplotlib.ticker import FixedLocator


class MPCAnimation:
    def __init__(self, anim_int, repeat, x_size, y_size, mpc,
                 output_file=None, progress_bar=None, zoning=False):
        backend = 'Agg' if output_file is not None else 'Qt5Agg'
        print(backend)
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

        self.c_list = np.load("model.npz")['res'].transpose(0, 2, 1)
        self.total_frames = len(self.c_list)

        self._setup_zones()

        self.ani = None
        self.im = None
        self.cbar = None
        self.mpc_line = None
        self.title = None

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

        self.title.set_text(f'Карта загрязнений (шаг {it + 1}/{self.total_frames})\nПДК = {self.mpc}')

        if self.progress_bar and self.output_file is not None:
            progress = int((it + 1) / self.total_frames * 100)
            self.progress_bar.setValue(progress)

        return [self.im, self.mpc_line, self.title]


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

        self.title = self.ax.text(
            0.5, 1.05,  # Позиция (x=0.5 - центр, y=1.05 - чуть выше осей)
            f'Карта загрязнений\nПДК = {self.mpc}',
            transform=self.ax.transAxes,
            ha='center',
            va='bottom',
            bbox={'facecolor': 'white', 'alpha': 0.7, 'pad': 5}
        )

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

        # Создание анимации
        self.ani = FuncAnimation(
            self.fig,
            self.update_frame,
            frames=self.total_frames,
            interval=self.anim_int,
            blit=False,
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
        # Determine number of workers (leave one core free for main thread)
        num_workers = max(1, multiprocessing.cpu_count() - 1)

        # Create frame rendering function that doesn't leak figures
        def render_frame(frame_num):
            # Create figure without using pyplot to avoid warnings
            fig = Figure(figsize=(10, 8))
            canvas = FigureCanvasAgg(fig)
            ax = fig.add_subplot(111)

            # Get current frame data
            current_data = self.c_list[frame_num]

            # Recreate the visualization
            scaled_levels = self._get_scaled_levels()
            norm = BoundaryNorm(scaled_levels, len(self.zones['colors']))
            cmap = ListedColormap(self.zones['colors'])

            interpolation = 'bilinear' if self.zoning else 'nearest'
            im = ax.imshow(
                current_data,
                extent=[0, self.x_size, 0, self.y_size],
                origin='lower',
                cmap=cmap,
                norm=norm,
                interpolation=interpolation)

            # Add contours
            mpc_line = ax.contour(
                current_data,
                levels=[self.mpc],
                colors=['white'],
                linewidths=2,
                linestyles='dashed',
                extent=[0, self.x_size, 0, self.y_size])

            # Add title
            ax.set_title(f'Карта загрязнений (шаг {frame_num + 1}/{self.total_frames})\nПДК = {self.mpc}')

            # Draw the figure
            canvas.draw()

            # Get the image data
            buf = canvas.buffer_rgba()
            width, height = canvas.get_width_height()
            img_array = np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 4)

            # Explicit cleanup
            fig.clear()
            plt.close(fig)
            del fig, canvas, ax

            return img_array

        try:
            # Process frames in batches to avoid memory issues
            batch_size = min(20, self.total_frames)
            frames = []

            for i in range(0, self.total_frames, batch_size):
                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    frames.extend(executor.map(render_frame, range(i, min(i + batch_size, self.total_frames))))

                if self.progress_bar:
                    progress = int((i + batch_size) / self.total_frames * 100)
                    self.progress_bar.setValue(min(progress, 100))

            # Save the frames
            writer = PillowWriter(fps=1000 / self.anim_int)
            with writer.saving(self.fig, self.output_file, dpi=100):
                for i, frame in enumerate(frames):
                    writer.grab_frame()
                    if self.progress_bar:
                        progress = int((i + 1) / self.total_frames * 100)
                        self.progress_bar.setValue(progress)

        except Exception as e:
            self.show_error(f"Ошибка при сохранении: {str(e)}")
        finally:
            plt.close('all')

    def _render_frame(self, frame_num):
        """Render a single frame and return the image data"""
        # Create a new figure and canvas for this frame
        fig, ax = plt.subplots(figsize=(10, 8))
        canvas = FigureCanvasAgg(fig)

        # Copy the content from our main figure
        self.update_frame(frame_num)

        # Draw the new figure with the same content
        ax.clear()
        ax.imshow(self.im.get_array(),
                  extent=[0, self.x_size, 0, self.y_size],
                  origin='lower',
                  cmap=self.im.get_cmap(),
                  norm=self.im.norm,
                  interpolation=self.im.get_interpolation())

        # Add contours if they exist
        if hasattr(self, 'mpc_line'):
            ax.contour(self.im.get_array(),
                       levels=[self.mpc],
                       colors=['white'],
                       linewidths=2,
                       linestyles='dashed',
                       extent=[0, self.x_size, 0, self.y_size])

        # Add title
        ax.set_title(f'Карта загрязнений (шаг {frame_num + 1}/{self.total_frames})\nПДК = {self.mpc}')

        # Draw the figure
        fig.canvas.draw()

        # Get the image data as numpy array
        buf = fig.canvas.buffer_rgba()
        width, height = fig.canvas.get_width_height()
        img_array = np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 4)

        # Close the temporary figure to free memory
        plt.close(fig)

        return img_array
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

        self.c_list = np.load("model.npz")['res'].transpose(0, 2, 1)
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