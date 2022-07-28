import time
from matplotlib import pyplot as plt
import numpy as np

def live_update_demo():

    plt.subplot(2, 1, 1)
    h1 = plt.imshow(np.random.randn(30, 30))
    redraw_figure()
    plt.subplot(2, 1, 2)
    h2, = plt.plot(np.random.randn(50))
    redraw_figure()

    t_start = time.time()
    for i in range(1000):
        h1.set_data(np.random.randn(30, 30))
        redraw_figure()
        h2.set_ydata(np.random.randn(50))
        redraw_figure()

def redraw_figure():
    plt.draw()
    plt.pause(0.00001)

live_update_demo()