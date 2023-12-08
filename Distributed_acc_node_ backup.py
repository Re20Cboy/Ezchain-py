from account import Account
from trans_msg_for_dts_acc import TransMsg
import threading


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
    def entry_point(self):
        # init (get all node's addr, uuid, ...)
        listen_hello = daemon_thread_builder(self.trans_msg.listen_hello, args=('Hello', )) # msg_type='Hello'
        self.trans_msg.brd_hello_to_neighbors(self.account.addr) # say hello when init
        listen_hello.start()

        # generate txns

        # send txns to pool

        # get proof from miner

        # send proof to receiver

        listen_hello.join()

############################################
############################################

def main():
    print("*" * 50)
    dst_node = DstAcc()
    dst_node.entry_point()

if __name__ == "__main__":
    main()
