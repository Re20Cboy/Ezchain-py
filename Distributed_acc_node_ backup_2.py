from account import Account
from trans_msg_for_dts_acc import TransMsg
import threading
import random
from Ezchain_simulate import EZsimulate
import unit

# Create Threads Function
def daemon_thread_builder(target, args=()) -> threading.Thread:
    th = threading.Thread(target=target, args=args)
    th.setDaemon(True)
    return th

# design for distributed account node
class DstAcc:
    def __init__(self):
        self.account = Account(ID=0) # this ID is designed for EZ simulate, useless here !
        self.account.generate_random_account() # init account info
        self.trans_msg = TransMsg()

    def send_txns_to_txn_pool(self):
        pass
    def generate_txns(self):
        pass

    def print_self_info(self):
        print(f"IP: {self.trans_msg.local_ip}")
        print(f"TCP Port: {self.trans_msg.self_port}")
        print(f"UUID: {self.trans_msg.node_uuid}")
        print(f"Address: {self.account.addr}")
        print("*" * 50)

    def random_select_recipients(self):
        def select_k_numbers(n, k): # select k numbers from (0,1,2,3,...,n-1)
            if k > n:
                raise ValueError("Error: k should be less than or equal to n")
            numbers = list(range(n))
            random.shuffle(numbers)
            selected_numbers = numbers[:k]
            return selected_numbers

        neighbors_num = len(self.trans_msg.neighbor_info)
        if neighbors_num > 0:
            recipients_num = random.randint(1, neighbors_num)
        else:
            return None
        selected_nums = select_k_numbers(neighbors_num, recipients_num)
        selected_neighbors = []
        for item in selected_nums:
            selected_neighbors.append(self.trans_msg.neighbor_info[item])

        acc_txns = self.account.random_generate_txns(selected_neighbors)
        return acc_txns

    def check_acc_num(self, acc_max_num = 3):

        Dst_acc = [0]*acc_max_num
        index_rank = [] # acc node's index with rank, to ensure rank's constance between every acc node
        uuid_lst = [] # all acc node's uuid lst
        while True:
            if len(self.trans_msg.neighbor_info) + 1 >= acc_max_num:
                # add uuid lst
                uuid_lst.append(self.trans_msg.node_uuid)
                for item in self.trans_msg.neighbor_info:
                    uuid_lst.append(item.uuid) # add neighbor
                index_rank = unit.sort_and_get_positions(uuid_lst)
                for i, item in enumerate(index_rank, start=0):
                    if i == 0:
                        Dst_acc[item] = self.account
                    else:
                        Dst_acc[item] = self.trans_msg.neighbor_info[i-1]
                self.entry_point(Dst_acc)
                return

    def entry_point(self, Dst_acc):
        EZs = EZsimulate()
        # generate genesis block
        genesis_block = EZs.generate_GenesisBlock_for_Dst(Dst_acc)
        print("==== Genesis Block ====")
        genesis_block.print_block()

        # generate txns
        acc_txns = self.random_select_recipients()

        # send txns to pool

        # get proof from miner

        # send proof to receiver

    def init_point(self):
        self.print_self_info()
        # init (get all node's addr, uuid, ...)
        # listen_hello thread listening hello brd msg from network
        listen_hello = daemon_thread_builder(self.trans_msg.listen_hello, args=('Hello', self.account.addr, )) # msg_type='Hello'
        # say hello to other nodes when init
        self.trans_msg.brd_hello_to_neighbors(self.account.addr) # say hello when init
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
    dst_node = DstAcc()
    dst_node.init_point()

if __name__ == "__main__":
    main()
