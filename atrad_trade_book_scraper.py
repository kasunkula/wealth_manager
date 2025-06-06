#!/usr/bin/python3
import gc
import os
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


import time
import csv
import keyring

login_retry_count = 5
login_retry_wait_interval_in_seconds = 120
working_dir = r'C:\Users\kasun\Desktop\daily_trades'
log_file_name = "trade_scraper_{}.log".format(datetime.now().strftime('%Y%m%d%H%M%S'))
abs_log_file_name = os.path.join(working_dir, 'logs', log_file_name)
trade_row_cells = []


def log_error(err_str):
    log(err_str, "ERR")


def log(log_str, log_prefix=None):
    if os.path.exists(abs_log_file_name):
        log_file = open(abs_log_file_name, 'a')
    else:
        log_file = open(abs_log_file_name, 'w')
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    log_prefix = "LOG" if log_prefix is None else log_prefix
    print("{} | {} | {}".format(timestamp, log_prefix, log_str))
    log_file.write("{} | {} | {}\n".format(timestamp, log_prefix, log_str))
    log_file.close()
    return


def log_in_to_atrad_with_retry():
    for login_attempt in range(login_retry_count):
        log_in_status, driver = log_in_to_atrad()
        if log_in_status:
            log("Log in to atrad attempt [{}] successful".format((login_attempt + 1)))
            return log_in_status, driver
        log_error("Log in to atrad attempt [{}] failed retrying in another {}seconds".
                  format((login_attempt + 1), login_retry_wait_interval_in_seconds))
        time.sleep(login_retry_wait_interval_in_seconds)
    return False, None


def log_in_to_atrad():
    try:
        # instantiate a chrome options object so you can set the size and headless preference
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920x1080")

        log("Navigating to atrad login page")
        driver = None
        driver = webdriver.Chrome(options=chrome_options)
        # driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
        driver.get("https://online2.cts1.lk/atsweb/login")

        WebDriverWait(driver, 10).until(
            lambda driver: driver.execute_script('return document.readyState') == 'complete')

        # login
        username_text_box = driver.find_element_by_xpath(
            "/html[@class='dj_webkit dj_chrome dj_contentbox']/body[@class='claro']/div[@id='topWrap']/div[@id='wrapper']/"
            "div[@id='container']/form[@id='loginForm']/div[@id='loginBox']/div[@class='loginBoxLeftAdjust']/div[@class='l"
            "oginBoxLeftAdjust2']/div[@class='loginTextBoxMidIamge']/div[@id='widget_txtUserName']"
            "/div[@class='dijitReset dijitInputField dijitInputContainer']/input[@id='txtUserName']")
        password_text_box = driver.find_element_by_xpath(
            "/html[@class='dj_webkit dj_chrome dj_contentbox']/body[@class='claro']/div[@id='topWrap']/div[@id='wrapper']"
            "/div[@id='container']/form[@id='loginForm']/div[@id='loginBox']/div[@class='loginPasswordAdjust']"
            "/div[@class='loginBoxLeftAdjust2']/div[@class='loginTextBoxMidIamge']/div[@id='widget_txtPassword']"
            "/div[@class='dijitReset dijitInputField dijitInputContainer']/input[@id='txtPassword']")

        username_text_box.send_keys("kasuncham")
        password_text_box.send_keys(keyring.get_password("atrad", "murapade"))

        actions = ActionChains(driver)
        actions.send_keys(Keys.TAB * 2)
        actions.perform()

        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()

        log("Logging in to atrad")
        login_button = driver.find_element_by_id("btnSubmit_label")
        login_button.click()

        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'dijit_PopupMenuBarItem_1_text')))
        log("logged in to atrad system")

        log("waiting for total trades element text ...")
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'totTrades3')))
        for x in range(6):
            tot_trades_element_text = driver.find_element_by_id("totTrades3").text
            log("waiting for total trades element text [{}]".format(tot_trades_element_text))
            if tot_trades_element_text != '':
                return True, driver
            time.sleep(5)
        log_error("Unable to read total trades.")
        return False, driver
    except Exception as e:
        log_error("exception encountered as in log_in_to_atrad [{}]".format(e))
        traceback.print_exc()
        return False, driver


