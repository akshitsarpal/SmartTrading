import pandas as pd
import numpy as np
import os
from string import digits
import datetime as dt
from alpha_vantage.timeseries import TimeSeries
from multiprocessing import Pool, cpu_count
import time

from constants import *
from args import parse_args
from logger import logger

os.environ["ALPHAVANTAGE_API_KEY"] = "100HED30C7HC9JMI"

class Stock(object):
    '''
    Extracts tickers for given indices, and extracts intraday or daily stock prices.
    '''
    def __init__(self, tickers_list=[],stock_index=None,
                 price_type=None, ts=None, after_hours=False, 
                 start_date=None, save_csv=False):
        self.tickers_df = None
        self.tickers_list = tickers_list
        self.stock_index = stock_index
        self.price_type = price_type
        self.ts = ts
        self.after_hours = after_hours
        self.start_date = start_date
        self.save_csv = save_csv
        

    def _remove_digits(self, input_str):
        remove_digits = str.maketrans('', '', digits)
        res = input_str.translate(remove_digits)
        return res


    def _check_start_date_format(self):
        if not self.start_date:
            if self.price_type == 'intraday':
                self.start_date = pd.Timestamp(dt.date.today()-dt.timedelta(days=default_days_intra))
                logger.info('''
                "start_date" not specified, using default of {dy}
                (business) days, with start date of {dt}.
                '''.format(dy=default_days_intra, 
                           dt=self.start_date.isoformat()))
                return
            elif self.price_type == 'daily':
                self.start_date = pd.Timestamp(dt.date.today()-dt.timedelta(days=default_days_daily))
                logger.info('''
                "start_date" not specified, using default of {dy}
                (business) days, with start date of {dt}.
                '''.format(dy=default_days_daily, 
                           dt=self.start_date.isoformat()))
                return
        elif isinstance(self.start_date, str):
            self.start_date = pd.Timestamp(self.start_date)
            return
        elif isinstance(self.start_date, pd.Timestamp):
            return
        else:
            ValueError('Check "start_date" format - should be passed as "yyyy-mm-dd" string.')

        
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
                self.tickers_df = self.tickers_df.head(6) #TODO: remove this
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
                self.tickers_df = self.tickers_df.head(6) #TODO: remove this
                self.tickers_list = list(self.tickers_df['Ticker'])
            else:
                ValueError('Check wikipedia data source for NASDAQ at \
                             https://en.wikipedia.org/wiki/NASDAQ-100#Components')
            logger.info('Fetched stock tickers from NASDAQ.')
            
        else:
            e = str('stock_index value '+ self.stock_index + ' not defined')
            raise ValueError(e)
        

    def get_prices_av(self, stock_ticker):
        '''
        Extract prices using the API.
        '''
        if self.price_type in ['intraday', 'daily']:
            try:
                if self.price_type == 'intraday':
                    price, _ = self.ts.get_intraday(stock_ticker, outputsize='full')
                elif self.price_type == 'daily':
                    price, _ = self.ts.get_daily(stock_ticker, outputsize='full')
                price_df = pd.DataFrame(price).transpose()
            except:
                logger.info('{ticker}: Skipped by Alphavantage.'.format(ticker=stock_ticker))
                price_df = pd.DataFrame(columns=['index', '1. open', '2. high', '3. low',
                     '4. close', '5. volume']).set_index('index')
        else:
            ValueError('"price_type" must be one of "intraday" or "daily".')
        
        price_df.index = pd.to_datetime(price_df.index)
        price_df = price_df[price_df.index >= self.start_date]
        if self.price_type == 'intraday' and not self.after_hours:
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


    def get_list_stock_prices(self):
        '''
        Fetch stock price for list of tickers.
        '''
        self._check_start_date_format()
        if not self.tickers_list:
            raise KeyError('tickers_list not provided, either pass as argument or \
                call get_tickers_index() method with index name to fetch tickers.')
        n_proc = max(cpu_count()-1, 4)
        self.pool = Pool(n_proc)
        
        # Split into chunks of no more than 5 since Alpha Vantage API takes 5 calls per min 
        tickers_list_chunked = [self.tickers_list[i:i+n_proc] 
                                for i in range(0, len(self.tickers_list), n_proc)]
        for chunk in tickers_list_chunked:
            prices_df_list = self.pool.map_async(self.get_prices_av, chunk).get()
            if self.save_csv:
                for ticker_prices in prices_df_list:
                    if len(ticker_prices.index) > 0:
                        try:
                            today = dt.date.today().strftime('%Y_%m_%d')
                            print(type(ticker_prices))
                            print(ticker_prices.shape)
                            ticker_prices.to_csv(price_store_path+ticker_prices.index.levels[0][0]+'_'+
                                                 self.price_type+'_'+today+'.csv', index=True)
                            logger.info('{ticker}: Saved prices.'.format(ticker=ticker_prices.index.levels[0][0]))
                        except:
                            logger.warning('Could not save prices.')
            logger.info("System sleep {} sec ....".format(sleep_time_sec))
            time.sleep(sleep_time_sec)
        self.pool.close()
        self.pool.join() 

    
    def __getstate__(self):
        self_dict = self.__dict__.copy()
        del self_dict['pool']
        return self_dict


    def __setstate__(self, state):
        self.__dict__.update(state)


if __name__=='__main__':

    logger = logger('ExtractDate')
    args = parse_args()
    tickers_list = args.tickers_list
    stock_index = args.stock_index
    price_type = args.price_type
    after_hours = args.after_hours
    start_date = args.start_date
    save_csv = args.save_csv

    ts = TimeSeries()
    s = Stock(tickers_list=[], stock_index=stock_index,
              price_type=price_type, ts=ts, after_hours=after_hours, 
              start_date=start_date, save_csv=save_csv)
    s.get_tickers_index()
    s.get_list_stock_prices()

