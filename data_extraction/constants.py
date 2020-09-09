import sys
import datetime as dt

ST_HOME = '/Users/akshit/SmartTrading/'
sys.path.append(ST_HOME)

today = dt.date.today().isoformat()
price_store_path = '/Users/akshit/SmartTrading_data/prices/'

default_days_intra = 14
default_days_daily = 10000
sleep_time_sec = 70

nasdaq_ll = 85
nasdaq_ul = 130
sp500_ll = 450
sp500_ul = 600