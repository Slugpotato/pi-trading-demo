"""
This contains trading strategies and functions that rely on the Alpaca trading platform

"""

import alpaca_trade_api as tradeapi
import support
import datetime
from pytz import timezone
import traceback


APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_API_BASE_URL = "", "", ""


def main():
    global APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_API_BASE_URL

    # Set global env variables
    set_vars()
    current_stock = ''

    while True:
        try:

            stocks_list = ["AMD", "AAPL"]

            st = timezone('EST')

            if support.is_trading_hours():
                for stock_tickers in stocks_list:
                    now = datetime.datetime.now(st)
                    current_stock = stock_tickers

                    print(f"Is trading hours! Time is: {now}, stock is: {current_stock}")

                    # Interact with rest api at alpaca
                    api = tradeapi.REST(key_id=APCA_API_KEY_ID, secret_key=APCA_API_SECRET_KEY, api_version='v2',
                                        base_url=APCA_API_BASE_URL)

                    api.submit_order(symbol="AMD", qty=1, side='buy', type='limit', time_in_force='day', limit_price='60')

                    # Trading strategy 1
                    trading_strategy_1(api, stock_ticker=stock_tickers, percent_aim=0.01)
                    # support.wait_time()

                    if not support.is_trading_hours():
                        break

            if not support.is_trading_hours():
                now = datetime.datetime.now(st)
                print(f"Turns out it isn't trading time. Time is: {now}")

                # Wait 15 minutes before checking again if not trading hours
                support.wait_time(seconds=900)

        except Exception as e:
            # support.wait_time()

            # Save error in .txt file
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


def trading_strategy_1(api, stock_ticker):
    """
    Fill in your own trading strategy here! Be advised though, I am not responsible for any trades you make and am not a financial advisor! 

    Parameters
    ----------
    api: Alpaca api object
    stock_ticker: Stock ticker string (ex: NRZ)
    percent_aim: Percent increase to sell at

    Returns
    -------
    None
    
    """

    account = api.get_account()

    currently_own_this_stock = support.currently_own_this_stock(api, stock_ticker)

    ###############################
    # Buying
    ###############################
    
    # Fill in some Buying logic here...

    ###############################
    # Selling
    ###############################

    # Fill in some Selling logic here...
    

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
    None

    """

    global APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_API_BASE_URL

    with open(f"{secrets_file}", 'r') as file:
        contents = file.read()
        env_vars = contents.replace('export ', '').split("\n")
        APCA_API_KEY_ID = env_vars[0].split("=")[1]
        APCA_API_SECRET_KEY = env_vars[1].split("=")[1]
        APCA_API_BASE_URL = env_vars[2].split("=")[1]


if __name__ == '__main__':
    main()
