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


class Node:
    def __init__(self, id, neighbors = [], port = 0, dst = False):
        self.id = id
        #self.port = port
        self.neighbors = neighbors
        self.blockchain = Blockchain(dst=dst)
        #self.current_block = None  # 当前正在处理的区块
        #self.difficulty = 4  # PoW共识难度
        self.tmpBlockMsg = None # 临时存储的区块信息
        self.tmpBlockBodyMsg = None # 临时存储的区块详细信息（默克尔树格式）
        self.privateKeyPath = None # 存储私钥的地址
        self.publicKeyPath = None # 存储公钥的地址
        self.privateKey = None # 私钥
        self.publicKey = None # 公钥
        self.addr = None
        self.generate_random_node() # 随机生成node的公私钥对及地址信息
        self.blockBrdCostedTime = [] # 用于记录广播消耗的时间，最后用于计算tps、区块确认等数据
        self.blockBodyBrdCostedTime = [] # 用于记录广播消耗的时间，最后用于计算tps、区块确认等数据
        self.blockCheckCostedTime = []  # 用于记录验证消耗的时间，最后用于计算tps、区块确认等数据
        self.blockBodyCheckCostedTime = []  # 用于记录验证消耗的时间，最后用于计算tps、区块确认等数据

    def generate_random_node(self, file_id=0):
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
        if file_id == 0: # for EZ simulate
            privatePath = NODE_PRIVATE_KEY_PATH + "private_key_node_"+str(self.id)+".pem"
            publicPath = NODE_PUBLIC_KEY_PATH + "public_key_node_"+str(self.id)+".pem"
        else: # for dst simulate
            privatePath = NODE_PRIVATE_KEY_PATH + "private_key_node_" + str(file_id) + ".pem"
            publicPath = NODE_PUBLIC_KEY_PATH + "public_key_node_" + str(file_id) + ".pem"
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

    def random_set_neighbors(self, nodeNum = NODE_NUM): # nodeNum表示所有节点的数量
        def random_sampling(nodeNum):
            if nodeNum <= SAMPLE_NEIGHBORS_NUM:
                sample = range(nodeNum)
            else:
                sample = random.sample(range(nodeNum), SAMPLE_NEIGHBORS_NUM)
            return sample
        self.neighbors = random_sampling(nodeNum)

    def start_mining(self):
        pass

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
        preBlockHash = self.blockchain.get_latest_block_hash()
        index = len(self.blockchain.chain)
        if m_tree_root is None:
            m_tree_root = self.tmpBlockBodyMsg.get_mTree_root_hash()
        miner = self.id
        block = Block(index = index, m_tree_root = m_tree_root, miner = miner, pre_hash = preBlockHash)
        #设置正确的bloom
        for item in self.tmpBlockBodyMsg.info_Txns:
            block.bloom.add(item[2])

        # 对区块进行签名
        sig = self.sig_block(block)
        block.sig = sig

        self.tmpBlockMsg = BlockMsg(block)
        self.blockchain.add_block(block)

    def create_new_block_for_dst(self, m_tree_root = None): # this func is designed for dst
        preBlockHash = self.blockchain.get_latest_block_hash()
        index = len(self.blockchain.chain)
        if m_tree_root is None:
            m_tree_root = self.tmpBlockBodyMsg.get_mTree_root_hash()
        miner = self.id
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

    def is_valid_block(self, block):
        # 判断区块是否有效
        pass

    def add_block_to_chain(self, block):
        # 将有效的区块添加到区块链中
        pass

    def receive_msg(self, msg, PKList, accPKList):
        # 判断是否有重复元素：
        def has_duplicates(lst):
            return len(lst) != len(set(lst))

        # 接收其他节点发送的区块
        if type(msg) == BlockMsg:
            # 验证block的数据合规性:
            # 1. 数字签名验证； 2. Nonce验证； 3. 数据格式验证 ###注意此处不需要对bloom进行验证，直接使用bloom来进行交易打包和挖掘新块即可。
            # 此过程几乎不耗时
            check_block_start_time = time.time()
            # 1. 数字签名验证；
            uncheckedBlock = msg.info
            uncheckedSig = uncheckedBlock.sig
            # loadPKPath = NODE_PUBLIC_KEY_PATH + "public_key_node_"+str(uncheckedBlock.miner)+".pem"
            minerPK = PKList[uncheckedBlock.miner] # 获取miner的公钥
            if not self.check_block_sig(block=uncheckedBlock, signature=uncheckedSig, load_public_key=minerPK):
                raise ValueError("区块签名检测错误！")
            # todo: 2. Nonce验证； 3. 数据格式验证
            # todo: 待完成
            # 将此块添加到本地区块链中
            self.blockchain.add_block(msg.info)
            # 记录程序结束时间
            check_block_end_time = time.time()
            # 计算程序运行时间
            run_time = check_block_end_time - check_block_start_time
            self.blockCheckCostedTime.append(run_time)

        elif type(msg) == BlockBodyMsg:
            # 验证block body的数据合规性
            # 1. 数字签名验证； 2. 默克尔树验证； 3. account（是否重复）验证 4. Txn格式的正确 5. 验证bloom的合法性
            ### 可以创建一个公共的交易数据空间，在winner节点需要传输BlockBodyMsg进行验证时，则可以广播索引即可，这样最大限度地节省带宽资源。
            ### 因为节点完全可以根据索引重构出BlockBody，进而对Block中的mTree root进行重构，以及验证bloom
            # 记录程序开始时间
            checkTree_start_time = time.time()

            #check mTree
            checkTreeFlag = msg.info.checkTree()
            if not checkTreeFlag: #测试默克尔树的构造是否正确
                return False

            tmpBloom = bloom.BloomFilter()
            senderLst = []
            for item in msg.info_Txns:
                # check account是否重复
                accTxnsDigest = item[0]
                accTxnsDigestBytes = accTxnsDigest.encode('utf-8')
                accTxnsSig = item[1]
                accTxnsSender = item[2]
                senderLst.append(accTxnsSender)
                accTxnsSenderID = item[3]
                # 检测签名
                load_public_key = accPKList[accTxnsSenderID]
                public_key = load_pem_public_key(load_public_key)
                signature_algorithm = ec.ECDSA(hashes.SHA256())
                # 添加bloom
                tmpBloom.add(accTxnsSender)
                # 验证签名
                try:
                    public_key.verify(
                        accTxnsSig,
                        accTxnsDigestBytes,
                        signature_algorithm
                    )
                    continue
                except:
                    return False
            if has_duplicates(senderLst):
                return False

            # check bloom
            if self.blockchain.get_latest_block().get_bloom().bit_array != tmpBloom.bit_array:
                return False

            # 记录程序结束时间
            checkTree_end_time = time.time()
            # 计算程序运行时间
            run_time = checkTree_end_time - checkTree_start_time
            self.blockBodyCheckCostedTime.append(run_time)

        else:
            raise ValueError("接收到的Msg类型未知，固错误！")
        return run_time

    def broadcast_block(self, block):
        # 将新生成的区块广播给相邻节点
        pass
