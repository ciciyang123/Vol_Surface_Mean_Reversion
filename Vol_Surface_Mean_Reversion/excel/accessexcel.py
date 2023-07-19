'''
This file will let the Spyder get access to the build in function in excel
''' 
import sys
libPath="C:\\Users\\AXZQ\\Desktop\\VolTick"
if libPath not in sys.path:
    sys.path.append(libPath)
from math import log    
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
from matplotlib import pyplot as plt
from scipy.stats import norm

#refday = '2022-09-19'
refday_lst = ['2015-02-09']

etf_name = "50ETF"
underlying = "510050"
#month = '2103'
#f new data

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

def dividend_yield(S, r, F, T):
    #T: time to maturity
    #F=S*exp(r-q)*T
    #q=r-ln(F/S)/T
    #for every tick, we have a S,F, r is fixed, and T is the same for every expire_date(not change as the tick change) 
    return r- log(F/S)/T 

def plot(underlying: str, tick_time: datetime, option_data, volsurf_interpol, expire):
        plt.figure(figsize=(8,6))
        t = tick_time.strftime("%Y-%m-%d %H:%M:%S.%f")
        expire_time=expire.strftime("%Y-%m-%d")
        plt.plot(option_data['strike'], volsurf_interpol, 'm.-.', color='red', label='volsurf')
        plt.plot(option_data['strike'], option_data['bid_iv'], '.', color='green', label='bid_iv')
        plt.plot(option_data['strike'], option_data['ask_iv'], '.', color='blue', label='ask_iv')
        plt.title(underlying + " iv at " + t+ "with expire date of "+ expire_time)
        plt.legend()
        plt.show()

def Vega(F,K,r,T,vol):
    d1 = (np.log(F/K) + (0.5* vol**2)*T) / (vol * np.sqrt(T))
    vega = F * np.exp(-r*T) * norm.pdf(d1) * np.sqrt(T)
    return vega

    
