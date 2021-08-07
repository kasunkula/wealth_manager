import csv
import datetime

import requests
import json
from prettytable import PrettyTable
import pickle
from colorama import init
from termcolor import colored

#  Control parameters
ignore_on_behalf_investing = True
mimic_real_timeline = True
max_forecast_offsets = 1
sgd_to_lkr_rate = 148

account_statement_file_names = [r"C:\Users\kasun\Desktop\Account Statement Sep EOM.csv",
                                r"C:\Users\kasun\Desktop\Account Statement.csv"]
buy_trade_books = {}
sell_trade_books = {}
sales_commission_percentage = 1.12

realized_profits = {}
closed_position_costs = {}
closed_position_sales_proceeds = {}
portfolio_summary = []

current_portfolio_cost_by_symbol = {}
current_portfolio_sales_proceeds_by_symbol = {}
market_prices = {  # EOY 2021
    "BIL.N0000": 10.00,
    "BRWN.N0000": 250.00,
    "DIPD.N0000": 80.00,
    # "EXPO.N0000": 70.00,
    "HAYC.N0000": 120.00,
    "HNB.N0000": 160.00,
    "JKH.N0000": 160.00,
    "SAMP.N0000": 60.00,
    "TKYO.X0000": 70.00,
    "LFIN.X0000": 75.00,
}

market_prices = {}

last_recorded_prices = None

#  Fund statistics
portfolio_target = 27000000.0 # EOY 2021 target
burrowed_money = 1100000.0  # from Ama 1,000,000 + interest 100,000
off_the_market_deposits = 2000000.00
withdrawals = (2000000.0 + 1680000)
deposits_for_reinvesting_withdrawals = (400000 + 0)
real_estate = 4250000.0
lending = 100000.0
sl_banks = (111004.0 + 2100000.0)
sg_banks = 3000
sg_stocks = 4435
estimated_savings = 3600000
on_behalf_deposits = 1100100.0  # (100100.00 + 1000000.00) for Nisala
on_behalf_cash_balance = 0
on_behalf_dividends_reinvested = 105045.00  # for Nisala
personal_dividends_reinvested = (245810.00 +  # SAMP
                                 15900.00 +  # JKH
                                 14745.00 +  # AEL
                                 15000 +  # JKH
                                 15000 +  # EXPO
                                 5486 +  # TPL
                                 8150 +  # RIL
                                 2437 +  # ACL
                                 10050 +  # LWL
                                 1000 +  # SUN
                                 9900 +  # RCL
                                 2000 +  # HHL
                                 3600 +  # RCL
                                 14000 +  # ??
                                 7505 +  # ??
                                 11550 +  # ??
                                 1016 +  # ??
                                 15600 +  # REG
                                 84348 +  # HNB
                                 5000.00 +  # ??
                                 9600.00 +  # ??
                                 24687.50 +  # ??
                                 480.00 +  # ??
                                 3250.00 +  # ??
                                 22252.23 +  # ??
                                 5875.00 +  # ??
                                 129525)  # SAMP

off_market_trades = {
    1: {
        "symbol": "ASPH.N0000",
        "side": "B",
        "qty": 10000000,
        "price": 0.20,
        "value": 2000000.00,
    },
    2: {
        "symbol": "PLC.N0000",
        "side": "B",
        "qty": 2692,
        "price": 0.0,
        "value": 0.0,
    },
    3: {
        "symbol": "ASPH.R0000",
        "side": "S",
        "qty": 2,
        "price": 0.1,
        "value": 0.2,
    },
    4: {
        "symbol": "HNB.N0000",
        "side": "B",
        "qty": 481,
        "price": 0.0,
        "value": 0.0,
    },
}
on_behalf_trades = {
    1: {
        "symbol": "SAMP.N0000",
        "side": "B",
        "qty": 1000,
        "price": 100.10,
    },
    2: {
        "symbol": "HNB.N0000",
        "side": "B",
        "qty": 909,
        "price": 115.50,
    },
    3: {
        "symbol": "SAMP.N0000",
        "side": "B",
        "qty": 7940,
        "price": 124.50,
    },
    4: {
        "symbol": "SAMP.N0000",
        "side": "S",
        "qty": 8940,
        "price": 139,
    },
    5: {
        "symbol": "SAMP.N0000",
        "side": "B",
        "qty": 9021,
        "price": 134.7,
    },
    6: {
        "symbol": "SAMP.N0000",
        "side": "S",
        "qty": 3021,
        "price": 158.00,
    },
    7: {
        "symbol": "HNB.N0000",
        "side": "B",
        "qty": 3347,
        "price": 140.00,
    },
}
splits = {
    "DIPD.N0000": {
        "date": "2021/02/16",
        "ratio": 10
    },
    "HAYC.N0000": {
        "date": "2021/02/16",
        "ratio": 10
    },
    "MGT.N0000": {
        "date": "2021/02/16",
        "ratio": 2
    },
    "REG.N0000": {
        "date": "2021/03/20",
        "ratio": 2
    },
    "SINS.N0000": {
        "date": "2021/03/10",
        "ratio": 3
    },
    "SAMP.N0000": {
        "date": "2021/03/23",
        "ratio": 3
    },
    "SUN.N0000": {
        "date": "2021/03/31",
        "ratio": 3
    },
    "LWL.N0000": {
        "date": "2021/04/01",
        "ratio": 5
    },
    "TILE.N0000": {
        "date": "2021/04/01",
        "ratio": 5
    },
    "HAYL.N0000": {
        "date": "2021/02/16",
        "ratio": 10
    },
    "RCL.N0000": {
        "date": "2021/04/26",
        "ratio": 10
    }
}


