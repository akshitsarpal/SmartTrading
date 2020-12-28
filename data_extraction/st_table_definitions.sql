/*
Table definitions of the SMART_TRADING database.
*/

-- Daily stock prices
create table SMART_TRADING.daily_prices_test(
ticker varchar(8) default '' not null,
dt date default '1990-01-01' not null,
open float,
high float,
low float,
close float,
volume int,

primary key(ticker, dt)
);

-- Intraday stock prices
create table SMART_TRADING.intraday_prices (
ticker varchar(8) default '' not null,
ts TIMESTAMP DEFAULT '1990-01-01 00:00:00' NOT NULL,
open float,
high float,
low float,
close float,
volume int,
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

primary key(ticker, ts)
);

-- Tickers for NASDAQ index
create table SMART_TRADING.tickers_nasdaq (
ticker varchar(8) default '' not null,
company varchar(64) default '' not null,

primary key (ticker)
);


-- Historical earnings reports and future earnings dates
create table SMART_TRADING.earnings (
ticker varchar(8) default '' not null,
ds date default '1990-01-01' not null,
company_name varchar(64) default null,
earnings_dt TIMESTAMP DEFAULT '1990-01-01 00:00:00' NOT NULL, 
datetime_type VARCHAR(12) default '', 
eps_estimate float,
eps_actual float, 
eps_surprise_pct float, 
time_zone varchar(6),
gmt_offset_ms float, 
quote_type varchar(32),
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP NOT NULL DEFAULT NOW() ON UPDATE NOW(),

primary key (ticker, ds)
);

-- All tickers with company name and index
-- Note: A ticker can appear in multiple indices
create table SMART_TRADING.tickers (

ticker varchar(8) default '' not null,
company varchar(64) default '' not null,
stock_index varchar(64) default '' not null,
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

primary key (ticker, stock_index)
);
