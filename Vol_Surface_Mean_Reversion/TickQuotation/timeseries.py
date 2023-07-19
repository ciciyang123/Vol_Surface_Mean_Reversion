'''
This file is designed to have a global function to create a flexible time series
'''
import pandas as pd
import numpy as np
def time_series(day):
    #start from 9:15-9:25, 9:30-11:30, 13:00 to 15:00
    start1=day+ ' 9:15:00'
    end1=day+ ' 9:25:00'
    start2=day+' 10:00:00'
    end2=day+' 11:30:00'
    start3=day+ ' 13:00:00'
    end3=day+ ' 15:00:00'
    date_index1=pd.date_range(start1, end1, freq='500L').to_pydatetime()
    date_index2=pd.date_range(start2, end2, freq='500L').to_pydatetime()
    date_index3=pd.date_range(start3, end3, freq='500L').to_pydatetime()

    
    return np.concatenate((date_index1, date_index2, date_index3), axis=0)
