import csv
import datetime

import requests
import json
from prettytable import PrettyTable
import pickle
from colorama import init
from termcolor import colored
import yfinance as yf
import pandas as pd
from pandas_datareader import data as pdr

#  Control parameters
ignore_on_behalf_investing = True
mimic_real_timeline = True
max_forecast_offsets = 1
sgd_to_lkr_rate = 0
usd_to_lkr_rate = 0

account_statement_file_names = [
    r"C:\Users\kasun\Google Drive\Documents\Finances\Portfolio Manager\Account Statement Sep EOM.csv",
    r"C:\Users\kasun\Google Drive\Documents\Finances\Portfolio Manager\Account Statement.csv"]

buy_trade_books = {}
sell_trade_books = {}
trade_commission_percentage = 1.12

realized_profits = {}
closed_position_costs = {}
closed_position_sales_proceeds = {}
portfolio_summary = []
current_portfolio_cost_by_symbol = {}
current_portfolio_sales_proceeds_by_symbol = {}
last_recorded_prices = None

# ===========================================================================
real_estate_investment = 4950000.0
lending = (0 + 0.0)
sl_banks = (0 + 0)
sg_banks = round(105000.00 + 0 + 0 +  # uob + dbs
                 5000 +  # lending
                 22742.00 +  # Fidelity - current balance on 13 May 2024
                 1141.05 +  # Fidelity - April
                 850 * 4 +  # share scheme - April'24
                 - 0  # sc cc loan
                 , 2)

burrowing = 0  # 1100000.0  # from Ama 1,000,000 + interest 100,000
# ===========================================================================
portfolio_target = 30000000.0  # EOY 2022 target
off_the_market_deposits = 2000000.00
withdrawals = (2000000.0 + 500000.0)
deposits_for_reinvesting_withdrawals = (400000 + 2285000)
on_behalf_deposits = 1100100.0  # (100100.00 + 1000000.00) for Nisala 
on_behalf_cash_balance = 0
on_behalf_dividends_reinvested = 105045.00  # for Nisala
recent_price_cache = {}


class Position:
    def __init__(self, symbol, qty, price):
        self.symbol = symbol
        self.price = price
        self.qty = qty
        self.original_qty = qty
        self.forecast_profit = 0
        self.forecast_profit_percentage = 0
        self.forecast_sales_proceeds = 0
        self.cost = 0
        self.forecast_sale_prices = {}
        self.sale_proceed_by_price_point = {}
        self.profit_by_price_point = {}

    def compute_open_position_statistics(self):
        current_price = get_valuation_price(self.symbol)
        self.forecast_sales_proceeds = get_sales_proceeds(self.qty, current_price)
        self.forecast_profit = round(self.forecast_sales_proceeds - self.cost, 2)
        if self.cost != 0.0:
            self.forecast_profit_percentage = round((self.forecast_profit / self.cost) * 100, 2)
        else:
            self.forecast_profit_percentage = 100.0
        for offset in range(max_forecast_offsets):
            self.forecast_sale_prices[offset] = \
                get_sale_price_for_expected_profit_percentage(self.cost, self.qty, offset)
            self.sale_proceed_by_price_point[offset] = \
                get_sales_proceeds(self.qty, self.forecast_sale_prices[offset])
            self.profit_by_price_point[offset] = \
                self.sale_proceed_by_price_point[offset] - self.cost
        return self


class AggregatePosition(Position):
    def add_trade(self, qty, cost):
        self.qty += qty
        self.cost = round(self.cost + cost, 2)
        self.original_qty = self.qty

    def offset_aggressor(self, aggressor):
        if self.qty >= aggressor.qty:
            effective_qty = aggressor.qty
            self.cost = round(self.cost * ((self.qty - effective_qty) / self.qty), 2)
            self.qty -= aggressor.qty
            aggressor.qty = 0
        else:
            effective_qty = self.qty
            aggressor.qty -= self.qty
            self.qty = 0
        buy_value = get_cost(effective_qty, self.price)
        sell_value = get_sales_proceeds(effective_qty, aggressor.price)
        profit = round(sell_value - buy_value, 2)
        return profit, buy_value, sell_value


