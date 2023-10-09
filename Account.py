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
        self.ValuePrfBlockPair = [] # 当前账户拥有的值和对应的证据、区块号，以及所在list的编号对
        # self.prfChain = [] # 此账户所有证明的集合，即，公链上所有和本账户相关的prf集合
        self.bloomPrf = [] # 被bloom过滤器“误伤”时，提供证据（哪些账户可以生成此bloom）表明自己的“清白”。
        self.accTxns = [] # 本账户本轮提交的交易集合
        self.accTxnsIndex = None # 本账户本轮提交的交易集合在blockbody中的编号位置，用于提取交易证明
        self.balance = 0 # 统计账户Value计算余额
        self.costedValues = [] # 用于记录本轮已花销的Values


    def add_VPBpair(self, item):
        self.ValuePrfBlockPair.append(item)
        # 更新余额
        self.balance += item[0].valueNum
    def delete_VPBpair(self, index):
        # 更新余额
        self.balance -= self.ValuePrfBlockPair[index][0].valueNum
        del self.ValuePrfBlockPair[index]
        # 更新索引
        # for item in self.ValuePrfBlockPair:
            # item[0][1] = self.ValuePrfBlockPair.index(item)

    def find_VPBpair_via_V(self, V): # 注意V是Value list
        index = []
        for value in V:
            for i, VPBpair in enumerate(self.ValuePrfBlockPair, start=0):
                if value is VPBpair[0]:
                    index.append(i)
        if index is not []:
            return index
        else:
            raise ValueError("未找到对应的Value")

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
            if V < 1:
                raise ValueError("参数V不能小于1")
            tmpCost = 0 # 动态记录要消耗多少值
            costList = [] # 记录消耗的Value的index
            changeValueIndex = 0 # 记录找零值的索引
            txn_2_sender = None
            txn_2_recipient = None

            for i, VPBpair in enumerate(self.ValuePrfBlockPair, start=0):
                value = VPBpair[0]
                if value in self.costedValues:
                    continue
                tmpCost += value.valueNum
                if tmpCost >= V: # 满足值的需求了，花费到此value为止
                    changeValueIndex = i
                    costList.append(i)
                    break
                changeValueIndex = i
                costList.append(i)

            change = tmpCost-V # 计算找零

            if change > 0:  # 需要找零，对值进行分割
                V1, V2 = self.ValuePrfBlockPair[changeValueIndex][0].split_value(change) # V2是找零
                tmpP = self.ValuePrfBlockPair[changeValueIndex][1]
                tmpB = self.ValuePrfBlockPair[changeValueIndex][2]
                # self.delete_VPBpair(changeValueIndex)
                # todo:V1在本轮的后续交易中都不可再使用
                # self.add_VPBpair([V1, tmpP, tmpB])
                # self.add_VPBpair([V2, tmpP, tmpB])
                #创建找零的交易
                txn_2_sender = Transaction.Transaction(sender=tmpSender, recipient=tmpSender,
                                                 nonce=tmpNonce, signature=tmpSig, value=[V2],
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                txn_2_recipient = Transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                 nonce=tmpNonce, signature=tmpSig, value=[V1],
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                self.costedValues.append(V1)
                self.costedValues.append(V2)
            return costList, changeValueIndex, txn_2_sender, txn_2_recipient

        accTxns = []
        tmpBalance = self.balance
        for item in randomRecipients:
            tmpTime = str(datetime.datetime.now())
            tmpTxnHash = '0x19f1df2c7ee6b464720ad28e903aeda1a5ad8780afc22f0b960827bd4fcf656d' # todo: 交易哈希暂用定值，待实现
            tmpSender = self.addr
            tmpRecipient = item.addr
            tmpNonce = 0  # 待补全
            tmpSig = unit.generate_signature(tmpSender)  # todo: 交易的签名待补全
            tmpV = 0
            if tmpBalance > 0: # 余额大于0时才能交易！
                tmpV = random.randint(1, 1000)  # 原来为row[8]，根据值转移思想，现改为随机生成一个1-1000的整数
                while tmpV > tmpBalance:
                    tmpV = random.randint(1, tmpBalance)
            costList, changeValueIndex, changeTxn2Sender, changeTxn2Recipient = pick_values_and_generate_txns(tmpV, tmpSender, tmpRecipient, tmpNonce, tmpSig, tmpTxnHash, tmpTime) # 花费的值和找零
            if changeTxn2Sender is None and changeTxn2Recipient is None: # 不需要找零
                tmpValues = []
                for i in costList:
                    tmpValues.append(self.ValuePrfBlockPair[i][0])
                    self.costedValues.append(self.ValuePrfBlockPair[i][0])
                    # 删除此值
                    # self.delete_VPBpair(i)
                tmpTxn = Transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                 nonce=tmpNonce, signature=tmpSig, value=tmpValues,
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                accTxns.append(tmpTxn)
            else: # 需要找零
                tmpValues = []
                for i in costList:
                    if i is not changeValueIndex:
                        tmpValues.append(self.ValuePrfBlockPair[i][0])
                        self.costedValues.append(self.ValuePrfBlockPair[i][0])
                    # 删除此值
                    # self.delete_VPBpair(i)
                if tmpValues is not []:
                    tmpTxn = Transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                     nonce=tmpNonce, signature=tmpSig, value=tmpValues,
                                                     tx_hash=tmpTxnHash, time=tmpTime)
                    accTxns.append(tmpTxn)

                tmpP = self.ValuePrfBlockPair[changeValueIndex][1]
                tmpB = self.ValuePrfBlockPair[changeValueIndex][2]
                self.delete_VPBpair(changeValueIndex)
                self.add_VPBpair([changeTxn2Recipient.Value[0], tmpP, tmpB]) # V1在本轮的后续交易中都不可再使用
                self.add_VPBpair([changeTxn2Sender.Value[0], tmpP, tmpB])

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
