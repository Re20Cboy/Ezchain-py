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
from unit import MTreeProof

# Create Threads Function
def daemon_thread_builder(target, args=()) -> threading.Thread:
    def target_with_info(*args):
        thread_name = threading.current_thread().name
        if PRINT_THREAD:
            print(f"Starting thread for: {target.__name__} - {thread_name}")
        try:
            target(*args)
        except Exception as e:
            print(f"Thread ERR: {target.__name__} - {thread_name} encountered an exception: \n {e}")
        finally:
            if PRINT_THREAD:
                print(f"Exiting thread: {thread_name}")

    th = threading.Thread(target=target_with_info, args=args)
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
        # lock
        self.resource_lock = threading.Lock()
        self.blockchain_lock = threading.Lock()
        self.temp_recv_mTree_prf_lock = threading.Lock()
        self.temp_sent_package_lock = threading.Lock()
        self.account_lock = threading.Lock()
        # lock
        # block_process_lock is a lock for all process after recv a new block, e.g.,
        # 1.) recv new block & mtree proof pair;
        # 2.) check and add block to local chain, check and add mtree proof pair to local;
        # 3.) if main chain's len change (+ >1), update local VPB pair;
        # 4.) if some VPB can be sent after update, send them to recipients.
        # True means LOCK, and False means UN-LOCK
        self.block_process_lock= False
        # generate_txns_lock is a lock for controlling all txns' generation process
        # controlling the parms included in txns' generation process:
        # 1.) unconfirmed value list
        # 2.) costed value and recipient list
        self.generate_txns_lock = False

        self.vpb_lock = False

    def set_block_process_lock_dst(self, boolean):
        self.block_process_lock = boolean
    def set_generate_txns_lock_dst(self, boolean):
        self.generate_txns_lock = boolean
    def set_vpb_lock_dst(self, boolean):
        self.vpb_lock = boolean
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
            aim_hash = hash(acc_txns_package[0]) # [0] is digest
            if aim_hash == package_hash:
                return acc_txns, acc_txns_package
            index_of_package -= 1
        return None

    def send_package_to_txn_pool(self):
        def generate_txns_with_lock():
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
            # NOTE: only record the value (# begin index, # end index),
            # DO NOT record its index in the vpb pair, since vpb lst changes when del or accept vpb.
            # func find_vpb_index_via_acc_txns_dst will check if the value is change, i.e, sent to self.
            value_in_acc_txns_lst = self.account.find_value_in_acc_txns_dst(acc_txns)
            self.account.add_unconfirmed_value_list_dst(value_in_acc_txns_lst)
            # update account's fresh_costed_value_and_recipes_dst
            # the clear of costed_value_and_recipes should be after add_unconfirmed_value_list_dst
            self.account.fresh_costed_value_and_recipes_dst()

        while True:
            # generate transactions periodically and submit them to the trading pool
            random_gap_time = random.uniform(1, TXN_GENERATE_GAP_TIME)
            time.sleep(random_gap_time)

            while self.vpb_lock:
                # wait un-lock
                print('generate_txns: wait 0.5 sec for un-lock of vpb lock...')
                time.sleep(0.5)

            self.set_vpb_lock_dst(True)
            generate_txns_with_lock()
            self.set_vpb_lock_dst(False)

    def check_mTree_prf_pair(self, mTree_prf_pair):
        # this func check the legal of mTree_prf_pair, which shapes as: (mTreePrf, block_index, block_hash)
        # the check test include:
        # 1.) if block has been confirmed (used for updating vpb)?
        # 2.) check block_index with block_hash, and find the corresponding block
        # 3.) if corresponding block has been confirmed and within the longest chain?
        # 4.) check the mTree proof

        # unpakage the mTree_prf_pair
        (mTreePrf, block_index, block_hash) = mTree_prf_pair
        # check recv mTree_prf_pair to ensure updating vpb pair correctly
        latest_confirmed_block_index = self.blockchain.get_latest_confirmed_block_index()
        if latest_confirmed_block_index == None:
            # no block has been confirmed, thus this mTree_prf_pair cannot be used for updating vpb
            print('check_mTree_prf_pair: no block has been confirmed')
            return False
        if block_index > latest_confirmed_block_index:
            # this block has not been confirmed
            print('check_mTree_prf_pair: this block has not been confirmed')
            return False
        if self.blockchain.check_block_hash_is_in_longest_chain(block_hash) == False:
            # the block should be in the main (longest) chain
            print('check_mTree_prf_pair: the block not in the main (longest) chain')
            return False

        # check block_index with block_hash
        result_block = self.blockchain.find_block_via_block_hash_dst(block_hash)

        # check the result_block:
        # 1.) result_block is not None; 2.) result_block's index is correct; 3.) this block has been confirmed
        if result_block == None:
            # not find block related to this mTree_prf_pair
            print('check_mTree_prf_pair: not find block related to this mTree_prf_pair')
            return False
        if result_block.get_index() != block_index:
            # block_index and block_hash do not match
            print('check_mTree_prf_pair: block_index and block_hash do not match')
            return False

        # check the mTree proof
        unchecked_mTree_prd = MTreeProof(mTreePrf)
        # get the info of acc_txns_digest & mTree_root
        mTree_root = mTreePrf[-1]
        # check mTree_root
        if mTree_root != result_block.get_m_tree_root():
            print('check_mTree_prf_pair: root err')
            return False

        # find costed_values_and_recipes via mTreePrf[0], i.e., acc_txns_package's hash
        result = self.find_acc_txns_via_package_hash(mTreePrf[0])
        if result == None:
            # this mTree proof has no corresponding local acc txns
            print('check_mTree_prf_pair: this mTree proof has no corresponding local acc txns')
            return False
        (related_acc_txns, related_acc_txns_package) = result
        # get the acc txns' digest
        acc_txns_digest = related_acc_txns_package[0]

        # check mTree_prd
        if not unchecked_mTree_prd.checkPrf(accTxnsDigest=acc_txns_digest, trueRoot=mTree_root):
            print('check_mTree_prf_pair: not pass the check of mTree proof')
            return False
        # pass all check
        return related_acc_txns

    def update_and_check_VPB_pairs(self):
        # check if the mTree_prf and its related block are immutable
        latest_confirmed_block_index = self.blockchain.get_latest_confirmed_block_index()
        if latest_confirmed_block_index == None:
            # no block is immutable, thus exit vpb updating directly
            return

        # 1.) longest chain flash, thus update self VPB pairs
        # 2.) after update, check which VPB can be sent
        if self.temp_recv_mTree_prf == []:
            return
        # the del lst record the index of mTree_prf_pair which should be del
        del_lst_of_mTree_prf_pair = []
        # scan every temp mtree proof
        for mTree_prf_pair_index, mTree_prf_pair in enumerate(self.temp_recv_mTree_prf):
            print('VPB update: process #'+str(mTree_prf_pair_index)+' mTree_prf_pair.')
            # un-package this mTree_prf_pair
            (mTreePrf, block_index, block_hash) = mTree_prf_pair
            # check the mtree prf is immutable
            related_acc_txns = self.check_mTree_prf_pair(mTree_prf_pair)
            if related_acc_txns == False:
                print('this mTree_prf_pair does not match the condition of updating vpb.')
                # this mTree_prf_pair does not match the condition of updating vpb
                continue

            # find costed_values_and_recipes via mTreePrf[0], i.e., acc_txns_package's hash
            # costed_values_and_recipes shapes as: [(value, value's owner), (), ...]
            costed_values_and_recipes = []
            for acc_txn in related_acc_txns:
                recipes = acc_txn.Recipient
                if recipes == self.account.addr:
                    # the recipe is self, do not add in the costed_values_and_recipes
                    continue
                value_lst = acc_txn.get_values()
                for one_value in value_lst:
                    costed_values_and_recipes.append((one_value, recipes))

            try:
                # update this VPB pair,
                # and get the list of values which need to be sent to recipients
                # lst_value_need_sent = [2,4,5,8, ...] (the index of self VPB pairs),
                # lst_cost_value_recipient = [addr_1,addr_2,addr_1,addr_2, ...] (the addr of recipient of value need to be sent).

                # in func update_VPB_pairs_dst, self vpb check is called,
                # self vpb check ensure that no p&b is loss
                print('Start update local vpb pair...')
                lst_value_need_sent, lst_cost_value_recipient = self.account.update_VPB_pairs_dst(
                    mTree_prf_pair, mTreePrf, block_index, costed_values_and_recipes, related_acc_txns, self.blockchain)
            except Exception as e:
                raise RuntimeError("An error occurred in acc_node.update_VPB_pairs_dst: " + str(e))


            # print('Update VPB pair success')
            # for de-bug: print the info of lst_value_need_sent & lst_cost_value_recipient
            '''print('costed_values_and_recipes:')
            for item in costed_values_and_recipes:
                (one_value, recipes) = item
                one_value.print_value()
                print(recipes)
                print('--------------')
            for one_value in [x[0] for x in self.account.ValuePrfBlockPair]:
                print('-----self local value-----')
                one_value.print_value()
            print('lst of value need sent is:')
            print(lst_value_need_sent)
            print('lst of recipient is:')
            print(lst_cost_value_recipient)'''

            if lst_value_need_sent != [] and lst_cost_value_recipient != []: # some value need sent
                print('costed_values_and_recipes:')
                for item in costed_values_and_recipes:
                    (one_value, recipes) = item
                    one_value.print_value()
                    print(recipes)
                    print('--------------')
                for one_value in [x[0] for x in self.account.ValuePrfBlockPair]:
                    print('-----self local value-----')
                    one_value.print_value()
                print('lst of value need sent is:')
                print(lst_value_need_sent)
                print('lst of recipient is:')
                print(lst_cost_value_recipient)

                # after vpb updating, the used mTree_prf_pair, which shapes as
                # (mTreePrf, block_index, block_hash), should be deleted.
                # record the del list of mTree_prf_pair
                del_lst_of_mTree_prf_pair.append(mTree_prf_pair_index)

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
                        # for test
                        # self.print_one_vpb(self.account.ValuePrfBlockPair[i])
                    self.trans_msg.tcp_send(other_tcp_port=recipient_port, data_to_send=need_send_vpb,
                                            msg_type="VPBPair", other_ip=recipient_ip)

            # start send new package to txn pool
            # self.send_package_flag += 0.4

        if del_lst_of_mTree_prf_pair != []:
            # [] means that no mTree_prf_pair is used for vpb updating
            # reverse del list for del process
            del_lst_of_mTree_prf_pair.reverse()
            # if use complete vpb, CANNOT del temp_recv_mTree_prf.
            # self.del_temp_recv_mTree_prf(del_lst_of_mTree_prf_pair)

        # del the sent VPB pair
        # todo: del the vpb pair after recv the 'txn success' msg from the payee
        #  note that: The deletion of VPB should be isolated from the next round
        #  of VPB update operations
        deleted_vpb_lst = self.account.del_vpb_pair_dst()
        # update self check points base on self VPBpairs
        if deleted_vpb_lst:
            # process the deleted vpb, make them suitable for ck-check
            '''for vpb in deleted_vpb_lst:
                p = vpb[1].prfList
                b = vpb[2]
                del p[-1]
                del b[-1]
                # for test
                if p[-1].owner != self.account.addr:
                    print('ERR: vpb check point fresh fail!')'''
            # self.account.VPBCheckPoints.fresh_local_vpb_check_point_dst(will_sent_vpb_pairs=deleted_vpb_lst)
            pass


    # for test
    def print_one_vpb(self, one_vpb):
        v = one_vpb[0]
        p = one_vpb[1]
        b = one_vpb[2]

        v.print_value()
        p.print_proof()
        print('block_index: '+str(b))

    def del_temp_recv_mTree_prf(self, del_lst):
        # check del_list is reversed
        first_element = del_lst[0]
        if len(del_lst) > 1:
            for index, item in enumerate(del_lst):
                if index == 0:
                    continue
                if item <= first_element:
                    raise ValueError('ERR: del lst is not reversed.')
                first_element = item
        # del the item in the del lst
        for del_index in del_lst:
            del self.temp_recv_mTree_prf[del_index]

    def complete_vpb_dst(self, uncompleted_vpb):
        # un-package this uncompleted vpb
        v = uncompleted_vpb[0]
        p = uncompleted_vpb[1].prfList
        b = uncompleted_vpb[2]

        # define the missing range: (begin_block_index, end_block_index]
        begin_block_index = b[-1] # in this block, the owner is changed to self
        end_block_index = self.blockchain.get_latest_confirmed_block_index() # end index is the latest main chain block's index
        if begin_block_index >= end_block_index:
            # this vpb is no need for complete
            return
        # missing block index lst includes the block index & mtree proof should be added in the vpb
        missing_block_index_lst = []

        for index in range(begin_block_index+1, end_block_index+1):
            # real range: (begin_block_index, end_block_index]
            if self.account.addr in self.blockchain.chain[index].bloom:
                # this block index & mtree proof should be added in the vpb
                missing_block_index_lst.append(index)

        # add the confirmed mtree proof to the uncompleted_vpb, and complete the vpb.
        for mTree_prf_pair in self.temp_recv_mTree_prf:
            # unpackage this mTree_prf_pair
            (mTreePrf, block_index, block_hash) = mTree_prf_pair
            # skip the mtree prf pair if not in missing lst
            if block_index not in missing_block_index_lst:
                continue
            # check if this mTree_prf_pair is confirmed
            related_acc_txns = self.check_mTree_prf_pair(mTree_prf_pair)
            if related_acc_txns == False:
                # this mTree_prf_pair does not match the condition of updating vpb:
                # 1.) if block has been confirmed (used for updating vpb)?
                # 2.) check block_index with block_hash, and find the corresponding block
                # 3.) if corresponding block has been confirmed and within the longest chain?
                # 4.) check the mTree proof
                continue
            owner = self.account.addr
            # create missing proof unit
            missing_proof_unit = unit.ProofUnit(owner=owner, ownerAccTxnsList=related_acc_txns,
                                    ownerMTreePrfList=mTreePrf)
            missing_block_index = block_index

            # find the position where this vpb should be added in the block index list
            index = len(b) - 1
            add_position = None
            # Determine the add position based on the block index
            while index >= 0:
                if b[index] == missing_block_index:
                    # this block index has been added, so ignore this vpb
                    break
                if b[index] < missing_block_index:
                    # this position should be added
                    add_position = index + 1
                    break
                index -= 1
            if add_position == None:
                # not find the add position, thus skip to next mtree prf pair
                continue
            # add P & B to self VPB pairs
            uncompleted_vpb[1].add_prf_unit_dst(prfUnit=missing_proof_unit, add_position=add_position)
            uncompleted_vpb[2].insert(add_position, missing_block_index)
            # print for test
            print('Complete vpb:')
            print('add_position = ' + str(add_position))
            print('missing_block_index = ' + str(missing_block_index))
            print('missing_proof_unit:')
            missing_proof_unit.print_proof_unit()



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
    print('test exit')

if __name__ == "__main__":
    main()
