#!/usr/bin/env python3

import os
import time
from concurrent.futures import ThreadPoolExecutor
from const import *

file_list = ["Distributed_con_node_i.py"]*DST_NODE_NUM + ["Distributed_acc_node_i.py"]*DST_ACC_NUM

def run_and_sleep(file):
    # os.system(f"start python {file}")
    if os.name == 'nt':
        os.system(f"start python {file}")
    else:
        os.system(f"python {file} &")
    time.sleep(1)

with ThreadPoolExecutor() as executor:
    executor.map(run_and_sleep, file_list)