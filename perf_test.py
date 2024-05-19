# Define a function to read the file and process the data
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import statistics
import numpy
import math

latest_buy_er_lookup_checkpoint = 'Checkpoint 9'
latest_sell_er_lookup_checkpoint = 'Checkpoint 10'
tp_lookup_checkpoint = 'Checkpoint 4'
initial_er_lookup_checkpoint = 'Checkpoint 11'

latest_er_lookup_times = []
tp_lookup_times = []
initial_er_lookup_times = []

data_dict = {}

er_x_axis_points = []
def process_file(file_path):
    global data_dict
    # Open the file and process each line
    with open(file_path, 'r') as file:
        initial_er_lookup_count = 1
        for line in file:
            # Split the line by pipe
            elements = line.strip().split('|')
            if len(elements) >= 10:  # Ensure the line has at least 9 elements
                transaction_id = elements[9]  # Fetch the transaction ID
                if transaction_id not in data_dict:
                    data_dict[transaction_id] = {}  # Create a new list for the transaction ID if not already present
                chekpt_name = elements[6].strip()
                timestamp = elements[0].strip()
                if chekpt_name == latest_buy_er_lookup_checkpoint:
                    latest_er_lookup_times.append(int(elements[10].strip().split(' ')[8].split('(')[0].replace("ms", "")))
                    er_x_axis_points.append(2.5*initial_er_lookup_count)
                    initial_er_lookup_count = initial_er_lookup_count + 1
                elif chekpt_name == latest_sell_er_lookup_checkpoint:
                    latest_er_lookup_times.append(int(elements[10].strip().split(' ')[8].split('(')[0].replace("ms", "")))
                    er_x_axis_points.append(2.5*initial_er_lookup_count)
                    initial_er_lookup_count = initial_er_lookup_count + 1
                elif chekpt_name == tp_lookup_checkpoint:
                    tp_lookup_times.append(int(elements[10].strip().split(' ')[8].split('(')[0].replace("ms", "")))
                elif chekpt_name == initial_er_lookup_checkpoint:
                    initial_er_lookup_times.append(int(elements[10].strip().split(' ')[7].split('(')[0].replace("ms", "")))
                data_dict[transaction_id][chekpt_name] = timestamp
    return data_dict


def process_ccp_sim_file_and_plot(file_path):
    with open(file_path, 'r') as file:
        latency_stats = []
        trade_count = 0
        busted_trade_count = 0
        cleared_trade_count = 0
        for line in file:
            # if trade_count >= 100000:
            #     break
            elements = line.strip().split(' ')
            if "[LATENCY_STAT]" != elements[1] and ("Busted" == elements[1] or "Cleared" == elements[1]):
                trade_count = trade_count + 1
            if "Busted" == elements[1] and elements[0].startswith("[T"):
                transaction_id = elements[0].replace('[', '').replace(']', '')
                time = int(elements[6].replace('ms', ''))/1000
                if time > 10:
                    print("[{}]{} - {}sec".format(trade_count, transaction_id, time))
                latency_stats.append(time)
                busted_trade_count = busted_trade_count + 1
            elif "Cleared" == elements[1] and elements[0].startswith("[T"):
                cleared_trade_count = cleared_trade_count + 1

        trade_count = trade_count + busted_trade_count
        busted_trade_count = busted_trade_count*2

        plot(latency_stats, range(0, len(latency_stats)*10, 10),
             'End to End Latency CCP Rejections for {} trades cleared/rejected : {}/{} \nTrade Rate - 10 Trades per second (2 rejected,8 accepted by CCP)'.format(trade_count, cleared_trade_count, busted_trade_count), 'Trades', 'Elapsed Time (sec)')


