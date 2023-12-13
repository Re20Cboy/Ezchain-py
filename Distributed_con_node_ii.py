import time

from node import Node
from trans_msg_for_dts import TransMsg
import threading
import random
from Ezchain_simulate import EZsimulate
import unit
import transaction
import copy
from const import *
import message

# Create Threads Function
def daemon_thread_builder(target, args=()) -> threading.Thread:
    th = threading.Thread(target=target, args=args)
    th.setDaemon(True)
    return th

# design for distributed account node
class DstConNode:
    def __init__(self):
        self.trans_msg = TransMsg(node_type="con")
        self.con_node = Node(id=0,dst=True) # this ID is designed for EZ simulate, useless here !
        self.con_node.generate_random_node(file_id=self.trans_msg.node_uuid) # init con-node info
        self.global_id = None # init when get all neighbors
        self.node_type = "con" # con for consensus
        self.txns_pool = unit.txnsPool() # for collect acc txns packages
        self.mine_lock = threading.Lock() # lock for func mine
        self.recv_new_block_flag = 'test' # copy.deepcopy(CONST_FALSE)


    def print_self_info(self):
        print(f"IP: {self.trans_msg.local_ip}")
        print(f"TCP Port: {self.trans_msg.self_port}")
        print(f"UUID: {self.trans_msg.node_uuid}")
        print(f"Address: {self.con_node.addr}")
        print("Node Type: con node")
        print(id(self.trans_msg.node_uuid))
        print(id(self.recv_new_block_flag))
        print("*" * 50)

    def check_con_num(self, con_max_num = DST_NODE_NUM):
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
                        # self.con_node.id = item
                    else:
                        Dst_con[item] = self.trans_msg.con_neighbor_info[i-1]
                self.entry_point(Dst_con)
                return

    def make_block_body(self):
        new_block_body = message.BlockBodyMsg()
        DigestAccTxns = []
        for item in self.txns_pool.pool:
            DigestAccTxns.append(item[0])
        new_block_body.random_generate_mTree(DigestAccTxns, self.txns_pool.pool)
        return new_block_body

    def monitor_txns_pool(self, max_packages = MAX_PACKAGES):
        while True:
            if self.txns_pool.get_packages_num() >= max_packages:
                self.mine()
                self.txns_pool.clearPool()

    def mine(self):
        with self.mine_lock:
            self.recv_new_block_flag = False
            print('Begin mine...')
            while not self.recv_new_block_flag:
                time.sleep(ONE_HASH_TIME) # simulate one hash compute cost
                if random.random() < ONE_HASH_SUCCESS_RATE: # success mine!
                    # make block body via acc txns packages
                    new_block_body = self.make_block_body()
                    self.con_node.tmpBlockBodyMsg = new_block_body
                    # make new block
                    new_block = self.con_node.create_new_block_for_dst()
                    # brd new block
                    print('Mine success and brd new block to neighbors!')
                    self.trans_msg.brd_block_to_neighbors(new_block)
                    break # return this round mine
            print('Recv new block, kill this mine().')

    def wait_for_genesis_block(self):
        while True:
            if len(self.con_node.blockchain.chain) == 0:
                time.sleep(0.5) # wait 0.5 sec
            else:
                return # out of wait

    def entry_point(self, Dst_con):
        # start listen to block (0-th is genesis block)
        self.wait_for_genesis_block()
        # get proof from miner


        # send proof to receiver


    def init_point(self):
        self.print_self_info()
        # init (get all node's addr, uuid, ...)
        # listen_hello thread listening hello brd msg from network
        listen_brd = daemon_thread_builder(self.trans_msg.listen_brd, args=(self.con_node.addr, self.node_type, self.con_node.blockchain, self.recv_new_block_flag, self.txns_pool, None, )) # msg_type='Hello'
        # say hello to other nodes when init
        self.trans_msg.brd_hello_to_neighbors(addr=self.con_node.addr, node_type=self.node_type) # say hello when init
        # listen_p2p thread listening hello tcp msg from network
        listen_p2p = daemon_thread_builder(self.trans_msg.tcp_receive)
        # check acc node num
        check_con_num = daemon_thread_builder(self.check_con_num)
        # check whether packages in txns pool reach the max line
        monitor_txns_pool = daemon_thread_builder(self.monitor_txns_pool)

        listen_brd.start()
        listen_p2p.start()
        check_con_num.start()
        monitor_txns_pool.start()

        listen_brd.join()
        listen_p2p.join()
        check_con_num.join()
        monitor_txns_pool.join()

############################################
############################################

def main():
    print("*" * 50)
    dst_node = DstConNode()
    dst_node.init_point()

if __name__ == "__main__":
    main()
