import time

from account import Account
from trans_msg_for_dts import TransMsg
import threading
import random
from Ezchain_simulate import EZsimulate
import unit
import transaction
import copy
from blockchain import Blockchain
from const import *
import hashlib

# Create Threads Function
def daemon_thread_builder(target, args=()) -> threading.Thread:
    th = threading.Thread(target=target, args=args)
    th.setDaemon(True)
    return th

# design for distributed account node
class DstAcc:
    def __init__(self):
        self.trans_msg = TransMsg(node_type="acc")
        self.account = Account(ID=0) # this ID is designed for EZ simulate, useless here !
        self.account.generate_random_account(file_id=self.trans_msg.node_uuid) # init account info
        self.global_id = None # init when get all neighbors
        self.blockchain = Blockchain(dst=True) # distributed simulate
        self.node_type = "acc" # acc for account
        self.send_package_flag = 0
        self.this_round_txns_num = 0
        self.this_round_success_txns_num = 0
        self.this_round_block_index = None
        self.temp_recv_mTree_prf = [] # temp storage recved (mTreePrf, block_index, block_hash) from miner
        self.temp_sent_package = [] # temp storage sent acc txn package, type as [(acc_txns, acc_txns_package), ...]

    def send_txns_to_txn_pool(self):
        pass
    def generate_txns(self):
        pass

    def print_self_info(self):
        print(f"IP: {self.trans_msg.local_ip}")
        print(f"TCP Port: {self.trans_msg.self_port}")
        print(f"UUID: {self.trans_msg.node_uuid}")
        print(f"Address: {self.account.addr}")
        print("Node Type: acc node")
        print("*" * 50)

    def clear_and_fresh_info_dst(self):
        self.this_round_txns_num = 0
        self.this_round_success_txns_num = 0
        self.this_round_block_index = None
        self.account.clear_and_fresh_info_dst()

    def generate_acc_txns_package(self):
        self.trans_msg.print_brief_acc_neighbors()
        # Read the transaction information entered by the user
        neighbor_addr_lst = []
        transfer_amount_lst = []
        while True:
            neighbor_number = input("Enter transfer account (number): ")
            if neighbor_number == "N":
                print("Quit.")
                return
            neighbor_number = int(neighbor_number)
            while neighbor_number < 0 or neighbor_number >= len(self.trans_msg.acc_neighbor_info):
                print("Illegal neighbor number!")
                neighbor_number = int(input("Enter transfer account (number): "))
            transfer_amount = int(input("Enter transfer amount: "))
            while transfer_amount <= 0 or transfer_amount > self.account.balance:
                print("Illegal neighbor amount!")
                transfer_amount = int(input("Enter transfer amount: "))
            neighbor_addr_lst.append(self.trans_msg.acc_neighbor_info[neighbor_number].addr)
            transfer_amount_lst.append(transfer_amount)
            continue_transfer = input("Continue with the transfer? (Enter 'Y' to continue, end with other characters)")
            if continue_transfer.upper() != 'Y':
                break
        acc_txns = self.account.generate_txn_dst(addr_lst=neighbor_addr_lst, amount_lst=transfer_amount_lst)
        tmp_acc_txns_package = transaction.AccountTxns(self.account.addr, self.global_id, acc_txns)
        tmp_acc_txns_package.sig_accTxn(self.account.privateKey)
        acc_txns_package = copy.deepcopy(
            (tmp_acc_txns_package.Digest, tmp_acc_txns_package.Signature, self.account.addr, self.global_id))
        return acc_txns, acc_txns_package  # send to txn pool

    def random_generate_acc_txns_package(self):
        def select_k_numbers(n, k): # select k numbers from (0,1,2,3,...,n-1)
            if k > n:
                raise ValueError("Error: k should be less than or equal to n")
            numbers = list(range(n))
            random.shuffle(numbers)
            selected_numbers = numbers[:k]
            return selected_numbers

        neighbors_num = len(self.trans_msg.acc_neighbor_info)
        if neighbors_num > 0:
            recipients_num = random.randint(1, neighbors_num)
        else:
            return None
        selected_nums = select_k_numbers(neighbors_num, recipients_num)
        self.this_round_txns_num = len(selected_nums)
        selected_neighbors = []
        for item in selected_nums:
            selected_neighbors.append(self.trans_msg.acc_neighbor_info[item])

        acc_txns = self.account.random_generate_txns(selected_neighbors)
        tmp_acc_txns_package = transaction.AccountTxns(self.account.addr, self.global_id, acc_txns)
        tmp_acc_txns_package.sig_accTxn(self.account.privateKey)
        acc_txns_package = copy.deepcopy((tmp_acc_txns_package.Digest, tmp_acc_txns_package.Signature, self.account.addr, self.global_id))
        return acc_txns, acc_txns_package # send to txn pool

    def check_acc_num(self, acc_max_num = DST_ACC_NUM):
        Dst_acc = [0]*acc_max_num
        index_rank = [] # acc node's index with rank, to ensure rank's constance between every acc node
        uuid_lst = [] # all acc node's uuid lst
        while True:
            if len(self.trans_msg.acc_neighbor_info) + 1 >= acc_max_num:
                # add uuid lst
                uuid_lst.append(self.trans_msg.node_uuid)
                for item in self.trans_msg.acc_neighbor_info:
                    uuid_lst.append(item.uuid) # add neighbor
                index_rank = unit.sort_and_get_positions(uuid_lst)
                for i, item in enumerate(index_rank, start=0):
                    if i == 0: # first index in item rank
                        Dst_acc[item] = self.account
                        self.global_id = item # set global id
                    else:
                        Dst_acc[item] = self.trans_msg.acc_neighbor_info[i-1]
                self.entry_point(Dst_acc)
                return

    def find_acc_txns_via_package_hash(self, package_hash):
        # unit hash tool
        def hash(val):
            if type(val) == str:
                return hashlib.sha256(val.encode("utf-8")).hexdigest()
            else:
                return hashlib.sha256(val).hexdigest()
        index_of_package = len(self.temp_sent_package) - 1
        while index_of_package >= 0:
            (acc_txns, acc_txns_package) = self.temp_sent_package[index_of_package]
            aim_hash = hash(acc_txns_package)
            if aim_hash == package_hash:
                return acc_txns
            index_of_package -= 1
        return None

    def send_package_to_txn_pool(self):
        while True:
            # generate transactions periodically and submit them to the trading pool
            time.sleep(10) # generate txns / 10 sec
            # generate txns
            if RANDOM_TXNS:
                acc_txns, acc_txns_package = self.random_generate_acc_txns_package()
            else:
                acc_txns, acc_txns_package = self.generate_acc_txns_package()
            print("This round generate " + str(len(acc_txns)) + " txns.")
            # send txns package to pool (brd to all con nodes)
            self.trans_msg.brd_acc_txns_package_to_con_node(acc_txns_package)
            self.account.accTxns = acc_txns
            # record sent package
            self.temp_sent_package.append((acc_txns, acc_txns_package))
            # record sent but unconfirmed value
            value_in_vpb_index_lst = self.account.find_vpb_index_via_acc_txns_dst(acc_txns)
            self.account.add_unconfirmed_vpb_list_dst(value_in_vpb_index_lst)

    """while True:
            if self.send_package_flag == 1:
                # generate txns
                if RANDOM_TXNS:
                    acc_txns, acc_txns_package = self.random_generate_acc_txns_package()
                else:
                    acc_txns, acc_txns_package = self.generate_acc_txns_package()
                print("This round generate " + str(len(acc_txns)) + " txns.")
                # send txns package to pool (brd to all con nodes)
                self.trans_msg.brd_acc_txns_package_to_con_node(acc_txns_package)
                self.send_package_flag = 0
                self.account.accTxns = acc_txns
                # record sent package
                self.temp_sent_package.append((acc_txns, acc_txns_package))
                # record sent but unconfirmed value
                value_in_vpb_index_lst = self.account.find_vpb_index_via_acc_txns_dst(acc_txns)
                self.account.add_unconfirmed_vpb_list_dst(value_in_vpb_index_lst)"""



    def update_and_check_VPB_pairs(self):
        # 1.) longest chain flash, thus update self VPB pairs
        # 2.) after update, check which VPB can be sent

        if self.temp_recv_mTree_prf == []:
            return
        # scan every temp mtree proof
        for mTree_prf_pair in self.temp_recv_mTree_prf:
            (mTreePrf, block_index, block_hash) = mTree_prf_pair
            # check block_index with block_hash
            result_block = self.blockchain.find_block_via_block_hash_dst(block_hash)
            if result_block == None:
                # not find block related to this mTree_prf_pair
                continue # skip this mTree_prf_pair
            if result_block.get_index() != block_index:
                # block_index and block_hash do not match
                # todo: del and process this mTree_prf_pair
                continue
            # todo: check mTree root with block

            # update self VPB pairs if :
            # 1.) this mTree_prf_pair cover at lest MAX_FORK_HEIGHT blocks
            # 2.) and mTree_prf_pair should be in the longest chain
            # 1.) and 2.) ensure that this mTree_prf_pair CANNOT be changed via fork
            if (self.blockchain.get_latest_block_index() - block_index + 1 >= MAX_FORK_HEIGHT
                    and self.blockchain.check_block_hash_is_in_longest_chain(block_hash)):
                try:
                    # find costed_values_and_recipes via mTreePrf[0], i.e., acc_txns_package's hash
                    related_acc_txns = self.find_acc_txns_via_package_hash(mTreePrf[0])
                    costed_values_and_recipes = []
                    for acc_txn in related_acc_txns:
                        value_lst = acc_txn.get_values()
                        recipes = acc_txn.Recipient
                        for one_value in value_lst:
                            costed_values_and_recipes.append((one_value, recipes))
                    # update this VPB pair,
                    # and get the list of values which need to be sent to recipients
                    # lst_value_need_sent = [2,4,5,8, ...] (the index of self VPB pairs),
                    # lst_cost_value_recipient = [addr_1,addr_2,addr_1,addr_2, ...] (the addr of recipient of value need to be sent).
                    lst_value_need_sent, lst_cost_value_recipient = self.account.update_VPB_pairs_dst(mTreePrf, block_index, costed_values_and_recipes, self.blockchain)
                except Exception as e:
                    raise RuntimeError("An error occurred in acc_node.update_VPB_pairs_dst: " + str(e))
                print('Update VPB pair success.')
                # todo: check if this vpb need to be sent
                #  AND this VPB can pass test

                # send VPB pairs to recipient
                # recipient_addr = [recipient_1, recipient_2, ...],
                # need_send_vpb_index = [[vpb_1_1, vpb_1_2, ...], [vpb_2_1, vpb_2_2, ...], ...],
                # where vpb_i_j (j=1,2,...) will be sent to recipient_i.
                recipient_addr, need_send_vpb_index = self.account.send_VPB_pairs_dst(
                    lst_value_need_sent, lst_cost_value_recipient)
                for index, item in enumerate(recipient_addr):
                    recipient_ip, recipient_port = self.trans_msg.find_neighbor_ip_and_port_via_addr(item)
                    need_send_vpb = []
                    for i in need_send_vpb_index[index]:
                        need_send_vpb.append(self.account.ValuePrfBlockPair[i])
                    self.trans_msg.tcp_send(other_tcp_port=recipient_port, data_to_send=need_send_vpb, msg_type="VPBPair",
                                  other_ip=recipient_ip)
                # start send new package to txn pool
                self.send_package_flag += 0.4
            else:
                # this recv mtree proof does not cover MAX_FORK_HEIGHT blocks,
                # or not in the longest chain
                pass

    def entry_point(self, Dst_acc):
        print('enrty point!')
        EZs = EZsimulate()
        # generate genesis block
        genesis_block = EZs.generate_GenesisBlock_for_Dst(Dst_acc)
        self.blockchain.add_block(genesis_block)
        # print("==== Genesis Block ====")
        # genesis_block.print_block()

        # send genesis block to con-node (only #0 acc brd genesis block)
        if self.global_id == 0:
            print('Brd genesis block')
            self.trans_msg.brd_block_to_neighbors(genesis_block)

        self.send_package_flag = 1
        send_package = daemon_thread_builder(self.send_package_to_txn_pool)
        send_package.start()

        # get proof from miner

        # send proof to receiver

        send_package.join()


    def init_point(self):
        self.print_self_info()
        # init (get all node's addr, uuid, ...)
        # listen_hello thread listening hello brd msg from network
        listen_brd = daemon_thread_builder(self.trans_msg.listen_brd, args=(self.account.addr, self.node_type, self.blockchain, self.account.publicKey, None, self, )) # msg_type='Hello'
        # say hello to other nodes when init
        self.trans_msg.brd_hello_to_neighbors(addr=self.account.addr, node_type=self.node_type, pk=self.account.publicKey) # say hello when init
        # listen_p2p thread listening hello tcp msg from network
        listen_p2p = daemon_thread_builder(self.trans_msg.tcp_receive, args=(self.blockchain, self, ))
        # check acc node num
        check_acc_num = daemon_thread_builder(self.check_acc_num)

        listen_brd.start()
        listen_p2p.start()
        check_acc_num.start()

        listen_brd.join()
        listen_p2p.join()
        check_acc_num.join()

############################################
############################################

def main():
    print("*" * 50)
    dst_node = DstAcc()
    dst_node.init_point()

if __name__ == "__main__":
    main()
