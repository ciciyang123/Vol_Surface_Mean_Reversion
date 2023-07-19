#from WindPy import *
from pandas import DataFrame
from numpy import unique, array
from datetime import datetime
from pandas import read_csv, concat
from pandas import to_datetime
#import pandas_market_calendars as mcal


class ETFOptionChain_:

    def __init__(self, underlying: str, end_date: str):
        # load underlying contract code
        self.end_date = end_date
        self.underlying = underlying
        # load option chain information
        #self.calendar = list()
        # self.__load_calendar()

        self.chain_str = ['us_code', 'option_code', 'strike_price', 'expiredate', 'call_put']
        self.option_chain = DataFrame(columns=self.chain_str)
        self.quotation_str = "last,ask1,asize1,bid1,bsize1,oi,volume"
        self.__load_option_chain()
        self.option_tick = list()

    # w.start()
    # def __load_option_chain(self):
    #     #for underlying in self.underlying:
    #     s = "date=" + self.end_date + ";us_code=" + self.underlying + ";option_var=全部;call_put=全部"
    #     option_data = w.wset("optionchain", s)
    #     option_data = DataFrame(option_data.Data, index=option_data.Fields, columns=option_data.Codes).T
    #     option_data = option_data[self.chain_str]
    #     self.option_chain = self.option_chain.append(option_data, ignore_index=True)

    #__load_option_chain is to read the static_file of option and load it to self.option_chain(dataframe)
    def __load_option_chain(self):
        option_class_dict = {'510050': '50ETF', '159919': '300ETF_SZ',
                             '510300': '300ETF_SH', '159922': '500ETF'}
        # end_date = '2020-10-12'
        # underlying = '510050.SH'
        path = path = "../data/" + option_class_dict[self.underlying] + "/static_file/" + self.end_date.replace('-', '') + ".csv"

        option_data = read_csv(path, index_col=0)
        option_data = option_data.drop_duplicates()
        option_data.columns = ["option_code", "strike_price", "first_tradedate", "last_tradedate", "ex_info_code",
                               "option_name", "multiplier", "call_put"]
        option_data["call_put"] = option_data["call_put"].map({'C': '认购', 'P': '认沽'})
        option_data['first_tradedate'] = option_data['first_tradedate'].apply(
            lambda x: to_datetime(str(x)).strftime("%Y-%m-%d"))
        option_data['last_tradedate'] = option_data['last_tradedate'].apply(
            lambda x: to_datetime(str(x)).strftime("%Y-%m-%d"))
        option_data['month'] = option_data['ex_info_code'].apply(lambda x: x[7:11])
        #print(option_data['month'])
        #option_data['expiredate'] = option_data.apply(lambda row: self.calendar.index(row['last_tradedate']) -
                                                                  #self.calendar.index(self.end_date), axis=1)
        tmp=datetime.strptime(self.end_date, "%Y-%m-%d").date()
        option_data['expiredate']=array([(datetime.strptime(time_string, "%Y-%m-%d").date()-tmp).days for time_string in option_data['last_tradedate']])
        option_data['us_code'] = self.underlying
        option_data = option_data.sort_values(['call_put', 'strike_price'], ascending=[False, True])
        self.option_chain = concat([self.option_chain, option_data], ignore_index=True)

    '''
    def __load_calendar(self):
        current_year = int(self.end_date[0:4])
        sse = mcal.get_calendar('SSE')
        bgn_date = '2015-02-09'
        en_date = str(current_year + 1) + '-12-31'
        self.calendar = sse.valid_days(bgn_date, en_date).strftime('%Y-%m-%d').to_list()
    '''

    def size(self):
        return len(self.option_chain)

    def loc_strike(self, index: int):
        return self.option_chain.iloc[index]['strike_price']

    def loc_expire_date(self, index: int):
        return self.option_chain.iloc[index]['last_tradedate']
    def loc_expire(self, index: int):
        return self.option_chain.iloc[index]['expiredate']

    def loc_option(self, index: int):
        return self.option_chain.iloc[index]['option_code']

    def loc_type(self, index: int):
        return self.option_chain.iloc[index]['call_put']

    def strikes_expires(self):
        data = self.option_chain[['last_tradedate', 'expiredate', 'strike_price', 'call_put']]
        data = DataFrame(data=data)
        data = data.rename(columns={'last_tradedate': 'expire_date', 'expiredate': 'expire', 'strike_price': 'strike', 'call_put': 'call_put'})
        return data

    def strikes(self):
        return unique(self.option_chain['strike_price'])

    def expires(self):
        return unique(self.option_chain['expiredate'])

    def options(self):
        return self.option_chain['option_code']

    def strikes_with_month(self, month: str):
        strikes = self.option_chain[self.option_chain['month'] == month]['strike_price']
        strikes = unique(strikes.tolist())
        return strikes

    def expires_with_month(self, month: str):
        expires = self.option_chain[self.option_chain['month'] == month]['expiredate']
        expires = unique(expires)
        return expires

    def reserve(self, month: array):
        for m in month:
            x = self.option_chain
            self.option_chain = x.drop(x[x['month'] != m].index)
        self.option_chain = DataFrame(self.option_chain.reset_index(drop=True), index=range(len(self.option_chain)))

    def option_code(self, strike: float, expire: float, option_type: str):
        x = self.option_chain
        x = x[x['strike_price'] == strike]
        x = x[x['expiredate'] == expire]
        x = x[x['call_put'] == option_type]
        return x['option_code']