if __name__=='__main__':
    excel = win32.DispatchEx('Excel.Application')
    #xllPath = "C:\\Users\\AXZQ\\Desktop\\QuantLibXL-v141-mt.xll"
    xllPath="C:\\Users\\AXZQ\\Desktop\\QuantLibXL-v141-mtVegaW.xll"
    res = excel.RegisterXLL(xllPath)
    print("load xll: " + str(res))
    
    for refday in refday_lst:
        end_date = refday
        path = "../data/" + etf_name + "/intraday/" + end_date.replace('-', '') + "/"
        if not os.path.exists( "../data/" + etf_name + "/intraday/" + end_date.replace('-', '') + "/"):
            os.makedirs( "../data/" + etf_name + "/intraday/" + end_date.replace('-', '') + "/")
        etf,options=load_tick_from_csv(underlying, path, end_date)
         
        
        
        #Date is the expire_date, under every now_date, we have several expire_date,we can have an array of expire dates 
        s=0
        proportion_sum=0
        rmse_smaller_sprd=0
        
        tick_lst=time_series(refday)
        
        
        for i in range(len(tick_lst)):
            
            op_obj=OptionPricing(etf, options, tick_lst[i], r, q, year)
            op_obj()
            
            
            
            
            if  not op_obj.OTM_option.empty:
                op_obj.OTM_option=op_obj.OTM_option.sort_values('strike')
                expiredate=op_obj.OTM_option['expire_date']
                expiredateobj=[datetime.strptime(i, "%Y-%m-%d") for i in expiredate]
                expire_lst=sorted(list(set(expiredateobj)))
                num_expiredate=len(expire_lst)
                #r
                crvFunc="CQL_Curve_InterpolatedYieldCurve_Create"
                dayCount="Actual/365 (Fixed)"
                crvName="NoColl"
                traitsId="ZeroYield"
                interpolator="BackwardFlat"
                obj_r=RunXll(excel, crvFunc, None, expire_lst, [r]*num_expiredate, datetime.strptime(refday, "%Y-%m-%d"), dayCount, ccy, crvName, traitsId, interpolator)
                #q
                ql=[]
                for e in expire_lst:  
                    ql.append(dividend_yield(etf.last_data(tick_lst[i])[0], r, op_obj.forward_lst[e.strftime("%Y-%m-%d")], (e.date()-datetime.strptime(refday, "%Y-%m-%d").date()).days/year))  
                
                crvName="Repo"
                interpolator="linearZT"
                interpolator_alter = "BackwardFlat"
                if len(ql)>1:
                    obj_q=  RunXll(excel, crvFunc, None, expire_lst, ql, datetime.strptime(refday,"%Y-%m-%d"), dayCount, ccy, crvName, traitsId, interpolator)
                elif len(ql)==1:
                    obj_q= RunXll(excel, crvFunc, None, expire_lst, ql, datetime.strptime(refday,"%Y-%m-%d"), dayCount, ccy, crvName, traitsId, interpolator_alter)
                    
                #vol
                volFunc="CQL_Volatility_EquityVolSurf_Create_WithOption"
                quotesType="Volatility"
                smoothMethod="SVI"
                checkDiscArb=False
                checkContArb=False
                    
                Date=expiredateobj
                Type=list(op_obj.OTM_option['call_put'])
                Strike=list(op_obj.OTM_option['strike'])
                IV=list(op_obj.OTM_option['iv'])
                Bid_IV=list(op_obj.OTM_option['bid_iv'])
                Ask_IV=list(op_obj.OTM_option['ask_iv'])
                obj_vol=RunXll(excel, volFunc, None , Date , Type , Strike , IV , underlying, quotesType,datetime.strptime(refday, "%Y-%m-%d"), etf.last_data(tick_lst[i])[0], obj_r, obj_q, smoothMethod, checkDiscArb, checkContArb)
                
                    
                #test how the model fits
                rmseFunc="CQL_Volatility_VolSurf_InterpolRMSE"
                interpolFunc="CQL_Volatility_VolSurf_Interpol"
                
                
               
                         
                for j in range(len(expire_lst)):
                    if len(expire_lst)==4:
                        s+=1
                        def vol_surf_interpol(row):
                            return RunXll(excel, interpolFunc, obj_vol, expire_lst[j], row['strike'])
                        
                        #before fit the surface, let's filter the data, select the rows of iv between 0.9 of median_iv to 1.1 of median_iv. 
                        df=op_obj.OTM_option[op_obj.OTM_option['expire_date']==expire_lst[j].strftime("%Y-%m-%d")]
                           
                           
                        vol_surf_interpol_smile=list(df.apply(vol_surf_interpol, axis=1))
                        Bid_IV_expire=df['bid_iv']
                        Ask_IV_expire=df['ask_iv']
                        Bid_Ask_sprd=np.median((Bid_IV_expire - Ask_IV_expire)/2)
                        proportion=sum(bid_vol<=volsurf_interpol<=ask_vol for bid_vol, volsurf_interpol, ask_vol in zip(Bid_IV_expire, vol_surf_interpol_smile, Ask_IV_expire))/len(Bid_IV_expire)
                        
                        plot(underlying, tick_lst[i],df,vol_surf_interpol_smile, expire_lst[j])
                       
                    
                        
                   
                        '''
                        proportion_sum+=proportion
                           
                        #print(f'With the expire date: {expire_lst[j].strftime("%Y-%m-%d")}, proportion of the vol surface between bid and ask is {proportion} at {tick_lst[i].strftime("%Y-%m-%d %H:%M:%S.%f")}')
                        
                        rmse=RunXll(excel, rmseFunc, obj_vol, j, None)
                        if rmse <= Bid_Ask_sprd:
                            rmse_smaller_sprd+=1
                       ''' 
                #print(f'proportion of the vol surface between bid and ask is {proportion_sum/s} at {tick_lst[i].strftime("%Y-%m-%d %H:%M:%S.%f")}') 
        print(f'On {refday},The proportion that the vol surface is between the bid and ask is {proportion_sum/s}')
        print(f'On {refday}, The proportion that rmse is smaller than bid_ask sprd is {rmse_smaller_sprd/s}')


         
                    
                        
                        
                
        
        
       
        
        
