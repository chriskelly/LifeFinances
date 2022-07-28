import matplotlib.pyplot as plt
import numpy as np
from random import randint

x = np.linspace(0, 6*np.pi, 100)
y = np.sin(x)

# You probably won't need this if you're embedding things in a tkinter plot...
plt.ion()

fig = plt.figure()
ax = fig.add_subplot(2,3,3) # Three integers (nrows, ncols, index).  https://matplotlib.org/stable/api/figure_api.html#matplotlib.figure.Figure.add_subplot
line1, = ax.plot(x, y, 'r-') # Returns a tuple of line objects, thus the comma
ax2 = fig.add_subplot(2,3,4) # Three integers (nrows, ncols, index).  https://matplotlib.org/stable/api/figure_api.html#matplotlib.figure.Figure.add_subplot
line2, = ax2.plot(x, y, 'r-') # Returns a tuple of line objects, thus the comma

for phase in np.linspace(0, 10*np.pi, 500):
    line1.set_ydata(np.sin(x + phase))
    line2.set_ydata(np.sin(x + phase))
    fig.canvas.flush_events()
    fig.canvas.draw()