def plot(data_points, vertical_axis_points, title, xlabel, ylabel):
    plt.plot(vertical_axis_points, data_points, marker='.')

    # Adding labels and title
    median = str(statistics.median(data_points))
    percentile90 = str(round(numpy.percentile(data_points, 90), 2))
    percentile95 = str(round(numpy.percentile(data_points, 95), 2))
    percentile99 = str(round(numpy.percentile(data_points, 99), 2))
    percentile99point99 = str(round(numpy.percentile(data_points, 99.99), 2))
    plt.title(title + '\nmedian:' + median + ', percentiles : 90% ' + percentile90 + " | 95% : " + percentile95 + " | 99% : " + percentile99 + " | 99.9% : " + percentile99point99)
    plt.ylabel(ylabel)
    plt.xlabel(xlabel)

    # Adding a legend
    plt.legend()

    # Displaying the graph
    plt.show()


start_checkpoint = 'Checkpoint 1'
end_checkpoint = 'Checkpoint 14'

# Example usage of the function with a file path
# process_ccp_sim_file_and_plot(r"C:\Users\kasun\Desktop\perf\slips5\latency_sd_with_changes_0108.log")
process_file(r'C:\Users\kasun\Desktop\perf\slips3\ref_letter\sd_chkpt.log')
process_file(r'C:\Users\kasun\Desktop\perf\slips3\ref_letter\pttps_chkpt.log')

start_timestamps = []
elapsed_times = []
index = 0
# sorted_dict = dict(sorted(result_dict.items(),
#                           key=lambda item: (
#                                   datetime.strptime(item[1][end_checkpoint], "%Y%m%d%H%M%S.%f") - datetime.strptime(item[1][start_checkpoint], "%Y%m%d%H%M%S.%f")
#                           ),
#                           reverse=True))

for transaction, timestamp_list in data_dict.items():
    if start_checkpoint in timestamp_list and end_checkpoint in timestamp_list:
        start_timestamp = datetime.strptime(timestamp_list[start_checkpoint], "%Y%m%d%H%M%S.%f")
        end_timestamp = datetime.strptime(timestamp_list[end_checkpoint], "%Y%m%d%H%M%S.%f")
        time_delta = (end_timestamp - start_timestamp)
        # elapsed_time = math.ceil((time_delta.seconds * 1000 * 1000 + time_delta.microseconds) / (1000*1000))
        elapsed_time = ((time_delta.seconds * 1000 * 1000 + time_delta.microseconds) / 1000)
        # elapsed_time = time_delta.seconds
        index += 1
        start_timestamps.append(index)
        elapsed_times.append(elapsed_time)
        print("{} = {} ({} - {})".format(transaction, elapsed_time, start_timestamp, end_timestamp))

x_axis_points = range(0, len(tp_lookup_times)*5, 5)
trade_count = len(elapsed_times)*5
# plot(elapsed_times, x_axis_points, 'SD to SD Processing Time {} trades \nTrade Rate - 10 Trades per second (2 rejected,8 accepted by CCP)'.format(trade_count), 'Time', 'Elapsed Time (millisec)')
# plot(elapsed_times, x_axis_points, 'Within SD Processing Time {} trades \nTrade Rate - 10 Trades per second (2 rejected,8 accepted by CCP)'.format(trade_count), 'Time', 'Elapsed Time (millisec)')
# plot(elapsed_times, x_axis_points, 'PTTPS Processing Time {} trades \nTrade Rate - 10 Trades per second (2 rejected,8 accepted by CCP)'.format(trade_count), 'Time', 'Elapsed Time (millisec)')
# plot(tp_lookup_times, x_axis_points, 'TP Lookup Time for {} trades \nTrade Rate - 10 Trades per second (2 rejected,8 accepted by CCP)'.format(trade_count), 'Trades', 'Elapsed Time (millisec)')
# plot(initial_er_lookup_times, x_axis_points, 'Initial ER Lookup Time for {} trades \nTrade Rate - 10 Trades per second (2 rejected,8 accepted by CCP)'.format(trade_count), 'Trades', 'Elapsed Time (millisec)')
# plot(latest_er_lookup_times, er_x_axis_points, 'Latest ER Lookup Time for {} trades \nTrade Rate - 10 Trades per second (2 rejected,8 accepted by CCP)'.format(trade_count), 'Trades', 'Elapsed Time (millisec)')

exit(0)
