import os
import pandas as pd
import numpy as np
import auth
import datetime as dt
from constants import *

from libs.PyDB.DBWrapper import DBWrapper
from libs.st_logger.logger import logger
from argparse import ArgumentParser

class Earnings(object):
    
    def __init__(self, st_db, st_logger, historical_earnings=False):
        import yahoo_earnings_calendar as YEC
        self._yec = YEC.YahooEarningsCalendar()
        self.st_db = st_db
        self.logger = st_logger
        self.historical_earnings = historical_earnings
        self._cols = cols = ['ticker', 'ds', 'company_name', 'earnings_dt', 'datetime_type', 
            'eps_estimate', 'eps_actual','eps_surprise_pct', 'time_zone',
            'gmt_offset_ms', 'quote_type']
        
    def _extract_earnings_json(self, ticker):
        return self._yec.get_earnings_of(ticker)
    
    def get_earnings_features_ticker(self, ticker):
        earnings_payload = self._extract_earnings_json(ticker)
        earnings_df = pd.DataFrame([], columns=self._cols)
        try:
            for d in earnings_payload:
                ticker = d['ticker']
                ds = d['startdatetime'][:10]
                company_name = d['companyshortname']
                earnings_dt = d['startdatetime']
                datetime_type = d['startdatetimetype']
                eps_estimate = d['epsestimate']
                eps_actual = d['epsactual']
                eps_surprise_pct = d['epssurprisepct']
                time_zone = d['timeZoneShortName']
                gmt_offset_ms = d['gmtOffsetMilliSeconds']
                quote_type = d['quoteType']
                parsed_series = pd.Series(
                    [ticker, ds, company_name, earnings_dt, 
                     datetime_type, eps_estimate, eps_actual, 
                     eps_surprise_pct, time_zone, gmt_offset_ms,
                     quote_type], index=self._cols)
                earnings_df = earnings_df.append(parsed_series, 
                                                 ignore_index=True)
        except:
            self.logger.warning('Could not get earnings data, \
                                returning empty data frame...')
        cols_float = ['eps_estimate', 'eps_actual', 'eps_surprise_pct']
        earnings_df[cols_float] = earnings_df[cols_float].astype(float)
        earnings_df.set_index(['ticker', 'ds'], inplace=True)

        # Truncate historical earnings if False
        if not self.historical_earnings:
            earnings_df = earnings_df \
                [earnings_df.index.get_level_values('ds') > dt.date.today().isoformat()]
        return earnings_df
    
    def write_earnings_to_db(self, earnings_df):
        
        # MySQL doesn't write NaN's for float cols, so convert to -99.0
        earnings_df = earnings_df.where((pd.notnull(earnings_df)), -99.0)
        
        # Convert to correct datetime format
        earnings_df['earnings_dt'] = pd.to_datetime(earnings_df["earnings_dt"],
                                        format="%Y-%m-%dT%H:%M:%S.%fZ")
        
        if ('ticker' in earnings_df.index.names) or \
            ('ds' in earnings_df.index.names):
            earnings_df.reset_index(inplace=True)
        cols_not_exist = set(self._cols).difference(set(earnings_df.columns))
        
        # Check if any necessary columns are missing, else write 
        if bool(cols_not_exist):
            raise ValueError('Missing columns: ', cols_not_exist)
        else:
            self.st_db.executeWriteQuery(earnings_df, 'earnings')
            self.logger.info('Successfully written earnings...')
            
            
    def load_earnings_all_tickers(self, stock_index):
        if stock_index in ['SP500', 'NASDAQ']:
            qry = '''
            SELECT 
                ticker
            FROM
                tickers
            WHERE
                stock_index = '{}'
            '''.format(stock_index)
        else:
            raise ValueError('stock_index must be in ["SP500", "NASDAQ"]')
        
        pdf_earnings_all = pd.DataFrame([], columns=self._cols) \
            .set_index(['ticker', 'ds'])
        
        stocks_list = list(st_db.executeReadQuery(qry)['ticker'])
        for ticker in stocks_list:
            try:
                pdf_earnings = self.get_earnings_features_ticker(ticker)
                pdf_earnings_all = pd.concat([pdf_earnings_all, pdf_earnings], axis=0)
            except:
                self.logger.info('Skipped ticker: {}'.format(ticker))
        if pdf_earnings_all.shape[0] > 0:
            self.write_earnings_to_db(pdf_earnings_all)
        


if __name__ == '__main__':

    st_db = DBWrapper('SMART_TRADING')
    st_logger = logger('Earnings')
    
    parser = ArgumentParser()
    parser.add_argument('--earnings-bootstrap',
        action='store_true', required=False, default=False,
        help='Set True to bootstrap historical earnings or False to save only new.')
    args = parser.parse_args()
    earnings_bootstrap = args.earnings_bootstrap

    ern = Earnings(st_db=st_db, st_logger=st_logger, historical_earnings=earnings_bootstrap)
    ern.load_earnings_all_tickers('NASDAQ')
