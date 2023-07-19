from TickQuotation.tickquotation import TickQuotation
from TickQuotation.ETFOptionQuotation import ETFOptionTick
from datetime import datetime
from numpy import array, exp, min, max, where, isnan, nan, average, nanmedian
from enum import Enum
from matplotlib import pyplot as plt
from py_vollib.black import implied_volatility
from PricingEngine.pricingengine  import PricingEngine, PricingEngineError
import pandas as pd

class IVSyntheticMethod(Enum):
    MedianFwdVol = 1
    AtmFwdVol = 2
    PutCallMove = 3
    PutCallMeanMove = 4


class ImpliedVolatility:
    # constructor
    def __init__(self, r: float, q: float, year: float = 365):
        self.r_ = r
        self.q_ = q
        self.year_ = year
        self.underlying = ''
        self.month = ''
        self.expire = 0.0
        self.spot = 0.0
        self.spot_ask = 0.0
        self.spot_bid = 0.0
        self.fwd_ask = 0.0
        self.fwd_bid = 0.0
        self.fwd_theo = 0.0
        self.atm_index_strikes = 0.0
        self.strikes = array([])
        self.call_ask = array([])
        self.call_bid = array([])
        self.put_ask = array([])
        self.put_bid = array([])
        self.iv_call_ask = array([])
        self.iv_call_bid = array([])
        self.iv_put_ask = array([])
        self.iv_put_bid = array([])
        self.iv_ask = list()
        self.iv_bid = list()
        self.iv_ask1 = list()
        self.iv_bid1 = list()

    def get_iv_call_ask(self):
        return self.iv_call_ask

    def get_iv_call_bid(self):
        return self.iv_call_bid

    def get_iv_put_ask(self):
        return self.iv_put_ask

    def get_iv_put_bid(self):
        return self.iv_put_bid

    # solve the implied volatility
    def __call__(
            self, ETF: TickQuotation, option: ETFOptionTick, month: str, tick_time: datetime, method: IVSyntheticMethod
    ):
        self.month = month
        self.__read_quotation(ETF=ETF, option=option, tick_time=tick_time)
        self.__forward_price(method=method)
        self.__iv_black()
        self.__iv_synthetic(method=method)
        #self.strike, self.month, self.iv_ask, self.iv_bid to put it in a dataframe
        data={'strike':self.strikes, 'iv_ask':self.iv_ask, 'iv_bid': self.iv_bid}
        print(pd.DataFrame(data))

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

    # read the ETF and option quotation
    def __read_quotation(self, ETF: TickQuotation, option: ETFOptionTick, tick_time: datetime):
        # read the future quotation
        etf_d = ETF.last_data_frame(tick_time=tick_time)
        self.underlying = ETF.name
        self.spot = etf_d['last_price'][0]
        self.spot_ask = etf_d['ask'][0]
        self.spot_bid = etf_d['bid'][0]

        # read the option quotation
        option = option.last_data(tick_time=tick_time)
        #print(option.option_chain.__load_option_chain())
        self.expire = option.option_chain.expires_with_month(month=self.month)[0] / self.year_
        self.strikes = option.option_chain.strikes_with_month(month=self.month)
        self.strikes = array(self.strikes)
        call = option.get_smile_tick_by_month(month=self.month, option_type='认购')
        put = option.get_smile_tick_by_month(month=self.month, option_type='认沽')
        self.call_ask = array(call['ask'].tolist())
        self.call_bid = array(call['bid'].tolist())
        self.put_ask = array(put['ask'].tolist())
        self.put_bid = array(put['bid'].tolist())

    # solve the synthetic forward price
    def __forward_price(self, method: IVSyntheticMethod):
        if method == IVSyntheticMethod.MedianFwdVol:
            fwd_asks = exp(self.r_ * self.expire) * (self.call_ask - self.put_bid) + self.strikes
            fwd_bids = exp(self.r_ * self.expire) * (self.call_bid - self.put_ask) + self.strikes
            self.forward = nanmedian((fwd_asks + fwd_bids) / 2)
            index = where(self.strikes <= self.forward)


            if len(index[0])>=1:
                index = where(self.strikes == max(self.strikes[index]))
                self.atm_index_strikes = self.strikes[index][0]

        else:
            difference = (self.call_ask + self.call_bid) / 2 - (self.put_ask + self.put_bid) / 2
            # replace nan value with zero
            difference = where(isnan(difference) == True, 0, difference)
            spread = min(difference)
            index = where(difference == spread)
            self.forward = exp(self.r_ * self.expire) * spread + self.strikes[index][0]
            index = where(self.strikes <= self.forward)
            if index:
                index = where(self.strikes == max(self.strikes[index]))
                self.atm_index_strikes = self.strikes[index][0]


    def __iv_black(self):
        n = len(self.strikes)
        iv_call_ask = list()
        iv_call_bid = list()
        iv_put_ask = list()
        iv_put_bid = list()
        for i in range(0, n):
            k = self.strikes[i]
            # calculating the call implied volatility
            cpa = self.call_ask[i]
            cpb = self.call_bid[i]
            cia = nan
            cib = nan
            if isnan(cpa) or isnan(cpb):

                pass
            else:

                try:
                    cia = self.implied_vol(price=cpa, f=self.forward, k=k, t=self.expire, call_put='c')
                    cib = self.implied_vol(price=cpb, f=self.forward, k=k, t=self.expire, call_put='c')
                except PricingEngineError as e:
                    if e.state_ == PricingEngineError.State.NegativeVolatility:
                        pass
                    else:
                        raise e
            iv_call_ask.append(cia)
            iv_call_bid.append(cib)

            # calculating the call implied volatility
            ppa = self.put_ask[i]
            ppb = self.put_bid[i]
            pia = nan
            pib = nan
            if isnan(ppa) or isnan(ppb):
                pass
            else:
                try:
                    pia = self.implied_vol(price=ppa, f=self.forward, k=k, t=self.expire, call_put='p')
                    pib = self.implied_vol(price=ppb, f=self.forward, k=k, t=self.expire, call_put='p')
                except PricingEngineError as e:
                    if e.state_ == PricingEngineError.State.NegativeVolatility:
                        pass
                    else:
                        raise e
            iv_put_ask.append(pia)
            iv_put_bid.append(pib)
        self.iv_call_ask = array(iv_call_ask)
        self.iv_call_bid = array(iv_call_bid)
        self.iv_put_ask = array(iv_put_ask)
        self.iv_put_bid = array(iv_put_bid)

    def __iv_synthetic(self, method: IVSyntheticMethod):
        strikes = self.strikes
        n = len(strikes)
        if method == IVSyntheticMethod.MedianFwdVol:
            for i in range(0, n):
                k = strikes[i]
                if self.forward < k:
                    iva = self.iv_call_ask[i]
                    ivb = self.iv_call_bid[i]
                else:
                    iva = self.iv_put_ask[i]
                    ivb = self.iv_put_bid[i]
                self.iv_ask.append(iva)
                self.iv_bid.append(ivb)
            

    def plot(self, underlying: str, tick_time: datetime):
        t = tick_time.strftime("%Y-%m-%d %H:%M:%S")
        plt.plot(self.strikes, self.iv_call_ask, 'm.-.', color='red', label='call_ask')
        plt.plot(self.strikes, self.iv_call_bid, 'm.-.', color='green', label='call_bid')
        plt.plot(self.strikes, self.iv_put_ask, 'm.-.', color='yellow', label='put_ask')
        plt.plot(self.strikes, self.iv_put_bid, 'm.-.', color='blue', label='put_bid')
        plt.title(underlying + " iv at " + t)
        plt.legend()
        plt.show()
