import pickle
import socket
import time
import uuid
import re
import sys
import gzip
import threading
from const import *
from block import Block
from blockchain import ForkBlock
import bloom
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
import hashlib
from datetime import datetime

ANSI_RESET = "\u001B[0m"
ANSI_RED = "\u001B[31m"
ANSI_GREEN = "\u001B[32m"
ANSI_YELLOW = "\u001B[33m"
ANSI_BLUE = "\u001B[34m"

_NODE_UUID = str(uuid.uuid4())[:8]


def print_yellow(msg):
    current_time = datetime.now()
    print(f"{ANSI_YELLOW}{msg}{ANSI_RESET}", current_time)


def print_blue(msg):
    current_time = datetime.now()
    print(f"{ANSI_BLUE}{msg}{ANSI_RESET}", current_time)


def print_red(msg):
    current_time = datetime.now()
    print(f"{ANSI_RED}{msg}{ANSI_RESET}", current_time)


def print_green(msg):
    current_time = datetime.now()
    print(f"{ANSI_GREEN}{msg}{ANSI_RESET}", current_time)


def get_broadcast_port():
    return 35498


def get_node_uuid():
    return _NODE_UUID

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

class NeighborInfo(object):
    def __init__(self, ip, tcp_port=None, uuid=None, addr=None, node_type=None, pk=None):
        self.ip = ip
        self.tcp_port = tcp_port
        self.uuid = uuid
        self.addr = addr
        self.node_type = node_type
        self.index = None
        self.pk = pk

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
        # set IP addr
        self.local_ip = socket.gethostbyname(socket.gethostname())

        # Server TCP
        self.server_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_tcp.bind((self.local_ip, 0))
        self.server_tcp.listen()

        # Broadcaster UDP
        self.broadcaster_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broadcaster_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.broadcaster_udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broadcaster_udp.settimeout(5)

        self.node_uuid = get_node_uuid()

        self.self_port = self.server_tcp.getsockname()[1]

        # Client TCP
        self.client_tcp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.client_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.client_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client_tcp.bind(('', get_broadcast_port()))


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
            print_green('Success add neighbor! Now I have '+str(len(self.neighbor_info))+' neighbors (acc: ' + str(len(self.acc_neighbor_info)) + ' and con: ' + str(len(self.con_neighbor_info)) + ').')
            # self.print_neighbors()

    def find_neighbor_ip_and_port_via_uuid(self, uuid):
        for neighbor in self.neighbor_info:
            if neighbor.uuid == uuid:
                return neighbor.ip, neighbor.tcp_port
        return None, None


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

    def find_neighbor_ip_and_port_via_addr(self, addr):
        for neighbor in self.neighbor_info:
            if neighbor.addr == addr:
                return neighbor.ip, neighbor.tcp_port
        return None, None

    def find_neighbor_pk_via_uuid(self, uuid):
        for neighbor in self.neighbor_info:
            if neighbor.uuid == uuid:
                return neighbor.pk
        return None

    def find_neighbor_pk_via_addr(self, addr):
        for neighbor in self.neighbor_info:
            if neighbor.addr == addr:
                return neighbor.pk
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
        # print_blue("The size of broadcast " + msg_type + " msg is " + str(sys.getsizeof(compressed_msg)) + " bytes.")
        # msg_size = sys.getsizeof(msg)

        self.broadcaster_udp.sendto(compressed_msg, ('255.255.255.255', get_broadcast_port()))
        # print_blue("broadcast *" + msg_type + "* msg, size = " + str(sys.getsizeof(compressed_msg)) + " bytes.")
        print_blue("broadcast *" + msg_type + "* msg")
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

    def get_msg_type(self, text):
        pattern = r"(\w+) MSG:"
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        else:
            return "no matched word"

    def tcp_receive(self, my_chain=None, acc_node=None):
        while True:
            conn, (sender_client_ip, sender_client_port) = self.server_tcp.accept()
            decompressed_data = gzip.decompress(conn.recv(10240))
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

            sender_server_ip, sender_server_port = self.find_neighbor_ip_and_port_via_uuid(uuid)

            # received_data = pickle.loads(conn.recv(4096))  # 这里的4096表示接收消息的最大字节数
            # print_blue("Received TCP data: " + received_data)
            # msg_type = self.get_msg_type(received_data)

            # the msg process is NOT parallel, if change to parallel,
            # some parms need process Lock!
            # todo: change msg process to be parallel, and add parm's Lock.
            #  24-1-16: change msg process to be parallel: MTreeProof & VPBPair
            if msg_type == "Hello":
                print_yellow('recv hello tcp msg.')
                self.tcp_hello_process(pure_msg)
            if msg_type == "MTreeProof":
                print_yellow('recv MTreeProof tcp msg.')
                tcp_MTree_proof_process = daemon_thread_builder(
                    self.tcp_MTree_proof_process, args=(pure_msg, acc_node))
                tcp_MTree_proof_process.start()
                tcp_MTree_proof_process.join()
            if msg_type == "VPBPair":
                print_yellow('recv VPBPair tcp msg.')
                if sender_server_ip == None or sender_server_port == None:
                    raise ValueError('sender server ip and port NOT FIND!')
                tcp_VPBPair_process = daemon_thread_builder(
                    self.tcp_VPBPair_process, args=(pure_msg, acc_node, my_chain, uuid,
                                                    sender_server_ip, sender_server_port))
                tcp_VPBPair_process.start()
                tcp_VPBPair_process.join()
            if msg_type == "TxnTestResult":
                print_yellow('recv TxnTestResult tcp msg.')
                self.tcp_txn_test_result_process(pure_msg, acc_node)


    def tcp_hello_process(self, pure_msg):
        (uuid, port, addr, node_type, pk, other_ip) = self.decode_hello_msg(pure_msg)
        # print_blue("Recv Hello msg, add new neighbor...")
        # process logic of recv hello msg:
        new_neighbor = NeighborInfo(ip= other_ip, tcp_port=port, uuid=uuid, addr=addr, node_type=node_type, pk=pk)
        self.add_neighbor(new_neighbor)

    def tcp_MTree_proof_process(self, pure_msg, acc_node):
        # unit tool
        def hash(val):
            if type(val) == str:
                return hashlib.sha256(val.encode("utf-8")).hexdigest()
            else:
                return hashlib.sha256(val).hexdigest()

        with acc_node.temp_recv_mTree_prf_lock:
            # update vpb (mTreePrf is the mtree proof in VPB, and block_index is the new block's index)
            (mTreePrf, block_index, block_hash) = pure_msg
            # find the related values in this acc_txns_package
            acc_package_hash = mTreePrf[0]
            # find related corresponding temporary package
            add_this_mtree_prf_flag = False
            if acc_node.temp_sent_package != []:
                # related_values = [] # record related values
                for item in acc_node.temp_sent_package:
                    (acc_txns, acc_txns_package) = item
                    (acc_package_digest, acc_package_sig, acc_addr, acc_global_id) = acc_txns_package
                    if hash(acc_package_digest) == acc_package_hash:
                        # this mTreePrf msg is need by self, thus add it.
                        """for acc_txn in acc_txns:
                            related_values += acc_txn.get_values()"""
                        # record the recv mTree proof and some other info
                        acc_node.temp_recv_mTree_prf.append((mTreePrf, block_index, block_hash))
                        add_this_mtree_prf_flag = True
            if not add_this_mtree_prf_flag:
                print_yellow('no corresponding temporary package, ignore this MTree proof msg.')
                pass
            else:
                print_green('Success add this mTree proof msg, now my mTree prd lst has ' +
                            str(len(acc_node.temp_recv_mTree_prf)) + ' prfs.')

    def tcp_VPBPair_process(self, pure_msg, acc_node, my_chain, uuid, other_ip, other_port):
        # wait for new block if necessary
        vpb_required_block_index = 0
        for one_vpb in pure_msg:
            b = one_vpb[2]
            # sure that confirmed blocks can support the check of this vpb
            if b[-1] > vpb_required_block_index:
                vpb_required_block_index = b[-1]
        while True:
            latest_confirmed_block_index = my_chain.get_latest_confirmed_block_index()
            if latest_confirmed_block_index == None:
                # no block has been confirmed, thus wait for vpb_required_block_index
                print('wait 1 sec for new confirmed block adding...')
                time.sleep(1) # wait 1 sec for recv more confirmed blocks
            else:
                if latest_confirmed_block_index >= vpb_required_block_index:
                    # confirmed blocks can support the check of vpb
                    break
                else:
                    print('wait 1 sec for new confirmed block adding...')
                    time.sleep(1)  # wait 1 sec for recv more confirmed blocks

        while acc_node.vpb_lock:
            # wait un-lock
            print('tcp_VPBPair_process: wait 0.5 sec for un-lock of vpb_lock...')
            time.sleep(0.5)

        ### vpb LOCK ###
        acc_node.set_vpb_lock_dst(True)

        # print_blue('recv VPB msg')
        # with acc_node.resource_lock:
        # the logic of processing recved vpb pair
        print_blue('recv VPB msg, testing...')

        # check each vpb in the recv vpb pairs
        test_flag = -1
        # check each vpb in pure_msg
        for index, one_vpb in enumerate(pure_msg):
            # for test
            # acc_node.print_one_vpb(one_vpb)
            if not acc_node.account.check_VPBpair(VPBpair=one_vpb, bloomPrf=[], blockchain=my_chain):
                test_flag = index

        # process test result
        if test_flag < 0:
            # pass test, thus add this new VPB pairs
            for one_vpb in pure_msg:
                try:
                    # complete the vpb via local mtree proof lst.
                    acc_node.complete_vpb_dst(one_vpb)
                except Exception as e:
                    raise RuntimeError("ERR-vpb complete fail:" + str(e))
                acc_node.account.add_VPBpair_dst(one_vpb)
            print_green("Accept the value(s) from " + str(uuid))
            # print new value(s) for test:
            accepted_values_lst = [x[0] for x in pure_msg]
            print_green('/////Accepted value list://///')
            for one_v in accepted_values_lst:
                one_v.print_value()

            self.tcp_send(other_tcp_port=other_port, data_to_send="txn success!",
                        msg_type="TxnTestResult", other_ip=other_ip)
        else:
            # vpb check fail (at least one vpb illegal)
            print_red("VPB test fail! reject this value from " + str(uuid))
            self.tcp_send(other_tcp_port=other_port, data_to_send="txn fail!",
                        msg_type="TxnTestResult", other_ip=other_ip)

        ### vpb UN-LOCK ###
        acc_node.set_vpb_lock_dst(False)

    def tcp_txn_test_result_process(self, pure_msg, acc_node):
        if pure_msg == 'txn success!':
            print_green('One txn has been confirmed!')
            acc_node.clear_and_fresh_info_dst()
        """if pure_msg == 'txn success!':
            acc_node.this_round_success_txns_num += 1
        if acc_node.this_round_success_txns_num >= acc_node.this_round_txns_num:
            print_green('All txns confirm! Entry next round.')
            # clear and flash self data
            acc_node.clear_and_fresh_info_dst()
            # start send new package to txn pool
            acc_node.send_package_flag += 0.1"""

    def tcp_send(self, other_tcp_port, data_to_send, msg_type, other_ip):
        """
        Open a connection to the other_ip, other_tcp_port
        and do the steps to exchange timestamps.
        Then update the neighbor_info map using other node's UUID.
        """
        pickled_msg = pickle.dumps(data_to_send)  # msg may not str!
        msg_prefix = "node_uuid: " + str(self.node_uuid) + " ON " + str(self.self_port) + " , " + msg_type + " MSG: "
        encoded_msg_prefix = msg_prefix.encode("utf-8")
        encode_msg = encoded_msg_prefix + pickled_msg

        compressed_msg = gzip.compress(encode_msg)  # zip msg

        SENDER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            SENDER.connect((other_ip, int(other_tcp_port)))
        except Exception as e:
            raise RuntimeError("An error occurred in SENDER.connect " + str(other_ip) +
                               ": " + str(other_tcp_port) + str(e))

        # address = (other_ip, int(other_tcp_port))
        # pickled_data = pickle.dumps(data_to_send)
        # print the size of compressed msg
        # print_blue("The size of tcp sent " + msg_type + " msg is " + str(sys.getsizeof(compressed_msg)) + " bytes.")
        print_blue('TCP send *'+msg_type+'* msg.')
        SENDER.send(compressed_msg)

        SENDER.close()

    def decode_hello_msg(self, hello_msg):
        decoded_msg = hello_msg.split(" ")
        uuid = decoded_msg[1]
        port = decoded_msg[3]
        addr = decoded_msg[5]
        node_type = decoded_msg[7]
        pk = bytes.fromhex(decoded_msg[9])
        ip = decoded_msg[11]
        return uuid, port, addr, node_type, pk, ip

    def listen_brd(self, my_addr, my_type, my_local_chain, my_pk, con_node, acc_node):
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
                    print_yellow('recv hello brd msg.')
                    hello_msg_process = daemon_thread_builder(
                        self.hello_msg_process, args=(my_addr, my_type, my_pk, pure_msg))
                    hello_msg_process.start()
                    hello_msg_process.join()
                elif msg_type == 'Block':
                    print_yellow('recv block brd msg.')
                    if self.node_type == "con": # con node process this msg, acc node ignore it.
                        block_msg_process = daemon_thread_builder(self.block_msg_process, args=(
                            my_local_chain, my_type, uuid, pure_msg, con_node, None))
                        block_msg_process.start()
                        block_msg_process.join()
                    elif self.node_type == "acc":
                        # with acc_node.resource_lock:
                        # self.block_msg_process(my_local_chain, my_type, uuid, pure_msg, None, acc_node)
                        block_msg_process = daemon_thread_builder(self.block_msg_process, args=(
                            my_local_chain, my_type, uuid, pure_msg, None, acc_node))
                        block_msg_process.start()
                        block_msg_process.join()
                elif msg_type == 'AccTxnsPackage':
                    print_yellow('recv AccTxnsPackage brd msg.')
                    if self.node_type == "con": # con node process this msg, acc node ignore it.
                        acc_txns_package_msg_process = daemon_thread_builder(self.acc_txns_package_msg_process, args=(
                            uuid, con_node, pure_msg,))
                        acc_txns_package_msg_process.start()
                        acc_txns_package_msg_process.join()
                else:
                    print_red('Not Find this msg_type: ' + msg_type)
                    pass

    def hello_msg_process(self, my_addr, my_type, my_pk, pure_msg):
        (uuid, port, addr, node_type, pk, other_ip) = self.decode_hello_msg(pure_msg)
        # print_blue("Recv Hello msg, add new neighbor...")
        # process logic of recv hello msg:
        new_neighbor = NeighborInfo(ip=other_ip, tcp_port=port, uuid=uuid, addr=addr, node_type=node_type, pk=pk)
        self.add_neighbor(new_neighbor)
        # create self info for new neighbor
        my_uuid = "uuid: " + str(self.node_uuid)
        my_port = "port: " + str(self.self_port)
        my_addr_2 = "addr: " + str(my_addr)
        my_type_2 = "node_type: " + my_type
        my_pk_2 = "pk: " + my_pk.hex()
        my_ip_addr = "ip: " + str(self.local_ip)
        hello_msg = my_uuid + " " + my_port + " " + my_addr_2 + " " + my_type_2 + " " + my_pk_2 + " " + my_ip_addr
        """msg_prefix = "node_uuid: " + str(self.node_uuid) + " ON " + str(self.self_port) + " Hello MSG: "
        new_msg_info = msg_prefix + hello_msg"""
        # send self info to new neighbor
        # print_blue("send tcp msg to " + port + " from " + my_port + ": " + str(new_msg_info))
        self.tcp_send(other_tcp_port=port, data_to_send=hello_msg, msg_type="Hello", other_ip=other_ip)

    def check_block_with_block_body(self, block, m_tree, acc_digests, acc_sigs, acc_addrs, acc_node=None):
        # check unit tool
        def has_duplicate(input_list):
            seen = set()
            for item in input_list:
                if item in seen:
                    return True
                seen.add(item)
            return False
        def hash(val):
            if type(val) == str:
                return hashlib.sha256(val.encode("utf-8")).hexdigest()
            else:
                return hashlib.sha256(val).hexdigest()
        # ver block via block body info
        # 0. init check info
        check_bloom = bloom.BloomFilter()
        # 1. check merkel tree
        if not m_tree.checkTree():
            return False
        # 2. check merkel tree root in the block
        if block.get_m_tree_root() != m_tree.getRootHash():
            return False
        # 3. check the acc_sigs with acc_addrs
        if len(acc_sigs) != len(acc_addrs) or len(acc_sigs) != len(acc_digests) or len(acc_sigs) != len(m_tree.leaves):
            return False
        if has_duplicate(acc_addrs):
            return False
        # 4. check sigs' legality
        for index, acc_sig in enumerate(acc_sigs):
            acc_addr = acc_addrs[index]
            check_bloom.add(acc_addr)
            acc_digest = acc_digests[index].encode('utf-8')
            if acc_node != None: # acc node
                if acc_addr == acc_node.account.addr: # this sig is sigged by self, pass check
                    continue
            load_acc_pk = self.find_neighbor_pk_via_addr(acc_addr)
            if load_acc_pk == None:
                raise ValueError('Not find neighbor with addr: '+str(acc_addr))
            # check sig
            public_key = load_pem_public_key(load_acc_pk)
            signature_algorithm = ec.ECDSA(hashes.SHA256())
            try:
                public_key.verify(
                    acc_sig,
                    acc_digest,
                    signature_algorithm
                )
            except:
                return False
        # 5. check block's bloom
        if block.get_bloom().bit_array != check_bloom.bit_array:
            return False
        # 6. check digest and merkel tree's leaves
        for index, leaf in enumerate(m_tree.leaves):
            if leaf.value != hash(acc_digests[index]):
                return False
        # all check pass
        return True

    def block_msg_process(self, my_local_chain, my_type, uuid, pure_msg, con_node, acc_node):
        if type(pure_msg) == Block: # genesis block
            if pure_msg.index != 0:
                print_yellow('block without body, ignore!')
                return
            block = pure_msg
            if len(my_local_chain.chain) == 0: # local chain is empty
                my_local_chain.add_block(block)
                print_green("Success add this GENESIS block: "+block.block_to_short_str()+", now my chain's len = " + str(len(my_local_chain.chain)))
            else:
                # print_yellow('Ignore this GENESIS block.')
                pass
        else: # non-genesis block
            # unpack block msg
            try:
                (block, m_tree, acc_digests, acc_sigs, acc_addrs) = pure_msg
            except:
                print_red('this block msg CANNOT unpack!')
                return
            # check block via block body info
            check_result = self.check_block_with_block_body(block, m_tree, acc_digests, acc_sigs, acc_addrs, acc_node)
            if not check_result:
                print_red('block body check NOT pass!')
                return
            # find miner's pk
            miner_pk = self.find_neighbor_pk_via_uuid(uuid)
            if miner_pk == None:
                print('No miner pk find!')
                return
            # logic of add block
            if my_type == "con": # con node
                if con_node.con_node.check_block_sig(block, block.sig, miner_pk):
                    # the block pass test of block sig
                    try:
                        longest_chain_flash_flag = my_local_chain.add_block(block)
                        # the process of after adding new block (longest chain or not)
                        # flash self txns pool due to new block body
                        con_node.txns_pool.clear_pool_dst(acc_digests)
                    except:
                        raise ValueError('Add block fail!')
                    # this block flash the longest chain
                    if longest_chain_flash_flag:
                        con_node.recv_new_block_flag = 1
                    print_green(
                        "Success add this block: " + block.block_to_short_str() + ", now my chain's len = " + str(
                            len(my_local_chain.chain)))
                    my_local_chain.print_latest_block_hash_lst_dst()
                else:
                    print('block sig illegal!')
            elif my_type == "acc": # acc node
                while acc_node.block_process_lock:
                    print('wait 1 sec for pre block process...')
                    time.sleep(1)

                # set the block process lock to True, LOCK the block process.
                acc_node.set_block_process_lock_dst(boolean=True)

                if acc_node.account.check_block_sig(block, block.sig, miner_pk):
                    try:
                        longest_chain_flash_flag = my_local_chain.add_block(block)
                    except:
                        raise ValueError('Add block fail!')
                    if longest_chain_flash_flag:
                        while acc_node.vpb_lock:
                            # wait un-lock
                            print('update_and_check_VPB_pairs: wait 0.5 sec for un-lock of vpb_lock...')
                            time.sleep(0.5)

                        ### vpb LOCK ###
                        acc_node.set_vpb_lock_dst(True)
                        # if the longest chain is changed, then update the vpb pairs.
                        acc_node.update_and_check_VPB_pairs()
                        ### vpb UN-LOCK ###
                        acc_node.set_vpb_lock_dst(False)

                    acc_node.send_package_flag += 0.5  # wait for vpb update, send_package_flag can be 1
                    print_green(
                        "Success add this block: " + block.block_to_short_str() + ", now my chain's len = " + str(
                            len(my_local_chain.chain)))
                    my_local_chain.print_latest_block_hash_lst_dst()
                    # set the block process lock to False, UN-LOCK the block process.
                    acc_node.set_block_process_lock_dst(boolean=False)
                else:
                    print('block sig illegal!')

    def block_body_msg_process(self, pure_msg):
        (block_hash, block_Mtree) = pure_msg

    def acc_txns_package_msg_process(self, uuid, con_node, pure_msg):
        if not con_node.txns_pool.check_is_repeated_package(pure_msg, uuid):
            # add acc_txns_package to self txn pool
            con_node.txns_pool.add_acc_txns_package_dst(pure_msg, uuid)
        else:
            print_yellow('Recv repeated package from ' + str(uuid))
            pass

    def decode_acc_txns_package_msg(self, acc_txns_package_msg):
        pass

    def listen_acc_txns_package(self, pure_msg):
        pass

    def brd_hello_to_neighbors(self, addr, node_type, pk):
        print_blue('Init and brd hello msg to neighbors!')
        uuid = "uuid: " + str(self.node_uuid)
        port = "port: " + str(self.self_port)
        addr_2 = "addr: " + str(addr)
        node_type_2 = "node_type: " + node_type
        pk_2 = "pk: " + pk.hex()
        ip_addr = "ip: " + str(self.local_ip)
        hello_msg = uuid + " " + port + " " + addr_2 + " " + node_type_2 + " " + pk_2 + " " + ip_addr
        self.broadcast(msg=hello_msg, msg_type='Hello')

    def brd_block_to_neighbors(self, block):
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

    def print_brief_acc_neighbors(self):
        print("=" * 25)
        for index, value in enumerate(self.acc_neighbor_info, start=0):
            print(f"Neighbor {index} Info:")
            print(f"IP: {value.ip}: {value.tcp_port}")
            print("-----------------")
        print("=" * 25)