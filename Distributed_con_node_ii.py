import time

from node import Node
from trans_msg_for_dts import TransMsg
import threading
import random
import unit
import transaction
import copy
from const import *
import message
import logging
import sys

# set log record
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Threads Function
def daemon_thread_builder(target, args=()) -> threading.Thread:
    def target_with_info(*args):
        thread_name = threading.current_thread().name
        if PRINT_THREAD:
            print(f"Starting thread for: {target.__name__} - {thread_name}")
        try:
            target(*args)
        except Exception as e:
            print(f"Thread {thread_name} encountered an exception: {e}")
        finally:
            if PRINT_THREAD:
                print(f"Exiting thread: {thread_name}")

    th = threading.Thread(target=target_with_info, args=args)
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
        self.recv_new_block_flag = 0

    def print_self_info(self):
        print(f"IP: {self.trans_msg.local_ip}")
        print(f"TCP Port: {self.trans_msg.self_port}")
        print(f"UUID: {self.trans_msg.node_uuid}")
        print(f"Address: {self.con_node.addr}")
        print("Node Type: con node")
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

    def check_acc_num(self, acc_max_num = DST_NODE_NUM):
        uuid_lst = [] # all acc node's uuid lst
        while True:
            if len(self.trans_msg.acc_neighbor_info) >= acc_max_num:
                # add uuid lst
                for item in self.trans_msg.acc_neighbor_info:
                    uuid_lst.append(item.uuid) # add neighbor
                index_rank = unit.sort_and_get_positions(uuid_lst)
                for i, item in enumerate(index_rank, start=0):
                    self.trans_msg.acc_neighbor_info[i].index = item
                return

    def make_block_body(self):
        new_block_body = message.BlockBodyMsg()
        DigestAccTxns = []
        packages_for_new_block = []
        show_one_pool_waits_txns_flag = True
        while packages_for_new_block == []:
            # this loop wait for new txns push in pool
            packages_for_new_block = self.txns_pool.get_packages_for_new_block_dst()
            if packages_for_new_block == [] and show_one_pool_waits_txns_flag:
                print('Txn pool waits for new txns...')
                show_one_pool_waits_txns_flag = False
        # if packages_for_new_block == []:
            # raise ValueError('ERR: empty txns pool!')
        for item in packages_for_new_block:
            DigestAccTxns.append(item[0])
        new_block_body.random_generate_mTree(DigestAccTxns, packages_for_new_block)
        return new_block_body

    def monitor_txns_pool(self, max_packages = MAX_PACKAGES):
        while True:
            # todo: re-write the logic of beginning mine
            if self.txns_pool.get_packages_num() >= max_packages:
                self.mine()
                # the flash of txns pool postponed to recving block
                # self.txns_pool.clearPool()

    def mine(self):
        with self.mine_lock:
            self.recv_new_block_flag = 0
            print('Begin mine...')
            mine_success = False
            while self.recv_new_block_flag == 0:
                # Generate normally distributed random numbers
                # gauss random can avoid the same random of two process
                random_time = random.gauss(ONE_HASH_TIME, ONE_HASH_TIME * 0.1)
                time.sleep(random_time) # simulate one hash compute cost

                if random.random() < ONE_HASH_SUCCESS_RATE: # success mine!
                    # make block body via acc txns packages
                    new_block_body = self.make_block_body()
                    self.con_node.tmpBlockBodyMsg = new_block_body
                    # make new block
                    new_block = self.con_node.create_new_block_for_dst()
                    # make new block body for brd
                    m_tree = new_block_body.info
                    acc_sigs = new_block_body.get_acc_sigs()
                    acc_addrs = new_block_body.get_acc_addrs()
                    acc_digests = new_block_body.get_acc_digests()
                    # generate the info for test, i.e., block body
                    new_block_info_4_brd = (new_block, m_tree, acc_digests, acc_sigs, acc_addrs)
                    # brd new block with test info, i.e., block body
                    self.trans_msg.brd_block_to_neighbors(new_block_info_4_brd)
                    # flash self txns pool
                    self.txns_pool.clear_pool_dst(acc_digests)
                    # set mine success flag
                    mine_success = True
                    # send mTree prf to all acc nodes
                    mTree = new_block_body.info
                    block_index = new_block.index
                    block_hash = new_block.get_hash()
                    for index, acc_neighbor_uuid in enumerate(self.txns_pool.sender_id, start=0):
                        acc_ip, acc_port = self.trans_msg.find_neighbor_ip_and_port_via_uuid(acc_neighbor_uuid)
                        if acc_port == None:
                            raise ValueError('Not find valid acc port!')
                        # for de-bug
                        if len(mTree.prfList) <= index:
                            raise ValueError('test')
                        new_msg = (mTree.prfList[index], block_index, block_hash)
                        self.trans_msg.tcp_send(other_tcp_port=acc_port, data_to_send=new_msg, msg_type="MTreeProof",other_ip=acc_ip)
                    break # return this round mine

            if mine_success:
                print('Mine success and brd new block to neighbors!')
            else:
                print('Recv new block, kill this mine().')
            return

    def wait_for_genesis_block(self):
        while True:
            if len(self.con_node.blockchain.chain) == 0:
                time.sleep(0.5) # wait 0.5 sec
            else:
                return # out of wait

    def awake(self):
        # this func ensure that all process awake
        while True:
            time.sleep(5)

    def entry_point(self, Dst_con):
        # start listen to block (0-th is genesis block)
        self.wait_for_genesis_block()
        # get proof from miner


        # send proof to receiver


    def init_point(self):
        try:
            self.print_self_info()
            # init (get all node's addr, uuid, ...)
            # listen_hello thread listening hello brd msg from network
            listen_brd = daemon_thread_builder(self.trans_msg.listen_brd, args=(self.con_node.addr, self.node_type, self.con_node.blockchain, self.con_node.publicKey, self, None, )) # msg_type='Hello'
            # say hello to other nodes when init
            self.trans_msg.brd_hello_to_neighbors(addr=self.con_node.addr, node_type=self.node_type, pk=self.con_node.publicKey) # say hello when init
            # listen_p2p thread listening hello tcp msg from network
            listen_p2p = daemon_thread_builder(self.trans_msg.tcp_receive)
            # check con and acc node num
            check_con_num = daemon_thread_builder(self.check_con_num)
            check_acc_num = daemon_thread_builder(self.check_acc_num)
            # check whether packages in txns pool reach the max line
            monitor_txns_pool = daemon_thread_builder(self.monitor_txns_pool)
            # create a process which ensure to be awake
            awake = daemon_thread_builder(self.awake)

            listen_brd.start()
            listen_p2p.start()
            check_con_num.start()
            check_acc_num.start()
            monitor_txns_pool.start()
            awake.start()

            listen_brd.join()
            listen_p2p.join()
            check_con_num.join()
            check_acc_num.join()
            monitor_txns_pool.join()
            awake.join()

        except Exception as e:
            logger.exception("ERR：{}".format(e))

############################################
############################################

def main():
    print("*" * 50)
    dst_node = DstConNode()
    dst_node.init_point()
    print('test exit')

if __name__ == "__main__":
    main()