def convert_symbol_to_yahoo_format(symbol):
    return '{}.CM'.format(symbol.replace('.', ''))


def preload_prices(counters, convert_symbol, curr):
    if curr is None:
        curr = "LKR"
    for counter in counters:
        price, currency = \
            get_last_traded_price(convert_symbol_to_yahoo_format(counter) if convert_symbol else counter, curr)
        recent_price_cache[counter] = {
            "price": price,
            "currency": curr
        }


def get_cse_last_traded_price(counter):
    if counter in recent_price_cache:
        return recent_price_cache[counter]["price"]
    last_traded_price, currency = get_last_traded_price(convert_symbol_to_yahoo_format(counter))
    if last_traded_price is not None:
        return last_traded_price
    response = requests.request("GET", 'https://sl-codes.herokuapp.com/lk/stocks/v1', params={'companySymbol': counter})
    if response.status_code == 200:
        res_dict = json.loads(response.text)
        if 'lastTradedPrice' in res_dict and res_dict['lastTradedPrice'] is not None:
            return res_dict['lastTradedPrice']
        else:
            return last_recorded_prices[counter]
    else:
        print("Failed to retrieve last traded price for {0}".format(counter))
        exit(1)


def get_last_traded_price(symbol, currency=None):
    if symbol in recent_price_cache:
        return recent_price_cache[symbol]["price"], recent_price_cache[symbol]["currency"]
    yf.pdr_override()
    today = datetime.date.today()
    start_date = (today - datetime.timedelta(days=5)).strftime("%Y-%m-%d")
    end_date = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    # print("get_data_yahoo from {0} to {1} for {2}".format(start_date, end_date, symbol))
    df = pdr.get_data_yahoo(symbol, start=start_date, end=end_date, period='1d')

    if not df.empty:
        if currency is None:
            dq = pdr.get_quote_yahoo([symbol])
            currency = dq.tail(1)['currency'][0]
        print("Price read from Yahoo for {0} : {1} {2}".format(symbol, round(df.tail(1)['Close'][0], 2), currency))
        return round(df.tail(1)['Close'][0], 2), currency
    return 0, None


def value_sg_portfolio():
    portfolio_value = 0.0
    for position in sgx_portfolio:
        last_traded_price, currency = get_last_traded_price(position["symbol"])
        portfolio_value += last_traded_price * position["qty"]
    return round(portfolio_value, 2)


def value_global_portfolio():
    portfolio_value = 0.0
    for position in global_portfolio:
        last_traded_price, currency = get_last_traded_price(position["symbol"])
        value = round(last_traded_price * position["qty"], 2)
        portfolio_value += value
        print("Global Portfolio {} : {}@{} = {} {}".format(position["symbol"], position["qty"], last_traded_price, value, currency))
    return round(portfolio_value, 2)


def value_trading_portfolio():
    portfolio_value = 0.0
    for position in trading_portfolio:
        last_traded_price = get_cse_last_traded_price(position["symbol"])
        portfolio_value += get_sales_proceeds(last_traded_price, position["qty"])
    return round(portfolio_value, 2)


def get_valuation_price(counter):
    if counter not in valuation_prices:
        valuation_prices[counter] = get_cse_last_traded_price(counter)

    return valuation_prices[counter]


def get_exchange_rate(from_currency, to_currency):
    url = 'https://v6.exchangerate-api.com/v6/6248dad3f8ce10fad08ab9ba/latest/{}'.format(from_currency)
    response = requests.get(url)
    data = response.json()
    return data["conversion_rates"][to_currency]


def get_cost(qty, price):
    return round(qty * price * (1 + (trade_commission_percentage / 100)), 2)


def get_sales_proceeds(qty, price):
    return round(qty * price * (1 - (trade_commission_percentage / 100)), 2)


def get_sale_price_for_expected_profit_percentage(cost, qty, profit_percentage):
    expected_sales_proceeds = round(cost * (profit_percentage / 100) + cost, 2)
    return round(expected_sales_proceeds / (qty * 0.9888), 2)