def get_current_market_price(counter):
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


def get_valuation_price(counter):
    if counter in market_prices:
        return market_prices[counter]

    market_prices[counter] = get_current_market_price(counter)
    return market_prices[counter]


def get_cost(qty, price):
    return round(qty * price * (1 + (sales_commission_percentage / 100)), 2)


def get_sales_proceeds(qty, price):
    return round(qty * price * (1 - (sales_commission_percentage / 100)), 2)


def get_sale_price_for_expected_profit_percentage(cost, qty, profit_percentage):
    expected_sales_proceeds = round(cost * (profit_percentage / 100) + cost, 2)
    return round(expected_sales_proceeds / (qty * 0.9888), 2)


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


def print_open_positions(symbol):
    if symbol in buy_trade_books and len(buy_trade_books[symbol]) != 0:
        valuation_price = get_valuation_price(symbol)
        current_market_price = get_current_market_price(symbol)
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
    for symbol in realized_profits:
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


def compute_open_positions(symbol, print_pos=True):
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

        avg_price =0.0
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


total_records = 0
total_trades = 0
total_deposits = 0
total_withdrawals = 0
total_turnover = 0
current_cash_balance = 0
last_recorded_prices = pickle.load(open("market_prices.pckl", "rb"))
init()
investment_start_date = None
investment_end_date = datetime.datetime.now()

for file_name in account_statement_file_names:
    with open(file_name, encoding="utf8") as csv_file:
        print("Reading File {0}".format(file_name))
        csv_rows = []
        csv_reader = csv.reader(csv_file, delimiter=',')
        row_counter = 0
        acc_summary = list(csv_reader)
        total_lines = len(acc_summary)
        for record in acc_summary:
            total_records += 1
            if record[1] == "B" or record[1] == "S" or record[1] == "BU" or record[1] == "SL":
                total_trades += 1
                symbol = ""
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
                    if symbol in splits:
                        trade_date = datetime.datetime.strptime(record[0], '%d/%m/%Y')
                        split_date = datetime.datetime.strptime(splits[symbol]["date"], '%Y/%m/%d')
                        if trade_date < split_date:
                            qty = round(qty * splits[symbol]["ratio"], 0)
                            price = round(price / splits[symbol]["ratio"], 2)
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
                    if symbol in splits:
                        trade_date = datetime.datetime.strptime(record[0], '%d/%m/%Y')
                        split_date = datetime.datetime.strptime(splits[symbol]["date"], '%Y/%m/%d')
                        if trade_date < split_date:
                            qty = round(qty * splits[symbol]["ratio"], 0)
                            price = round(price / splits[symbol]["ratio"], 2)
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

print("{} - capital excluding dividends {} ({})".
      format('N/A', personal_dividends_reinvested, off_the_market_deposits
             + total_deposits - total_withdrawals - personal_dividends_reinvested))

print("Total Deposits on and off the market - {}".format(off_the_market_deposits + total_deposits))

