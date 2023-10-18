import random
import string
# 使用ECC椭圆密码
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import datetime
import unit
import Transaction
import copy
from const import *
import hashlib

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
        self.recipientList = []

    def clear_info(self):
        self.accTxns = []
        self.accTxnsIndex = None
        self.costedValues = []
        self.recipientList = []

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
    def get_VPB_index_via_VPB(self, VPBpair):
        for index, item in enumerate(self.ValuePrfBlockPair,start=0):
            if item == VPBpair:
                return index
        raise ValueError("未在本账户中找到此VPB！")

    def update_balance(self):
        balance = 0
        for VBPpair in self.ValuePrfBlockPair:
            balance += VBPpair[0].valueNum
        self.balance = balance

    def find_VPBpair_via_V(self, V): # 注意V是Value list
        index = []
        for value in V:
            for i, VPBpair in enumerate(self.ValuePrfBlockPair, start=0):
                if value == VPBpair[0]:
                    index.append(i)
                    break
        if index != []:
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
            changeValueIndex = -1 # 记录找零值的索引
            txn_2_sender = None
            txn_2_recipient = None
            value_Enough = False
            for i, VPBpair in enumerate(self.ValuePrfBlockPair, start=0):
                value = VPBpair[0]
                if value in self.costedValues:
                    continue
                tmpCost += value.valueNum
                if tmpCost >= V: # 满足值的需求了，花费到此value为止
                    changeValueIndex = i
                    costList.append(i)
                    value_Enough = True
                    break
                changeValueIndex = i
                costList.append(i)

            # 判断余额是否足够
            if not value_Enough:
                raise ValueError("余额不足！")

            change = tmpCost-V # 计算找零

            if change > 0:  # 需要找零，对值进行分割
                V1, V2 = self.ValuePrfBlockPair[changeValueIndex][0].split_value(change) # V2是找零
                #创建找零的交易
                txn_2_sender = Transaction.Transaction(sender=tmpSender, recipient=tmpSender,
                                                 nonce=tmpNonce, signature=tmpSig, value=[V2],
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                txn_2_recipient = Transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                 nonce=tmpNonce, signature=tmpSig, value=[V1],
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                self.costedValues.append(V1)
                # self.costedValues.append(V2) # V2不用加入已被花费的list！！！
            else:
                changeValueIndex = -1
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
            tmpV = random.randint(1, 1000)
            if tmpBalance <= tmpV: # 余额大于0时才能交易！
                raise ValueError("余额不足！！！")
            else:
                tmpBalance -= tmpV
            costList, changeValueIndex, changeTxn2Sender, changeTxn2Recipient = pick_values_and_generate_txns(tmpV, tmpSender, tmpRecipient, tmpNonce, tmpSig, tmpTxnHash, tmpTime) # 花费的值和找零
            if changeValueIndex < 0: # 不需要找零
                tmpValues = []
                for index in costList:
                    tmpValues.append(self.ValuePrfBlockPair[index][0])
                    self.costedValues.append(self.ValuePrfBlockPair[index][0])
                    # 删除此值
                    # self.delete_VPBpair(i)
                tmpTxn = Transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                 nonce=tmpNonce, signature=tmpSig, value=tmpValues,
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                accTxns.append(tmpTxn)
            else: # 需要找零
                tmpValues = []
                for i in costList:
                    if i != changeValueIndex:
                        tmpValues.append(self.ValuePrfBlockPair[i][0])
                        self.costedValues.append(self.ValuePrfBlockPair[i][0])
                    # 删除此值
                    # self.delete_VPBpair(i)
                if tmpValues != []:
                    tmpTxn = Transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                     nonce=tmpNonce, signature=tmpSig, value=tmpValues,
                                                     tx_hash=tmpTxnHash, time=tmpTime)
                    accTxns.append(tmpTxn)

                tmpP = self.ValuePrfBlockPair[changeValueIndex][1]
                tmpB = self.ValuePrfBlockPair[changeValueIndex][2]
                self.delete_VPBpair(changeValueIndex)
                self.add_VPBpair([changeTxn2Recipient.Value[0], copy.deepcopy(tmpP), copy.deepcopy(tmpB)]) # V1在本轮的后续交易中都不可再使用
                self.add_VPBpair([changeTxn2Sender.Value[0], copy.deepcopy(tmpP), copy.deepcopy(tmpB)])

                accTxns.append(changeTxn2Sender)
                accTxns.append(changeTxn2Recipient)

        self.accTxns = accTxns
        return accTxns

    def receipt_txn_and_prf(self):
        pass

    def updateBloomPrf(self, bloom, txnAccList, blockIndex):
        if self.costedValues == [] and self.addr in bloom:
            # 被bloom误判，执行添加布隆证明操作
            self.bloomPrf.append([copy.deepcopy(txnAccList), copy.deepcopy(blockIndex)]) # 布隆证明 = [此布隆过滤器中所有账户的地址，此布隆隶属的区块号]

    def check_VPBpair(self, VPBpair, bloomPrf, blockchain):
        def hash(val):
            # return hashlib.sha256(val.encode("utf-8")).hexdigest()
            if type(val) == str:
                return hashlib.sha256(val.encode("utf-8")).hexdigest()
            else:
                return hashlib.sha256(val).hexdigest()

        # 1 检测数据类型：
        if type(VPBpair[0]) != unit.Value or type(VPBpair[1]) != unit.Proof or type(VPBpair[2]) != list:
            print("VPB检测报错：数据结构错误")
            return False # 数据结构错误

        value = VPBpair[0]
        valuePrf = VPBpair[1].prfList
        blockIndex = VPBpair[2]

        if len(valuePrf) != len(blockIndex):
            print("VPB检测报错：证据和块索引非一一映射")
            return False # 证据和块索引非一一映射，固错误

        # 2 检测value的结构合法性：
        if not value.checkValue:
            print("VPB检测报错：value的结构合法性检测不通过")
            return False # value的结构合法性检测不通过

        recordOwner = None # 此变量用于记录值流转的持有者

        epochRealBList = [] # 记录epoch内的真实的B的信息，用于和VPB中的B进行对比
        BList = [] # 记录epoch内的VPB的B的信息，结构为：[(owner,[list of block index]), (...), (...), ...]用于进行对比验证
        oneEpochBList = [] # 结构为：[list of block index]

        # 3 检验proof的正确性
        for index, prfUnit in enumerate(valuePrf, start=0):
            # 由于第一个prfUnit是创世块中的交易因此需要特殊的验证处理
            if index == 0: # 说明是创世块
                recordOwner = prfUnit.owner
                ownerAccTxnsList = prfUnit.ownerAccTxnsList
                ownerMTreePrfList = prfUnit.ownerMTreePrfList
                # 创世块的检测
                if ownerMTreePrfList == [blockchain.chain[0].get_mTreeRoot()]:  # 说明这是创世块
                    tmpGenesisAccTxns = Transaction.AccountTxns(GENESIS_SENDER, ownerAccTxnsList)
                    tmpEncode = tmpGenesisAccTxns.Encode()
                    if hash(tmpEncode) != blockchain.chain[0].get_mTreeRoot():
                        print("VPB检测报错：交易集合哈希错误，节点伪造了创世块中的交易")
                        return False  # 树根值错误，说明节点伪造了创世块中的交易。
                    # 检测此value是否在创世块中且持有者是创世块中的接收者：
                    for genesisTxn in ownerAccTxnsList:
                        if genesisTxn.Recipient == recordOwner:
                            if not genesisTxn.Value.isInValue(value):
                                print("VPB检测报错：此值溯源到创世块中发现为非法值")
                                return False
                else:
                    print("VPB检测报错：proof中创世块树根检测错误")
                    return False
                oneEpochBList.append(blockIndex[index])

            else: # 非创世块检测
                isNewEpoch = False
                oneEpochBList.append(blockIndex[index])

                if recordOwner != prfUnit.owner: # 说明 owner 已改变，该值进入下一个owner持有的epoch
                    isNewEpoch = True
                    lastBlockIndex = oneEpochBList.pop() # 获得最后一个交易的区块号
                    # 更新epoch内的VPB的B的信息
                    BList.append((copy.deepcopy(recordOwner), copy.deepcopy(oneEpochBList)))
                    oneEpochBList = [lastBlockIndex] # 为下一段证明保留最初的交易所在的区块号
                    recordOwner = prfUnit.owner  # 更新持有者信息

                ownerAccTxnsList = prfUnit.ownerAccTxnsList
                ownerMTreePrfList = prfUnit.ownerMTreePrfList

                # 检测：ownerAccTxnsList和ownerMTreePrfList的信息是相符的
                # 注意，这里的Encode()函数只对accTxns进行编码，因此可以设sender='sender'，结果不影响。
                uncheckedAccTxns = Transaction.AccountTxns(sender='sender', accTxns=ownerAccTxnsList)
                uncheckedMTreePrf = unit.MTreeProof(MTPrfList=ownerMTreePrfList)

                # 检测：ownerMTreePrfList和主链此块中的root是相符的
                if not uncheckedMTreePrf.checkPrf(accTxns=uncheckedAccTxns, trueRoot=blockchain.chain[blockIndex[index]].get_mTreeRoot()):
                    print("VPB检测报错：默克尔树检测未通过")
                    return False # 默克尔树检测未通过，固错误！

                # 记录epoch内的VPB的B的信息
                oneEpochBList.append((blockIndex[index]))

                if isNewEpoch:
                    # 所有txn中应当有且仅有一个交易将值转移到新的owner手中
                    SpendValueTxnList = [] # 记录在此accTxns中此值被转移的所有交易，合法的情况下，此list的长度应为1
                    for txn in ownerAccTxnsList:
                        if txn.check_value_is_in_txn(value):
                            if txn.Sender != txn.Recipient: # 若不是转移给自己则计入值的花销列表
                                SpendValueTxnList.append(txn)
                    if len(SpendValueTxnList) != 1:
                        print("VPB检测报错：存在双花！或者未转移值给owner！")
                        return False # 存在双花！或者未转移值给owner！
                    if SpendValueTxnList[0].Recipient != recordOwner:
                        print("VPB检测报错：此值未转移给指定的owner")
                        return False # 此值未转移给指定的owner
                else:
                    # 此值尚未转移给新的owner
                    for txn in ownerAccTxnsList:
                        if txn.check_value_is_in_txn(value):
                            print("VPB检测报错：此值不应当在此处被提前花费")
                            return False # 此值不应当在此处被花费！

        # 检测：每个epoch内的B和主链上的布隆过滤器的信息是相符的，即，epoch的owner没有在B上撒谎
        for epochRecord in BList:
            (owner, uncheckedBList) = epochRecord
            if len(uncheckedBList) < 1:
                print("VPB检测报错：本段owner持有值没有记录")
                return False # 本段owner持有值没有记录，固错误！
            ownerBegin = uncheckedBList[0] # owner刚拥有该值时的block index
            ownerEnd = uncheckedBList[-1] # owner将在下一个区块将此值转移给其他owner，即，最后一个持有此值的block index
            if ownerEnd < ownerBegin:
                print("VPB检测报错：owner持有值的区块号记录有误")
                return False # owner持有值的区块号记录有误！
            # 在blockchain中根据ownerBegin和ownerEnd进行搜索符合bloom过滤器的的区块index
            for i in range(ownerBegin, ownerEnd+1):
                if i != 0: # i=0为创世块，创世块已经过验证，固跳过
                    if owner in blockchain.chain[i].bloom:
                        epochRealBList.append(i)
                else: # i=0为创世块，创世块已经过验证，固直接加入
                    epochRealBList.append(i)
            # 对比epochRealBList和uncheckedBList
            if epochRealBList != uncheckedBList:
                # 若不同则需要检测bloom proof，排除被bloom过滤器“误伤”的可能
                if bloomPrf == []:
                    print("VPB检测报错：没有提供bloom proof")
                    return False # 没有提供bloom proof，因此没有误伤，则说明owner提供的值持有记录和真实记录不同，错误！
                else:
                    # todo: 检测bloom proof
                    pass

        return True


    def generate_txn_prf_when_use(self, begin_index, end_index): # begin_index, end_index分别表示此txn在本账户手中开始的区块号和结束的区块号
        # todo: 根据交易、区块等input，生成目标交易的proof。
        # proof = 原证明 + 新生成的证明（在此account时期内的证明）
        # proof单元的数据结构：（区块号，mTree证明）
        # 生成new proof（在此account时期内的证明）
        new_proof = []
        pass