def print_open_positions(symbol):
    if symbol in buy_trade_books and len(buy_trade_books[symbol]) != 0:
        valuation_price = get_valuation_price(symbol)
        current_market_price = get_cse_last_traded_price(symbol)
        distance_to_valuation = 0.0
        if current_market_price != 0.0 and current_market_price != -1 and current_market_price is not None:
            distance_to_valuation = round(((valuation_price - current_market_price) * 100 / current_market_price), 0)

        pretty_table = PrettyTable()
        table_header = [symbol, "Qty", "Original Qty", "Price", "Cost",
                        "Valuation Price (%)" if valuation_price != current_market_price else "Valuation Price",
                        "Current Price",
                        "Sales Proceeds", "Profit", "Profit %"] + list(range(max_forecast_offsets))
        pretty_table.field_names = table_header
        total_forecast_sales_proceeds = 0
        total_cost = 0
        total_qty = 0
        total_forecast_profit = 0
        pos_counter = 0
        forecast_profit_by_price_point = [0.0] * max_forecast_offsets

        for key, position in sorted(buy_trade_books[symbol].items()):
            if position is not None:
                pos_counter += 1
                open_pos = position.compute_open_position_statistics()
                row = [pos_counter, open_pos.qty, open_pos.original_qty, open_pos.price, open_pos.cost,
                       "{0} ({1}%)".format(valuation_price,
                                           distance_to_valuation) if valuation_price != current_market_price
                       else valuation_price,
                       current_market_price, open_pos.forecast_sales_proceeds, open_pos.forecast_profit,
                       open_pos.forecast_profit_percentage] + list(open_pos.forecast_sale_prices.values())
                pretty_table.add_row(row)

                total_forecast_sales_proceeds += open_pos.forecast_sales_proceeds
                total_cost += open_pos.cost
                total_forecast_profit += open_pos.forecast_profit
                total_qty += open_pos.qty

                counter = 0
                for item in open_pos.profit_by_price_point.values():
                    forecast_profit_by_price_point[counter] += item
                    forecast_profit_by_price_point[counter] = round(forecast_profit_by_price_point[counter], 2)
                    counter += 1

        total_forecast_sales_proceeds = round(total_forecast_sales_proceeds, 2)
        total_cost = round(total_cost, 2)
        current_portfolio_sales_proceeds_by_symbol[symbol] = total_forecast_sales_proceeds
        current_portfolio_cost_by_symbol[symbol] = total_cost

        # print summary row
        column_index = 0
        totals_table_row = []
        for column in table_header:
            totals_table_row.append("-" * 3)
            column_index += 1
        totals_table_row[0] = symbol
        totals_table_row[1] = total_qty
        totals_table_row[4] = current_portfolio_cost_by_symbol[symbol]
        totals_table_row[7] = total_forecast_sales_proceeds
        totals_table_row[8] = round(total_forecast_profit, 2)

        portfolio_summary.append([symbol, total_qty, current_portfolio_cost_by_symbol[symbol],
                                  total_forecast_sales_proceeds, round(total_forecast_profit, 2)])

        for item in forecast_profit_by_price_point:
            totals_table_row[10:] = forecast_profit_by_price_point
        separator_row = []
        column_index = 0
        for column in table_header:
            separator_row.append("=" * max(len(str(column)), 9))
            column_index += 1
        pretty_table.add_row(separator_row)
        pretty_table.add_row(totals_table_row)

        print(pretty_table)


def print_profits():
    print("=======================================================")
    print("=========== Materialized Profits ======================")
    print("=======================================================")
    total_profit = 0
    for symbol in sorted(realized_profits):
        profit_percentage = 0
        realized_profits[symbol] = round(realized_profits[symbol], 2)
        if realized_profits[symbol] != 0.0:
            profit_percentage = round(realized_profits[symbol] * 100 / closed_position_costs[symbol], 2)
        if profit_percentage > 0.0:
            print(colored("{0} = {1} ({2}%)".format(symbol, realized_profits[symbol], profit_percentage), 'green'))
        else:
            print(colored("{0} = {1} ({2}%)".format(symbol, realized_profits[symbol], profit_percentage), 'red'))
        total_profit += realized_profits[symbol]
    total_profit = round(total_profit, 2)
    print("=======================================================")
    print("Total Profit {0}".format(total_profit))
    print("=======================================================")


