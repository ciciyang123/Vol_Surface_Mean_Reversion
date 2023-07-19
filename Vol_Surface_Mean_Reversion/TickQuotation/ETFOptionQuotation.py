from TickQuotation.tickquotation import TickQuotation
from TickQuotation.ETFOptionChain import ETFOptionChain_
from pandas import DataFrame
from numpy import array, where
from datetime import datetime

Tick_String = ['last_price', 'ask', 'bid', 'ask_vol', 'bid_vol', 'volume', 'open_interest', 'tick']
class ETFOptionCurrentTick:
    def __init__(self, option_chain: ETFOptionChain_):  # underlying: array, strike: array, expire: array):
        self.option_chain = option_chain
        self.current_tick_str = ['expire_date','strike', 'expire', 'call_put']
        for ts in Tick_String:
            self.current_tick_str.append(ts)
        tick_frame = self.option_chain.strikes_expires()
        self.underlying = option_chain.underlying
        index = range(0, len(tick_frame))
        self.tick = DataFrame(index=index, columns=self.current_tick_str)
        for i in index:
            self.tick.iloc[i]['strike'] = tick_frame.iloc[i]['strike']
            self.tick.iloc[i]['expire'] = tick_frame.iloc[i]['expire']
            self.tick.iloc[i]['expire_date'] = tick_frame.iloc[i]['expire_date']
            self.tick.iloc[i]['call_put'] = tick_frame.iloc[i]['call_put']
        n = len(tick_frame)
        '''
        self.tick.loc[n, 'strike'] = -1
        self.tick.loc[n, 'expire'] = -1
        self.tick.loc[n, 'call_put'] = 'None'
        '''
        self.tick = self.tick.set_index(keys=['expire_date', 'strike', 'expire', 'call_put'])

    def size(self):
        return len(self.tick) - 1

    #
    # def get_tick_by_option(self, option: str):
    #     chain = self.option_chain.option_chain
    #     index = chain[chain['option_code'] == option].index
    #     expire = chain.loc[index, 'expiredate']
    #     strike = chain.loc[index, 'strike']

    def get_strike_by_month(self, month: str):
        return self.option_chain.strikes_with_month(month=month)

    def get_expire_by_month(self, month: str):
        return self.option_chain.expires_with_month(month=month)[0]

    def get_smile_tick_by_month(self, month: str, option_type: str):
        expire = self.get_expire_by_month(month=month)
        x = self.tick.xs(expire, level='expire')
        x = x.xs(option_type, level='call_put')
        return x

    def set_value(self, expire_date, strike, expire, option_type, tick):
        self.tick.loc[(expire_date, strike, expire, option_type)] = tick


class ETFOptionTick:
    def __init__(self, underlying: str, end_date: str):
        self.option_chain = ETFOptionChain_(
            underlying=underlying,
            end_date=end_date
        )
        self.option_tick = list()
        chain = self.option_chain
        self.current_tick = ETFOptionCurrentTick(option_chain=chain)

    def __chain_size(self) -> int:
        return self.option_chain.size()



    def last_data(self, tick_time: datetime):
        for i in range(0, self.__chain_size()):
            strike = self.option_chain.loc_strike(index=i)
            expire = self.option_chain.loc_expire(index=i)
            expire_date=self.option_chain.loc_expire_date(index=i)
            tick = self.option_tick[i].last_data(tick_time=tick_time)
            option_type = self.option_chain.loc_type(index=i)
            self.current_tick.set_value(expire_date=expire_date, strike=strike, expire=expire, tick=tick, option_type=option_type)
        return self.current_tick

    #                   #
    #    persistence    #
    #                   #
    def to_tick_csv(self, path: str):
        for option_tick in self.option_tick:
            option_tick.to_tick_csv(path=path)

    def read_tick_csv(self, path: str):
        self.option_tick.clear()
        options = self.option_chain.options()
        for option in options:
            option_tick = TickQuotation(name=str(option))
            option_tick.read_tick_csv(path=path)
            self.option_tick.append(option_tick)
