import sys
import datetime as dt

ST_HOME = '/Users/akshit/SmartTrading/'
sys.path.append(ST_HOME)

today = dt.date.today().isoformat()
PRICE_STORE_PATH = '/Users/akshit/SmartTrading_data/prices/{}/'.format(today)

DEFAULT_DAYS_INTRA = 30 # trucate intraday prices older than 'default_days_intra' days
DEFAULT_DAYS_DAILY = 10000 # trucate daily prices older than 'default_days_intra' days
SLEEP_TIME_SEC = 70 # sleep time between AlphaVantage API requests

# When extracting tickers from indices, exception wll shown 
# if ticker count not between the following range
NASDAQ_LL = 85
NASDAQ_UL = 130
SP500_LL = 450
SP500_UL = 600

TRUNCATE_BUFFER = 90 # today-TRUNCATE_BUFFER is date before which earnings to get truncated