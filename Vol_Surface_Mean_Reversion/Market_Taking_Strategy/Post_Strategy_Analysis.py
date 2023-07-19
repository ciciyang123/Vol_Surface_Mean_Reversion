# -*- coding: utf-8 -*-
"""
Created on Thu Jun 29 11:21:46 2023

@author: AXZQ
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter
import numpy as np


def Pnl_Drawdown(pnl_ax, pnl_lst, timeseries, position_lst, position_time_lst, unwind_lst, unwind_time_lst, tick_time, underlying):
    
    # Identify pullback points and pullback numbers
    drawdown_time = []
    drawdown_numbers = []
    max_value = pnl_lst[0]
    
    for i in range(1, len(pnl_lst)):
        if pnl_lst[i] < max_value:
            drawdown_time.append(timeseries[i])
            drawdown_numbers.append(max_value - pnl_lst[i])
        else:
            max_value = pnl_lst[i]
    
    # Create histogram-like pullback plot
    dd_ax = pnl_ax.twinx()
    pnl_ax.plot(timeseries, pnl_lst, label='Cumulative PnL', color='blue')
    #Plot markers for the position points
    pnl_ax.scatter(position_time_lst, position_lst, marker='^', s=80, color = 'green', label = 'Position')
    #plot markers for the unwind points
    pnl_ax.scatter(unwind_time_lst, unwind_lst, marker = 'v', s=80, color='red', label='unwind')
    
    dd_ax.vlines(drawdown_time, 0, drawdown_numbers, colors='yellow', linestyles='solid', label = 'Pullback')
    pnl_ax.grid()
    pnl_ax.legend(loc = 'upper left')
    dd_ax.legend(loc = 'upper right')
    pnl_ax.set_xlabel('Time')
    pnl_ax.set_ylabel('Cumulative PnL')
    dd_ax.set_ylabel('Drawdown')
    pnl_ax.set_title(f'{tick_time.strftime("%Y-%m-%d %H:%M:%S")} {underlying} PnL and Drawdown Analysis')
    
    
    
    pnl_ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
   

def Vol_Surface_plot(vol_ax, options_df, options_exposure, position_or_not, just_unwind_or_not):
    #this options_df should only have one expiry and strikes in ascending order
    #options_df = self.tick_data
    options_df = options_df.sort_values('strike')
    strikes = options_df['strike']
    bid_vol = options_df['bid_iv']
    ask_vol = options_df['ask_iv']
    svi_vol = options_df['iv_theo']
    vol_ax.plot(strikes, svi_vol, 'm.-', label = 'theo_iv')
    vol_ax.plot(strikes, bid_vol, '.', color = 'green', label = 'bid_vol')
    vol_ax.plot(strikes, ask_vol, '.', color= 'blue', label = 'ask_vol')
    if position_or_not:
        #if we have position this time tick, we need to emphasize the position holding options
        vol_ax.scatter([options_exposure[0]['strike'].iloc[0], options_exposure[1]['strike'].iloc[0]], [options_exposure[0]['ask_iv'].iloc[0], options_exposure[1]['bid_iv'].iloc[0]], marker = 'o', s=80, color = 'red', label = 'Position')
    elif just_unwind_or_not:
        #do this before unwind
        vol_ax.scatter([options_exposure[0]['strike'].iloc[0], options_exposure[1]['strike'].iloc[0]], [options_exposure[0]['ask_iv'].iloc[0], options_exposure[1]['bid_iv'].iloc[0]], marker = 'o', s=80, color = 'black', label = 'Unwind')
    vol_ax.grid()
    vol_ax.set_xlabel('Strike')
    vol_ax.legend(loc = 'upper center')
    vol_ax.set_title('vol surface')
    

def Position_plot(position_ax, strikes, options_exposure, low_size, high_size):
    #strikes should be sorted and unique list of strikes
    #by default, we have positions; if at the time we do not have positions, then the function will not be implemented
    bar_width = 0.3
    long_call_pos  = [0] * len(strikes)
    short_call_pos  = [0] * len(strikes)
    long_put_pos  = [0] * len(strikes)
    short_put_pos  = [0] * len(strikes)
    ba_sprd_lst = [0] * len(strikes)
    
    low_call_or_not = options_exposure[0][options_exposure[0]['call_put'] == 'Call'] #df
    high_call_or_not = options_exposure[1][options_exposure[1]['call_put'] == 'Call'] #df
    
    strike_low =  options_exposure[0]['strike'].iloc[0]
    strike_high = options_exposure[1]['strike'].iloc[0]
    ba_sprd_low = options_exposure[0]['ask'].iloc[0] - options_exposure[0]['bid'].iloc[0]
    ba_sprd_high = options_exposure[1]['ask'].iloc[0] - options_exposure[1]['bid'].iloc[0]
    
    
    if (not low_call_or_not.empty) and low_size>0:
        #long call
        long_call_pos[strikes.index(strike_low)] = low_size
        
    elif (low_call_or_not.empty) and low_size>0:
        #long put
        long_put_pos[strikes.index(strike_low)] = low_size
    ba_sprd_lst[strikes.index(strike_low)] = ba_sprd_low
    
    if (not high_call_or_not.empty) and high_size<0:
        #short call
        short_call_pos[strikes.index(strike_high)] = high_size
    elif (high_call_or_not.empty) and high_size<0:
        #short put
        short_put_pos[strikes.index(strike_high)] = high_size
    
    ba_sprd_lst[strikes.index(strike_high)] = ba_sprd_high
    
   
    
    
    # Create the bar chart using call_strikes and put_strikes as x-axis positions
    indices = np.arange(len(strikes))
    position_ax.bar(indices, height=long_call_pos, width=bar_width, label='long call')
    position_ax.bar(indices, height=short_call_pos, width=bar_width, label='short call')
    position_ax.bar(indices + bar_width, height=long_put_pos, width=bar_width, label='long put')
    position_ax.bar(indices + bar_width, height=short_put_pos, width=bar_width, label='short put')
    
    
    position_ax.legend()
    position_ax.set_xticks(indices + bar_width/2)
    position_ax.set_xticklabels([f'{round(x_strike, 2)}\n {"%.2g" % label}' for x_strike, label in zip(strikes, ba_sprd_lst)])
    
    position_ax.grid()
    position_ax.set_title('Greeks PnL will be here')



    
'''  
def total_plot(pnl_lst, timeseries, position_lst, position_time_lst, unwind_lst, unwind_time_lst,
               options_df, options_exposure, position_or_not, just_unwind_or_not, unwind_or_not,
               strikes, low_size, high_size, tick_time, underlying):
    plt.figure(figsize = (10, 8))
    layout = (3,1)
    
    #First Plot: Cumulative PnL and drawdown
    pnl_ax = plt.subplot2grid(layout, (0,0))
    Pnl_Drawdown(pnl_ax, pnl_lst, timeseries, position_lst, position_time_lst, unwind_lst, unwind_time_lst, tick_time, underlying)
    
    #Second Plot: Vol Surface
    vol_ax = plt.subplot2grid(layout, (1,0))
    
    Vol_Surface_plot(vol_ax, options_df, options_exposure, position_or_not, just_unwind_or_not)
    
    #Third Plot: Position
    position_ax = plt.subplot2grid(layout, (2,0))
    if (not unwind_or_not):
        Position_plot(position_ax, strikes, options_exposure, low_size, high_size)
        
    plt.tight_layout()
    plt.draw()
    plt.pause(0.01)
    
''' 
   
def total_plot(pnl_lst, timeseries, position_lst, position_time_lst, unwind_lst, unwind_time_lst,
               options_df, options_exposure, position_or_not, just_unwind_or_not, unwind_or_not,
               strikes, low_size, high_size, tick_time, underlying, delta_pnl, vega_pnl, vega_sprd_lst):
    
    cum_delta_pnl = sum(delta_pnl)
    cum_vega_smile_pnl = sum(sub_vega_pnl[0] for sub_vega_pnl in vega_pnl)
    cum_vega_sprd_pnl = vega_pnl[-1][1] + sum(vega_sprd_lst)
    other_pnl = pnl_lst[-1] - cum_delta_pnl - cum_vega_smile_pnl - cum_vega_sprd_pnl
    
    plt.figure(figsize = (10, 8))
    layout = (3,1)
    
    #First Plot: Cumulative PnL and drawdown
    pnl_ax = plt.subplot2grid(layout, (0,0))
    Pnl_Drawdown(pnl_ax, pnl_lst, timeseries, position_lst, position_time_lst, unwind_lst, unwind_time_lst, tick_time, underlying)
    
    #Second Plot: Vol Surface
    vol_ax = plt.subplot2grid(layout, (1,0))
    
    Vol_Surface_plot(vol_ax, options_df, options_exposure, position_or_not, just_unwind_or_not)
    
    #Third Plot: Position
    position_ax = plt.subplot2grid(layout, (2,0))
    if (not unwind_or_not):
        Position_plot(position_ax, strikes, options_exposure, low_size, high_size)
    else:
        Position_plot(position_ax, strikes, options_exposure, 0, 0)
    
    position_ax.set_title(f'Cum_Delta_PnL: {round(cum_delta_pnl, 2)}  '
                          f'Cum_Vega_Smile_PnL: {round(cum_vega_smile_pnl, 2)} '
                          f'Cum_Vega_Sprd_PnL: {round(cum_vega_sprd_pnl, 2)} '
                          f'Others_PnL: {round(other_pnl, 2)} '
                          f'\n Delta_pnL : {round(delta_pnl[-1], 2)} '
                          f'Vega_Smile_pnL: {round(vega_pnl[-1][0] , 2)} ')
    plt.tight_layout()
    plt.draw()
    #Save the plot to an image file
    plt.savefig('Plot.png')
    plt.pause(0.01)
    
   
    
    
    
    
    
    
    