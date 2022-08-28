import scipy.stats as ss
import numpy as np
import matplotlib.pyplot as plt

x = np.arange(34,35)
xU, xL = x + 0.5, x - 0.5 
prob = ss.norm.cdf(xU, scale =(35-34)/7) - ss.norm.cdf(xL, scale = (35-34)/7)
prob = prob / prob.sum() # normalize the probabilities so their sum is 1
nums = np.random.choice(x, size = 10000, p = prob)
plt.hist(nums, bins = len(x))