    #!/usr/bin/python3
import base64
import json
import os
import traceback

from botocore.exceptions import ClientError
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time
import boto3
import csv

all_trades = []
working_dir = r'/tmp'
working_dir = r'C:\Users\kasun\Desktop\daily_trades'
s3_bucket_name = 'atrad-daily-trades'
SENDER = "ATRAD TRADE SCRAPER <kasunkula@gmail.com>"
RECIPIENT = "kasunkula@gmail.com"
AWS_REGION = "ap-southeast-1"
secret_name = "atrad_pwd"
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


def send_status_email(email_subject_str, description):
    ses_client = boto3.client('ses', region_name=AWS_REGION)
    try:
        ses_client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': "UTF-8",
                        'Data': description,
                    },
                },
                'Subject': {
                    'Charset': "UTF-8",
                    'Data': email_subject_str,
                },
            },
            Source=SENDER,
        )
    except ClientError as e:
        log_error(e.response['Error']['Message'])
    else:
        log("Status Email sent!"),


start = time.time()
try:
    # instantiate a chrome options object so you can set the size and headless preference
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920x1080")

    log("Navigating to atrad login page")
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=AWS_REGION
    )

    get_secret_value_response = client.get_secret_value(
        SecretId=secret_name
    )

    if 'SecretString' in get_secret_value_response:
        secret = json.loads(get_secret_value_response['SecretString'])
        secret = secret[secret_name]

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://online2.cts1.lk/atsweb/login")

    WebDriverWait(driver, 10).until(lambda driver: driver.execute_script('return document.readyState') == 'complete')

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
    password_text_box.send_keys(secret)

    actions = ActionChains(driver)
    actions.send_keys(Keys.TAB * 2)
    actions.perform()

    actions = ActionChains(driver)
    actions.send_keys(Keys.ENTER)
    actions.perform()

    log("Logging in to atrad")
    login_button = driver.find_element_by_id("btnSubmit_label")
    login_button.click()

    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'dijit_PopupMenuBarItem_2_text')))
    log("logged in to atrad system")

    market_drop_down = driver.find_element_by_id("dijit_PopupMenuBarItem_2_text")
    driver.execute_script("arguments[0].click();", market_drop_down)

    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'dijit_MenuItem_13_text')))
    trade_summary_element = driver.find_element_by_id("dijit_MenuItem_13_text")
    driver.execute_script("arguments[0].click();", trade_summary_element)
    no_of_pages = 0
    last_page_no = 0
    go_to_next_page_timeouts = 0
    while True:
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'dojox_grid__View_9')))
        table_parent = driver.find_element_by_id("dojox_grid__View_9")
        WebDriverWait(table_parent, 60).until(EC.presence_of_element_located((By.CLASS_NAME, 'dojoxGridRowTable')))
        if no_of_pages == 0:
            log("navigated to trades screen")
            no_of_pages = int(driver.find_element_by_id("lblPageNo").text)

            WebDriverWait(driver, 60).until(lambda driver: driver.find_element_by_id("totTrades3").text.strip() != '')
            total_trades = int(driver.find_element_by_id("totTrades3").text.replace(',', ''))
            log("total trades to be scraped {}".format(total_trades))

            log("Total number of pages to scrape {} and total trades to be scraped {}".
                format(no_of_pages, total_trades))
        page_number = driver.find_element_by_id("spnPageNoBox").get_attribute('value')
        page_number = int(page_number.replace(',', ''))
        if page_number != last_page_no + 1:
            log_error("expected page number {} and actual page number {} mismatch".
                      format(last_page_no + 1, page_number))
            break
        last_page_no = page_number
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
            all_trades.append(trade)
            if len(all_trades) % 1000 == 0:
                log("[Page {} of {}] Trades scraped so far {}".format(last_page_no, no_of_pages, len(all_trades)))
        next_button = driver.find_element_by_id("btnNextPageBut")
        if not next_button.is_displayed():
            break
        driver.execute_script("arguments[0].click();", next_button)
        try:
            WebDriverWait(driver, 3).until(EC.visibility_of_element_located((By.ID, 'imgmtsRefreshCursor')))
            WebDriverWait(driver, 3).until(EC.invisibility_of_element_located((By.ID, 'imgmtsRefreshCursor')))
        except:
            print("Timeout exception ignored while waiting for imgmtsRefreshCursor")
            go_to_next_page_timeouts += 1
            if go_to_next_page_timeouts % 50 == 0:
                log("[Total go to next page timeouts encountered so far {}".format(go_to_next_page_timeouts))
except Exception as e:
    log_error("exception encountered as [{}]".format(e))
    traceback.print_exc()
finally:
    try:
        if last_page_no != no_of_pages or total_trades != len(all_trades):
            trade_file_name = "trades_{}.csv".format(datetime.now().strftime('%Y%m%d%H%M%S'))
            log("Only {} pages scraped out of {} total pages".format(last_page_no, no_of_pages))
            log("Only {} trades scraped out of {} total trades".format(len(all_trades), total_trades))
            email_subject = 'Failed - {} trades scraped from {} pages out of {}'.format(len(all_trades),
                                                                                        last_page_no, no_of_pages)
        else:
            trade_file_name = "trades_{}.csv".format(datetime.now().strftime('%Y%m%d'))
            log("All {} pages scraped out of {} total pages".format(last_page_no, no_of_pages))
            email_subject = 'Success - All {} trades scraped from {} pages'.format(len(all_trades), no_of_pages)
        log("{} trades scraped".format(len(all_trades)))
    except:
        log_error("exception encountered as [{}]".format(e))
        traceback.print_exc()
    finally:
        abs_trade_file_name = os.path.join(working_dir, trade_file_name)
        with open(abs_trade_file_name, mode='w', newline='') as daily_trades_file:
            writer = csv.writer(daily_trades_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(['Security', 'Board Id', 'Trade Time', 'Quantity', 'Price', 'Net Change'])
            writer.writerows(all_trades)
            daily_trades_file.close()

        end = time.time()
        desc = "Total trades scraped {0}. Elapsed time {1}min".format(len(all_trades), round((end - start) / 60), 0)
        log(desc)
        driver.close()

        s3_client = boto3.client('s3')
        response = s3_client.upload_file(abs_trade_file_name, s3_bucket_name, trade_file_name)

        with open(abs_log_file_name, 'r') as file:
            log_file_data = file.read()
        send_status_email(email_subject, log_file_data)
        os.remove(abs_trade_file_name)
        os.remove(abs_log_file_name)

        ec2 = boto3.client('ec2', region_name='ap-southeast-1')
        ec2.stop_instances(InstanceIds=['i-087d9efa4f2600a19'])
        log('stopped instances : ' + str('i-087d9efa4f2600a19'))
