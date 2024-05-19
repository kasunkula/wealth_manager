import datetime

import yfinance as yf
from pandas_datareader import data as pdr

# ===========================================
from prettytable import PrettyTable

symbols = ["BN4.SI", "S68.SI"]
symbol = "S68.SI"
start_date = "2024-01-01"
starting_capital = 5000
cut_loss_at = 7  # cut loss when when loss is %
take_profit_on = 15  # take profit when profit is %
double_down_on_drop = 15
buy_on_dip_from_last_high = 10  # buy when process falls % from last high
take_profit_for = 100   # 7%
buying_base_unit_value = 2500
# ===========================================
accumulate_fraction = 50
print_audit_trail = False
show_idle_day_audit_trail = False
rounding_precision = 6
# ===========================================

last_buy_price = None
last_buy_cost = None
cum_qty = 0
cum_cost = 0
avg_price = None
last_peak = 0
remaining_capital = starting_capital
audit_trail = []


def buy(symbol, date, price, value, scenario):
    global last_buy_cost, cum_qty, cum_cost, avg_price, last_buy_price, remaining_capital
    consideration = round(last_buy_cost * 2 if last_buy_cost is not None else buying_base_unit_value, rounding_precision) if value is None else value

    if consideration > remaining_capital:
        consideration = remaining_capital

    if consideration <= 0:
        return

    if value is None:
        last_buy_cost = consideration

    remaining_capital = round(remaining_capital - consideration, rounding_precision)

    buy_qty = round(consideration / price, rounding_precision)
    cum_qty += buy_qty
    cum_qty = round(cum_qty, rounding_precision)
    cum_cost += consideration
    cum_cost = round(cum_cost, rounding_precision)
    avg_price = round(cum_cost / cum_qty, rounding_precision)
    last_buy_price = price
    if print_audit_trail:
        print("[{}][BUY ][{}] Price {} | {}@{} = {} | cum {}@{} = {} | remaining capital {}"
              .format(date, scenario.ljust(40, " "), price, buy_qty, price, consideration, cum_qty, avg_price, cum_cost, remaining_capital))
    add_audit_trail_entry(symbol, date, "Buy", scenario, price, buy_qty, price, consideration)


def sell(symbol, date, price, scenario):
    global cum_qty, cum_cost, avg_price, last_buy_price, last_buy_cost, remaining_capital
    sell_qty = round(cum_qty * take_profit_for / 100, rounding_precision)
    sales_proceeds = round(sell_qty * price, rounding_precision)
    remaining_capital = round(remaining_capital + sales_proceeds, rounding_precision)
    if print_audit_trail:
        print("[{}][SELL][{}] Price {} | cum {}@{} = {} | remaining capital {}"
              .format(date, scenario.ljust(40, " "), price, cum_qty, avg_price, cum_cost, remaining_capital))

    last_buy_price = price
    last_buy_cost = None
    cum_qty = round(cum_qty - sell_qty, rounding_precision)
    if cum_qty == 0:
        avg_price = None
        cum_cost = 0
    else:
        cum_cost = round(cum_qty * avg_price, rounding_precision)
    add_audit_trail_entry(symbol, date, "Sell", scenario, price, sell_qty, price, sales_proceeds)


def get_current_portfolio_value(price):
    if cum_qty == 0:
        return 0
    return round(cum_qty * price, rounding_precision)


def get_current_nav(price):
    return round(get_current_portfolio_value(price) + remaining_capital, rounding_precision)


def get_current_gain(price):
    return "{}%".format(round((get_current_nav(price) - starting_capital) * 100 / starting_capital, 0))


def add_audit_trail_entry(symbol, date, action, scenario, price, action_qty, action_price, action_consideration):
    audit_trail.append(
        [symbol, date, action, scenario, get_closing_price_stat(price), action_qty, action_price, action_consideration,
         cum_qty, avg_price, cum_cost, get_current_portfolio_value(price), remaining_capital, get_current_nav(price), get_current_gain(price)])


def get_closing_price_stat(price):
    if avg_price is not None:
        return "{} ({}%)".format(price, round(100 * (price - avg_price) / avg_price, 0))
    else:
        return "{} (N/A)".format(price)


yf.pdr_override()
today = datetime.date.today()
start_date = (today - datetime.timedelta(days=365)).strftime("%Y-%m-%d") if start_date is None else start_date
end_date = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
print("get_data_yahoo from {} to {} for {}".format(start_date, end_date, symbol))
df = pdr.get_data_yahoo(symbol, start=start_date, end=end_date, period='1d')

trading_days_processed = 0
closing_price = None
period_open_price = round(df.head(1)['Close'][0], rounding_precision)
if not df.empty:
    buy(symbol, start_date, round(df.head(1)['Close'][0], rounding_precision), buying_base_unit_value, "initial buy")
    for index, row in df.iterrows():
        trading_days_processed = trading_days_processed + 1
        closing_price = round(row['Close'], rounding_precision)
        if closing_price > last_peak:
            last_peak = closing_price
        idle_day = None

        if avg_price is not None and closing_price <= avg_price * (1 - cut_loss_at / 100):
            sell(symbol, row.name.date(), closing_price, "cut loss at {}%".format(cut_loss_at))
        elif closing_price <= last_buy_price * (1 - double_down_on_drop / 100):
            buy(symbol, row.name.date(), closing_price, None, "double down on dip of {}% from last buy price {}".format(double_down_on_drop, last_buy_price))
        elif closing_price < last_peak * (1 - buy_on_dip_from_last_high / 100):
            buy(symbol, row.name.date(), closing_price, buying_base_unit_value, "Dip of {}% from last peak {}".format(buy_on_dip_from_last_high, last_peak))
            last_peak = closing_price
        elif avg_price is not None and closing_price >= avg_price * (1 + take_profit_on / 100):
            sell(symbol, row.name.date(), closing_price, "on {}% gain".format(take_profit_on))
        elif avg_price is not None and accumulate_fraction != 0 and avg_price >= closing_price:
            buy(symbol, row.name.date(), closing_price, accumulate_fraction, "Accumulate")
        else:
            add_audit_trail_entry(symbol, row.name.date(), "None", "Idle", closing_price, 0, 0, 0)
            if print_audit_trail and show_idle_day_audit_trail:
                print("[{}][NONE][NONE] Price {} Last Buy {} Last High {} | cum {}@{} = {} | remaining capital {}"
                      .format(row.name.date(), closing_price, last_buy_price, last_peak, cum_qty, avg_price, cum_cost, remaining_capital))
print("Total Trading Days processed from {} to {} is {}".format(start_date, end_date, trading_days_processed))
portfolio_value = round(closing_price * cum_qty, rounding_precision)
nav = round(portfolio_value + remaining_capital, rounding_precision)
print("Last close {} Remaining Capital {} Portfolio Value {} Total {}".format(closing_price, remaining_capital, portfolio_value, nav))
table = PrettyTable()
table.align = "r"
table_header = ["Symbol", "Date", "Action", "Scenario", "Closing Price", "Action Qty", "Action Price", "Action Consideration",
                "Cum Qty", "Average Price", "Cum Cost", "Current Value", "Remaining Capital", "NAV", "Gain"]
table.field_names = table_header
for row in audit_trail:
    if not show_idle_day_audit_trail and row[1] == 'None':
        continue
    table.add_row(row)
print(table)
