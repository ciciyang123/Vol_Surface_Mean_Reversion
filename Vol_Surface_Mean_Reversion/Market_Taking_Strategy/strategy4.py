# -*- coding: utf-8 -*-
"""
This file is strategy implementation. 
"""
import sys
libPath="C:\\Users\\AXZQ\\Desktop\\VolTick"
if libPath not in sys.path:
    sys.path.append(libPath)  
import pandas as pd
import numpy as np
from numpy import exp
from datetime import datetime,date, timedelta
from TickQuotation.tickquotation import TickQuotation
from TickQuotation.ETFOptionQuotation import ETFOptionTick
from PricingEngine.optionpricing import OptionPricing
from TickQuotation.timeseries import time_series
from Market_Taking_Strategy.vol_surface import Theo_Option
from scipy.stats import norm
from Market_Taking_Strategy.Post_Strategy_Analysis import *


class Strategy4:
    def __init__(self, excel, underlying, etf, options, timeseries, r, q, year, expiry_index, refday, ccy, latest_unwind_time, stop_loss_time):
        '''
        Here we have our postion, which is a list: [option_low, option_high]
        '''
        self.excel = excel
        self.ccy = ccy
        self.refday = refday
        self.underlying = underlying
        self.expiry_index = expiry_index
        self.r =r
        self.q =q
        self.year = year
        self.etf = etf
        self.options =options
        self.timeseries = timeseries
        self.latest_unwind_time = latest_unwind_time
        self.stop_loss_time = stop_loss_time
        self.strikes = []
        
        self.tick_data = pd.DataFrame()
        self.bid_larger_than_surf = pd.DataFrame()
        self.ask_smaller_than_surf = pd.DataFrame()
        self.forward = None
        self.position = []
        self.stop_loss = 0
        self.position_taking_time = datetime(1900,1,1,0,0,0)
        
        self.delta_theo_vol = pd.Series()
        self.bid_theo_vol = pd.Series()
        self.ask_theo_vol = pd.Series()
        self.pre_tick_data = pd.DataFrame()
        self.bgn_bid_theo_vol = pd.Series()
        self.bgn_ask_theo_vol = pd.Series()
        self.delta_sprd_vol_low = pd.Series()
        self.delta_sprd_vol_high = pd.Series()
        
        self.bgn_ba_sprd = pd.Series()
        self.ba_sprd = pd.Series()
        
        
        
        self.S = 0
        self.pre_S = 0
        self.delta_S = 0
        #etf_d =  self.ETF.last_data_frame(tick_time=self.tick_time)
        #self.spot = etf_d['last_price'][0]
        
        self.size_high = 0
        self.size_low = 0
        self.size_forward = 0
        self.position_bgn = 0
        self.position_end = 0
        self.investment = 0
        self.position_before_unwind = 0
        
        self.PnL_before_unwind_lst = []
        self.time_lst = []
        self.position_taking_points = []
        self.position_time_lst=[]
        self.position_unwind_points = []
        self.unwind_time_lst = []
        
        self.total_pnl = 0
        self.cum_pnl =0
        self.total_return = 0
        self.delta_pnl_lst = []
        self.vega_pnl_lst = []
        self.vega_sprd_lst = []
        self.synthetic_forward = [] #two element, long and short
        #self.pre_synthetic_forward_price = 0
        self.atm_strike = 0
        
        
    def tick_data_generate(self, i):
        #given an index i, I can get the option dataframe with iv_theo. 
        op_obj=OptionPricing(self.etf, self.options, self.timeseries[i], self.r, self.q, self.year, self.atm_strike)
        op_obj()
        if (not self.atm_strike):
            self.atm_strike = op_obj.assign_atm_strikes()
        
        if (not op_obj.OTM_option.empty) and (len(op_obj.expire_date_lst)==4) and (len(op_obj.synthetic_forward_dict)==4):
            expire_date = op_obj.expire_date_lst[self.expiry_index] #expire_date is a time string "%Y-%m-%d"
            
            self.synthetic_forward = op_obj.synthetic_forward_dict[expire_date]
            op_theo = Theo_Option(self.excel, self.etf, self.underlying, op_obj, self.timeseries[i], self.r, self.q, self.year, self.expiry_index, self.refday, self.ccy)
            self.tick_data = op_theo.vol_surf_interpol(op_obj.option[op_obj.option['expire_date']==expire_date])
            self.tick_data.reset_index(inplace=True)
            self.bid_larger_than_surf = self.tick_data[self.tick_data['bid_iv'] > self.tick_data['iv_theo']]
            self.ask_smaller_than_surf = self.tick_data[self.tick_data['ask_iv'] < self.tick_data['iv_theo']]
            self.forward = op_theo.forward
            self.strikes = sorted(set(self.tick_data['strike'].tolist()))
        
        else:
            self.tick_data = pd.DataFrame()
    
    def vol_operation(self):
        #we need self.delta_theo_vol, self.bid_theo_vol, self.ask_theo_vol, self.pre_bid_theo_vol, self.pre_ask_theo_vol
        self.bid_theo_vol = self.tick_data['bid_iv'] - self.tick_data['iv_theo']
        self.ask_theo_vol = self.tick_data['ask_iv'] - self.tick_data['iv_theo']
        
        if self.pre_tick_data.empty:
            self.bgn_bid_theo_vol = self.tick_data['bid_iv'] - self.tick_data['iv_theo']
            self.bgn_ask_theo_vol = self.tick_data['ask_iv'] - self.tick_data['iv_theo']
            self.bgn_ba_sprd = self.tick_data['ask_iv'] - self.tick_data['bid_iv']
            self.tick_data['bid_theo_vol'] = self.bid_theo_vol
            self.tick_data['ask_theo_vol'] = self.ask_theo_vol
        if (not self.pre_tick_data.empty):
            self.delta_sprd_vol_low = self.bid_theo_vol - self.bgn_ask_theo_vol
            self.delta_sprd_vol_high = self.ask_theo_vol - self.bgn_bid_theo_vol
            self.delta_theo_vol = self.tick_data['iv_theo'] - self.pre_tick_data['iv_theo']
            self.tick_data['delta_theo_vol'] = self.delta_theo_vol
            self.tick_data['delta_sprd_vol_low'] = self.delta_sprd_vol_low  #delta sprd vol is from beginning
            self.tick_data['delta_sprd_vol_high']  = self.delta_sprd_vol_high #delta sprd vol is from beginning
            self.ba_sprd = self.tick_data['ask_iv'] - self.tick_data['bid_iv']
            self.tick_data['delta_bid_vol'] = self.bid_theo_vol - self.bgn_bid_theo_vol
            self.tick_data['basprd'] = self.ba_sprd
            self.tick_data['bgn_basprd'] = self.bgn_ba_sprd
        
    def process_tick(self, freq, num):
        #time_str = '14:55:00'
        datetime_str = self.refday + ' '+ self.latest_unwind_time
        dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        #load time series, each tick we generate a df
        for i in range(len(self.timeseries)):
            if not i%freq:
                #it controls out loop freq
                
                
                self.tick_data_generate(i) #it modifies tick_data
                
                
                if not self.tick_data.empty:
                    self.pre_S = self.S
                    self.vol_operation()
                    if not self.position:
                        #we then see if it hits the trading signal
                        self.check_trading_signal()
                        if self.position:
                            self.position_taking_time = self.timeseries[i]
                            #it means we triggered the signal and we have positions rn
                            #self.vol_operation() #assign values to self.bgn_bid_theo_vol and self.bgn_ask_theo_vol
                            if len(self.options_exposure()) == 2:
                                self.S = self.etf.last_data(self.timeseries[i])[0]
                                self.PnL_before_unwind_lst.append(self.PnL_before_unwind() + self.total_pnl)
                                self.time_lst.append(self.timeseries[i])
                                self.position_taking_points.append(self.PnL_before_unwind() + self.total_pnl)
                                self.position_time_lst.append(self.timeseries[i])
                                self.delta_pnl_lst.append(self.Delta_PnL())
                                self.vega_pnl_lst.append(self.Vega_PnL())
                                
                                
                                #plot Pnl_drawdown
                                #plot Vol_surface
                                #plot Position
                                
                                total_plot(self.PnL_before_unwind_lst, self.time_lst, self.position_taking_points, self.position_time_lst, self.position_unwind_points, self.unwind_time_lst,
                                           self.tick_data, self.options_exposure(), True, False, False,
                                           self.strikes, self.size_low, self.size_high, self.timeseries[i], self.underlying, self.delta_pnl_lst, self.vega_pnl_lst, self.vega_sprd_lst)
                                self.pre_tick_data = self.tick_data
                                
                        
                        if (not self.total_return) and self.timeseries[i] >= dt:
                            print(f'No trade happens today at {self.timeseries[i]} :(')
                            break
                        elif (self.total_return) and self.timeseries[i]>=dt:
                            print(f'Congrats! Your total pnl is {self.total_pnl} and total return is {self.total_return}')
                            #plot here
                            '''
                            total_plot(self.PnL_before_unwind_lst, self.time_lst, self.position_taking_points, self.position_time_lst, self.position_unwind_points, self.unwind_time_lst,
                                       self.tick_data, self.options_exposure(), False, False, True,
                                       self.strikes, self.size_low, self.size_high, self.timeseries[i], self.underlying, self.delta_pnl_lst, self.vega_pnl_lst, self.vega_sprd_lst)
                            '''
                            #Pnl_Drawdown(self.PnL_before_unwind_lst, self.time_lst, self.position_taking_points, self.position_time_lst, self.position_unwind_points, self.unwind_time_lst)
                            
                            break
                    #since we already have positions, that means we already hedged, but since forward will change as tick_time
                    #C-P will have different strikes, we will short our previous positions and long new positions and dynamically hedging
                    
                      
                    elif self.timeseries[i] >= dt:
                        self.S = self.etf.last_data(self.timeseries[i])[0]
                        if self.pre_S:
                            self.delta_S = self.S - self.pre_S
                        
                        
                        
                        self.cum_pnl = self.PnL_before_unwind() + self.total_pnl
                        self.PnL_before_unwind_lst.append(self.cum_pnl)
                        self.time_lst.append(self.timeseries[i])
                        self.delta_pnl_lst.append(self.Delta_PnL())
                        self.vega_pnl_lst.append(self.Vega_PnL())
                        
                        #can add vega_sprd_lst here
                        total_plot(self.PnL_before_unwind_lst, self.time_lst, self.position_taking_points, self.position_time_lst, self.position_unwind_points, self.unwind_time_lst,
                                   self.tick_data, self.options_exposure(), False, True, True,
                                   self.strikes, self.size_low, self.size_high, self.timeseries[i], self.underlying, self.delta_pnl_lst, self.vega_pnl_lst, self.vega_sprd_lst)
                        
                        self.unwind() #means we are at the end of today or suddenly we do not have enough liquidity. using the pricing data of self.pre_tick_data to unwind
                        print(f'At the end of today: {self.timeseries[i]}, The PnL is {self.total_pnl} and return is {self.total_return}')
                        
                        
                        break
                        
                    
                    
                    else:
                        if len(self.options_exposure())==2:
                            self.S = self.etf.last_data(self.timeseries[i])[0]
                            if self.pre_S:
                                self.delta_S = self.S - self.pre_S
                            
                            #we have exposure, so we see if we need to unwind
                            #1': we unwind because of stop loss
                            if self.check_stop_loss(self.timeseries[i]):
                                self.unwind_time_lst.append(self.timeseries[i])
                                self.position_unwind_points.append(self.total_pnl + self.PnL_before_unwind())
                                
                                self.PnL_before_unwind_lst.append(self.total_pnl + self.PnL_before_unwind()) #whether it's time to unwind or not can use self.PnL_before_unwind() to calculate the cumulative pnl
                                self.time_lst.append(self.timeseries[i])
                                self.delta_pnl_lst.append(self.Delta_PnL())
                                self.vega_pnl_lst.append(self.Vega_PnL())
                                total_plot(self.PnL_before_unwind_lst, self.time_lst, self.position_taking_points, self.position_time_lst, self.position_unwind_points, self.unwind_time_lst,
                                      self.tick_data, self.options_exposure(), False, True, True,
                                      self.strikes, self.size_low, self.size_high, self.timeseries[i], self.underlying,self.delta_pnl_lst, self.vega_pnl_lst, self.vega_sprd_lst)
                                self.unwind()
                                print(f'Sorry, the strategy does not work. The total PnL is {self.total_pnl}. The return is {self.total_return}')
                                
                                #break
                                continue
                            #2': we unwind because of the mean reversion
                            unwind_signal_or_not = self.check_unwind_signal()  #it will modify total_pnl and empty positions
                            if unwind_signal_or_not:
                                self.cum_pnl = self.total_pnl + self.PnL_before_unwind()
                                self.unwind_time_lst.append(self.timeseries[i])
                                self.position_unwind_points.append(self.cum_pnl)
                                #print(f'Total PnL at {self.timeseries[i]} is {self.total_pnl} and return is {self.total_return}')
                            else:
                                self.cum_pnl = self.PnL_before_unwind() + self.total_pnl
                                print(f'Unwind signal has not been triggered. The PnL in the process at {self.timeseries[i]} is {self.cum_pnl} and return is {self.cum_pnl /abs(self.investment)} ')
                            self.PnL_before_unwind_lst.append(self.cum_pnl) #whether it's time to unwind or not can use self.PnL_before_unwind() to calculate the cumulative pnl
                            self.time_lst.append(self.timeseries[i])
                            self.delta_pnl_lst.append(self.Delta_PnL())
                            self.vega_pnl_lst.append(self.Vega_PnL())
                            
                            if unwind_signal_or_not:
                                
                                total_plot(self.PnL_before_unwind_lst, self.time_lst, self.position_taking_points, self.position_time_lst, self.position_unwind_points, self.unwind_time_lst,
                                      self.tick_data, self.options_exposure(), False, True, True,
                                      self.strikes, self.size_low, self.size_high, self.timeseries[i], self.underlying,self.delta_pnl_lst, self.vega_pnl_lst, self.vega_sprd_lst)
                                
                                self.unwind()
                                print(f'Total PnL at {self.timeseries[i]} is {self.total_pnl} and return is {self.total_return}')
                            else:
                                
                                
                                total_plot(self.PnL_before_unwind_lst, self.time_lst, self.position_taking_points, self.position_time_lst, self.position_unwind_points, self.unwind_time_lst,
                                   self.tick_data, self.options_exposure(), True, False, False,
                                   self.strikes, self.size_low, self.size_high, self.timeseries[i], self.underlying,self.delta_pnl_lst, self.vega_pnl_lst, self.vega_sprd_lst)
                                self.pre_tick_data = self.tick_data
                            #plot pnl_drawdown here
                            #plot vol_surface here
                            #plot position
                            
                
                
                
                
    def check_trading_signal(self):
        #check if it hits the trading sigal
        #it will modify self.position
        
        #trading signal design: we have bid larger than the surf and ask smaller than the surf and the options should be close enough in terms of strikes
        if (not self.bid_larger_than_surf.empty) and (not self.ask_smaller_than_surf.empty):
            
            
            
            option_high = self.tick_data[self.tick_data['bid_iv_diff%']==max(self.tick_data['bid_iv_diff%'])] #choose an option deviates positive the most
            option_low = self.tick_data[self.tick_data['ask_iv_diff%']==min(self.tick_data['ask_iv_diff%'])] #choose an option deviates negative the most
            
            #we will check if at this bid and ask iv, if we can make money
            profit_check_high = option_high['bid_theo_vol'].iloc[0] - (option_high['ask_iv'].iloc[0] - option_high['bid_iv'].iloc[0]) > 0 
            profit_check_low = - option_low['ask_theo_vol'].iloc[0] - (option_low['ask_iv'].iloc[0] - option_low['bid_iv'].iloc[0]) > 0 
            
            if profit_check_high and profit_check_low:
                if abs(option_high['strike'].iloc[0] - option_low['strike'].iloc[0]) <= 0.05:
                
                
                    print("Good News! We hit the signal")
                    self.size_low = 10000 #one contract is 10000 unit options
                    
                    self.size_high = - self.vega(option_low) / self.vega(option_high) * self.size_low
                    
                    self.size_forward = - (self.delta(option_low) * self.size_low + self.delta(option_high) * self.size_high)
                    if self.size_forward>0:
                        synthetic_forward_price = self.synthetic_forward[0]
                    else:
                        synthetic_forward_price = self.synthetic_forward[1]
                    
                    self.position.append(option_low)
                    self.position.append(option_high)
                    
                    
                    self.position_bgn = self.size_low * option_low['ask'].iloc[0] + self.size_high * option_high['bid'].iloc[0] + self.size_forward * synthetic_forward_price
                    self.investment += self.position_bgn
                    
                    
                
       
    
    def unwind(self):
        #calculate the position_end and pnl and empty the positions
        option_low_price = self.options_exposure()[0]['bid'].iloc[0]
        option_high_price = self.options_exposure()[1]['ask'].iloc[0]
        synthetic_forward_price = self.synthetic_forward[0] if self.size_forward >0 else self.synthetic_forward[1]
        
        self.position_end = option_low_price * self.size_low + self.size_forward * synthetic_forward_price + \
        option_high_price * self.size_high
        self.total_pnl += self.position_end - self.position_bgn
        self.total_return = self.total_pnl / abs(self.investment)
        self.vega_sprd_lst.append(self.Vega_PnL()[1])
        #empty position
        self.position_bgn = 0
        self.position_end = 0
        self.position_before_unwind = 0
        self.pre_S = 0
        self.S = 0
       
        
        #empty forward, position, iv_spread, stop_loss
        self.forward = None
        self.position = []
        self.stop_loss = 0
        
        #empty all size
        self.size_high = 0
        self.size_low = 0
        self.size_forward = 0
        
        self.pre_tick_data = pd.DataFrame()
        
        
                   
    def Delta_PnL(self):
        #total delta_pnl = delta_S * (delta_low * size_low + delta_high * size_high + delta_forward * size_forward
        #we need to have position
        #delta_pnl is from the pnl between ticks, not cumulative pnl
        if (self.delta_S) and self.position:
            type_low = self.tick_data['call_put']== self.position[0]['call_put'].iloc[0]
            strike_low = self.tick_data['strike'] == self.position[0]['strike'].iloc[0]
            option_low_hold = self.tick_data[type_low & strike_low]
        
            type_high = self.tick_data['call_put']== self.position[1]['call_put'].iloc[0]
            strike_high = self.tick_data['strike'] == self.position[1]['strike'].iloc[0]
            option_high_hold = self.tick_data[type_high & strike_high]
            
            return self.delta(option_low_hold) * self.delta_S * self.size_low + self.delta(option_high_hold) * self.delta_S * self.size_high + 1 * self.size_forward * self.delta_S
        else:
            return 0
            
    def Vega_PnL(self):
        if self.position and ('delta_theo_vol' in self.tick_data.columns):
            type_low = self.tick_data['call_put']== self.position[0]['call_put'].iloc[0]
            strike_low = self.tick_data['strike'] == self.position[0]['strike'].iloc[0]
            option_low_hold = self.tick_data[type_low & strike_low]
        
            type_high = self.tick_data['call_put']== self.position[1]['call_put'].iloc[0]
            strike_high = self.tick_data['strike'] == self.position[1]['strike'].iloc[0]
            option_high_hold = self.tick_data[type_high & strike_high]
            
            delta_theo_vol_low = option_low_hold['delta_theo_vol'].iloc[0]
            delta_theo_vol_high = option_high_hold['delta_theo_vol'].iloc[0]
            delta_sprd_vol_low = option_low_hold['delta_sprd_vol_low'].iloc[0]
            delta_sprd_vol_high = option_high_hold['delta_sprd_vol_high'].iloc[0]
            
            vega_smile_pnl = self.vega(option_low_hold) * delta_theo_vol_low * self.size_low + self.vega(option_high_hold) * delta_theo_vol_high * self.size_high
            #vega_sprd_pnl is cumulative pnl
            vega_sprd_pnl =  self.vega(option_low_hold) * delta_sprd_vol_low * self.size_low + self.vega(option_high_hold) * delta_sprd_vol_high * self.size_high
            '''
            delta_vol_high = option_high_hold['delta_vol_high'].iloc[0]
            if (not delta_vol_low):
                delta_vol_low = 0
            if (not delta_vol_high):
                delta_vol_high = 0
            '''
            print(f'vega_low : {self.vega(option_low_hold)}, delta_theo_vol_low : {delta_theo_vol_low}, delta_sprd_vol_low: {delta_sprd_vol_low} '
                  f'\n vega_high: {self.vega(option_high_hold)}, delta_theo_vol_high : {delta_theo_vol_high}, delta_sprd_vol_high: {delta_sprd_vol_high} ')
            return [vega_smile_pnl, vega_sprd_pnl]
        
        else:
            return [0,0]
            
            
        
        
        
    def check_unwind_signal(self):
        option_low_hold = self.options_exposure()[0]
        option_high_hold = self.options_exposure()[1]
        #check if it hits the unwinding signal. Both ask_iv and bid_iv should go back to above and below the surface
        low_ask_above_surf = option_low_hold['ask_iv'].iloc[0] > self.options_exposure()[0]['iv_theo'].iloc[0]
        high_bid_below_surf = option_high_hold['bid_iv'].iloc[0] < self.options_exposure()[1]['iv_theo'].iloc[0]
        
       
        sprd_cross_check_low = option_low_hold['delta_bid_vol'].iloc[0] - option_low_hold['bgn_basprd'].iloc[0] > 0 
        sprd_cross_check_high = - option_high_hold['delta_bid_vol'].iloc[0] - option_high_hold['basprd'].iloc[0] > 0
         
       
            
        #if not ((not self.bid_larger_than_surf.empty) and (not self.ask_smaller_than_surf.empty)):
        if low_ask_above_surf and high_bid_below_surf and sprd_cross_check_low and sprd_cross_check_high:
            print("Good news! Mean Reversion Achieved!")
            #self.unwind()
            return True
            
        return False
        
        
        
    def vega(self, option_df):
        #option_df includes all info of an option in a one-row option_df
        F = self.forward
        K = option_df['strike'].iloc[0]
        vol = option_df['iv'].iloc[0]
        T = option_df['expire'].iloc[0]/self.year
        d1 = (np.log(F/K) + (0.5* vol**2)*T) / (vol * np.sqrt(T))
        return F * np.exp(-self.r*T) * norm.pdf(d1) * np.sqrt(T)
        
        
        
        
        
    def delta(self, option_df):
        option_type = option_df['call_put'].iloc[0]
        F = self.forward
        K = option_df['strike'].iloc[0]
        vol = option_df['iv'].iloc[0]
        T = option_df['expire'].iloc[0]/self.year
        d1 = (np.log(F/K) + (0.5* vol**2)*T) / (vol * np.sqrt(T))
        if option_type == 'Call':
            return norm.cdf(d1)
        else:
            return norm.cdf(d1) -1
        
    
    
    def options_exposure(self):
        # return a list of holding option_df(two elements)
        type_low = self.tick_data['call_put']== self.position[0]['call_put'].iloc[0]
        strike_low = self.tick_data['strike'] == self.position[0]['strike'].iloc[0]
        option_low_hold = self.tick_data[type_low & strike_low]
        
        type_high = self.tick_data['call_put']== self.position[1]['call_put'].iloc[0]
        strike_high = self.tick_data['strike'] == self.position[1]['strike'].iloc[0]
        option_high_hold = self.tick_data[type_high & strike_high]
        
        if (not option_low_hold.empty) and (not option_high_hold.empty):
            return [option_low_hold, option_high_hold]
        elif (not option_low_hold.empty):
            return [option_low_hold]
        elif (not option_high_hold.empty):
            return [option_high_hold]
        else:
            return []
    
    def PnL_before_unwind(self):
        option_low_price = self.options_exposure()[0]['bid'].iloc[0]
        option_high_price = self.options_exposure()[1]['ask'].iloc[0]
        synthetic_forward_price = self.synthetic_forward[1] if self.size_forward >0 else self.synthetic_forward[0]
        self.position_before_unwind = option_low_price * self.size_low + synthetic_forward_price * self.size_forward + \
        option_high_price * self.size_high
        print(f'position_before_unwind now is {self.position_before_unwind} and position_bgn: {self.position_bgn} '
              f'{option_low_price * self.size_low}, {option_high_price * self.size_high}, {synthetic_forward_price * self.size_forward} '
              f'synthetic_forward_bid : {self.synthetic_forward[0]} and ask: {self.synthetic_forward[1]}')
        return self.position_before_unwind - self.position_bgn
        
    
    
    def check_stop_loss(self, tick_time):
        dt1 = datetime.strptime(self.refday + ' '+ '11:30:00', '%Y-%m-%d %H:%M:%S')
        dt2 = datetime.strptime(self.refday + ' ' + '13:00:00', '%Y-%m-%d %H:%M:%S')
        if self.position_taking_time <= dt1 and tick_time >= dt2:
            if (tick_time - self.position_taking_time) > timedelta(minutes = self.stop_loss_time + 90):
                return True
            
        elif  tick_time - self.position_taking_time > timedelta(minutes=self.stop_loss_time):
            #self.unwind()
            #print(f'Sorry, the strategy does not work. The total PnL is {self.total_pnl}. The return is {self.total_return}')
            return True
        return False
        
    
    
            
    
        
            
        
        
        
        
        
        
        
            
            
            
        