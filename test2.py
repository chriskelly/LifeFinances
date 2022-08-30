import matplotlib.pyplot as plt
import scipy.stats as ss
import numpy as np
#instantiate a Generator
rng = np.random.default_rng()

while True:
    center= 35
    max_deviation= 1
    scale= max_deviation/1.5
    x = np.arange(-max_deviation, max_deviation+1) +center
    xU, xL = x + 0.5, x - 0.5
    prob = ss.norm.cdf(xU,loc=center, scale = scale) - ss.norm.cdf(xL,loc=center, scale = scale)
    prob = prob / prob.sum() # normalize the probabilities so their sum is 1
    num = np.random.choice(x, p = prob)
    print(num)
# nums = np.random.choice(x, size = 1000, p = prob)
# plt.hist(nums, bins = len(x))
# plt.show()