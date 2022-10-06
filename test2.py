import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt


SS_MAX_EARNINGS = [ 
    [2002,84.900],
    [2003,87.000],
    [2004,87.900],
    [2005,90.000],
    [2006,94.200],
    [2007,97.500],
    [2008,102.000],
    [2009,106.800],
    [2010,106.800],
    [2011,106.800],
    [2012,110.100],
    [2013,113.700],
    [2014,117.000],
    [2015,118.500],
    [2016,118.500],
    [2017,127.200],
    [2018,128.400],
    [2019,132.900],
    [2020,137.700],
    [2021,142.800],
]
SS_INDEXES = [ 
    [2002,1.7665978],
    [2003,1.7244432],
    [2004,1.6478390],
    [2005,1.5896724],
    [2006,1.5198170],
    [2007,1.4538392],
    [2008,1.4211470],
    [2009,1.4429071],
    [2010,1.4095913],
    [2011,1.3667660],
    [2012,1.3253803],
    [2013,1.3086540],
    [2014,1.2637941],
    [2015,1.2213044],
    [2016,1.2076578],
    [2017,1.1673463],
    [2018,1.1265158],
    [2019,1.0858240],
    [2020,1.0559868],
    [2021,1.0000000]
 ]

SS_MAX_EARNINGS = np.transpose(np.array(SS_MAX_EARNINGS))
SS_INDEXES = np.transpose(np.array(SS_INDEXES))

# https://rowannicholls.github.io/python/curve_fitting/exponential.html
def exponential_fit(x, a, b, c):
    return a*np.exp(b*x) + c

if __name__ == "__main__":
    x = np.array([0, 1, 2, 3, 4, 5])
    y = np.array([30, 50, 80, 160, 300, 580])
    x = SS_INDEXES[0]
    y = SS_INDEXES[1]
    # Have an initial guess as to what the values of the parameters are
    # a_guess = 0.000000000000000000000723719835 # values from excel line fitting
    # b_guess = 0.026533
    # c_guess = 0
    # fitting_parameters, covariance = curve_fit(exponential_fit, x, y, p0=(a_guess, b_guess, c_guess))
    # a, b, c = fitting_parameters
    
    p = np.polyfit(x, np.log(y), 1)
    
    a = np.exp(p[1])
    b = p[0]
    
    next_x = 2025
    next_y = exponential_fit(next_x, a, b, c=0)
    
    plt.plot(y)
    plt.plot(np.append(y, next_y), 'ro')
    plt.show()