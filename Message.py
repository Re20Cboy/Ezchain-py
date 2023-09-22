from const import *
import csv
import sys
import Transaction
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

    def get_size(self):
        return self.size

    def get_info_MTree(self):
        return self.info

    def get_info_Txns(self):
        return self.info_Txns

    def random_generate_mTree(self, numTxns): #num为读取csv文件生成txn数据的数量
        Txns = []
        # 计算商和余数
        quotient = numTxns // TNX_CSV_NUM
        remainder = numTxns % TNX_CSV_NUM

        for _ in range(quotient + 1):
            # 读取CSV文件
            with open(TNX_CSV_PATH, 'r') as file:
                reader = csv.reader(file)
                # 跳过标题行
                next(reader)
                # 遍历每一行
                for row in reader:
                    # 获取特定列的数据并添加到相应的变量中
                    # sender, recipient, nonce, signature, value, tx_hash, time
                    tmpTime = row[1]
                    tmpTxnHash = row[2]
                    tmpSender = row[3]
                    tmpRecipient = row[4]
                    tmpNonce = 0 # 待补全
                    tmpSig = unit.generate_signature(tmpSender) # 待补全
                    tmpValue = row[8]
                    tmpTxn = Transaction.Transaction(sender = tmpSender, recipient = tmpRecipient,
                                         nonce = tmpNonce, signature = tmpSig, value = tmpValue,
                                         tx_hash = tmpTxnHash, time = tmpTime)
                    Txns.append(tmpTxn.Encode())
        del Txns[-(TNX_CSV_NUM - remainder):]
        #构造默克尔树
        mTree = unit.MerkleTree(Txns)
        self.info = mTree
        self.info_Txns = Txns
        self.size = asizeof.asizeof(self.info_Txns) * 8 # 以bit为单位，仅计算Txns的容量因为只有交易是需要被广播传输和验证的，mTree完全可以根据Txns被重构。

        print('Our Txn size = ' + str(asizeof.asizeof(Txns[0])) + ' bytes') #查看一笔交易多少字节

    def get_mTree_root_hash(self):
        return self.info.getRootHash()

    def print_mTree(self):
        self.info.printTree(self.info.getRootHash())



