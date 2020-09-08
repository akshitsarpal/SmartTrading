import sys
import datetime as dt

ST_HOME = '/Users/akshit/SmartTrading/'
sys.path.append(ST_HOME)

today = dt.date.today().isoformat()
price_store_path = '/Users/akshit/SmartTrading_data/prices/'

default_days_intra = 14
default_days_daily = 90
sleep_time_sec = 70