def print_trades(symbol):
    if symbol in buy_trade_books and len(buy_trade_books[symbol]) != 0:
        print("============ Buy trades for {0} ============".format(symbol))
        for key, value in sorted(buy_trade_books[symbol].items()):
            if value is not None:
                value.compute_open_position_statistics()
        print("====================================================")

    if symbol in sell_trade_books and len(sell_trade_books[symbol]) != 0:
        print("============ Sell trades for {0} ============".format(symbol))
        if symbol in sell_trade_books:
            for key, value in sorted(sell_trade_books[symbol].items()):
                if value is not None:
                    value.compute_open_position_statistics()
        print("====================================================")


def get_ca_adjusted_position(symbol, traded_date, trade_qty, trade_price):
    if symbol in splits:
        trade_date = datetime.datetime.strptime(traded_date, '%d/%m/%Y')
        split_date = datetime.datetime.strptime(splits[symbol]["date"], '%Y/%m/%d')
        if trade_date < split_date:
            trade_qty = round(trade_qty * splits[symbol]["ratio"], 0)
            trade_price = round(trade_price / splits[symbol]["ratio"], 2)
    return trade_qty, trade_price


def compute_open_positions(symbol, print_pos=False):
    profit = 0
    cost = 0
    sales_proceed = 0
    if symbol not in buy_trade_books:
        return
    if mimic_real_timeline:
        total_qty = 0
        total_cost = 0
        for buy_price, buy_trade in sorted(buy_trade_books[symbol].items()):
            total_qty += buy_trade.qty
            total_cost += buy_trade.cost
        avg_price = 0.0
        if total_qty != 0.0:
            avg_price = round(total_cost / total_qty, 2)
        del buy_trade_books[symbol]
        buy_trade_books[symbol] = {}
        buy_trade_books[symbol][avg_price] = AggregatePosition(symbol, 0, avg_price)
        buy_trade_books[symbol][avg_price].add_trade(total_qty, total_cost)

    for buy_price, buy_trade in sorted(buy_trade_books[symbol].items()):
        if symbol in sell_trade_books:
            for sell_price, sell_trade in reversed(sorted(sell_trade_books[symbol].items())):
                if sell_trade is None:
                    continue
                profit_stats = buy_trade.offset_aggressor(sell_trade)
                profit += profit_stats[0]
                cost += profit_stats[1]
                sales_proceed += profit_stats[2]
                if sell_trade.qty == 0:
                    sell_trade_books[symbol][sell_price] = None
                    del sell_trade_books[symbol][sell_price]
                    if len(sell_trade_books[symbol]) == 0:
                        del sell_trade_books[symbol]
                if buy_trade.qty == 0:
                    buy_trade_books[symbol][buy_price] = None
                    del buy_trade_books[symbol][buy_price]
                    if len(buy_trade_books[symbol]) == 0:
                        del buy_trade_books[symbol]
                    break
    if symbol not in realized_profits:
        realized_profits[symbol] = 0.0
    realized_profits[symbol] += round(profit, 2)
    if symbol not in closed_position_costs:
        closed_position_costs[symbol] = 0.0
    closed_position_costs[symbol] += round(cost, 2)
    if symbol not in closed_position_sales_proceeds:
        closed_position_sales_proceeds[symbol] = 0.0
    closed_position_sales_proceeds[symbol] += round(sales_proceed, 2)
    if print_pos:
        print_open_positions(symbol)


