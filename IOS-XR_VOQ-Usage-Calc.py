from netmiko import ConnectHandler  # for connecting and configuring device
import getpass
from collections import Counter
import time  # Importing time module to check total runtime.
import pandas  # Importing pandas module to convert csv rows to individual lists based on first row headers.
import csv


# Capturing start time
start = time.time()

time_str = time.strftime("%d%m%Y-%H%M%S")       # time string for result csv filename
result_file = 'result_' + time_str + '.csv'

# Converting csv rows to individual lists based on first row headers. CSV file should have 'Ip_Address' header for IPs
devices_list = pandas.read_csv("device_details.csv", header=0)

try:
    ip_s = list(devices_list.Ip_Address)
except Exception as e:
    print(f'Some Exception happened. Check your "device_details.csv" file. \nError: {e}')


username = input('Enter Username for device Login: ')

password = getpass.getpass(prompt="Enter device password: ")
# password = input("Enter device password: ")

for ip in ip_s:
    print(150*'#')

    device = {
        'device_type': 'cisco_xr',
        'host': ip,
        'username': username,
        'password': password,
        'port': 22,  # optional, default 22
        'verbose': True  # optional, default False
    }

    connection = ConnectHandler(**device)
    prompt = connection.find_prompt()
    prompt_strip = prompt.find(':') + 1
    hostname = prompt[prompt_strip:-1]

    # Run show platform command to find LCs and capture them in 'lc_list'
    lc_ouptut = connection.send_command('show platform | i CPU | ex RP', max_loops=50000, delay_factor=5)
    loc1 = lc_ouptut.find('PHT') + 4
    lc_ouptut = lc_ouptut[loc1:]        # Striping first line for time from command output

    lc_str = lc_ouptut.splitlines()     # Capturing each line as List object

    lc_list = []
    for x in lc_str:
        obj1 = x.split()
        lc = obj1[0]
        lc_list.append(lc)

    print(f'List of LCs on {hostname} : {lc_list}\n')

    # Running for loop for each Line Card
    for lc_num in lc_list:
        print(50 * '#')
        print(f'LC - {lc_num}\n')

        # Executing 'show controllers npu voq-usage interface all instance all location x/x/CPU0 | i local' Command
        npu_voq_cmd = 'show controllers npu voq-usage interface all instance all location ' + lc_num + '| i local'
        output = connection.send_command(npu_voq_cmd, max_loops=50000, delay_factor=5)

        loc1 = output.find('PHT') + 4
        output = output[loc1:]          # Striping first line for time from command output

        list1 = output.splitlines()      # Capturing each line as List object

        # Creating two empty lists, one for each Core
        npu0_core0 = []
        npu0_core1 = []

        # Running through each item in 'list1', split each word to save each word as 'obj'
        for x in list1:
            obj = x.split()

            interface_name = obj[0]
            npu = int(obj[2])
            core = int(obj[3])

            if npu == 0 and core == 0:
                npu0_core0.append(interface_name)
            if npu == 0 and core == 1:
                npu0_core1.append(interface_name)

        # Converting both lists to set
        s_npu0_core0 = set(npu0_core0)
        s_npu0_core1 = set(npu0_core1)

        # Using Counter collection to Count Occurrences of each Interface. Count of each interface will be Total VOQ
        # in use for that interface.
        voq_core0 = Counter(npu0_core0)
        # print(voq_core0)
        voq_core1 = Counter(npu0_core1)
        # print(voq_core1)

        row_list = []           # result file Header List
        header1 = hostname + " " + lc_num
        row_list.append(header1)
        row_list.append('Total Count')

        # Create result file and Add interface with it's VOQ configured with Core information.
        with open(result_file, 'a') as rfile:
            writer = csv.writer(rfile)
            writer.writerow(row_list)
            writer.writerow(['Core-0'])
            for key, count in voq_core0.items():
                writer.writerow([key, count])   # Output both the key and the count

            writer.writerow(['Core-1'])
            for key, count in voq_core1.items():
                writer.writerow([key, count])   # Output both the key and the count

            writer.writerow([])


        # Count Total VoQ count
        total_voq_core0 = sum(voq_core0.values())
        total_voq_core1 = sum(voq_core1.values())

        # Calculate Actual VoQ delivered via running config.
        print(f'Total VoQ policies on {hostname}, {lc_num} Core 0 : {total_voq_core0}')

        print(f'Total VoQ policies on {hostname}, {lc_num} Core 1 : {total_voq_core1}')

    connection.disconnect()     # Disconnect from Device and continue to next.


# Capturing end time
end = time.time()

print(f'\nTotal time taken by Script: {round(end-start, 2)} seconds\n')

