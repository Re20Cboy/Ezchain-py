from const import *
import bloom
import datetime
import unit
import hashlib

class Block:
    def __init__(self, index, mTreeRoot, miner, prehash, nonce = 0, bloomsize = 1024*1024, bloomhashcount = 5, time = datetime.datetime.now()):
        self.index = index
        self.nonce = nonce
        self.bloom = bloom.BloomFilter(bloomsize, bloomhashcount)
        self.mTreeRoot = mTreeRoot
        self.time = datetime.datetime.now() #创建此区块时的时间戳
        self.miner = miner # 这里的miner是miner的id
        self.preHash = prehash
        self.sig = unit.generate_signature(miner) #数字签名待实现

    def block2str(self): # 将区块转译为字符串方便进行hash摘要、签名等操作，固此字符串转译中不能有签名加入。
        block_str = f"Index: {self.index}\n"
        block_str += f"Nonce: {self.nonce}\n"
        block_str += f"Bloom: {str(self.bloom)}\n"
        block_str += f"Merkle Tree Root: {self.mTreeRoot}\n"
        block_str += f"Time: {str(self.time)}\n"
        block_str += f"Miner: {self.miner}\n"
        block_str += f"Previous Hash: {self.preHash}\n"
        return block_str

    def get_index(self):
        return self.index
    def get_nonce(self):
        return self.nonce
    def get_bloom(self):
        return self.bloom
    def get_mTreeRoot(self):
        return self.mTreeRoot
    def get_time(self):
        return self.time
    def get_miner(self):
        return self.miner
    def get_preHash(self):
        return self.preHash
    def get_sig(self):
        return self.sig
    def get_hash(self):
        return hashlib.sha256(self.block2str().encode("utf-8"))
    def add_item_2_bloom(self, item):
        self.bloom.add(item)
    def is_in_bloom(self, item):
        if item in self.bloom:
            return True
        else:
            return False

