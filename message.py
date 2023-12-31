from const import *
import csv
import sys
import transaction
from pympler import asizeof
import unit

class BlockMsg:
    def __init__(self, block):
        self.info = block
        self.size = asizeof.asizeof(block) * 8 # *8转换为以bit为单位

    def get_size(self):
        return self.size
    def get_info(self):
        return self.info

class BlockBodyMsg: #即，交易的原始信息(以默克尔树的形式)
    def __init__(self, mTree = None, Txns = None):
        self.info = mTree
        self.info_Txns = Txns #此处的Txns实际上是多余的，此处主要为了便利验证test
        self.size = 0

    def get_acc_sigs(self):
        acc_sigs = []
        for acc_package in self.info_Txns:
            acc_sigs.append(acc_package[1])
        return acc_sigs

    def get_acc_addrs(self):
        acc_addrs = []
        for acc_package in self.info_Txns:
            acc_addrs.append(acc_package[2])
        return acc_addrs

    def get_acc_digests(self):
        acc_digests = []
        for acc_package in self.info_Txns:
            acc_digests.append(acc_package[0])
        return acc_digests

    def get_size(self):
        return self.size

    def get_info_MTree(self):
        return self.info

    def get_info_Txns(self):
        return self.info_Txns

    def random_generate_mTree(self, DigestAccTxns, packages_for_new_block):
        #构造默克尔树
        mTree = unit.MerkleTree(DigestAccTxns)
        self.info = mTree
        self.info_Txns = packages_for_new_block
        self.size = asizeof.asizeof(self.info_Txns) * 8 # 以bit为单位，仅计算Txns的容量因为只有交易是需要被广播传输和验证的，mTree完全可以根据Txns被重构。
        # print('Our Txn size = ' + str(asizeof.asizeof(txnsPool[0])) + ' bytes') #查看一笔交易多少字节

    def get_mTree_root_hash(self):
        return self.info.getRootHash()

    def print_mTree(self):
        self.info.printTree(self.info.getRootHash())
