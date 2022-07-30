import numpy
from scipy.stats import skewnorm,skew,kurtosis
from scipy import stats
import matplotlib.pyplot as plt
import pandas as pd

historical_data = pd.read_csv('HistoricalInflationData.csv')
historical_data = historical_data['Inflation'].to_list()
a=skew(historical_data)
kurt = kurtosis(historical_data)
p_value = stats.shapiro(historical_data)[1] # less that 0.05 means it's likely not normal distribution?

mean = 1.037
var = 0.027

mean, var = skewnorm.stats(a, moments='mv')

data= skewnorm.rvs(a, size=1000)
#numpy.savetxt("foo.csv", data, delimiter=",")

plt.hist(data, 20)
plt.show() 