def get_non_on_behalf_trade_qty(symbol, side, price, qty, value):
    non_onbehalf_trade_qty = qty
    non_onbehalf_trade_value = value
    on_behalf_trade_key = None
    if ignore_on_behalf_investing:
        for key, on_behalf_trade in on_behalf_trades.items():
            if on_behalf_trade["symbol"] == symbol and \
                    on_behalf_trade["side"] == side and \
                    on_behalf_trade["price"] == price:
                on_behalf_trade_key = key
                if qty >= on_behalf_trade["qty"]:
                    non_onbehalf_trade_qty = qty - on_behalf_trade["qty"]
                    on_behalf_trade["qty"] = 0
                else:
                    non_onbehalf_trade_qty = 0
                    on_behalf_trade["qty"] -= qty
                break
        if on_behalf_trade_key is not None and on_behalf_trades[on_behalf_trade_key]["qty"] == 0:
            del on_behalf_trades[on_behalf_trade_key]
    if qty != non_onbehalf_trade_qty and non_onbehalf_trade_value != 0:
        non_onbehalf_trade_value = round(value * (non_onbehalf_trade_qty / qty), 2)
    return non_onbehalf_trade_qty, non_onbehalf_trade_value


def analyse_portfolio():
    global last_recorded_prices, sgd_to_lkr_rate, usd_to_lkr_rate
    sgd_to_lkr_rate = get_exchange_rate("SGD", "LKR")
    usd_to_lkr_rate = get_exchange_rate("USD", "LKR")
    usd_to_sgd_rate = get_exchange_rate("USD", "SGD")
    sgd_to_aud_rate = get_exchange_rate("SGD", "AUD")
    total_records = total_trades = total_deposits = total_withdrawals = total_turnover = current_cash_balance = 0
    last_recorded_prices = pickle.load(open("market_prices.pckl", "rb"))
    init()  # termcolor
    investment_start_date = None
    investment_end_date = datetime.datetime.now()

    for file_name in account_statement_file_names:
        with open(file_name, encoding="utf8") as csv_file:
            print("Reading File {0}".format(file_name))
            csv_reader = csv.reader(csv_file, delimiter=',')
            acc_summary = list(csv_reader)
            for record in acc_summary:
                total_records += 1
                if record[1] == "B" or record[1] == "S" or record[1] == "BU" or record[1] == "SL":
                    total_trades += 1
                    qty = int(record[4].replace(',', ''))
                    price = float(record[5].replace(',', ''))
                    value = float(record[6].replace(',', ''))
                    total_turnover += abs(value)
                    current_cash_balance = float(record[7].replace(',', ''))
                    if record[1] == "B" or record[1] == "BU":
                        symbol = record[3][12:]
                        qty, value = get_non_on_behalf_trade_qty(symbol, "B", price, qty, value)
                        if qty <= 0:
                            continue
                        qty, price = get_ca_adjusted_position(symbol, record[0], qty, price)
                        if symbol not in buy_trade_books:
                            buy_trade_books[symbol] = {}
                        if price not in buy_trade_books[symbol]:
                            buy_trade_books[symbol][price] = AggregatePosition(symbol, 0, price)
                        buy_trade_books[symbol][price].add_trade(qty, value)
                    elif record[1] == "S" or record[1] == "SL":
                        symbol = record[3][8:]
                        qty, value = get_non_on_behalf_trade_qty(symbol, "S", price, qty, value)
                        if qty <= 0:
                            continue
                        qty, price = get_ca_adjusted_position(symbol, record[0], qty, price)
                        if symbol not in sell_trade_books:
                            sell_trade_books[symbol] = {}
                        if price not in sell_trade_books[symbol]:
                            sell_trade_books[symbol][price] = AggregatePosition(symbol, 0, price)
                        sell_trade_books[symbol][price].add_trade(qty, value)
                        if mimic_real_timeline:
                            compute_open_positions(symbol, False)
                elif record[1] == "R":
                    total_deposits += abs(float(record[6].replace(',', '')))
                    print("{2} - Deposits on the market {0} ({1})".
                          format(abs(float(record[6].replace(',', ''))), total_deposits - total_withdrawals, record[0]))
                    current_cash_balance = float(record[7].replace(',', ''))
                elif record[1] == "PV":
                    total_withdrawals += abs(float(record[6].replace(',', '')))
                    current_cash_balance = float(record[7].replace(',', ''))
                    print("{2} - Withdrawal from the market {0} ({1})".
                          format(abs(float(record[6].replace(',', ''))), total_deposits - total_withdrawals, record[0]))
                else:
                    continue
                if investment_start_date is None:
                    investment_start_date = datetime.datetime.strptime(record[0], '%d/%m/%Y')
    print("{} - off the market deposits {} ({})".
          format('N/A', off_the_market_deposits, off_the_market_deposits + total_deposits - total_withdrawals, ))
    for trade in off_market_trades:
        qty, value = get_non_on_behalf_trade_qty(trade["symbol"], "B", trade["price"], trade["qty"], trade["value"])
        if qty <= 0:
            continue
        if trade["symbol"] not in buy_trade_books:
            buy_trade_books[trade["symbol"]] = {}
        if trade["price"] not in buy_trade_books[trade["symbol"]]:
            buy_trade_books[trade["symbol"]][trade["price"]] = AggregatePosition(trade["symbol"], 0, trade["price"])
        buy_trade_books[trade["symbol"]][trade["price"]].add_trade(qty, value)

    current_portfolio_total_sales_proceeds = 0
    current_portfolio_total_cost = 0
    preload_prices(list(buy_trade_books.keys()), True, "LKR")
    for symbol in sorted(buy_trade_books):
        compute_open_positions(symbol)
        if symbol in current_portfolio_sales_proceeds_by_symbol:
            current_portfolio_total_sales_proceeds += current_portfolio_sales_proceeds_by_symbol[symbol]
        if symbol in current_portfolio_cost_by_symbol:
            current_portfolio_total_cost += current_portfolio_cost_by_symbol[symbol]
    current_portfolio_total_sales_proceeds = round(current_portfolio_total_sales_proceeds, 2)
    # print_profits()
    print("Total records scanned {}. Total trades {}".format(total_records, total_trades))
    print("Total Deposits on the market {}".format(total_deposits))
    print("Reinvesting deposits of earlier withdrawals {}".format(deposits_for_reinvesting_withdrawals))
    total_deposits -= deposits_for_reinvesting_withdrawals  # adjust the total deposits
    print("Adjusted total deposits on the market {}".format(total_deposits))
    print("Total Deposits off the market {}".format(off_the_market_deposits))
    print("Total deposited capital".format(total_deposits + off_the_market_deposits))

    if ignore_on_behalf_investing:
        total_deposited_capital_in_the_market = total_deposits - \
                                                (on_behalf_deposits + personal_dividends_reinvested +
                                                 on_behalf_dividends_reinvested)
        total_deposited_capital = total_deposited_capital_in_the_market + off_the_market_deposits
        total_dividends_reinvested = personal_dividends_reinvested
        print("Total on-behalf deposits {}".format(on_behalf_deposits + on_behalf_dividends_reinvested))
    else:
        total_deposited_capital_in_the_market = total_deposits - \
                                                (personal_dividends_reinvested + on_behalf_dividends_reinvested)
        total_deposited_capital = total_deposited_capital_in_the_market + off_the_market_deposits
        total_dividends_reinvested = personal_dividends_reinvested + on_behalf_dividends_reinvested

    print("Total dividends reinvested {}".format(total_dividends_reinvested))
    print("Total deposited capital excluding dividend reinvesting deposits {}".format(total_deposited_capital))

    cash_balance = round(-1 * current_cash_balance, 2)
    if ignore_on_behalf_investing:
        cash_balance = round(cash_balance - on_behalf_cash_balance, 2)
    print("Cash balance {}".format(cash_balance))
    print("Total Withdrawals {}".format(withdrawals))
    print("Total Withdrawals All Time {}".format(total_withdrawals))
    total_invested_capital = round(total_deposited_capital - cash_balance, 2)
    print("Total turn over (all time) {}".format(round(total_turnover, 2)))
    # print("Total invested capital (all time) {}".format(total_invested_capital))
    print("=======================================================")
    print("Total invested capital (current) {}".format(round(total_invested_capital - withdrawals), 2))
    print("Current portfolio valuation {}".format(current_portfolio_total_sales_proceeds))
    current_profit_perc = \
        round((current_portfolio_total_sales_proceeds + cash_balance + withdrawals - total_deposited_capital) * 100 /
              total_deposited_capital, 2)
    total_gain = round((current_portfolio_total_sales_proceeds + cash_balance + withdrawals) - total_deposited_capital,
                       2)
    print("Total gain to date {0} ({1}%)".format(total_gain, current_profit_perc))

    investment_period_in_days = investment_end_date - investment_start_date
    print("Investment Period  {0} - {1} to {2}".format(investment_period_in_days.days,
                                                       investment_start_date.strftime("%Y/%m/%d"),
                                                       investment_end_date.strftime("%Y/%m/%d")))
    total_stock_portfolio = round(current_portfolio_total_sales_proceeds + cash_balance, 0)
    print("Total Stock portfolio value {0}".format(total_stock_portfolio))
    print("=======================================================")
    sg_stock_portfolio_valuation = value_sg_portfolio()
    global_portfolio_valuation = value_global_portfolio()
    sg_total_portfolio_in_sgd = \
        round(sg_banks + sg_stock_portfolio_valuation + global_portfolio_valuation * usd_to_sgd_rate, 0)
    sg_total_portfolio = round((sg_banks + sg_stock_portfolio_valuation) * sgd_to_lkr_rate
                               + global_portfolio_valuation * usd_to_lkr_rate, 0)
    total_liquid_assets_sl = round(total_stock_portfolio + sl_banks + lending - burrowing, 0)
    total_assets_sl = round(total_stock_portfolio + real_estate_investment + sl_banks + lending - burrowing, 0)
    total_assets_estimate = round(total_assets_sl + sg_total_portfolio, 0)
    total_liquid_assets_estimate = round(total_liquid_assets_sl + sg_total_portfolio, 0)
    print("=======================================================")
    print("Exchange Rates : SGD-LKR={}, USD-LKR={}, USD-SGD={}, SGD-AUD={}".format(sgd_to_lkr_rate, usd_to_lkr_rate, usd_to_sgd_rate, sgd_to_aud_rate))
    print("Lending {:,}".format(lending))
    print("Real Estate {:,}".format(real_estate_investment))
    print("Cash at Bank SL {:,}".format(sl_banks))
    print("Cash at Bank SG {:,} (SGD {:,}) (AUD {:,})".format(round(sg_banks * sgd_to_lkr_rate, 2), sg_banks, round(sg_banks * sgd_to_aud_rate, 2)))
    print("Cash balance in CDS {}".format(cash_balance))
    print("Total Stock portfolio value SL {:,} (SGD {:,})".format(current_portfolio_total_sales_proceeds, round(
        current_portfolio_total_sales_proceeds / sgd_to_lkr_rate, 2)))
    print("Total Stock portfolio value SG {:,} (SGD {:,})".
          format(round(sg_stock_portfolio_valuation * sgd_to_lkr_rate, 2), sg_stock_portfolio_valuation))
    print("Total global portfolio value SG {:,} (SGD {:,})".
          format(round(global_portfolio_valuation * usd_to_lkr_rate, 2),
                 round(global_portfolio_valuation * usd_to_sgd_rate, 2)))
    print("Burrowing -{:,}".format(burrowing))
    print("Total Liquid Assets as of now LK {:,} (SGD {:,})".format(total_liquid_assets_sl,
                                                                    round(total_liquid_assets_sl / sgd_to_lkr_rate, 2)))
    print("Total Liquid Assets as of now SG {:,} (SGD {:,}) (AUD {:,})".format(sg_total_portfolio, sg_total_portfolio_in_sgd, round(sg_total_portfolio_in_sgd * sgd_to_aud_rate), 2))
    print("Total Liquid Assets as of now {:,}".format(total_liquid_assets_sl + sg_total_portfolio))
    print("Total Assets as of now LK {:,}".format(total_assets_sl))
    print("Total Assets as of now SG {:,}".format(sg_total_portfolio))
    print("Total Assets as of now {:,}".format(total_assets_sl + sg_total_portfolio))
    print("=======================================================")

    # trading_portfolio_value = value_trading_portfolio()
    # print("Trading Portfolio Value {:,}".format(trading_portfolio_value))
    # print("Cash at Hand {:,}".format(round((sl_banks + cash_balance), 0)))
    # print("Total Cash at hand (% of total SL portfolio value) {:,} ({})%".
    #       format(round((sl_banks + cash_balance + trading_portfolio_value), 0),
    #              round((sl_banks + cash_balance + trading_portfolio_value) * 100 / total_stock_portfolio, 2)))

    print("=======================================================")
    print("Total Estimated EOY Assets {:,}".format(total_assets_estimate))
    print("Total Estimated EOY Liquid Assets {:,}".format(total_liquid_assets_estimate))
    print("=======================================================")
    pickle.dump(valuation_prices, open("market_prices.pckl", "wb"))


