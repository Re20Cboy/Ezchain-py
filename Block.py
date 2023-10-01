from const import *
import Bloom
import datetime
import unit

class Block:
    def __init__(self, index, mTreeRoot, miner, prehash, nonce = 0, bloomsize = 1024*1024, bloomhashcount = 5,  time = datetime.datetime.now()):
        self.index = index
        self.nonce = nonce
        self.bloom = Bloom.BloomFilter(bloomsize, bloomhashcount)
        self.mTreeRoot = mTreeRoot
        self.time = time #创建此区块时的时间戳
        self.miner = miner
        self.preHash = prehash
        self.sig = unit.generate_signature(miner) #数字签名待实现

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
        return hash(self)
    def add_item_2_bloom(self, item):
        self.bloom.add(item)
    def is_in_bloom(self, item):
        if item in self.bloom:
            return True
        else:
            return False
