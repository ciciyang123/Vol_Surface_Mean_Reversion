'''
This file prepares option data ready for model input, including filter the OTM options, adding the iv, and clean the data finallly
'''
import pandas as pd
import py_lets_be_rational.exceptions

from TickQuotation.tickquotation import TickQuotation
from TickQuotation.ETFOptionQuotation import ETFOptionTick
from datetime import datetime
from numpy import array, exp, min, max, where, isnan, nan, average, nanmedian,median
from enum import Enum
from py_vollib.black import implied_volatility
from TickQuotation.timeseries import time_series
from PricingEngine.pricingengine import PricingEngineError


class OptionPricing:
    def __init__(self, etf:TickQuotation, option_tick:ETFOptionTick, tick_time, r, q, year, atm_strike):
        self.ETF=etf
        self.options=option_tick
        self.r=r
        self.q=q
        self.year=year
        self.tick_time=tick_time
        etf_d =  self.ETF.last_data_frame(tick_time=self.tick_time)
        self.spot = etf_d['last_price'][0]
        #initiate self.options using tick time
        self.options.last_data(tick_time)


        self.OTM_option=pd.DataFrame()
        self.merged=pd.DataFrame()
        self.forward_lst={} #for every expire_date, we have a forward

        #reset the index of the self.options, add quote, and modify the name of option_type
        option_df=self.options.current_tick.tick.reset_index()
        option_df['call_put'] = option_df['call_put'].map({'认购': 'Call', '认沽': 'Put'})
        option_df['quote'] = (option_df['bid'] + option_df['ask']) / 2
        self.option_dataframe=option_df

        #remove the options with nan value, this is the option we will use later
        self.option=self.option_dataframe.dropna().reset_index(drop=True)
        self.expire_date_lst=sorted(list(set(list(self.option['expire_date']))))
        
        
        
        self.atm_index_strike = atm_strike
        self.atm_call_ask =0
        self.atm_call_bid = 0
        self.atm_put_ask = 0
        self.atm_put_bid = 0
        self.synthetic_forward_dict= {}

    def __call__(self):
        #assign the forward price to self.forward
        self.forward_price()
        #assign the OTM_option to self.OTM_option
        self.atm_strikes() #feed the synthetic_forward_dict
        self.OTM()
        #add the iv columns to self.OTM_option
        self.OTM_IV()
        
        self.data_cleaning()
        

     # calculate the Black Scholes implied volatility
    def implied_vol(self, price: float, f: float, k: float, t: float, call_put: str) -> float:
        
        try:
            vol = implied_volatility.implied_volatility_of_discounted_option_price(
                discounted_option_price=price, F=f, K=k, r=self.r_, t=t, flag=call_put)
        except:
            return nan
        if vol < 0:
            raise PricingEngineError(
                state=PricingEngineError.State.NegativeVolatility
            )
        return vol

    def forward_price(self):
        for date in self.expire_date_lst:
            #calculate the forward for each expire_date, we first need call_ask-put_bid, call_bid-put_ask
            options_filtered=self.option[self.option['expire_date']==date]
            days_to_mature=options_filtered['expire'].iloc[0]
            calls=options_filtered[options_filtered['call_put']=='Call']
            puts=options_filtered[options_filtered['call_put']=='Put']

            # Rename the columns
            calls = calls.rename(columns={'bid': 'call_bid', 'ask': 'call_ask'})
            puts = puts.rename(columns={'bid': 'put_bid', 'ask': 'put_ask'})

            self.merged=pd.merge(calls, puts, on='strike')

            #calculate the call_ask-put_bid and call_bid-put_ask
            self.merged['call_ask_minus_put_bid']=self.merged['call_ask']-self.merged['put_bid']
            self.merged['call_bid_minus_put_ask']=self.merged['call_bid']-self.merged['put_ask']

            self.merged=self.merged.dropna().reset_index(drop=True)
            if not self.merged.empty:

                fwd_asks=exp(self.r*days_to_mature/self.year)*(self.merged['call_ask_minus_put_bid'])+self.merged['strike']
                fwd_bids=exp(self.r*days_to_mature/self.year)*(self.merged['call_bid_minus_put_ask'])+self.merged['strike']
                forward = median((fwd_asks.to_numpy() + fwd_bids.to_numpy()) / 2)
                self.forward_lst[date]=forward
    
    def atm_strikes(self):
        if len(self.expire_date_lst) == len(self.forward_lst):
            for date in self.forward_lst:
                df = self.option[self.option['expire_date']==date]
                df=df.reset_index()
                
                if (not self.atm_index_strike):
                    index = where(df['strike'] <= self.forward_lst[date])[0]
                    if len(index)>=1:
                        indexx = where(df['strike']== max(df['strike'][index]))
                        self.atm_index_strike = df['strike'].iloc[indexx[0][0]]
                df1 = df[(df['strike']==self.atm_index_strike) & (df['call_put']=='Call')]
                df2 = df[(df['strike']==self.atm_index_strike) & (df['call_put']=='Put')]
                
                if self.atm_index_strike and (not df1.empty) and (not df2.empty):
                    
                    self.atm_call_ask = df1['ask'].iloc[0]
                    self.atm_put_bid = df2['bid'].iloc[0]
                    self.atm_call_bid = df1['bid'].iloc[0]
                    self.atm_put_ask = df2['ask'].iloc[0]
                    self.synthetic_forward_dict[date] = [self.atm_call_ask-self.atm_put_bid, self.atm_call_bid - self.atm_put_ask] #long, short
                        
    def assign_atm_strikes(self):
        if not self.atm_index_strike:
            return self.atm_index_strike
        return 0

    def OTM(self):
        def is_otm(row):
            expire_date = row['expire_date']
            forward_price = self.forward_lst[expire_date]
            if row['call_put'] == 'Call':
                return row['strike'] > forward_price
            else:
                return row['strike'] < forward_price
        if (not self.option.empty) and (len(self.expire_date_lst)==len(self.forward_lst)):
            self.OTM_option= self.option[self.option.apply(is_otm, axis=1)]
            self.OTM_option= self.OTM_option.reset_index(drop=True)
    
    def OTM_spot(self):
        def is_otm_spot(row):
            if row['call_put']=='Call':
                return row['strike']>self.spot
            else:
                return row['strike']<self.spot
        if (not self.option.empty) and (len(self.expire_date_lst)==len(self.forward_lst)):
            self.OTM_option= self.option[self.option.apply(is_otm_spot, axis=1)]
            self.OTM_option= self.OTM_option.reset_index(drop=True)
        
        

    def OTM_IV(self):
        def compute_iv(row):
            try:
                price = row['quote']
                option_type = row['option_type']
                strike = row['strike']
                forward = self.forward_lst[row['expire_date']]
                time_to_maturity = row['expire'] / self.year

                return implied_volatility.implied_volatility_of_discounted_option_price(
            price, forward, strike, self.r, time_to_maturity, option_type)
            except:
                return nan
           
        def compute_iv_bid(row):
            try:
                price = row['bid']
                option_type = row['option_type']
                strike = row['strike']
                forward = self.forward_lst[row['expire_date']]
                time_to_maturity = row['expire'] / self.year

                return implied_volatility.implied_volatility_of_discounted_option_price(
            price, forward, strike, self.r, time_to_maturity, option_type)
            except:
                return nan
        def compute_iv_ask(row):
            try:
                price = row['ask']
                option_type = row['option_type']
                strike = row['strike']
                forward = self.forward_lst[row['expire_date']]
                time_to_maturity = row['expire'] / self.year

                return implied_volatility.implied_volatility_of_discounted_option_price(
            price, forward, strike, self.r, time_to_maturity, option_type)
            except:
                return nan
            
            
        if not self.OTM_option.empty:
            self.OTM_option.loc[:, 'option_type'] = self.OTM_option['call_put'].map({'Call': 'c', 'Put': 'p'})



            self.OTM_option['iv']=self.OTM_option.apply(compute_iv, axis=1)
            self.OTM_option['bid_iv']=self.OTM_option.apply(compute_iv_bid, axis=1)
            self.OTM_option['ask_iv']=self.OTM_option.apply(compute_iv_ask, axis=1)
            self.OTM_option=self.OTM_option.dropna().reset_index(drop=True)
        
    def call_spread_arbitrage_free(self):
        if not self.OTM_option.empty:
            self.OTM_option.sort_values(['expire_date', 'strike'], inplace=True)

            while True:
                # Group the options dataframe by 'expire_date'
                groups = self.OTM_option.groupby('expire_date')

                # Flag to check if all groups satisfy the relationship
                all_groups_satisfy = True

                # Iterate over each group
                for _, group in groups:
                    # Get the option types within the group
                    option_types = group['call_put'].unique()

                    # Flag to check if the group satisfies the relationship
                    group_satisfies = True

                    # Check the relationship for each option type within the group
                    for option_type in option_types:
                        # Get the subset of rows for the current option type
                        option_type_rows = group[group['call_put'] == option_type]

                        # Get the price values and strike values for the option type
                        prices = option_type_rows['quote'].values
                       

                        # Check the relationship between price and strike within the option type
                        if option_type == 'Call':
                            mask = prices[1:] < prices[:-1]  # Compare consecutive prices for calls
                        else:
                            mask = prices[1:] > prices[:-1]  # Compare consecutive prices for puts

                        # Check if all rows within the option type satisfy the relationship
                        option_type_satisfies = all(mask)

                        if not option_type_satisfies:
                            group_satisfies = False

                            # Find the indices of rows that violate the relationship within the option type
                            violation_indices = option_type_rows.index[1:][~mask]

                            # Delete the rows that violate the relationship within the option type
                            self.OTM_option.drop(violation_indices, inplace=True)

                    if not group_satisfies:
                        all_groups_satisfy = False

                # Check if all groups satisfy the relationship
                if all_groups_satisfy:
                    break
    def delete_options_under_expiry(self):
        for expiry in self.expire_date_lst:
            options_under_expire_date=self.OTM_option[self.OTM_option['expire_date']==expiry]
            num_options=len(options_under_expire_date)
            median_num_options=self.OTM_option.groupby('expire_date').size().median()
            
            if num_options<0.2*median_num_options:
                self.OTM_option=self.OTM_option[self.OTM_option['expire_date']!=expiry]
    
    def data_cleaning(self):
        if not self.OTM_option.empty:
            #step1: delete the options with expire less than 1 day
            self.OTM_option=self.OTM_option[self.OTM_option['expire']>1]
            #step2: delete the options with 0 quote
            self.OTM_option=self.OTM_option[self.OTM_option['quote']>0.0001]
            #step3: delete the options with 0 volume，but the market is so illquid...
            
            #step4:dispose the options whose Bid1=Ask1
            self.OTM_option=self.OTM_option[self.OTM_option['bid']!=self.OTM_option['ask']]
            
            #Filtered until this step, we can use this OTM_option dataframe to arbitrage
            self.option = self.OTM_option
            #step5: dispose the options whose Bid1 and Ask1 differ more than 1%
            diff = (self.OTM_option['ask']-self.OTM_option['bid'])
            self.OTM_option = self.OTM_option[diff < 0.0025]
            #if the triggering points bid ask sprd is too wide
            
            
            
            
            #step6: delete the call spread arbitrage points
            #for each expire_date, for calls, strike and price should have a negative relationship; for puts, strike and price should have a positive relationship
            self.call_spread_arbitrage_free()
            
            #step7： for every expire_date, calculate the #num of options, if some expire date whose #num of option is less than 20% of the median, then delete all the options under the expire date
            self.delete_options_under_expiry()
            
            #step8: delete the options with iv less than 50% of the median iv or more than twice of the median iv
            median_iv=self.OTM_option['iv'].median()
            self.OTM_option=self.OTM_option[(self.OTM_option['iv']<=2*median_iv) & (self.OTM_option['iv']>=0.5*median_iv)]
            
                
                
            self.expire_date_lst=sorted(list(set(list(self.OTM_option['expire_date']))))
   