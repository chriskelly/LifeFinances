"""Creates a skewed distribution given skew parameter

https://stackoverflow.com/questions/49801071/how-can-i-use-skewnorm-to-produce-a-distribution-with-the-specified-skew/58111859#58111859"""

import numpy as np
from scipy import stats

def create_skew_dist(mean:float, std:float, skew:float, size:int, debug:bool = False) -> np.ndarray:
    """Creates a skewed distribution given skew parameter

    Args:
        mean (float)
        
        std (float): standard diviation
        
        skew (float)
        
        size (int): total qty desired
        
        debug (bool, optional): Create plot of distribution. Defaults to False

    Returns:
        np.ndarray: list skewed values with size = size
    """

    # Calculate the degrees of freedom 1 required to obtain the
    # specific skewness statistic, derived from simulations
    loglog_slope=-2.211897875506251
    loglog_intercept=1.002555437670879
    df2=500
    df1 = 10**(loglog_slope*np.log10(abs(skew)) + loglog_intercept)

    # Sample from F distribution
    fsample = np.sort(stats.f(df1, df2).rvs(size=size))

    # Adjust the variance by scaling the distance from each point to
    # the distribution mean by a constant, derived from simulations
    k1_slope = 0.5670830069364579
    k1_intercept = -0.09239985798819927
    k2_slope = 0.5823114978219056
    k2_intercept = -0.11748300123471256

    scaling_slope = abs(skew)*k1_slope + k1_intercept
    scaling_intercept = abs(skew)*k2_slope + k2_intercept

    scale_factor = (std - scaling_intercept)/scaling_slope
    new_dist = (fsample - np.mean(fsample))*scale_factor + fsample

    # flip the distribution if specified skew is negative
    if skew < 0:
        new_dist = np.mean(new_dist) - new_dist

    # adjust the distribution mean to the specified value
    final_dist = new_dist + (mean - np.mean(new_dist))

    if debug:
        import matplotlib.pyplot as plt # pylint: disable=import-outside-toplevel # lazy import
        import seaborn as sns # pylint: disable=import-outside-toplevel # lazy import
        print('Input mean: ', mean)
        print('Result mean: ', np.mean(final_dist),'\n')

        print('Input SD: ', std)
        print('Result SD: ', np.std(final_dist),'\n')

        print('Input skew: ', skew)
        print('Result skew: ', stats.skew(final_dist))
        # inspect the plots & moments, try random sample
        _, axis = plt.subplots(figsize=(12,7))
        sns.distplot(final_dist, hist=True, ax=axis, color='green', label='generated distribution')
        axis.legend()
        plt.show()

    return final_dist


# def test_unit():
#     import matplotlib.pyplot as plt
#     import seaborn as sns
#     desired_mean = 1.037
#     desired_skew = 1.642
#     desired_sd = .027

#     final_dist = create_skew_dist(mean=desired_mean, std=desired_sd,
#                       skew=desired_skew, size=135000, debug=True)

#     # inspect the plots & moments, try random sample
#     _, ax = plt.subplots(figsize=(12,7))
#     sns.distplot(final_dist, hist=True, ax=ax, color='green', label='generated distribution')
#     ax.legend()

#     plt.show()
