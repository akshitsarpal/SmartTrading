'''
This module is used for extracting and saving list of tickers belonging to top stock indices, 
and extracting historical stock prices and writing 
'''

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
from libs.st_logger.logger import logger
from libs.PyDB.DBWrapper import DBWrapper
import auth

class Stock(object):
    '''
    A class to represent stock tickers and their prices

    ...

    Attributes
    ----------
    logger : st_logger.logger
        object of class st_logger.logger
    tickers_df : pandas.DataFrame
        a dataframe with list of stock tickers in given index
    tickers_list : list[str]
        a list of tickers to be used, if specified 
    stock_index : str
        stock index to use, currently supports 'SP500' or 'NASDAQ'
    price_type : str
        type of price, currently supports 'intraday' or 'daily'
    ts : alpha_vantage.timeseries.TimeSeries
        object to invoke AlphaVantage API calls ofr price extraction
    after_hours : bool
        False if after-hours prices are to be truncated
    start_date : str
        start date to truncate prices at
    write_csv : bool
        True if output is to be written as csv in the location specified in config
    write_db : bool
        True if output is to be written in database
    st_db : PyDB.DBWrapper.DBWrappper
        DBWrapper object for interacting with database

    Methods
    -------
    update_tickers_db()
        reads tickers list in the given index from Wiki and writes to database
    get_tickers_from_index()
        reads list of tickers in the given index from database
    get_prices_av(stock_ticker)
        extracts stock price for gven ticker using AlphaVantage API
    write_to_db(ticker_prices)
        write ticker prices to database
    write_to_csv(ticker_prices, today)
        write ticker prices to csv in the folder under directory specified in config
    '''

    def __init__(self, tickers_list=[],stock_index=None,
                 price_type=None, ts=None, after_hours=False, 
                 start_date=None, write_csv=False, write_db=False,
                 st_db=None, st_logger=None):
        '''
        Parameters
        ----------
        tickers_list : list[str], optional
            A list of tickers to be used, if specified 
        stock_index : str, optional
            Stock index to use, currently supports 'SP500' or 'NASDAQ' (default is 'NASDAQ')
        price_type : str
            Type of price, currently supports 'intraday' or 'daily'
        ts : alpha_vantage.timeseries.TimeSeries
            Object to invoke AlphaVantage API calls ofr price extraction
        after_hours : bool, optional
            False if after-hours prices are to be truncated (default=False)
        start_date : str, optional
            Start date to truncate prices at, uses default from config if missing
        write_csv : bool, optional
            True if output is to be written as csv in the location specified in config (default=False)
        write_db : bool, optional
            True if output is to be written in database (default=False)
        st_db : PyDB.DBWrapper.DBWrappper, optional
            DBWrapper object for interacting with database (default=None)
        st_logger : st_logger.logger
            An object of class logger
        '''
        self.logger = st_logger
        self.tickers_df = None
        self.tickers_list = tickers_list
        if stock_index in ['NASDAQ', 'SP500']:
            self.stock_index = stock_index
        elif not stock_index:
            self.stock_index = 'NASDAQ'
            self.logger.warning('"stock_index" not specified, using default of "NASDAQ".')
        else:
            e = str('stock_index value '+ self.stock_index + ' not defined')
            raise ValueError(e)
        self.price_type = price_type
        self.ts = ts
        self.after_hours = after_hours
        self.start_date = start_date
        self.write_csv = write_csv
        self.write_db = write_db
        self.st_db = st_db
        

    def _remove_digits(self, input_str):
        '''Removes digits from input string'''
        remove_digits = str.maketrans('', '', digits)
        res = input_str.translate(remove_digits)
        return res


    def _check_start_date_format(self):
        '''Check if start date provided else set default start date'''
        if not self.start_date:
            if self.price_type == 'intraday':
                self.start_date = pd.Timestamp(dt.date.today()-dt.timedelta(days=DEFAULT_DAYS_INTRA))
                self.logger.info('''
                "start_date" not specified, using default of {dy}
                (business) days, with start date of {dt}.
                '''.format(dy=DEFAULT_DAYS_INTRA, 
                           dt=self.start_date.isoformat()))
                return
            elif self.price_type == 'daily':
                self.start_date = pd.Timestamp(dt.date.today()-dt.timedelta(days=DEFAULT_DAYS_DAILY))
                self.logger.info('''
                "start_date" not specified, using default of {dy}
                (business) days, with start date of {dt}.
                '''.format(dy=DEFAULT_DAYS_DAILY, 
                           dt=self.start_date.isoformat()))
                return
        elif isinstance(self.start_date, str):
            self.start_date = pd.Timestamp(self.start_date)
            return
        elif isinstance(self.start_date, pd.Timestamp):
            return
        else:
            ValueError('Check "start_date" format - should be passed as "yyyy-mm-dd" string.')

        
    def _refresh_tickers_index(self):
        '''Get the list of all stocks in a given index'''
        if self.stock_index == 'SP500':
            self.logger.info('Getting stock tickers for SP500 from Wiki .....')
            payload = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', header=0)
            self.tickers_df = payload[0]
            self.tickers_df = self.tickers_df.rename({'Symbol':'Ticker'}, axis=1)
            if not (len(self.tickers_df.index) > SP500_LL) and (len(self.tickers_df.index) < SP500_UL):
                ValueError('Check wikipedia data source for SP 500 at \
                             https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
            self.logger.info('Fetched stock tickers from SP500.')
            
        elif self.stock_index == 'NASDAQ':
            self.logger.info('Getting stock tickers for NASDAQ from Wiki .....')
            payload = pd.read_html('https://en.wikipedia.org/wiki/NASDAQ-100#Components', header=0)
            self.tickers_df = payload[3]
            if not (len(self.tickers_df.index) > NASDAQ_LL) and (len(self.tickers_df.index) < NASDAQ_UL):
                ValueError('Check wikipedia data source for NASDAQ at \
                             https://en.wikipedia.org/wiki/NASDAQ-100#Components')
            self.logger.info('Fetched stock tickers from NASDAQ.')


    def update_tickers_db(self):
        '''Write updated tickers to database'''
        self._refresh_tickers_index()
        if self.stock_index == 'SP500':
            df = self.tickers_df.rename({'Symbol': 'ticker', 'Security': 'company'},
                                        axis=1)
            df['stock_index'] = 'SP500'
            self.st_db.executeWriteQuery(df[['ticker', 'company', 'stock_index']], 
                                         'tickers')
        elif self.stock_index == 'NASDAQ':
            df = self.tickers_df.rename({'Company': 'company', 'Ticker': 'ticker'}, 
                                        axis=1)
            df['stock_index'] = 'NASDAQ'
            self.st_db.executeWriteQuery(df, 'tickers')
        


    def get_tickers_from_index(self):
        '''Read tickers in given index from database'''
        qry = '''
        SELECT
            *
        FROM
            SMART_TRADING.tickers
        WHERE 
            stock_index = '{}'
        '''.format(self.stock_index)
        self.tickers_df = self.st_db.executeReadQuery(qry)
        self.tickers_list = list(self.tickers_df['ticker'])


    def get_prices_av(self, stock_ticker):
        '''Extract prices using the API

        Parameters
        ----------
        stock_ticker : str
            Name of stock ticker to get prices for

        Raises
        ------
        ValueError 
            If price_type not in 'intraday' or 'daily'
        '''
        if self.price_type in ['intraday', 'daily']:
            try:
                if self.price_type == 'intraday':
                    price, _ = self.ts.get_intraday(stock_ticker, outputsize='full')
                elif self.price_type == 'daily':
                    price, _ = self.ts.get_daily(stock_ticker, outputsize='full')
                price_df = pd.DataFrame(price).transpose()
            except:
                self.logger.info('{ticker}: Skipped by Alphavantage.'.format(ticker=stock_ticker))
                price_df = pd.DataFrame(columns=['index', '1. open', '2. high', '3. low',
                     '4. close', '5. volume']).set_index('index')
        else:
            ValueError('"price_type" must be one of "intraday" or "daily".')
        
        price_df.index = pd.to_datetime(price_df.index)
        price_df = price_df[price_df.index >= self.start_date]
        if self.price_type == 'intraday' and not self.after_hours:
            self.logger.info('''{ticker}: Truncating pre-market and after-hours data.
                        '''.format(ticker=stock_ticker))
            price_df = price_df[(price_df.index.time>=dt.time(9,30)) & 
                                (price_df.index.time<=dt.time(16,0))]

        price_df.columns = [self._remove_digits(col) for col in price_df.columns]
        price_df.columns = [col.replace('. ', '') for col in price_df.columns]
        price_df['ticker'] = stock_ticker
        price_df = price_df.reset_index().rename({'index':'dt'}, axis=1) \
            .set_index(['ticker', 'dt'])
        return price_df


    def write_to_db(self, ticker_prices):
        '''Writes ticker prices to database

        Attributes
        ----------
        ticker_prices : pd.DataFrame
            A dataframe of extracted prices to write to database

        Raises
        ------
        ValueError
            If price_type not in 'intraday' or 'daily'
        '''
        try:
            if self.price_type == 'daily':
                self.st_db.executeWriteQuery(ticker_prices, 'daily_prices', index=True)
            elif self.price_type == 'intraday':
                ticker_prices.index.names = ['ticker', 'ts']
                self.st_db.executeWriteQuery(ticker_prices, 'intraday_prices', index=True)
            else:
                ValueError('"price_type" must be in "daily" or "intraday"')
        except:
            ticker = ticker_prices.index.levels[0][0]
            self.logger.info('{}: Could not write to DB.'.format(ticker))


    def write_to_csv(self, ticker_prices, today):
        '''Writes ticker prices to csv

        Attributes
        ----------
        ticker_prices : pd.DataFrame
            A dataframe of extracted prices to write to database
        today : str
            Today date to create subdirectory for writing csv in

        Raises
        ------
        ValueError
            If price_type not in 'intraday' or 'daily'
        '''
        ticker = ticker_prices.index.levels[0][0]
        try:
            filepath = PRICE_STORE_PATH + ticker + '_' + \
                       self.price_type + '_' + today + '.csv'
            ticker_prices.to_csv(filepath, index=True)
            self.logger.info('{}: Saved prices.'.format(ticker))
        except:
            self.logger.warning('{}: Could not save prices.'.format(ticker))
    

    def get_list_stock_prices(self):
        '''Fetch stock price for list of tickers

        Raises
        ------
        KeyError
            If ticker list is not available in the attribute. 
        '''
        self._check_start_date_format()
        if not self.tickers_list:
            raise KeyError('tickers_list not provided, either pass as argument or \
                call get_tickers_from_index() method with index name to fetch tickers.')
        n_proc = max(cpu_count()-1, 4)
        self.pool = Pool(n_proc)
        today = dt.date.today().strftime('%Y_%m_%d')
        if not os.path.isdir(PRICE_STORE_PATH):
            os.mkdir(PRICE_STORE_PATH)
            self.logger.info('Created directory to save csvs: {}'.format(PRICE_STORE_PATH))
        
        # Split into chunks of no more than 5 since Alpha Vantage API takes 5 calls per min 
        tickers_list_chunked = [self.tickers_list[i:i+n_proc] 
                                for i in range(0, len(self.tickers_list), n_proc)]
        for chunk in tickers_list_chunked:
            prices_df_list = self.pool.map_async(self.get_prices_av, chunk).get()
            t_start = time.time()

            if self.write_db:
                for ticker_prices in prices_df_list:
                    if len(ticker_prices.index) > 0:
                        self.write_to_db(ticker_prices)
            
            if self.write_csv:
                for ticker_prices in prices_df_list:
                    if len(ticker_prices.index) > 0:
                        self.write_to_csv(ticker_prices, today)

            t_elapsed = round(time.time() - t_start, 2)
            if t_elapsed < SLEEP_TIME_SEC:
                self.logger.info("System sleep {} sec ....".format(SLEEP_TIME_SEC - t_elapsed))
                time.sleep(SLEEP_TIME_SEC - t_elapsed)

        self.pool.close()
        self.pool.join() 

    
    def __getstate__(self):
        self_dict = self.__dict__.copy()
        del self_dict['pool']
        return self_dict


    def __setstate__(self, state):
        self.__dict__.update(state)


if __name__=='__main__':
    st_logger = logger('ExtractPrices')
    args = parse_args()
    tickers_list = args.tickers_list
    stock_index = args.stock_index
    price_type = args.price_type
    after_hours = args.after_hours
    start_date = args.start_date
    write_csv = args.write_csv
    write_db = args.write_db
    st_db = DBWrapper('SMART_TRADING')
    ts = TimeSeries()
    s = Stock(tickers_list=tickers_list, stock_index=stock_index,
              price_type=price_type, ts=ts, after_hours=after_hours, 
              start_date=start_date, write_csv=write_csv, write_db=write_db,
              st_db=st_db, st_logger=st_logger)
    if not s.tickers_list:
        s.get_tickers_from_index()
        st_logger.info('Extracted stock tickers from Index: {}'.format(s.stock_index))
    s.get_list_stock_prices()

