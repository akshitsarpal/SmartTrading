from argparse import ArgumentParser

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--tickers-list',
        nargs='+', required=False, default=None,
        help="Space separated list of stock tickers.")
    parser.add_argument('--stock-index', 
        type=str, required=False, default=None,
        help='Index to get tickers - "SP500" or "NASDAQ".')
    parser.add_argument('--price-type', 
        type=str, required=False, default=None,
        help='Frequency of prices - "daily" or "intraday".')
    parser.add_argument('--after-hours', 
        action='store_true', required=False, default=False,
        help='If intraday prices, whether to keep after hours prices or not.')
    parser.add_argument('--start-date',
        type=str, required=False, default=None,
        help='Start date for stock prices to extract.')

    parser.add_argument('--earnings-bootstrap',
        action='store_true', required=False, default=False,
        help='Set True to bootstrap historical earnings or False to save only new.')
    
    parser.add_argument('--write-csv', 
        action='store_true', required=False, default=False,
        help='Whether to write prices to csvs.')
    parser.add_argument('--write-db', 
        action='store_true', required=False, default=False,
        help='Whether to write prices to db.')

    return parser.parse_args()
