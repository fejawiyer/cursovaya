import os
import sys
import tempfile

from PyQt5.QtWidgets import QDialog, QFileDialog, QVBoxLayout, QPushButton, QLineEdit, QLabel, QMessageBox
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.io.ffmpeg_writer import ffmpeg_write_video
from tkinter.messagebox import showinfo
from tkinter.messagebox import showerror
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.backends.backend_agg import FigureCanvasAgg
import logging
import numpy as np

logger = logging.getLogger(__name__)


class SaveAnimation:
    def __init__(self, anim_int, repeat, x_size, y_size, output_file="animation.gif", progress_bar=None):
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

        self.c_list = np.load("model.npz")['res']
        self.total_frames = len(self.c_list)

        if progress_bar:
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)

    def update_frame(self, it):
        self.im.set_array(self.c_list[it])

        if self.progress_bar:
            progress = int((it + 1) / self.total_frames * 100)
            self.progress_bar.setValue(progress)

        return [self.im]

    def save(self):
        self.im = self.ax.imshow(
            self.c_list[0],
            extent=[0, self.x_size, 0, self.y_size],
            origin='lower',
            cmap='hot',
            vmin=0,
            vmax=np.max(self.c_list))

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
        QMessageBox.critical(self, "Ошибка", message)

    def show_info(self, message):
        QMessageBox.information(self, "Успех", message)
