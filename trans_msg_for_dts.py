import pickle
import socket
import uuid
import re
import sys
import gzip
import threading

ANSI_RESET = "\u001B[0m"
ANSI_RED = "\u001B[31m"
ANSI_GREEN = "\u001B[32m"
ANSI_YELLOW = "\u001B[33m"
ANSI_BLUE = "\u001B[34m"

_NODE_UUID = str(uuid.uuid4())[:8]


def print_yellow(msg):
    print(f"{ANSI_YELLOW}{msg}{ANSI_RESET}")


def print_blue(msg):
    print(f"{ANSI_BLUE}{msg}{ANSI_RESET}")


def print_red(msg):
    print(f"{ANSI_RED}{msg}{ANSI_RESET}")


def print_green(msg):
    print(f"{ANSI_GREEN}{msg}{ANSI_RESET}")


def get_broadcast_port():
    return 35498


def get_node_uuid():
    return _NODE_UUID

def daemon_thread_builder(target, args=()) -> threading.Thread:
    th = threading.Thread(target=target, args=args)
    th.setDaemon(True)
    return th

class NeighborInfo(object):
    def __init__(self, ip="127.0.0.1", tcp_port=None, uuid=None, addr=None, node_type=None):
        self.ip = ip
        self.tcp_port = tcp_port
        self.uuid = uuid
        self.addr = addr
        self.node_type = node_type