def go_to_trades_screen(driver, go_to_page):
    go_to_trades_screen_start_time = time.time()
    return_status = True
    try:
        total_trades = int(driver.find_element_by_id("totTrades3").text.replace(',', ''))
        log("total trades to be scraped {}".format(total_trades))
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'dijit_MenuItem_13_text')))
        trade_summary_element = driver.find_element_by_id("dijit_MenuItem_13_text")
        driver.execute_script("arguments[0].click();", trade_summary_element)
        no_of_pages = 0
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'dojox_grid__View_9')))
        table_parent = driver.find_element_by_id("dojox_grid__View_9")
        WebDriverWait(table_parent, 60).until(EC.presence_of_element_located((By.CLASS_NAME, 'dojoxGridRowTable')))
        log("navigated to trades screen")
        no_of_pages = int(driver.find_element_by_id("lblPageNo").text.replace(',', ''))
        log("Total number of pages to scrape {} and total trades to be scraped {}".
            format(no_of_pages, total_trades))
        if go_to_page != 1:
            log("Navigating to page {}".format(go_to_page))
            WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'widget_spnPageNoBox')))
            page_no_box = driver.find_element_by_id("widget_spnPageNoBox")
            up_button = page_no_box.find_element_by_class_name(
                "dijitReset.dijitLeft.dijitButtonNode.dijitArrowButton.dijitUpArrowButton")
            actions = webdriver.common.action_chains.ActionChains(driver)
            actions.click(up_button)
            for x in range(int(go_to_page - 2)):
                actions.perform()
            go_button = driver.find_element_by_id("btnGoBut")
            driver.execute_script("arguments[0].click();", go_button)
            try:
                WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, 'imgmtsRefreshCursor')))
                WebDriverWait(driver, 20).until(EC.invisibility_of_element_located((By.ID, 'imgmtsRefreshCursor')))
            except:
                log_error("[GO_TO_PAGE] Timeout exception encountered while waiting for imgmtsRefreshCursor")
                traceback.print_exc()
                return_status = False
            go_to_next_status, is_last_page, time_go_to_next = go_to_next_page(driver)
            return_status = return_status and go_to_next_status
        current_page_no = driver.find_element_by_id("spnPageNoBox").get_attribute('value')
        if int(current_page_no) != go_to_page:
            log_error("Go to page error expected page at the end {} but actual {}".format(go_to_page, current_page_no))
            return False, None, None
        go_to_trades_screen_end_time = time.time()
        log("Navigated to page {} in {} mins".
            format(current_page_no, round((go_to_trades_screen_end_time - go_to_trades_screen_start_time) / 60, 0)))
    except Exception as e:
        log_error("exception encountered in go_to_trades_screen as [{}]".format(e))
        traceback.print_exc()
        return_status = False
    return return_status, total_trades, no_of_pages


def scrape_trades_from_page(driver, scraped_trades, no_of_total_pages):
    try:
        scraping_start_time = time.time()
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'dojox_grid__View_9')))
        table_parent = driver.find_element_by_id("dojox_grid__View_9")
        WebDriverWait(table_parent, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'dojoxGridRowTable')))
        current_page_no = int(driver.find_element_by_id("spnPageNoBox").get_attribute('value').replace(',', ''))
        scrape_trades_from_grid(current_page_no, no_of_total_pages, scraped_trades, table_parent)
        scraping_end_time = time.time()
        return True, current_page_no, round(scraping_end_time - scraping_start_time, 2)
    except Exception as e:
        log_error("exception encountered in scrape_trades_from_page as [{}]".format(e))
        traceback.print_exc()
        return False, None, None


def scrape_trades_from_grid(current_page_no, no_of_total_pages, scraped_trades, table_parent):
    trade_rows = table_parent.find_elements_by_class_name("dojoxGridRowTable")
    for table_row in trade_rows:
        scraped_trades.append(scrape_trade_from_grid_row(table_row))
        if len(scraped_trades) % 500 == 0:
            log("[Page {} of {}] Trades scraped so far {}".format(current_page_no, no_of_total_pages,
                                                                  len(scraped_trades)))


def scrape_trade_from_grid_row(table_row):
    cells = table_row.find_elements_by_class_name("dojoxGridCell")
    return compose_trade_from_grid_row_cells(cells)


def compose_trade_from_grid_row_cells(cells):
    qty = int(cells[3].text.replace(',', ''))
    price = float(cells[4].text.replace(',', '').replace('(', '').replace(')', ''))
    net_change = float(cells[5].text.replace(',', '').replace('(', '').replace(')', ''))
    return [cells[0].text, cells[1].text, cells[2].text, qty, price, net_change, round(qty * price, 2)]


def go_to_next_page(driver):
    """go to next page by clicking on next button
        return status, is_last_page, time_to_go_to_next_page
        """
    try:
        go_to_next_page_start_time = time.time()
        next_button = driver.find_element_by_id("btnNextPageBut")
        if not next_button.is_displayed():
            return True, True, None
        driver.execute_script("arguments[0].click();", next_button)
        try:
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'imgmtsRefreshCursor')))
            WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.ID, 'imgmtsRefreshCursor')))
        except:
            log_error("Timeout exception encountered while waiting for imgmtsRefreshCursor")
            return False, False, None
        go_to_next_page_end_time = time.time()
        return True, False, round((go_to_next_page_end_time - go_to_next_page_start_time), 2)
    except:
        return False, False, None


