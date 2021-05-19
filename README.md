# SmartTrading

The objective is to extract stock price data, model and forecast prices. Data is currently being extracted using a couple of APIs and stored in a local MySQL instance. Two active users by the IDs `akshitsarpal` and `sarpalak` have made commits; both accounts are owned by the repo owner Akshit Sarpal. 


### 1. Extract Stock Prices 

To extract intraday prices (available at 15 minute intervals through AlphaVantage API) and write to MySQL, use:

`python extract_prices.py --stock-index NASDAQ --price-type intraday --write-db`

For daily prices, specify `--price-type` argument as `daily`. To extract S&P500 stock prices, specify `--stock-index` as `SP500`. One can also save prices to csv by adding `--write-csv`. Other arguments available in `~data_extraction/args.py`.

It is also possible to extract prices for given tickers. The below line when executes, will only extract and save latest additional prices for AAPL, AMZN and FB:

` python extract_prices.py --price-type 'daily' --write-db --tickers-list 'AAPL' 'AMZN' 'FB'`


### 2. Extract past earnings and upcoming earnings dates

Variation in stock prices can be explained by earnings and earning dates. Therefore it can be an important feature to consider for forecasting price. To extract earnings, the following can be used:

`python extract_earnings.py --stock-index NASDAQ`

This brings last 90 day earnings data for given tickers (e.g. NASDAQ). To bootstrap past earnings, add `--earnings-bootstrap`, which will overwrite an historical earnings data if changes are observed.


#### Dependencies

- Requires an `auth.py` file in the directory with environment variables
  - `db_user`: Username for local MySQL instance
  - `db_pwd`: Password for local MySql instance
  - `ALPHAVANTAGE_API_KEY`: Authentication key for AlphaVantage API