class TransMsg:
    def __init__(self, node_type):
        self.self_port = 0
        self.node_uuid = 0
        self.neighbor_info = []
        self.acc_neighbor_info = []
        self.con_neighbor_info = []
        self.server_tcp = None
        self.broadcaster_udp = None
        self.client_tcp = None
        self.recv_brd_msgs = [] # recv brd msg list
        self.local_ip = None
        self.node_type = node_type # acc or con
        self.generate_init_info()

    def generate_init_info(self):
        # Server TCP
        self.server_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_tcp.bind(('127.0.0.1', 0))
        self.server_tcp.listen()

        # Broadcaster UDP
        self.broadcaster_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broadcaster_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.broadcaster_udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broadcaster_udp.settimeout(4)

        self.node_uuid = get_node_uuid()

        self.self_port = self.server_tcp.getsockname()[1]

        # Client TCP
        self.client_tcp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.client_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.client_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client_tcp.bind(('', get_broadcast_port()))

        # set IP addr
        self.local_ip = socket.gethostbyname(socket.gethostname())

    def add_neighbor(self, neighbor_info_instance):
        if self.check_is_repeat_neighbor(neighbor_info_instance):
            # print_yellow('Repeated neighbor, ignore.')
            pass
        else:
            if neighbor_info_instance.node_type == 'acc':
                self.acc_neighbor_info.append(neighbor_info_instance)
            elif neighbor_info_instance.node_type == 'con':
                self.con_neighbor_info.append(neighbor_info_instance)
            self.neighbor_info.append(neighbor_info_instance)
            print_green('Success add neighbor! Now I have '+str(len(self.neighbor_info))+' neighbors')
            # self.print_neighbors()

    def check_is_repeat_neighbor(self, neighbor_info_instance):
        unchecked_uuid = neighbor_info_instance.uuid
        for item in self.neighbor_info:
            if item.uuid == unchecked_uuid:
                return True
        return False

    def find_neighbor_via_uuid(self, uuid):
        for index, item in enumerate(self.neighbor_info, start=0):
            if item.uuid == uuid:
                return index
        return None

    def check_is_self(self, msg):
        if (self.node_uuid != msg and self.find_neighbor_via_uuid(msg) == None):
            return 1
        elif (self.node_uuid != msg and self.find_neighbor_via_uuid(msg) != None):
            return 2
        else:  # node_uuid == message, i.e., node itself
            return 0

    def broadcast(self, msg, msg_type):
        pickled_msg = pickle.dumps(msg) # msg may not str!
        msg_prefix = "node_uuid: " + str(self.node_uuid) + " ON " + str(self.self_port) + " , " + msg_type +" MSG: "
        encoded_msg_prefix = msg_prefix.encode("utf-8")
        encode_msg = encoded_msg_prefix + pickled_msg

        compressed_msg = gzip.compress(encode_msg)  # zip msg

        # encode_msg_size = sys.getsizeof(all_msg)
        compressed_encode_msg_size = sys.getsizeof(compressed_msg)
        # msg_size = sys.getsizeof(msg)

        self.broadcaster_udp.sendto(compressed_msg, ('255.255.255.255', get_broadcast_port()))
        # print_green("broadcast *" + msg_type + "* msg, size = " + str(compressed_encode_msg_size) + " Bytes.")
        pass


    def brd_receive(self): # msg_type is str
        while True:
            recv_brd_msg, (ip, port) = self.client_tcp.recvfrom(4096) # max: 4096 Bytes

            # define prefix
            prefix = " MSG: "
            # find prefix's index
            prefix_index = recv_brd_msg.find(prefix.encode("utf-8"))
            non_data_info = recv_brd_msg[:(prefix_index + len(prefix))].decode("utf-8")
            parsed_msg = non_data_info.split(" ")
            parsed_uuid = parsed_msg[1]
            parsed_port = parsed_msg[3]
            is_self_flag = self.check_is_self(parsed_uuid)

            if (is_self_flag == 1 or is_self_flag == 2): # not self
                print_blue("Add msg.")
                self.recv_brd_msgs.append((recv_brd_msg, parsed_port))  # 将接收到的消息加入列表
            else: # self node
                print_red("Ignore msg.")
                pass

    def find_word_after_msg(self, text):
        pattern = r"MSG: (\w+)"
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        else:
            return "no matched word"

    def find_word_before_msg(self, text):
        pattern = r"(\w+) MSG:"
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        else:
            return "no matched word"

    def tcp_receive(self):
        """
        Args:
        - server
        """
        while True:
            conn, addr = self.server_tcp.accept()
            received_data = pickle.loads(conn.recv(4096))  # 这里的4096表示接收消息的最大字节数
            # print_blue("Received TCP data: " + received_data)

            result = self.find_word_before_msg(received_data)
            if result == "Hello":
                self.process_tcp_hello(received_data)

    def process_tcp_hello(self, received_data):
        # define prefix
        prefix =' Hello' + " MSG: "
        # find prefix's index
        prefix_index = received_data.find(prefix)
        msg_info = received_data[(prefix_index + len(prefix)):]
        prefix_info = received_data[:(prefix_index + len(prefix))]
        parsed_msg = prefix_info.split(" ")
        parsed_uuid = parsed_msg[1]
        (uuid, port, addr, node_type) = self.decode_hello_msg(msg_info)
        # print_blue("Recv this msg, add new neighbor...")
        # process logic of recv hello msg:
        new_neighbor = NeighborInfo(tcp_port=port, uuid=uuid, addr=addr, node_type=node_type)
        self.add_neighbor(new_neighbor)

    def tcp_send(self, other_tcp_port, data_to_send, other_ip="127.0.0.1"): # local test, thus other_ip="127.0.0.1"
        """
        Open a connection to the other_ip, other_tcp_port
        and do the steps to exchange timestamps.
        Then update the neighbor_info map using other node's UUID.
        """
        SENDER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        SENDER.connect((other_ip, int(other_tcp_port)))
        # address = (other_ip, int(other_tcp_port))
        pickled_data = pickle.dumps(data_to_send)
        SENDER.send(pickled_data)

        SENDER.close()

    def decode_hello_msg(self, hello_msg):
        decoded_msg = hello_msg.split(" ")
        uuid = decoded_msg[1]
        port = decoded_msg[3]
        addr = decoded_msg[5]
        node_type = decoded_msg[7]
        return uuid, port, addr, node_type

    def listen_brd(self, my_addr, my_type, my_local_chain, con_node, acc_node):
        while True:
            received_compressed_msg, (ip, port) = self.client_tcp.recvfrom(8192)  # max: 4096 Bytes
            # decompress recv msg
            decompressed_data = gzip.decompress(received_compressed_msg)
            # decode decompress recv msg
            prefix = " MSG: "
            # find prefix's index
            prefix_index = decompressed_data.find(prefix.encode("utf-8"))
            if prefix_index < 0:
                raise ValueError('prefix_index < 0 !')
            pure_msg = pickle.loads(decompressed_data[(prefix_index + len(prefix)):])
            prefix_info = decompressed_data[:(prefix_index + len(prefix))].decode("utf-8")
            parsed_msg = prefix_info.split(" ")
            uuid = parsed_msg[1]
            port = parsed_msg[3]
            msg_type = parsed_msg[5]

            # check is self's msg
            if self.check_is_self(uuid) == 0:
                # print_yellow('self msg, ignore.')
                pass
            else:
                # enter diff process func
                if msg_type == 'Hello':
                    hello_msg_process = daemon_thread_builder(
                        self.hello_msg_process, args=(my_addr, my_type, pure_msg, ))
                    hello_msg_process.start()
                    hello_msg_process.join()
                elif msg_type == 'Block':
                    if self.node_type == "con": # con node process this msg, acc node ignore it.
                        block_msg_process = daemon_thread_builder(self.block_msg_process, args=(
                            my_local_chain, my_type, pure_msg, con_node, None))
                        block_msg_process.start()
                        block_msg_process.join()
                    elif self.node_type == "acc":
                        block_msg_process = daemon_thread_builder(self.block_msg_process, args=(
                            my_local_chain, my_type, pure_msg, None, acc_node))
                        block_msg_process.start()
                        block_msg_process.join()
                elif msg_type == 'AccTxnsPackage':
                    if self.node_type == "con": # con node process this msg, acc node ignore it.
                        acc_txns_package_msg_process = daemon_thread_builder(self.acc_txns_package_msg_process, args=(
                            con_node, pure_msg,))
                        acc_txns_package_msg_process.start()
                        acc_txns_package_msg_process.join()
                else:
                    print_red('Not Find this msg_type: ' + msg_type)
                    pass

    def hello_msg_process(self, my_addr, my_type, pure_msg):
        (uuid, port, addr, node_type) = self.decode_hello_msg(pure_msg)
        print_blue("Recv Hello msg, add new neighbor...")
        # process logic of recv hello msg:
        new_neighbor = NeighborInfo(tcp_port=port, uuid=uuid, addr=addr, node_type=node_type)
        self.add_neighbor(new_neighbor)
        # create self info for new neighbor
        my_uuid = "uuid: " + str(self.node_uuid)
        my_port = "port: " + str(self.self_port)
        my_addr_2 = "addr: " + str(my_addr)
        my_type_2 = "node_type: " + my_type
        hello_msg = my_uuid + " " + my_port + " " + my_addr_2 + " " + my_type_2
        msg_prefix = "node_uuid: " + str(self.node_uuid) + " ON " + str(self.self_port) + " Hello MSG: "
        new_msg_info = msg_prefix + hello_msg
        # send self info to new neighbor
        # print_blue("send tcp msg to " + port + " from " + my_port + ": " + str(new_msg_info))
        self.tcp_send(other_tcp_port=port, data_to_send=new_msg_info)

    def block_msg_process(self, my_local_chain, my_type, pure_msg, con_node, acc_node):
        block = pure_msg
        # print_blue("Recv Block msg, add new block...")
        if block.index == 0: # is genesis block
            if len(my_local_chain.chain) == 0: # local chain is empty
                my_local_chain.add_block(block)
                print_green("Success add this GENESIS block: "+block.block_to_short_str()+", now my chain's len = " + str(len(my_local_chain.chain)))
            else:
                # print_yellow('Ignore this GENESIS block.')
                pass
        elif my_local_chain.is_valid_block(block): # valid block, otherwise ignore this block
            if my_type == "con": # con node
                con_node.recv_new_block_flag = 1
            my_local_chain.add_block(block)
            print_green("Success add this block: "+block.block_to_short_str()+", now my chain's len = " + str(len(my_local_chain.chain)))
            if my_type == "acc": # acc node
                acc_node.send_package_flag = 1

        else:
            print_red("Ignore this block.")

    def acc_txns_package_msg_process(self, con_node, pure_msg):
        if not con_node.txns_pool.check_is_repeated_package(pure_msg):
            # add acc_txns_package to self txn pool
            con_node.txns_pool.add_acc_txns_package(pure_msg)

    def decode_acc_txns_package_msg(self, acc_txns_package_msg):
        pass

    def listen_acc_txns_package(self, pure_msg):
        pass

    def brd_hello_to_neighbors(self, addr, node_type):
        print_blue('Init and brd hello msg to neighbors!')
        uuid = "uuid: " + str(self.node_uuid)
        port = "port: " + str(self.self_port)
        addr_2 = "addr: " + str(addr)
        node_type_2 = "node_type: " + node_type
        hello_msg = uuid + " " + port + " " + addr_2 + " " + node_type_2
        self.broadcast(msg=hello_msg, msg_type='Hello')

    def brd_block_to_neighbors(self, block):
        if block.index == 0:
            # print_blue('Brd GENESIS block to all nodes!')
            pass
        else:
            # print_blue('Brd block to all nodes!')
            pass
        self.broadcast(msg=block, msg_type='Block')

    def brd_acc_txns_package_to_con_node(self, acc_txns_package):
        # print_blue('Brd acc txns package to con-nodes (txn pool)!')
        self.broadcast(msg=acc_txns_package, msg_type='AccTxnsPackage')

    def print_neighbors(self):
        print("=" * 25)
        for index, value in enumerate(self.neighbor_info, start=0):
            print(f"Neighbor {index} Info:")
            print(f"IP: {value.ip}")
            print(f"TCP Port: {value.tcp_port}")
            print(f"UUID: {value.uuid}")
            print(f"Address: {value.addr}")
            print(f"Node Type: {value.node_type}")
            print("-----------------")
        print("=" * 25)