"""
This contains trading strategies and functions that rely on Alpha Vantage and Alpaca

Limits:
---------
Alpha Vantage has a limit of up to 5 API requests per minute and 500 requests per day

"""

import alpaca_trade_api as tradeapi
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.techindicators import TechIndicators
import support
import datetime
from pytz import timezone
import traceback


APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_API_BASE_URL, ALPHA_VANTAGE_API_KEY = "", "", "", ""


def main():
    global APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_API_BASE_URL

    # Set global env variables
    set_vars()
    current_stock = ''

    while True:
        try:

            stocks_list = ["NRZ", "GAIN", "NEWT", "ORI", "IRT", "SHOP", "PAYC", "AMD", "ABR"]

            st = timezone('EST')

            if support.is_trading_hours():
                for stock_tickers in stocks_list:
                    now = datetime.datetime.now(st)
                    current_stock = stock_tickers

                    print(f"Is trading hours! Time is: {now}, stock is: {current_stock}")

                    # Interact with rest api at alpaca
                    api = tradeapi.REST(key_id=APCA_API_KEY_ID, secret_key=APCA_API_SECRET_KEY, api_version='v2',
                                        base_url=APCA_API_BASE_URL)

                    # Trading strategy 1
                    trading_strategy_1(api, stock_ticker=stock_tickers, percent_aim=0.01)
                    support.wait_time()

                    if not support.is_trading_hours():
                        break

            if not support.is_trading_hours():
                now = datetime.datetime.now(st)
                print(f"Turns out it isn't trading time. Time is: {now}")

                # Wait 15 minutes before checking again if not trading hours
                support.wait_time(seconds=900)

        except Exception as e:
            support.wait_time()

            # TODO PUT log.txt in S3
            # Save query in .txt file as well
            with open("log.txt", 'a') as f:  # Use file to refer to the file object

                f.write("\n \n")
                f.write(f"Stock ticker was {current_stock}")
                f.write("\n \n")
                f.write(f"Time is: {datetime.datetime.now()}")
                f.write(f"'exception_type: '{type(e).__name__}, \n"
                        f"'error_reason': {e.args}, \n"
                        f"\n")
                f.write(f"Traceback is: {traceback.format_exc()}")
                print(f"Breaking because of an error: {e}")


