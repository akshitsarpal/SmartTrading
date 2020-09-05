import pandas as pd
import numpy as np
import os
from string import digits
import datetime as dt
from alpha_vantage.timeseries import TimeSeries
from multiprocessing import Pool, cpu_count
import logging
from constants import *

# os.environ["ALPHAVANTAGE_API_KEY"] = "MY_API_KEY"

def remove_digits(input_str):
    remove_digits = str.maketrans('', '', digits)
    res = input_str.translate(remove_digits)
    return res


class Stock(object):
    '''
    Extracts tickers for given indices, and extracts intraday or daily stock prices.
    '''
    def __init__(self, tickers_list=[],stock_index=None,
                 price_type=None, ts=None, after_hours=False, 
                 start_date=None):
        self.tickers_df = None
        self.tickers_list = tickers_list
        self.stock_index = stock_index
        self.price_type = price_type
        self.ts = ts
        self.prices_df = None
        self.after_hours = after_hours
        self.start_date = start_date
        
    def _remove_digits(self, input_str):
        remove_digits = str.maketrans('', '', digits)
        res = input_str.translate(remove_digits)
        return res
        
    def get_tickers_index(self):
        '''
        Get the list of all stocks in a given index.
        TODO: Change this to a regular ETL that saves any changes to file system
              and read from there for stability.
        '''
        if not self.stock_index:
            self.stock_index = 'SP500'
            logger.warning('"stock_index" not specified, using default of "SP500".')
            
        if self.stock_index == 'SP500':
            logger.info('Getting stock tickers for SP500 from Wiki .....')
            payload = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', header=0)
            self.tickers_df = payload[0]
            if len(self.tickers_df.index) >= 450:
                self.tickers_df = self.tickers_df.head(2) #TODO: remove this
                self.tickers_ds = self.tickers_df.rename({'Symbol':'Ticker'}, axis=1)
                self.tickers_list = list(self.tickers_df['Symbol'])
            else:
                ValueError('Check wikipedia data source for SP 500 at \
                             https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
            logger.info('Fetched stock tickers from SP500.')
            
        elif self.stock_index == 'NASDAQ':
            logger.info('Getting stock tickers for NASDAQ from Wiki .....')
            payload = pd.read_html('https://en.wikipedia.org/wiki/NASDAQ-100#Components', header=0)
            self.tickers_df = payload[3]
            if len(self.tickers_df.index) >= 90:
                self.tickers_df = self.tickers_df.head(2) #TODO: remove this
                self.tickers_list = list(self.tickers_df['Ticker'])
            else:
                ValueError('Check wikipedia data source for NASDAQ at \
                             https://en.wikipedia.org/wiki/NASDAQ-100#Components')
            logger.info('Fetched stock tickers from NASDAQ.')
            
        else:
            e = str('stock_index value '+ self.stock_index + ' not defined')
            raise ValueError(e)
        

    def get_list_stock_prices(self):
        '''
        Fetch stock price for list of tickers.
        '''
        if not self.tickers_list:
            raise KeyError('tickers_list not provided, either pass as argument or \
                call get_tickers_index() method with index name to fetch tickers.')
        self.pool = Pool(cpu_count()-1)
        prices_df_list = self.pool.map_async(self.get_individual_stock_price, self.tickers_list).get()
        self.prices_df = pd.concat(prices_df_list)
        
    
    def get_individual_stock_price(self, stock_ticker):
        '''
        Fetch stock price using the Alphavantage API. 
        '''
        if self.price_type == 'intraday':
            if not self.start_date:
                self.start_date = pd.Timestamp(dt.date.today()-dt.timedelta(days=default_days_intra))
                logger.info('''
                {ticker}: "start_date" not specified, using default of {dy}
                (business) days, with start date of {dt}.
                '''.format(ticker=stock_ticker, dy=default_days_intra, 
                           dt=self.start_date.isoformat()))
            elif isinstance(self.start_date, pd.Timestamp):
                logger.info('''{ticker}: Using previously defined "start_date" of {dt}.
                               '''.format(ticker=stock_ticker, dt=self.start_date))
            else:
                self.start_date = pd.Timestamp(self.start_date)
            price, meta_data = self.ts.get_intraday(stock_ticker, outputsize='full')
            price_df = pd.DataFrame(price).transpose()
            price_df.index = pd.to_datetime(price_df.index)
            price_df = price_df[price_df.index >= self.start_date]
            if not self.after_hours:
                logger.info('''{ticker}: Truncating pre-market and after-hours data.
                            '''.format(ticker=stock_ticker))
                price_df = price_df[(price_df.index.time>=dt.time(9,30)) & 
                                    (price_df.index.time<=dt.time(16,0))]
            price_df.columns = [self._remove_digits(col) for col in price_df.columns]
            price_df.columns = [col.replace('. ', '') for col in price_df.columns]
            price_df['ticker'] = stock_ticker
            price_df = price_df.reset_index().rename({'index':'ts'}, axis=1) \
                .set_index(['ticker', 'ts'])
            return price_df
        
        elif self.price_type == 'daily':
            if not self.start_date:
                self.start_date = pd.Timestamp(dt.date.today()-dt.timedelta(days=default_days_daily))
                logger.info('''
                {ticker}: "start_date" not specified, using default of {dy}
                (business) days, with start date of {dt}.
                '''.format(ticker=stock_ticker, dy=default_days_daily,
                           dt=self.start_date.isoformat()))
            elif isinstance(self.start_date, pd.Timestamp):
                logger.info('''{ticker}: Using previously defined "start_date" of {dt}.
                               '''.format(ticker=stock_ticker, dt=self.start_date))
            else:
                self.start_date = pd.Timestamp(self.start_date)
            price, meta_data = self.ts.get_daily(stock_ticker, outputsize='full')
            price_df = pd.DataFrame(price).transpose()
            price_df.index = pd.to_datetime(price_df.index)
            price_df = price_df[price_df.index >= self.start_date]
            price_df.columns = [self._remove_digits(col) for col in price_df.columns]
            price_df.columns = [col.replace('. ', '') for col in price_df.columns]
            price_df['ticker'] = stock_ticker
            price_df = price_df.reset_index().rename({'index':'ts'}, axis=1) \
                .set_index(['ticker', 'ts'])
            return price_df
        
        else:
            raise ValueError('"price_type" must be one of "daily" or "intraday"')
    
    def __getstate__(self):
        self_dict = self.__dict__.copy()
        del self_dict['pool']
        return self_dict

    def __setstate__(self, state):
        self.__dict__.update(state)


if __name__=='__main__':
    logging.basicConfig()
    logging.root.setLevel(logging.NOTSET)
    logging.basicConfig(level=logging.NOTSET)
    logger = logging.getLogger("ExtractData")

    ts = TimeSeries()

    s = Stock(price_type='intraday', ts=ts)
    s.get_tickers_index()
    s.get_list_stock_prices()

    today = dt.date.today().strftime('%Y_%m_%d')
    s.prices_df.to_csv(price_store_path+'prices_'+today+'.csv', index=True)
    logger.info('Saved prices.')
