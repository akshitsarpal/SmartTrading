import datetime as dt

today = dt.date.today().isoformat()
price_store_path = '/Users/akshit/SmartTrading_data/prices/{}'.format(today)

default_days_intra = 14
default_days_daily = 90
