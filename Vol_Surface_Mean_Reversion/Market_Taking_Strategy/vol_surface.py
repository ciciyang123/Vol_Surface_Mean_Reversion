# -*- coding: utf-8 -*-
"""
This file builds a class related to theo_vol: it takes the option from optionpricing.py as input and builds obj_vol and outputs
creates df of a particular smile at a tick time
"""

from math import log    
import win32com.client as win32
import pandas as pd
import numpy as np
from datetime import datetime,date
from TickQuotation.tickquotation import TickQuotation
from TickQuotation.ETFOptionQuotation import ETFOptionTick
from PricingEngine.optionpricing import OptionPricing
from excel.xllfunc import RunXll
from TickQuotation.timeseries import time_series
from scipy.stats import norm
'''
This class will allow us fit smile by expire_date and generate df with theo_iv and iv_diff%
we need etf, option_fit_with_expire
'''


class Theo_Option:
    def __init__(self, excel, etf, underlying, option_fit, tick_time:datetime, r, q, year, expiry_index, refday, ccy):
        
        self.excel = excel 
        self.underlying = underlying
        expiry = option_fit.expire_date_lst[expiry_index] #this is string time date type
        option_fit_with_expire = option_fit.OTM_option[option_fit.OTM_option['expire_date']==expiry]
        expiredate = option_fit_with_expire['expire_date']
        self.expiredate = [datetime.strptime(i, "%Y-%m-%d") for i in expiredate]
        self.fitting_option = option_fit_with_expire.sort_values('strike')  #This is the option used for fitting the smile
        self.expiry = [datetime.strptime(expiry, "%Y-%m-%d")]
        self.forward = option_fit.forward_lst[self.expiry[0].strftime("%Y-%m-%d")]
        self.year = year
        self.ccy = ccy
        self.r = r
        self.refday = refday
        self. etf = etf
        self.tick_time = tick_time
        
        self.obj_r = None
        self.r_curve()
        self.obj_q =None
        self.q_curve()
        self.obj_vol = None
        self.vol_object()


    def r_curve(self):
        #r
        crvFunc="CQL_Curve_InterpolatedYieldCurve_Create"
        dayCount="Actual/365 (Fixed)"
        crvName="NoColl"
        traitsId="ZeroYield"
        interpolator="BackwardFlat"
        self.obj_r=RunXll(self.excel, crvFunc, None, self.expiry, [self.r], datetime.strptime(self.refday, "%Y-%m-%d"), dayCount, self.ccy, crvName, traitsId, interpolator)
        
        
    
    def q_curve(self):
        def dividend_yield(S, r, F, T):
            return r- log(F/S)/T 
        #q
        ql=[]
        for e in self.expiry:  
            ql.append(dividend_yield(self.etf.last_data(self.tick_time)[0], self.r, self.forward, (e.date()-datetime.strptime(self.refday, "%Y-%m-%d").date()).days/self.year))  
        crvFunc="CQL_Curve_InterpolatedYieldCurve_Create"
        crvName="Repo"
        interpolator="linearZT"
        interpolator_alter = "BackwardFlat"
        dayCount="Actual/365 (Fixed)"
        traitsId="ZeroYield"
        
        if len(ql)>1:
            self.obj_q =  RunXll(self.excel, crvFunc, None, self.expiry, ql, datetime.strptime(self.refday,"%Y-%m-%d"), dayCount, self.ccy, crvName, traitsId, interpolator)
        elif len(ql)==1:
            self.obj_q= RunXll(self. excel, crvFunc, None, self.expiry, ql, datetime.strptime(self.refday,"%Y-%m-%d"), dayCount, self.ccy, crvName, traitsId, interpolator_alter)
        
        
        
        
    def vol_object(self):
        #vol
        volFunc="CQL_Volatility_EquityVolSurf_Create_WithOption"
        quotesType="Volatility"
        smoothMethod="SVI"
        checkDiscArb=False
        checkContArb=False
            
        
        Type=list(self.fitting_option['call_put'])
        Strike=list(self.fitting_option['strike'])
        IV=list(self.fitting_option['iv'])
        self.obj_vol=RunXll(self.excel, volFunc, None , self.expiredate , Type , Strike , IV , self.underlying, quotesType,datetime.strptime(self.refday, "%Y-%m-%d"), self.etf.last_data(self.tick_time)[0], self.obj_r, self.obj_q, smoothMethod, checkDiscArb, checkContArb)
        
        
    def vol_surf_interpol(self, option_to_fit):
        #option_to_fit has to be the dataframe of options with the same expiry
        interpolFunc="CQL_Volatility_VolSurf_Interpol"
                
        def vol_surf_interpol(row):
            return RunXll(self.excel, interpolFunc, self.obj_vol, self.expiry[0], row['strike'])       
         
        
        vol_surf_interpol_smile=list(option_to_fit.apply(vol_surf_interpol, axis=1)) 
        option_to_fit.loc[:, 'iv_theo'] = vol_surf_interpol_smile
        option_to_fit.loc[:, 'iv_diff%'] = (option_to_fit['iv']-option_to_fit['iv_theo'])/ option_to_fit['iv_theo']
        option_to_fit.loc[:, 'bid_iv_diff%'] = (option_to_fit['bid_iv'] - option_to_fit['iv_theo'])/ option_to_fit['iv_theo'] #find the max
        option_to_fit.loc[:, 'ask_iv_diff%'] = (option_to_fit['ask_iv'] - option_to_fit['iv_theo'])/ option_to_fit['iv_theo'] #find the min
        return option_to_fit           
                
                        
                        
                        
        
        
        
        
        
        
        
        
        
            
        
        
            
        
        
        
        