def transform_data_file_in_to_dicts():
    df = pd.read_excel(r'C:\Users\kasun\Google Drive\Documents\Finances\Portfolio Analysis.xlsx',
                       sheet_name=None, engine='openpyxl')

    if df['on_behalf_trades'] is not None:
        globals()['on_behalf_trades'] = {}
        counter = 1
        for on_behalf_trade_row in df['on_behalf_trades'].to_dict('records'):
            globals()['on_behalf_trades'][counter] = {
                "symbol": on_behalf_trade_row['symbol'],
                "side": on_behalf_trade_row['side'],
                "qty": on_behalf_trade_row['qty'],
                "price": on_behalf_trade_row['price'],
            }
            counter += 1

    if df['sgx_portfolio'] is not None:
        globals()['sgx_portfolio'] = df['sgx_portfolio'].to_dict('records')
        preload_prices([item['symbol'] for item in globals()['sgx_portfolio']], False, "SGD")

    if df['global_portfolio'] is not None:
        globals()['global_portfolio'] = df['global_portfolio'].to_dict('records')
        preload_prices([item['symbol'] for item in globals()['global_portfolio']], False, "USD")

    if df['trading_portfolio'] is not None:
        globals()['trading_portfolio'] = df['trading_portfolio'].to_dict('records')

    if df['valuation_prices'] is not None:
        globals()['valuation_prices'] = {}
        for price_row in df['valuation_prices'].to_dict('records'):
            globals()['valuation_prices'][price_row['Symbol']] = price_row['Price']

    if df['splits'] is not None:
        globals()['splits'] = {}
        for splits_row in df['splits'].to_dict('records'):
            globals()['splits'][splits_row['symbol']] = {
                "date": str(splits_row['date']),
                "ratio": splits_row['ratio']
            }

    if df['dividends'] is not None:
        globals()['personal_dividends_reinvested'] = 0
        for div_row in df['dividends'].to_dict('records'):
            globals()['personal_dividends_reinvested'] += div_row['Dividend Amount']

    if df['off_market_trades'] is not None:
        globals()['off_market_trades'] = df['off_market_trades'].to_dict('records')


