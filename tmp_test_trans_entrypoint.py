import time

import trans_msg_for_dts
import threading

class P2P_node:
    def __init__(self):
        self.trans_msg = trans_entrypoint.TransMsg()
        self.msg = 1
        self.msg_type = "int"

    # Create Threads Function
    def daemon_thread_builder(self, target, args=()) -> threading.Thread:
        th = threading.Thread(target=target, args=args)
        th.setDaemon(True)
        return th

    def brd_msg(self):
        while True:
            self.trans_msg.broadcast(self.msg, self.msg_type)
            time.sleep(3)

    def recv_brd_msg(self):
        self.trans_msg.brd_receive()

    def recv_p2p_msg(self):
        self.trans_msg.tcp_receive()

    def send_p2p_msg(self, other_tcp_port, msg, other_ip="127.0.0.1"):
        self.trans_msg.tcp_send(other_ip=other_ip, other_tcp_port=other_tcp_port, data_to_send=msg)

    def send_p2p_msg_thread(self):
        while True:
            if self.trans_msg.recv_brd_msgs != []:
                recv_brd_msg, parsed_port = self.trans_msg.recv_brd_msgs[-1]
                self.send_p2p_msg(other_tcp_port=parsed_port, msg='Hello !')
                return


############################################
##################  MAIN  ##################
############################################

def main():
    print("*" * 50)
    print("To terminate this program use: CTRL+C")
    print("If the program blocks/throws, you have to terminate it manually.")
    p2p_node = P2P_node()
    print(f"NODE UUID: {p2p_node.trans_msg.node_uuid}")
    print("*" * 50)
    time.sleep(0.5)   # Wait a little bit.

    brd_thread = p2p_node.daemon_thread_builder(p2p_node.brd_msg, args=())
    brd_thread.start()

    recv_brd_msg_thread = p2p_node.daemon_thread_builder(p2p_node.recv_brd_msg, args=())
    recv_brd_msg_thread.start()

    recv_p2p_msg_thread = p2p_node.daemon_thread_builder(p2p_node.recv_p2p_msg, args=())
    recv_p2p_msg_thread.start()

    send_p2p_msg_thread = p2p_node.daemon_thread_builder(p2p_node.send_p2p_msg_thread, args=())
    send_p2p_msg_thread.start()

    brd_thread.join()
    recv_brd_msg_thread.join()
    recv_p2p_msg_thread.join()
    send_p2p_msg_thread.join()

if __name__ == "__main__":
    main()
