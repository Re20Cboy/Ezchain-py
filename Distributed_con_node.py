from block import Block
from blockchain import Blockchain
from message import BlockBodyMsg, BlockMsg
from const import *
import random
import time
import bloom
# 签名所需引用
import string
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from utils import ensure_directory_exists, write_data_to_file

import threading
import socket
import time
import uuid
import random
import blockchain
import json

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
    def __init__(self, delay, last_timestamp, broadcast_count, ip=None, tcp_port=None):
        # Ip and port are optional, if you want to store them.
        self.delay = delay
        self.last_timestamp = last_timestamp
        self.broadcast_count = broadcast_count
        self.ip = ip
        self.tcp_port = tcp_port

""" /////////////////////
       Global Variables
    ///////////////////// """

class ConNode:
    def __init__(self, port=0, new_port=0, node_uuid=0):
        self.blockchain = Blockchain()
        self.tmpBlockMsg = None # 临时存储的区块信息
        self.tmpBlockBodyMsg = None # 临时存储的区块详细信息（默克尔树格式）
        self.privateKeyPath = None # 存储私钥的地址
        self.publicKeyPath = None # 存储公钥的地址
        self.privateKey = None # 私钥
        self.publicKey = None # 公钥
        self.addr = None


        self.blockBrdCostedTime = [] # 用于记录广播消耗的时间，最后用于计算tps、区块确认等数据
        self.blockBodyBrdCostedTime = [] # 用于记录广播消耗的时间，最后用于计算tps、区块确认等数据
        self.blockCheckCostedTime = []  # 用于记录验证消耗的时间，最后用于计算tps、区块确认等数据
        self.blockBodyCheckCostedTime = []  # 用于记录验证消耗的时间，最后用于计算tps、区块确认等数据

        # distributed network part
        self.port = port
        self.new_port = new_port
        self.node_uuid = get_node_uuid()
        self.neighbor_info = {}
        self.one_hash_time = D_ONE_HASH_TIME
        self.no_recv_new_block = False
        self.mining_lock = threading.Lock()
        # Server TCP
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('127.0.0.1', 0))
        self.server.listen()
        # Broadcaster UDP
        self.broadcaster = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broadcaster.settimeout(4)

        self.generate_node_info()  # 随机生成node的公私钥对及地址信息

    def generate_node_info(self):
        '''
        随机生成node的公钥、私钥及地址信息
        '''
        # 生成随机地址
        self.addr = ''.join(random.choices(string.ascii_letters + string.digits, k=42)) # bitcoin地址字符数为42
        # 生成私钥
        private_key = ec.generate_private_key(ec.SECP384R1())
        # 从私钥中获取公钥
        public_key = private_key.public_key()
        # 保存公私钥的地址：
        privatePath = NODE_PRIVATE_KEY_PATH + "private_key_node_"+str(self.node_uuid)+".pem"
        publicPath = NODE_PUBLIC_KEY_PATH + "public_key_node_"+str(self.node_uuid)+".pem"
        self.privateKeyPath = privatePath
        self.publicKeyPath = publicPath
        # 生成私钥
        self.privateKey = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        # 生成公钥
        self.publicKey = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        # 保存私钥到文件（请谨慎操作，不要轻易泄露私钥）
        ensure_directory_exists(privatePath)
        write_data_to_file(privatePath, self.privateKey)
        # 保存公钥到文件（公钥可以公开分发给需要验证方）
        ensure_directory_exists(publicPath)
        write_data_to_file(publicPath, self.publicKey)

    def sig_block(self, block):
        # 从私钥路径加载私钥
        # with open(self.privateKeyPath, "rb") as key_file:
        private_key = load_pem_private_key(self.privateKey, password=None)
        # 使用SHA256哈希算法计算区块的哈希值
        block_hash = hashes.Hash(hashes.SHA256())
        block_hash.update(block.block_to_str().encode('utf-8'))
        digest = block_hash.finalize()
        signature_algorithm = ec.ECDSA(hashes.SHA256())
        # 对区块哈希值进行签名
        signature = private_key.sign(data=digest, signature_algorithm=signature_algorithm)
        return signature

    def check_block_sig(self, block, signature, load_public_key):
        # 从公钥路径加载公钥
        # with open(load_public_key_path, "rb") as key_file:
        public_key = load_pem_public_key(load_public_key)
        # 使用SHA256哈希算法计算区块的哈希值
        block_hash = hashes.Hash(hashes.SHA256())
        block_hash.update(block.block_to_str().encode('utf-8'))
        digest = block_hash.finalize()
        signature_algorithm = ec.ECDSA(hashes.SHA256())
        # 验证签名
        try:
            public_key.verify(
                signature,
                digest,
                signature_algorithm
            )
            return True
        except:
            return False

    def create_new_block_body(self):
        blockBody = BlockBodyMsg()
        blockBody.random_generate_mTree(PICK_TXNS_NUM)
        self.tmpBlockBodyMsg = blockBody

    def create_new_block(self, m_tree_root = None):
        # 首先打包交易，形成block body
        self.create_new_block_body()

        preBlockHash = self.blockchain.get_latest_block_hash()
        index = len(self.blockchain.chain)
        if m_tree_root is None:
            m_tree_root = self.tmpBlockBodyMsg.get_mTree_root_hash()
        miner = self.node_uuid
        block = Block(index = index, m_tree_root = m_tree_root, miner = miner, pre_hash = preBlockHash)
        #设置正确的bloom
        for item in self.tmpBlockBodyMsg.info_Txns:
            block.bloom.add(item[2])

        # 对区块进行签名
        sig = self.sig_block(block)
        block.sig = sig

        self.tmpBlockMsg = BlockMsg(block)
        self.blockchain.add_block(block)
        return block

    def get_block_from_json(self, json_str):
        data = json.loads(json_str)
        index = data["index"]
        nonce = data["nonce"]
        bloom = data["bloom"]
        m_tree_root = data["m_tree_root"]
        time = data["time"]
        miner = data["miner"]
        pre_hash = data["pre_hash"]
        sig = data["sig"]

        reconstructed_block = Block(index=index, m_tree_root=m_tree_root, miner=miner, pre_hash=pre_hash)
        reconstructed_block.time = time
        reconstructed_block.bloom = bloom
        reconstructed_block.sig = sig

        return reconstructed_block

    def one_round_hash(self):
        time.sleep(self.one_hash_time)

    def one_round_mine(self, port_number):
        with self.mining_lock:
            global no_recv_new_block
            no_recv_new_block = True

            print_yellow('begin mine...')
            mine_count = 0
            mine_flag = random.randint(500, 1000)  # 随机生成mine时间
            while no_recv_new_block:
                self.one_round_hash()
                mine_count += 1
                if mine_count >= mine_flag:  # 完成一轮挖矿，并广播
                    # generate new block
                    print_green('mine success and brd block.')
                    new_block = self.create_new_block()
                    self.send_broadcast_thread(port_number, new_block)
                    miner = self.daemon_thread_builder(self.one_round_mine, args=(port_number,))
                    miner.start()
                    print_red('mine new block, kill this mine.')
                    return
            print_red('recv new block, kill this mine.')

    # Send the broadcast Message Function
    def send_broadcast_thread(self, port_number, new_block):
        new_block_json = new_block.block_to_json()
        Message = str(self.node_uuid) + " ON " + str(port_number) + " block: "
        # ip_and_port = server.getsockname()
        Message_V2 = Message.encode("utf-8")
        encode_block = Message_V2 + new_block_json
        self.broadcaster.sendto(encode_block, ('255.255.255.255', get_broadcast_port()))
        print_green("msg(new block) is brd.")
        pass


    # Chef If Node Recieve Itself Function
    def checkIfsameNode(self, message):
        if (self.node_uuid != message[0] and self.neighbor_info.get(message[0]) == None):
            return 1
        elif (self.node_uuid != message[0] and self.neighbor_info.get(message[0]) != None):
            return 2
        else: # node_uuid == message[0], i.e., node itself
            return 0

    # Receive the broadcast Message Function
    def receive_broadcast_thread(self):
        """
        Receive broadcasts from other nodes,
        launches a thread to connect to new nodes
        and exchange timestamps.
        """
        global neighbor_information
        global no_recv_new_block
        global server
        self_port = server.getsockname()[1]

        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client.bind(('', get_broadcast_port()))

        while True:
            data, (ip, port) = client.recvfrom(4096) # 这里的4096限制发送消息的大小为4096字节

            # 定义block的前缀
            prefix = " block: "
            # 寻找前缀的位置并获取其后面的部分作为 parsed_block_json
            prefix_index = data.find(prefix.encode("utf-8"))
            parsed_block_json = data[(prefix_index + len(prefix)):].decode("utf-8")
            block_from_json = self.get_block_from_json(parsed_block_json)

            non_block_info = data[:(prefix_index + len(prefix))].decode("utf-8")
            parsed = non_block_info.split(" ")
            newnodeflag = self.checkIfsameNode(parsed)

            if(newnodeflag == 1 or newnodeflag == 2):
                # todo: ver block
                valid_flag = self.blockchain.is_valid_block(block_from_json)
                if valid_flag:
                    print_blue(f'test success, add recv block to chain, FROM: {ip}:{port}.')
                else:
                    print_red('test fail, ignore recv block, FROM: {ip}:{port}.')
                    continue

                no_recv_new_block = False
                self.blockchain.add_block(block_from_json)
                miner = self.daemon_thread_builder(self.one_round_mine, args=(self_port,))
                miner.start()
                # miner.join()


    # Create Threads Function
    def daemon_thread_builder(self, target, args=()) -> threading.Thread:
        """
        Use this function to make threads. Leave as is.
        """
        th = threading.Thread(target=target, args=args)
        th.setDaemon(True)
        return th

    # Start Sending and Receiving Broadcast Message
    def entrypoint(self):
        self_port = self.server.getsockname()[1]

        # Receive Broadcast
        receiver = self.daemon_thread_builder(self.receive_broadcast_thread)
        miner = self.daemon_thread_builder(self.one_round_mine, args=(self_port,))

        miner.start()
        receiver.start()

        miner.join()
        receiver.join()

        pass


############################################
############################################


def main():
    print("*" * 50)
    print_red("To terminate this program use: CTRL+C")
    print_red("If the program blocks/throws, you have to terminate it manually.")
    print_green(f"NODE UUID: {get_node_uuid()}")
    print("*" * 50)
    time.sleep(0.5)   # Wait a little bit.

    con_node = ConNode()
    con_node.generate_node_info()
    con_node.entrypoint()

if __name__ == "__main__":
    main()