def render_portfolio_ui():
    import PySimpleGUI as sg
    layout = [[sg.Text("Hello from PySimpleGUI")], [sg.Button("OK")]]

    # Create the window
    # window = sg.Window("Demo", layout)

    columns = ["Symbol", "Qty", "Cost", "Sales Proceeds", "Profit Forecast"]
    total_cost = total_sales_proceeds = total_profit_forecast = 0
    for position in portfolio_summary:
        total_cost += position[2]
        total_sales_proceeds += position[3]
        total_profit_forecast += position[4]

        position[1] = '{:,}'.format(position[1])
        position[2] = '{:,}'.format(position[2])
        position[3] = '{:,}'.format(position[3])
        position[4] = '{:,}'.format(position[4])
    portfolio_summary.append(["Total", "", '{:,}'.format(round(total_cost, 2)),
                              '{:,}'.format(round(total_sales_proceeds, 2)),
                              '{:,}'.format(round(total_profit_forecast, 2))])

    layout = [
        [sg.Table(values=portfolio_summary,
                  headings=columns,
                  auto_size_columns=False)]
    ]

    window = sg.Window('Table', layout, grab_anywhere=False)

    # Create an event loop
    while True:
        event, values = window.read()
        # End program if user closes window or
        # presses the OK button
        if event == "OK" or event == sg.WIN_CLOSED:
            break

    window.close()


if __name__ == "__main__":
    transform_data_file_in_to_dicts()
    globals()['valuation_prices'] = {}
    analyse_portfolio()
    # render_portfolio_ui()