def trading_strategy_1(api, stock_ticker, percent_aim):
    """
    This will operate between 09:30 and 16:00 EST
    Due to Alpha Vantage limits, this will check every minute for a total of 390 api requests

    ----------
    Buying strategy
    ----------

    This trading strategy monitors the average prices of a certain stock and submits a buy order if the current price is
    below the weekly average. Before buying, the strategy checks that the portfolio doesn't currently contain this stock
    already, there hasn't been any purchases of this stock in the last week, and that the month's return for the stock
    is not on a negative trajectory.

    If all of these criteria check out, then move to purchase as many stock as possible with half the available
    amount of money. If half the available amount of money cannot purchase any stock, then try the full amount of the
    remaining buying power.

    ----------
    Selling strategy
    ----------

    This trading strategy checks the price of the specified stock, assuming the stock is already owned and not bought
    the same day, and compares the bought price to the current price. If the difference is greater than the specified
    percent_aim, then submit a sell order.

    Parameters
    ----------
    api: Alpaca api object
    stock_ticker: Stock ticker string (ex: NRZ)
    percent_aim: Percent increase to sell at

    Returns
    -------
    None
    
    """

    global ALPHA_VANTAGE_API_KEY

    account = api.get_account()

    currently_own_this_stock = support.currently_own_this_stock(api, stock_ticker)

    ###############################
    # Buying
    ###############################

    # If the portfolio currently contains this stock, don't buy more
    if currently_own_this_stock is False:

        purchase_in_last_week = support.trade_in_time_period(api, stock_ticker, trade_type='buy', day_range=7)

        # If there hasn't been a purchase in a week on the same stock
        if purchase_in_last_week is False:

            # Get current price of stock
            ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
            curr_price_data, curr_price_meta_data = ts.get_intraday(symbol=stock_ticker, interval='1min',
                                                                    outputsize='compact')
            # curr_open = float(curr_price_data['1. open'].iloc[0])
            # curr_high = float(curr_price_data['2. high'].iloc[0])
            # curr_low = float(curr_price_data['3. low'].iloc[0])
            curr_close = float(curr_price_data['4. close'].iloc[0])
            # current_price_avg = (curr_open + curr_high + curr_low + curr_close)/4
            current_stock_price = curr_close

            # Set number of shares to buy equal to possible number bought with half the buying power
            buying_power = float(account.buying_power)
            num_of_shares_can_purchase = int((buying_power / 2) / current_stock_price)

            # If no shares can be bought with half the buying power, use all remaining buying power
            if num_of_shares_can_purchase <= 0:
                num_of_shares_can_purchase = int(buying_power / current_stock_price)

            # Make sure there is enough money to purchase a stock
            if num_of_shares_can_purchase > 0:

                # Retrieving Simple Moving Average of stock a month ago and subtracting this from current price
                ti = TechIndicators(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
                sma_df_data_monthly, sma_meta_data_monthly = ti.get_sma(symbol=stock_ticker, interval='monthly',
                                                                        time_period=30)
                month_ago_price = sma_df_data_monthly['SMA'].iloc[-1]
                month_return_of_stock = float(current_stock_price) - float(month_ago_price)

                # if the month's return is not on a negative trajectory
                if month_return_of_stock > 0:

                    # Retrieving Simple Moving Average of stock
                    ti = TechIndicators(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
                    sma_df_data_weekly, sma_meta_data_weekly = ti.get_sma(symbol=stock_ticker, interval='weekly',
                                                                          time_period=4)
                    weekly_avg_price_of_stock = sma_df_data_weekly['SMA'].iloc[-1]

                    # If the stock tips below the moving average stock price for the week
                    if current_stock_price < weekly_avg_price_of_stock:
                        support.limit_trade(limit_price=str(current_stock_price), api=api, stock_ticker=stock_ticker,
                                            quantity=str(num_of_shares_can_purchase),  side='buy', trade_type='limit',
                                            time_in_force='day', stop_price=None, client_order_id=None,
                                            extended_hours=None)

    ###############################
    # Selling
    ###############################
    purchased_today = support.trade_in_time_period(api, stock_ticker, 'buy', day_range=1)

    # If the portfolio currently contains this stock, look to see if strategy should sell
    if currently_own_this_stock is True:

        # Check to see if the stock was purchased today
        if purchased_today is False:
            # Get current price of stock
            ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
            curr_price_data, curr_price_meta_data = ts.get_intraday(symbol=stock_ticker, interval='1min',
                                                                    outputsize='compact')
            # curr_open = float(curr_price_data['1. open'].iloc[0])
            # curr_high = float(curr_price_data['2. high'].iloc[0])
            # curr_low = float(curr_price_data['3. low'].iloc[0])
            curr_close = float(curr_price_data['4. close'].iloc[0])
            # current_price_avg = (curr_open + curr_high + curr_low + curr_close)/4
            current_stock_price = curr_close

            bought_price, num_of_shares_owned = support.get_last_bought_price(api, stock_ticker=stock_ticker)

            percent_change = round((float(current_stock_price) - float(bought_price)) / float(current_stock_price), 4)

            if percent_change >= percent_aim:
                support.limit_trade(limit_price=str(current_stock_price), api=api, stock_ticker=stock_ticker,
                                    quantity=str(num_of_shares_owned), side='sell', trade_type='limit',
                                    time_in_force='day', stop_price=None, client_order_id=None,
                                    extended_hours=None)


# Initializing
def set_vars(secrets_file="secrets-alpaca.env"):
    """
    This function initializes the credentials by setting APCA_API_KEY_ID, APCA_API_SECRET_KEY, and APCA_API_BASE_URL
    global variables from a specified .env file in the same directory

    Parameters
    ----------
    secrets_file: Default set to secrets-alpaca.env, can be any secrets file containing the

    Returns
    -------

    """

    global APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_API_BASE_URL, ALPHA_VANTAGE_API_KEY

    file = open(f"{secrets_file}", 'r')
    contents = file.read()
    env_vars = contents.replace('export ', '').split("\n")
    APCA_API_KEY_ID = env_vars[0].split("=")[1]
    APCA_API_SECRET_KEY = env_vars[1].split("=")[1]
    APCA_API_BASE_URL = env_vars[2].split("=")[1]
    ALPHA_VANTAGE_API_KEY = env_vars[3].split("=")[1]


if __name__ == '__main__':
    main()