def scrape_trades_staring_from_page_batch(starting_page_no=1, page_batch_size=None):
    """scrapes trades from trade screen starting from the give page until page_batch_size number of pages
            return
            status,
            end_reached,
            current_page_no, total_pages_to_be_scraped, total_trades_to_be_scraped, trades_scraped_from_page_batch
            """
    log("Stating Page batch {} of from {}".format(page_batch_size, starting_page_no))
    start = time.time()
    trades_scraped_from_page_batch = []
    pages_scraped = 0
    current_page_no = 0
    total_pages_to_be_scraped = 0
    total_trades_to_be_scraped = 0
    is_last_page = False

    log_in_status, driver = log_in_to_atrad_with_retry()
    if not log_in_status:
        return False, is_last_page, current_page_no, total_pages_to_be_scraped, \
               total_trades_to_be_scraped, trades_scraped_from_page_batch

    go_to_screen_return_status, total_trades_to_be_scraped, total_pages_to_be_scraped = \
        go_to_trades_screen(driver, starting_page_no)

    if not go_to_screen_return_status:
        return False, is_last_page, current_page_no, total_pages_to_be_scraped, \
               total_trades_to_be_scraped, trades_scraped_from_page_batch

    gc.disable()
    while True:
        status, current_page_no, scraping_time = \
            scrape_trades_from_page(driver, trades_scraped_from_page_batch, total_pages_to_be_scraped)

        if not status:
            log_error("Trade scraping encountered problem. aborting current batch".
                      format(current_page_no, (starting_page_no + pages_scraped)))
            return False, is_last_page, current_page_no, total_pages_to_be_scraped, total_trades_to_be_scraped, \
                   trades_scraped_from_page_batch

        if current_page_no != (starting_page_no + pages_scraped):
            log_error("Current page is {} where as expected is {}".
                      format(current_page_no, (starting_page_no + pages_scraped)))
            return False, is_last_page, current_page_no, total_pages_to_be_scraped, \
                   total_trades_to_be_scraped, trades_scraped_from_page_batch
        pages_scraped += 1

        status, is_last_page, time_go_to_next = go_to_next_page(driver)
        print("[{}/{}][Page {} of {}] Trades scraped so far from batch {} time spent {}s/{}s".
              format(pages_scraped, "ALL" if page_batch_size is None else page_batch_size, current_page_no,
                     total_pages_to_be_scraped, len(trades_scraped_from_page_batch), scraping_time,
                     time_go_to_next))
        if not status:
            return False, is_last_page, current_page_no, total_pages_to_be_scraped, \
                   total_trades_to_be_scraped, trades_scraped_from_page_batch
        if is_last_page is True:
            if total_pages_to_be_scraped != current_page_no:
                log_error("Go to next indicated as last page, but expected last page {}, actual {}".
                          format(total_pages_to_be_scraped, current_page_no))
            break
        if page_batch_size is not None and pages_scraped == page_batch_size:
            break
    gc.enable()
    end = time.time()
    log("Page batch of {} from {} to {} completed in {}mins".
        format(pages_scraped, starting_page_no, current_page_no, round((end - start) / 60, 2)))
    if driver is not None:
        driver.close()
    return True, is_last_page, current_page_no, total_pages_to_be_scraped, total_trades_to_be_scraped, \
           trades_scraped_from_page_batch


def scrape_trades():
    start = time.time()
    try:
        all_scraped_trades = []
        last_page_no = 0
        log_in_status = False
        while True:
            status, end_reached, tmp_last_page_no, total_pages_to_be_scraped, total_trades_to_be_scraped, trades_scraped_from_page_batch = \
                scrape_trades_staring_from_page_batch((last_page_no + 1), 500)
            log_in_status = (log_in_status or status)
            if status is not True:
                log_error("trade scraping from batch failed hence restarting the same batch from [{}]".
                          format((last_page_no + 1)))
            else:
                if len(trades_scraped_from_page_batch) != 0:
                    all_scraped_trades.extend(trades_scraped_from_page_batch)
                last_page_no = tmp_last_page_no
                if end_reached:
                    log("End reached last read page number {} total pages to be read".
                        format(tmp_last_page_no, total_pages_to_be_scraped))
                    break
    except Exception as e:
        log_error("exception encountered as [{}]".format(e))
        traceback.print_exc()
    finally:
        if log_in_status:
            if total_pages_to_be_scraped != last_page_no or total_trades_to_be_scraped != len(all_scraped_trades):
                trade_file_name = "trades_{}.csv".format(datetime.now().strftime('%Y%m%d%H%M%S'))
                log("Only {} pages scraped out of {} total pages".format(last_page_no, total_pages_to_be_scraped))
                log("Only {} trades scraped out of {} total trades".format(len(all_scraped_trades),
                                                                           total_trades_to_be_scraped))
            else:
                trade_file_name = "trades_{}.csv".format(datetime.now().strftime('%Y%m%d'))
                log("All {} pages scraped out of {} total pages".format(last_page_no, total_pages_to_be_scraped))
            log("{} trades scraped".format(len(all_scraped_trades)))

            abs_trade_file_name = os.path.join(working_dir, 'scraped_trades', trade_file_name)
            with open(abs_trade_file_name, mode='w', newline='') as daily_trades_file:
                writer = csv.writer(daily_trades_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(['Security', 'Board Id', 'Trade Time', 'Quantity',
                                 'Price', 'Net Change', 'Consideration'])
                writer.writerows(all_scraped_trades)
                daily_trades_file.close()
        end = time.time()
        log("Total trades scraped {0}. Elapsed time {1}min".format(len(all_scraped_trades), round((end - start) / 60),
                                                                   0))


if __name__ == "__main__":
    scrape_trades()