for trade in off_market_trades.values():
    qty, value = get_non_on_behalf_trade_qty(trade["symbol"], "B", trade["price"], trade["qty"], trade["value"])
    if qty <= 0:
        continue
    if trade["symbol"] not in buy_trade_books:
        buy_trade_books[trade["symbol"]] = {}
    if price not in buy_trade_books[trade["symbol"]]:
        buy_trade_books[trade["symbol"]][trade["price"]] = AggregatePosition(trade["symbol"], 0, trade["price"])
    buy_trade_books[trade["symbol"]][trade["price"]].add_trade(qty, value)

current_portfolio_total_sales_proceeds = 0
current_portfolio_total_cost = 0
for symbol in sorted(buy_trade_books):
    compute_open_positions(symbol)
    if symbol in current_portfolio_sales_proceeds_by_symbol:
        current_portfolio_total_sales_proceeds += current_portfolio_sales_proceeds_by_symbol[symbol]
    if symbol in current_portfolio_cost_by_symbol:
        current_portfolio_total_cost += current_portfolio_cost_by_symbol[symbol]
current_portfolio_total_sales_proceeds = round(current_portfolio_total_sales_proceeds, 2)
current_portfolio_total_cost = round(current_portfolio_total_cost, 2)
print_profits()
print("Total records {}. Total trades {}".format(total_records, total_trades))
print("Total Deposits on the market {}".format(total_deposits))
print("Reinvesting deposits of earlier withdrawals {}".format(deposits_for_reinvesting_withdrawals))
total_deposits -= deposits_for_reinvesting_withdrawals # adjust the total deposits
print("Adjusted total deposits on the market {}".format(total_deposits))
print("Total Deposits off the market {}".format(off_the_market_deposits))


if ignore_on_behalf_investing:
    total_deposited_capital_in_the_market = total_deposits - \
                                            (on_behalf_deposits + personal_dividends_reinvested +
                                             on_behalf_dividends_reinvested)
    total_deposited_capital = total_deposited_capital_in_the_market + off_the_market_deposits
    total_dividends_reinvested = personal_dividends_reinvested
    print("Total dividends reinvested {}".format(total_dividends_reinvested))
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
total_invested_capital = round(total_deposited_capital - cash_balance, 2)
print("Total turn over (all time) {}".format(round(total_turnover, 2)))
print("Total invested capital (all time) {}".format(total_invested_capital))
print("Total invested capital (current) {}".format(round(total_invested_capital - withdrawals), 2))
print("Current portfolio valuation {}".format(current_portfolio_total_sales_proceeds))
current_profit_perc = \
    round((current_portfolio_total_sales_proceeds + cash_balance + withdrawals - total_deposited_capital) * 100 /
          total_deposited_capital, 2)
total_gain = round((current_portfolio_total_sales_proceeds + cash_balance + withdrawals) - total_deposited_capital, 2)
print("=======================================================")
print("Total gain to date {0} ({1}%)".format(total_gain, current_profit_perc))

investment_period_in_days = investment_end_date - investment_start_date
print("Investment Period  {0} - {1} to {2}".format(investment_period_in_days.days,
                                                   investment_start_date.strftime("%Y/%m/%d"),
                                                   investment_end_date.strftime("%Y/%m/%d")))
total_stock_portfolio = round(current_portfolio_total_sales_proceeds + cash_balance, 2)
print("Total Stock portfolio value {0}".format(total_stock_portfolio))
print("=======================================================")
sg_total_postfolio = round((sg_banks + sg_stocks)*sgd_to_lkr_rate, 2)
total_assets = round(total_stock_portfolio + real_estate + sl_banks + lending - burrowed_money, 2)
total_assets_estimate = round(total_assets + estimated_savings, 2)
distance_to_target = round(portfolio_target - total_assets_estimate, 2)
print("Real Estate assets {0}".format(real_estate))
print("Cash at Bank SL {0}".format(sl_banks))
print("Cash at Bank SG {0}".format(sg_banks))
print("Lending {0}".format(lending))
print("SG Portfolio {0}".format(sg_total_postfolio))
print("Total Stock portfolio value {0}".format(total_stock_portfolio))
print("Total Assets as of now {0}".format(total_assets))
print("Distance to EOY Target {0}".format(distance_to_target))
print("=======================================================")
print("Total Estimated EOY Assets with savings {0}".format(total_assets_estimate))
print("=======================================================")

# summary_table = PrettyTable()
# summary_table.field_names = ["Symbol", "Qty", "Cost", "Sales Proceeds", "Profit"]
# for row in portfolio_summary:
#     summary_table.add_row(row)
# print(summary_table)

pickle.dump(market_prices, open("market_prices.pckl", "wb"))
