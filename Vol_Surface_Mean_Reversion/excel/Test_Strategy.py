'''
This file will test strategy
''' 
import sys
libPath="C:\\Users\\AXZQ\\Desktop\\VolTick"
if libPath not in sys.path:
    sys.path.append(libPath)   
import win32com.client as win32
import pandas as pd
import numpy as np
import os
from datetime import datetime,date
from TickQuotation.tickquotation import TickQuotation
from TickQuotation.ETFOptionQuotation import ETFOptionTick
from PricingEngine.optionpricing import OptionPricing
from xllfunc import RunXll
from TickQuotation.timeseries import time_series
from Market_Taking_Strategy.vol_surface import Theo_Option
from Market_Taking_Strategy.strategy4 import Strategy4

#First Expiry 50ETF
# No trades on 2019-12-23， 2020-10-12， 2021-09-17,2022-09-19, 2023-04-24, 2023-06-01, 2023-06-02, 2023-07-11



#Second Expiry
#2.7% intraday return on 2019-12-23 for 50ETF. Triggered trading signal but not unwind signal. 
#-19% intraday return on 2020-10-12 for 50ETF. Triggered trading signal but not unwind signal. 
# nothing happends on 2021-09-17 for 50ETF / No trades for 300ETF_SZ. Does not even trigger the trading signal.
#-98% intraday return on 2022-09-19 for 50ETF(Large Bid Ask Sprd and small position begin: 4)/ No trades for 300ETF_SZ. Does not trigger the unwind signal. 
# 15.8% intraday return on 2023-04-24 for 50 etf / No trades for 300ETF_SZ. Triggered the trading sigal and unwind signal only in one mins, which means market is . Position_bgn: 27.99, Position_end: 32.32
# No trades happen on 2023-06-01 for 50ETF or 300ETF_SZ. Does not trigger the trading signal.
#No trades happen on 2023-06-02 for 50ETF or 300ETF_SZ. Does not trigger the trading signal.
# -8% return on 2023-06-19 for 50ETF. Does not mean reversion and lack of market liquidity.
#-6% return on 2023-07-05 for 50 ETF. 
#No trades happen on 2023-07-11 for 50ETF or 300ETF_SZ. Does not trigger the trading signal. 

#Third Expiry 50ETF
#No trades happen on 2019-12-23, 2020-10-12, 2022-09-19, 2023-05-31
#-20% intraday return on 2023-06-02 (Is it cuz the market is more illquid if the TTM is large)  

refday = '2023-07-05'
end_date = refday
etf_name = "50ETF"
underlying = "510050"


r = 0.025
q = r
year = 365
ccy="CNY"

def load_tick_from_csv(underlying, path, end_date):
    # 1.1   load future tick
    etf_tick = TickQuotation(name=underlying)
    etf_tick.read_tick_csv(path=path)

    # 1.2   load option chain tick
    option_tick = ETFOptionTick(underlying=underlying, end_date=end_date)
    #   option_tick.reserve(month=array([month]))
    option_tick.read_tick_csv(path=path)
    return etf_tick, option_tick



    
if __name__=='__main__':
    excel = win32.DispatchEx('Excel.Application')
    #xllPath="C:\\Users\\AXZQ\\Desktop\\QuantLibXL-v141-mtVegaW.xll" 
    current_dir = os.getcwd()
    xllpath = "QuantLibXL-v141-mtVegaW.xll"
    xllPath = os.path.join(current_dir, xllpath)
    res = excel.RegisterXLL(xllPath)
    print("load xll: " + str(res))
    
    
    
    
    path = "../data/" + etf_name + "/intraday/" + end_date.replace('-', '') + "/"
    if not os.path.exists( "../data/" + etf_name + "/intraday/" + end_date.replace('-', '') + "/"):
        os.makedirs( "../data/" + etf_name + "/intraday/" + end_date.replace('-', '') + "/")
    etf,options=load_tick_from_csv(underlying, path, end_date)
 




    expiry_index = 1
    #threshold_l = 0.03
    #threshold_s = 0.01
    freq = 60 #loop every 30s
    num = 60  #if we have 5 consecutive ticks have bizarre iv_diff%,then unwind
    tick_lst=time_series(refday)
    latest_unwind_time = "14:35:00"
    stop_loss_time = 20 #minutes




       

    strategy_obj = Strategy4(excel = excel, underlying = underlying, etf= etf, options = options, timeseries = tick_lst, r=r, q=q, year=year, expiry_index = expiry_index, refday = refday, ccy= ccy, latest_unwind_time = latest_unwind_time, \
                             stop_loss_time = stop_loss_time)
    
    print(strategy_obj.process_tick(freq, num))











    
    
    
    
   
        
        
        
