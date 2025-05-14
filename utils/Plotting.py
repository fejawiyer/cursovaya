import numpy as np
from matplotlib import pyplot as plt, animation


class Plot:
    def __init__(self, anim_int, repeat, x_size, y_size, update_conc=False):
        plt.switch_backend('Qt5Agg')
        plt.close('all')

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111)

        self.anim_int = anim_int
        self.repeat = repeat
        self.x_size = x_size
        self.y_size = y_size
        self.update_conc = update_conc

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
        self.im = self.ax.imshow(
            self.c_list[0],
            extent=[0, self.x_size, 0, self.y_size],
            origin='lower',
            cmap='hot',
            vmin=0,
            vmax=vmax)

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

