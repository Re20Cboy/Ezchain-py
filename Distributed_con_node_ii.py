from node import Node
from trans_msg_for_dts import TransMsg
import threading
import random
from Ezchain_simulate import EZsimulate
import unit
import transaction
import copy
from const import *

# Create Threads Function
def daemon_thread_builder(target, args=()) -> threading.Thread:
    th = threading.Thread(target=target, args=args)
    th.setDaemon(True)
    return th

# design for distributed account node
class DstConNode:
    def __init__(self):
        self.trans_msg = TransMsg()
        self.con_node = Node(id=0,dst=True) # this ID is designed for EZ simulate, useless here !
        self.con_node.generate_random_node(file_id=self.trans_msg.node_uuid) # init con-node info
        self.global_id = None # init when get all neighbors
        self.node_type = "con" # con for consensus

    def print_self_info(self):
        print(f"IP: {self.trans_msg.local_ip}")
        print(f"TCP Port: {self.trans_msg.self_port}")
        print(f"UUID: {self.trans_msg.node_uuid}")
        print(f"Address: {self.con_node.addr}")
        print("*" * 50)

    def check_acc_num(self, con_max_num = DST_NODE_NUM):
        Dst_con = [0]*con_max_num
        index_rank = [] # acc node's index with rank, to ensure rank's constance between every acc node
        uuid_lst = [] # all acc node's uuid lst
        while True:
            if len(self.trans_msg.con_neighbor_info) + 1 >= con_max_num:
                # add uuid lst
                uuid_lst.append(self.trans_msg.node_uuid)
                for item in self.trans_msg.con_neighbor_info:
                    uuid_lst.append(item.uuid) # add neighbor
                index_rank = unit.sort_and_get_positions(uuid_lst)
                for i, item in enumerate(index_rank, start=0):
                    if i == 0:
                        Dst_con[item] = self.con_node
                        self.global_id = item # set global id
                        self.con_node.id = item
                    else:
                        Dst_con[item] = self.trans_msg.con_neighbor_info[i-1]
                self.entry_point(Dst_con)
                return

    def entry_point(self, Dst_con):
        # start listen to block (1-th is genesis block)
        listen_block = daemon_thread_builder(self.trans_msg.listen_block,
                                             args=(self.con_node.blockchain, 'Block'))  # msg_type='Block'
        listen_block.start()

        # get proof from miner


        # send proof to receiver

        listen_block.join()

    def init_point(self):
        self.print_self_info()
        # init (get all node's addr, uuid, ...)
        # listen_hello thread listening hello brd msg from network
        listen_hello = daemon_thread_builder(self.trans_msg.listen_hello, args=(self.con_node.addr, self.node_type, 'Hello')) # msg_type='Hello'
        # say hello to other nodes when init
        self.trans_msg.brd_hello_to_neighbors(addr=self.con_node.addr, node_type=self.node_type) # say hello when init
        # listen_p2p thread listening hello tcp msg from network
        listen_p2p = daemon_thread_builder(self.trans_msg.tcp_receive)
        # check acc node num
        check_acc_num = daemon_thread_builder(self.check_acc_num)

        listen_hello.start()
        listen_p2p.start()
        check_acc_num.start()

        listen_hello.join()
        listen_p2p.join()
        check_acc_num.join()

############################################
############################################

def main():
    print("*" * 50)
    dst_node = DstConNode()
    dst_node.init_point()

if __name__ == "__main__":
    main()
