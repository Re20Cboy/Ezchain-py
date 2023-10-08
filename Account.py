import random
import string
# 使用ECC椭圆密码
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import datetime
import unit
import Transaction

class Account:
    def __init__(self):
        self.addr = None
        self.privateKey = None
        self.publicKey = None
        self.ValuePrfBlockPair = [] # 当前账户拥有的值和对应的证据对
        # self.prfChain = [] # 此账户所有证明的集合，即，公链上所有和本账户相关的prf集合
        self.bloomPrf = [] # 被bloom过滤器“误伤”时，提供证据（哪些账户可以生成此bloom）表明自己的“清白”。
        self.accTxns = [] # 本账户本轮提交的交易集合
        self.accTxnsIndex = None # 本账户本轮提交的交易集合在blockbody中的编号位置，用于提取交易证明
        self.balance = 0 # 统计账户Value计算余额


    def add_VPBpair(self, item):
        self.ValuePrfBlockPair.append(item)
        # 更新余额
        self.balance += item[0].valueNum
    def delete_VPBpair(self,index):
        # 更新余额
        self.balance -= self.ValuePrfBlockPair[index][0].valueNum
        del self.ValuePrfBlockPair[index]


    def generate_random_account(self):
        # 生成随机地址
        self.addr = ''.join(random.choices(string.ascii_letters + string.digits, k=42)) #bitcoin地址字符数为42
        # 生成随机公钥和私钥
        private_key = ec.generate_private_key(ec.SECP256K1())
        self.privateKey = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        self.publicKey = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def random_generate_txns(self, randomRecipients):
        def pick_values_and_generate_txns(V, tmpSender, tmpRecipient, tmpNonce, tmpSig, tmpTxnHash, tmpTime): # V为int，是要挑拣的值的总量
            tmpCost = 0 # 动态记录要消耗多少值
            count = -1
            txn_2_sender = None
            txn_2_recipient = None

            for VPBpair in self.ValuePrfBlockPair:
                value = VPBpair[0]
                tmpCost += value.valueNum
                if tmpCost >= V: # 满足值的需求了，花费到此value为止
                    break
                count += 1

            change = tmpCost-V # 计算找零

            if change > 0:  # 需要找零，对值进行分割
                V1, V2 = self.ValuePrfBlockPair[costIndex][0].split_value(change)
                tmpP = self.ValuePrfBlockPair[costIndex][1]
                tmpB = self.ValuePrfBlockPair[costIndex][2]
                self.delete_VPBpair(costIndex)
                self.add_VPBpair((V1, tmpP, tmpB))
                self.add_VPBpair((V2, tmpP, tmpB))
                #创建找零的交易
                txn_2_sender = Transaction.Transaction(sender=tmpSender, recipient=tmpSender,
                                                 nonce=tmpNonce, signature=tmpSig, value=V2,
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                txn_2_recipient = Transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                 nonce=tmpNonce, signature=tmpSig, value=V1,
                                                 tx_hash=tmpTxnHash, time=tmpTime)
            return count, txn_2_sender, txn_2_recipient

        accTxns = []
        for item in randomRecipients:
            tmpTime = str(datetime.datetime.now())
            tmpTxnHash = '0x19f1df2c7ee6b464720ad28e903aeda1a5ad8780afc22f0b960827bd4fcf656d' # todo: 交易哈希暂用定值，待实现
            tmpSender = self.addr
            tmpRecipient = item.addr
            tmpNonce = 0  # 待补全
            tmpSig = unit.generate_signature(tmpSender)  # todo: 交易的签名待补全
            tmpV = 0
            if self.balance > 0: # 余额大于0时才能交易！
                tmpV = random.randint(1, 1000)  # 原来为row[8]，根据值转移思想，现改为随机生成一个1-1000的整数
                while tmpV > self.balance:
                    tmpV = random.randint(1, self.balance)
            costIndex, changeTxn2Sender, changeTxn2Recipient = pick_values_and_generate_txns(tmpV, tmpSender, tmpRecipient, tmpNonce, tmpSig, tmpTxnHash, tmpTime) # 花费的值和找零
            if costIndex >= 0: # 表示有不需要拆分就被cost掉的value
                tmpValues = []
                for i in range(costIndex):
                    tmpValues.append(self.ValuePrfBlockPair[i][0])
                tmpTxn = Transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                 nonce=tmpNonce, signature=tmpSig, value=tmpValues,
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                accTxns.append(tmpTxn)
            # 所有cost的值都是要拆分的
            accTxns.append(changeTxn2Sender)
            accTxns.append(changeTxn2Recipient)

        self.accTxns = accTxns
        return accTxns

    def receipt_txn_and_prf(self):
        # todo:接收函数的后续处理
        pass
    def generate_txn_prf_when_use(self, begin_index, end_index): # begin_index, end_index分别表示此txn在本账户手中开始的区块号和结束的区块号
        # todo: 根据交易、区块等input，生成目标交易的proof。
        # proof = 原证明 + 新生成的证明（在此account时期内的证明）
        # proof单元的数据结构：（区块号，mTree证明）
        # 生成new proof（在此account时期内的证明）
        new_proof = []

        pass
