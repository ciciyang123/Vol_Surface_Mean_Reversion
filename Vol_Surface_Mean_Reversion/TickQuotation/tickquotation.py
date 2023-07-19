from numpy import array, nan
from enum import Enum
from datetime import datetime,timedelta
from pandas import DataFrame, read_csv
from abc import abstractmethod


Tick_String = ['last_price', 'ask', 'bid', 'ask_vol', 'bid_vol', 'volume', 'open_interest', 'tick']


class QEState(Enum):
    NullData = -1
    LoadQuotationError = -2
    LoadHistoryFileNull = -3
    NoAsset = -4


class QuotationException(Exception):
    def __init__(self, state: QEState):
        self.state = state

class TickQuotation:
    

    def __init__(self, name):
        # tick detail
        self.quotation_str = "last,ask1,asize1,bid1,bsize1,oi,volume"
        self.tick_str = Tick_String
        self.csv_str = ['last', 'ask1', 'asize1', 'bid1', 'bsize1', 'oi', 'volume']
        self.name = name
        # tick time
        self.tick = list()
        self.null_tick_time = datetime.strptime('1900-01-01 00:00:00', "%Y-%m-%d %H:%M:%S")
        self.current_tick = -1
        # tick empty_data
        self.last_price = self.ask_price = self.ask_volume = self.bid_price = \
            self.bid_volume = self.open_interest = self.volume = list()
    '''
    def load_tick(self, begin: str, end: str):
        wd = w.wst(self.name, self.quotation_str, begin, end, "")
        if wd.ErrorCode != 0:
            raise QuotationException(QEState.LoadQuotationError)
        self.tick = array(wd.Times)
        if self.size() > 0:
            self.current_tick = 0
            empty_data = wd.Data
            self.last_price = array(empty_data[0])
            self.ask_price = array(empty_data[1])
            self.ask_volume = array(empty_data[2])
            self.bid_price = array(empty_data[3])
            self.bid_volume = array(empty_data[4])
            self.open_interest = array(empty_data[5])
            self.volume = array(empty_data[6])
    '''

    #                   #
    #   tick operation  #
    #                   #
    def size(self) -> int:
        return len(self.tick)

    def null(self) -> bool:
        if self.size() <= 0:
            return True
        else:
            return False

    def end(self) -> bool:
        if self.null():
            return True
        if self.current_tick < self.size():
            return False
        else:
            return True

    def current_tick_time(self):
        return self.current_tick

    def next_tick(self)->int:
        if self.null() is True:
            raise QuotationException(QEState.NullData)
        i = self.current_tick
        if self.end() is False:
            self.current_tick += 1
        return i

    def last_tick(self, tick_time: datetime):
        if self.size() <= 0:
            return -1
        if self.tick[0] - tick_time > timedelta(milliseconds=0):
            return -1
        if self.size()-1 == self.current_tick:
            return self.current_tick
        for i in range(self.current_tick, self.size()-1):
            if self.tick[i] - tick_time <= timedelta(milliseconds=0) and self.tick[i+1]-tick_time>timedelta(milliseconds=0):
                self.current_tick = i
                return i
        self.current_tick = self.size()-1
        return self.current_tick

    #                   #
    #   empty_data operation  #
    #                   #
    def append(self, tick: datetime, last_price: float, ask: float, bid: float,
               ask_vol: float, bid_vol: float, volume: float, oi: float):
        # ['last_price', 'ask', 'bid', 'ask_vol', 'bid_vol', 'volume', 'open_interest', 'tick']
        self.current_tick = 0
        self.tick.append(tick)
        self.last_price.append(last_price)
        self.ask_price.append(ask)
        self.bid_price.append(bid)
        self.ask_volume.append(ask_vol)
        self.bid_volume.append(bid_vol)
        self.volume.append(volume)
        self.open_interest.append(oi)

    def next_data(self):
        i = self.next_tick()
        t = self.tick[i]
        price = self.last_price[i]
        volume = self.volume[i]
        ask = self.ask_price[i]
        ask_vol = self.ask_volume[i]
        bid = self.bid_price[i]
        bid_vol = self.bid_volume[i]
        oi = self.open_interest[i]
        return price, ask, bid, ask_vol, bid_vol, volume, oi, t

    def last_data(self, tick_time: datetime):
        i = self.last_tick(tick_time=tick_time)
        if i == -1:
            t = self.null_tick_time
            price = volume = ask = ask_vol = bid = bid_vol = oi = nan
        else:
            t = self.tick[i]
            price = self.last_price[i]
            volume = self.volume[i]
            ask = self.ask_price[i]
            ask_vol = self.ask_volume[i]
            bid = self.bid_price[i]
            bid_vol = self.bid_volume[i]
            oi = self.open_interest[i]
        return price, ask, bid, ask_vol, bid_vol, volume, oi, t

    def last_data_frame(self, tick_time: datetime):
        d = self.last_data(tick_time=tick_time)
        data = DataFrame(index=range(0, 1), columns=self.tick_str)
        data[self.tick_str[0]] = d[0]
        data[self.tick_str[1]] = d[1]
        data[self.tick_str[2]] = d[2]
        data[self.tick_str[3]] = d[3]
        data[self.tick_str[4]] = d[4]
        data[self.tick_str[5]] = d[5]
        data[self.tick_str[6]] = d[6]
        data[self.tick_str[7]] = d[7]
        return data

    #                   #
    #    persistence    #
    #                   #
    def clear(self):
        self.current_tick = -1
        self.last_price = array([])
        self.ask_price = array([])
        self.ask_volume = array([])
        self.bid_price = array([])
        self.bid_volume = array([])
        self.open_interest = array([])
        self.volume = array([])

    def to_tick_csv(self, path: str):
        df = DataFrame(index=self.tick, columns=self.csv_str)
        df['last'] = self.last_price
        df['ask1'] = self.ask_price
        df['asize1'] = self.ask_volume
        df['bid1'] = self.bid_price
        df['bsize1'] = self.bid_volume
        df['oi'] = self.open_interest
        df['volume'] = self.volume
        filename = path + self.name + ".csv"
        df.to_csv(filename)

    def read_tick_csv(self, path: str):
        self.clear()
        filename = path + self.name + ".csv"
        df = read_csv(filename, index_col=0, header=0)
        #if you use new data
        df.sort_index(inplace=True)
        df['oi'] = 0
        
        self.tick = list()
        for t in df.index.values:
            self.tick.append(datetime.strptime(t, "%Y-%m-%d %H:%M:%S.%f"))
        self.tick = array(self.tick)
        self.last_price = array(df['last'].tolist())
        self.ask_price = array(df['ask1'].tolist())
        self.ask_volume = array(df['asize1'].tolist())
        self.bid_price = array(df['bid1'].tolist())
        self.bid_volume = array(df['bsize1'].tolist())
        self.open_interest = array(df['oi'].tolist())
        self.volume = array(df['volume'].tolist())
        if len(self.tick) > 0:
            self.current_tick = 0
        else:
            raise QuotationException(state=QEState.LoadHistoryFileNull)

    #                       #
    #    abstract method    #
    #                       #
    @abstractmethod
    def synthetic_tick_update(self, tick: array):
        pass
