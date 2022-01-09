#!/usr/bin/python3
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
import time
import csv

working_dir = r'C:\Users\kasun\Desktop\daily_trades'
log_file_name = "trade_scraper_{}.log".format(datetime.now().strftime('%Y%m%d%H%M%S'))
abs_log_file_name = os.path.join(working_dir, log_file_name)


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


def log_in_to_atrad():
    try:
        # instantiate a chrome options object so you can set the size and headless preference
        chrome_options = Options()
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920x1080")

        log("Navigating to atrad login page")

        driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
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
        password_text_box.send_keys("D2p9HNDe@GwiXPJ")

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

        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'totTrades3')))
        for x in range(6):
            tot_trades_element_text = driver.find_element_by_id("totTrades3").text
            log("waiting for total trades element text [{}]".format(tot_trades_element_text))
            if tot_trades_element_text != '':
                return True, driver
            time.sleep(10)
        log_error("Unable to read total trades.")
        return False, driver
    except Exception as e:
        log_error("exception encountered as [{}]".format(e))
        traceback.print_exc()


def go_to_trades_screen(driver, go_to_page):
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
        if go_to_page is not None:
            log("Navigating to page {}".format(go_to_page))
            WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'widget_spnPageNoBox')))
            page_no_box = driver.find_element_by_id("widget_spnPageNoBox")
            up_button = page_no_box.find_element_by_class_name(
                "dijitReset.dijitLeft.dijitButtonNode.dijitArrowButton.dijitUpArrowButton")
            actions = webdriver.common.action_chains.ActionChains(driver)
            actions.click(up_button)
            for x in range(go_to_page + 1):
                actions.perform()
            go_button = driver.find_element_by_id("btnGoBut")
            driver.execute_script("arguments[0].click();", go_button)
            try:
                WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'imgmtsRefreshCursor')))
                WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.ID, 'imgmtsRefreshCursor')))
            except:
                log_error("[GO_TO_PAGE] Timeout exception ignored while waiting for imgmtsRefreshCursor")
        current_page_no = driver.find_element_by_id("spnPageNoBox").get_attribute('value')
        log("Navigated to page {}".format(current_page_no))
    except Exception as e:
        log_error("exception encountered as [{}]".format(e))
        traceback.print_exc()
    return total_trades, no_of_pages


def scrape_trades_from_page(driver, scraped_trades):
    return True


def scrape_trades():
    start = time.time()
    try:
        all_trades = []
        log_in_status, driver = log_in_to_atrad()
        if log_in_status:
            total_trades, no_of_total_pages = go_to_trades_screen(driver, None)
            while True:
                page_start_time = time.time()
                WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'dojox_grid__View_9')))
                table_parent = driver.find_element_by_id("dojox_grid__View_9")
                WebDriverWait(table_parent, 60).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'dojoxGridRowTable')))
                current_page_no = driver.find_element_by_id("spnPageNoBox").get_attribute('value')
                for table_row in table_parent.find_elements_by_class_name("dojoxGridRowTable"):
                    trade = []
                    col_index = 0
                    for item in table_row.find_elements_by_class_name("dojoxGridCell"):
                        if col_index == 3:  # Quantity
                            trade.append(int(item.text.replace(',', '')))
                        elif col_index == 4 or col_index == 5:  # Price or Net Change
                            trade.append(float(item.text.replace(',', '').replace('(', '').replace(')', '')))
                        else:
                            trade.append(item.text)
                        col_index += 1
                    trade.append(round(trade[3] * trade[4], 2))
                    all_trades.append(trade)
                    if len(all_trades) % 500 == 0:
                        log("[Page {} of {}] Trades scraped so far {}".format(current_page_no, no_of_total_pages,
                                                                              len(all_trades)))
                scraping_end_time = time.time()
                next_button = driver.find_element_by_id("btnNextPageBut")
                if not next_button.is_displayed():
                    break
                driver.execute_script("arguments[0].click();", next_button)
                try:
                    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'imgmtsRefreshCursor')))
                    WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.ID, 'imgmtsRefreshCursor')))
                except:
                    log_error("Timeout exception ignored while waiting for imgmtsRefreshCursor")
                page_end_time = time.time()
                time_spent_scraping_page = round((scraping_end_time - page_start_time), 0)
                e2e_time_for_page = round((page_end_time - page_start_time), 0)
                print("[Page {} of {}] Trades scraped so far {} time spent {}s/{}s".
                      format(current_page_no, no_of_total_pages, len(all_trades), time_spent_scraping_page,
                             e2e_time_for_page))
    except Exception as e:
        log_error("exception encountered as [{}]".format(e))
        traceback.print_exc()
    finally:
        if log_in_status:
            int_current_page_no = int(current_page_no.replace(',', ''))
            if no_of_total_pages != int_current_page_no or total_trades != len(all_trades):
                trade_file_name = "trades_{}.csv".format(datetime.now().strftime('%Y%m%d%H%M%S'))
                log("Only {} pages scraped out of {} total pages".format(int_current_page_no, no_of_total_pages))
                log("Only {} trades scraped out of {} total trades".format(len(all_trades), total_trades))
            else:
                trade_file_name = "trades_{}.csv".format(datetime.now().strftime('%Y%m%d'))
                log("All {} pages scraped out of {} total pages".format(int_current_page_no, no_of_total_pages))
            log("{} trades scraped".format(len(all_trades)))

            abs_trade_file_name = os.path.join(working_dir, trade_file_name)
            with open(abs_trade_file_name, mode='w', newline='') as daily_trades_file:
                writer = csv.writer(daily_trades_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(['Security', 'Board Id', 'Trade Time', 'Quantity',
                                 'Price', 'Net Change', 'Consideration'])
                writer.writerows(all_trades)
                daily_trades_file.close()
        end = time.time()
        log("Total trades scraped {0}. Elapsed time {1}min".format(len(all_trades), round((end - start) / 60), 0))
        if driver is not None:
            driver.close()


if __name__ == "__main__":
    scrape_trades()
