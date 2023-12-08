import pickle
import socket
import uuid

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


class NeighborInfo(object):
    def __init__(self, ip="127.0.0.1", tcp_port=None, uuid=None, addr=None):
        self.ip = ip
        self.tcp_port = tcp_port
        self.uuid = uuid
        self.addr = addr

class TransMsg:
    def __init__(self):
        self.self_port = 0
        self.node_uuid = 0
        self.neighbor_info = {}
        self.server_tcp = None
        self.broadcaster_udp = None
        self.client_tcp = None
        self.recv_brd_msgs = [] # recv brd msg list
        self.local_ip = None
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
        self.neighbor_info[neighbor_info_instance.uuid] = neighbor_info_instance
    def check_is_self(self, msg):
        if (self.node_uuid != msg and self.neighbor_info.get(msg) == None):
            return 1
        elif (self.node_uuid != msg and self.neighbor_info.get(msg) != None):
            return 2
        else:  # node_uuid == message, i.e., node itself
            return 0

    def broadcast(self, msg, msg_type):
        pickled_msg = pickle.dumps(msg)
        msg_prefix = "node_uuid: " + str(self.node_uuid) + " ON " + str(self.self_port) + " MSG: " + msg_type + ": "
        encoded_msg_prefix = msg_prefix.encode("utf-8")
        encode_msg = encoded_msg_prefix + pickled_msg
        self.broadcaster_udp.sendto(encode_msg, ('255.255.255.255', get_broadcast_port()))
        print_green("broadcast msg.")
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


    def tcp_receive(self):
        """
        Args:
        - server
        """
        conn, addr = self.server_tcp.accept()
        received_data = pickle.loads(conn.recv(4096))  # 这里的4096表示接收消息的最大字节数
        print_blue("Received TCP data: " + received_data)

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
        return uuid, port, addr

    def listen_hello(self, msg_type: str):
        while True:
            recv_brd_msg, (ip, port) = self.client_tcp.recvfrom(4096)  # max: 4096 Bytes

            # define prefix
            prefix = " MSG: " + msg_type + ": "
            # find prefix's index
            prefix_index = recv_brd_msg.find(prefix.encode("utf-8"))
            msg_info = pickle.loads(recv_brd_msg[(prefix_index + len(prefix)):])
            prefix_info = recv_brd_msg[:(prefix_index + len(prefix))].decode("utf-8")

            parsed_msg = prefix_info.split(" ")
            parsed_uuid = parsed_msg[1]

            (uuid, port, addr) = self.decode_hello_msg(msg_info)

            is_self_flag = self.check_is_self(parsed_uuid)
            if (is_self_flag == 1 or is_self_flag == 2):  # not self
                print_blue("Recv this msg, add new neighbor...")
                # process logic of recv hello msg:
                new_neighbor = NeighborInfo(tcp_port=port, uuid=uuid, addr=addr)
                self.add_neighbor(new_neighbor)
                print_green("Success add.")
            else:  # self node
                print_yellow("Ignore this msg.")

    def brd_hello_to_neighbors(self, addr):
        print_blue('Init and brd hello msg to neighbors!')
        uuid = "uuid: " + str(self.node_uuid)
        port = "port: " + str(self.self_port)
        addr = "addr: " + str(addr)
        hello_msg = uuid + " " + port + " " + addr
        self.broadcast(msg=hello_msg, msg_type='Hello')