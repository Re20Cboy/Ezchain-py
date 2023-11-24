import random
import datetime
import unit
import Transaction
import copy
from const import *
import hashlib
# 签名所需引用
import string
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from pympler import asizeof
import time

class Account:
    def __init__(self, ID):
        self.addr = None
        self.id = ID
        self.privateKeyPath = None # 存储私钥的地址
        self.publicKeyPath = None # 存储公钥的地址
        self.privateKey = None  # 私钥
        self.publicKey = None  # 公钥
        self.ValuePrfBlockPair = [] # 当前账户拥有的值和对应的证据、区块号，以及所在list的编号对
        # self.prfChain = [] # 此账户所有证明的集合，即，公链上所有和本账户相关的prf集合
        self.bloomPrf = [] # 被bloom过滤器“误伤”时，提供证据（哪些账户可以生成此bloom）表明自己的“清白”。
        self.accTxns = [] # 本账户本轮提交的交易集合
        self.accTxnsIndex = None # 本账户本轮提交的交易集合在blockbody中的编号位置，用于提取交易证明
        self.balance = 0 # 统计账户Value计算余额
        self.costedValuesAndRecipes = [] # 用于记录本轮已花销的Values，type为[(value, 新的owner即交易的接收者), (..., ...), ...]
        self.recipientList = []
        self.verifyTimeCostList = [] # 用于记录验证一笔交易的各项消耗值（证明容量大小）
        self.verifyStorageCostList = [] # 用于记录验证一笔交易的各项消耗值（验证时间），单位为bit
        self.acc2nodeDelay = [] # 记录acc讲accTxn传递到交易池的延迟
        self.VPBCheckPoints = unit.checkedVPBList() # 记录已验证过的VPB的记录以减少account传输、存储、验证的成本
        self.accRoundVPBCostList = [] # 记录本节点每轮VPB的存储消耗
        self.accRoundCKCostList = [] # 记录本节点每轮CK的存储消耗
        self.accRoundAllCostList = [] # 记录本节点每轮VPB+CK(总的)存储消耗

    def test(self):
        test = copy.deepcopy(self.ValuePrfBlockPair)
        for i, vpb in enumerate(self.ValuePrfBlockPair):
            v = vpb[0]
            p = vpb[1].prfList
            b = vpb[2]
            for j, item in enumerate(test):
                if i == j:
                    continue
                v2 = item[0]
                p2 = item[1].prfList
                b2 = item[2]
                flag = v.isIntersectValue(v2)
                if flag:
                    print("VPB中有重复记录！")

    def clear_and_fresh_info(self):
        self.accTxns = []
        self.accTxnsIndex = None
        self.costedValuesAndRecipes = []
        self.recipientList = []
        # 检测每轮的vpb中的v是否有重复
        # self.test()
        # 根据本轮的VPBpairs对check points进行更新
        self.VPBCheckPoints.addAndFreshCheckPoint(self.ValuePrfBlockPair)
        # 更新acc的存储成本信息
        self.freshStorageCost()

    def freshStorageCost(self):
        accRoundVPBCost = asizeof.asizeof(self.ValuePrfBlockPair) / 1048576
        accRoundCKCost = asizeof.asizeof(self.VPBCheckPoints) / 1048576
        self.accRoundVPBCostList.append(accRoundVPBCost) # 转化为MB
        self.accRoundCKCostList.append(accRoundCKCost) # 转化为MB
        self.accRoundAllCostList.append(accRoundVPBCost + accRoundCKCost) # 转化为MB

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
                if VPBpair[0].isSameValue(value):
                    index.append(i)
                    break
        if index != []:
            return index
        else:
            raise ValueError("未找到对应的Value")

    def generate_random_account(self):
        # 生成随机地址
        self.addr = ''.join(random.choices(string.ascii_letters + string.digits, k=42)) #bitcoin地址字符数为42
        # 生成私钥
        private_key = ec.generate_private_key(ec.SECP384R1())
        # 从私钥中获取公钥
        public_key = private_key.public_key()
        # 保存公私钥的地址：
        privatePath = ACCOUNT_PRIVATE_KEY_PATH + "private_key_node_"+str(self.id)+".pem"
        publicPath = ACCOUNT_PUBLIC_KEY_PATH + "public_key_node_"+str(self.id)+".pem"
        self.privateKeyPath = privatePath
        self.publicKeyPath = publicPath
        self.privateKey = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        self.publicKey = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        # 保存私钥到文件（请谨慎操作，不要轻易泄露私钥）
        with open(privatePath, "wb") as f:
            f.write(self.privateKey)
        # 保存公钥到文件（公钥可以公开分发给需要验证方）
        with open(publicPath, "wb") as f:
            f.write(self.publicKey)

    def random_generate_txns(self, randomRecipients):
        def pick_values_and_generate_txns(V, tmpSender, tmpRecipient, tmpNonce, tmpTxnHash, tmpTime): # V为int，是要挑拣的值的总量
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
                if value in [i[0] for i in self.costedValuesAndRecipes]:
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
                                                 nonce=tmpNonce, signature=None, value=[V2],
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                txn_2_sender.sig_txn(self.privateKey)
                txn_2_recipient = Transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                 nonce=tmpNonce, signature=None, value=[V1],
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                txn_2_recipient.sig_txn(self.privateKey)
                self.costedValuesAndRecipes.append((V1, tmpRecipient))
            else:
                changeValueIndex = -1
            return costList, changeValueIndex, txn_2_sender, txn_2_recipient

        # todo:重新写找零逻辑，最大化利用零钱
        accTxns = []
        tmpBalance = self.balance

        for item in randomRecipients:
            tmpTime = str(datetime.datetime.now())
            tmpTxnHash = '0x19f1df2c7ee6b464720ad28e903aeda1a5ad8780afc22f0b960827bd4fcf656d' # todo: 交易哈希暂用定值，待实现
            tmpSender = self.addr
            tmpRecipient = item.addr
            tmpNonce = 0  # 待补全
            # tmpSig = unit.generate_signature(tmpSender)
            tmpV = random.randint(1, 1000)
            if tmpBalance <= tmpV: # 余额大于0时才能交易！
                raise ValueError("余额不足！！！")
            else:
                tmpBalance -= tmpV

            # costList是花费的值的索引列表（包括需要找零的值），changeValueIndex是唯一找零值的索引（已包含在costList中）
            costList, changeValueIndex, changeTxn2Sender, changeTxn2Recipient = pick_values_and_generate_txns(tmpV, tmpSender, tmpRecipient, tmpNonce, tmpTxnHash, tmpTime) # 花费的值和找零
            if changeValueIndex < 0: # 不需要找零
                tmpValues = []
                for index in costList:
                    tmpValues.append(self.ValuePrfBlockPair[index][0])
                    self.costedValuesAndRecipes.append((self.ValuePrfBlockPair[index][0], tmpRecipient))
                    # 删除此值
                    # self.delete_VPBpair(i)
                tmpTxn = Transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                 nonce=tmpNonce, signature=None, value=tmpValues,
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                tmpTxn.sig_txn(load_private_key=self.privateKey)
                accTxns.append(tmpTxn)
            else: # 需要找零
                tmpValues = []
                for i in costList:
                    if i != changeValueIndex: # 表示i被花费又不是唯一找零值
                        tmpValues.append(self.ValuePrfBlockPair[i][0])
                        self.costedValuesAndRecipes.append((self.ValuePrfBlockPair[i][0], tmpRecipient))

                if tmpValues != []: # 非找零值且被花费的
                    tmpTxn = Transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                     nonce=tmpNonce, signature=None, value=tmpValues,
                                                     tx_hash=tmpTxnHash, time=tmpTime)
                    tmpTxn.sig_txn(load_private_key=self.privateKey)
                    accTxns.append(tmpTxn)

                tmpP = self.ValuePrfBlockPair[changeValueIndex][1]
                tmpB = self.ValuePrfBlockPair[changeValueIndex][2]
                self.delete_VPBpair(changeValueIndex)
                self.add_VPBpair([changeTxn2Recipient.Value[0], copy.deepcopy(tmpP), copy.deepcopy(tmpB)]) # V1在本轮的后续交易中都不可再使用
                self.add_VPBpair([changeTxn2Sender.Value[0], copy.deepcopy(tmpP), copy.deepcopy(tmpB)])

                accTxns.append(changeTxn2Sender)
                accTxns.append(changeTxn2Recipient)

        self.accTxns = accTxns
        self.acc2nodeDelay.append(asizeof.asizeof(accTxns) * 8 / BANDWIDTH + NODE_ACCOUNT_DELAY)
        return accTxns

    def optimized_generate_txns(self, randomRecipients):
        def pick_values_and_generate_txns(V, tmpSender, tmpRecipient, tmpNonce, tmpTxnHash, tmpTime): # V为int，是要挑拣的值的总量
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
                if value in [i[0] for i in self.costedValuesAndRecipes]:
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
                                                 nonce=tmpNonce, signature=None, value=[V2],
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                txn_2_sender.sig_txn(self.privateKey)
                txn_2_recipient = Transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                 nonce=tmpNonce, signature=None, value=[V1],
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                txn_2_recipient.sig_txn(self.privateKey)
                self.costedValuesAndRecipes.append((V1, tmpRecipient))
            else:
                changeValueIndex = -1
            return costList, changeValueIndex, txn_2_sender, txn_2_recipient

        # todo:重新写找零逻辑，最大化利用零钱
        accTxns = []
        tmpBalance = self.balance

        for item in randomRecipients:
            tmpTime = str(datetime.datetime.now())
            tmpTxnHash = '0x19f1df2c7ee6b464720ad28e903aeda1a5ad8780afc22f0b960827bd4fcf656d' # todo: 交易哈希暂用定值，待实现
            tmpSender = self.addr
            tmpRecipient = item.addr
            tmpNonce = 0  # 待补全
            # tmpSig = unit.generate_signature(tmpSender)
            tmpV = random.randint(1, 1000)
            if tmpBalance <= tmpV: # 余额大于0时才能交易！
                raise ValueError("余额不足！！！")
            else:
                tmpBalance -= tmpV

            # costList是花费的值的索引列表（包括需要找零的值），changeValueIndex是唯一找零值的索引（已包含在costList中）
            costList, changeValueIndex, changeTxn2Sender, changeTxn2Recipient = pick_values_and_generate_txns(tmpV, tmpSender, tmpRecipient, tmpNonce, tmpTxnHash, tmpTime) # 花费的值和找零
            if changeValueIndex < 0: # 不需要找零
                tmpValues = []
                for index in costList:
                    tmpValues.append(self.ValuePrfBlockPair[index][0])
                    self.costedValuesAndRecipes.append((self.ValuePrfBlockPair[index][0], tmpRecipient))
                    # 删除此值
                    # self.delete_VPBpair(i)
                tmpTxn = Transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                 nonce=tmpNonce, signature=None, value=tmpValues,
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                tmpTxn.sig_txn(load_private_key=self.privateKey)
                accTxns.append(tmpTxn)
            else: # 需要找零
                tmpValues = []
                for i in costList:
                    if i != changeValueIndex: # 表示i被花费又不是唯一找零值
                        tmpValues.append(self.ValuePrfBlockPair[i][0])
                        self.costedValuesAndRecipes.append((self.ValuePrfBlockPair[i][0], tmpRecipient))

                if tmpValues != []: # 非找零值且被花费的
                    tmpTxn = Transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                     nonce=tmpNonce, signature=None, value=tmpValues,
                                                     tx_hash=tmpTxnHash, time=tmpTime)
                    tmpTxn.sig_txn(load_private_key=self.privateKey)
                    accTxns.append(tmpTxn)

                tmpP = self.ValuePrfBlockPair[changeValueIndex][1]
                tmpB = self.ValuePrfBlockPair[changeValueIndex][2]
                self.delete_VPBpair(changeValueIndex)
                self.add_VPBpair([changeTxn2Recipient.Value[0], copy.deepcopy(tmpP), copy.deepcopy(tmpB)]) # V1在本轮的后续交易中都不可再使用
                self.add_VPBpair([changeTxn2Sender.Value[0], copy.deepcopy(tmpP), copy.deepcopy(tmpB)])

                accTxns.append(changeTxn2Sender)
                accTxns.append(changeTxn2Recipient)

        self.accTxns = accTxns
        self.acc2nodeDelay.append(asizeof.asizeof(accTxns) * 8 / BANDWIDTH + NODE_ACCOUNT_DELAY)
        return accTxns

    def receipt_txn_and_prf(self):
        pass

    def updateBloomPrf(self, bloom, txnAccList, blockIndex):
        if self.costedValuesAndRecipes == [] and self.addr in bloom:
            # 被bloom误判，执行添加布隆证明操作
            self.bloomPrf.append([copy.deepcopy(txnAccList), copy.deepcopy(blockIndex)]) # 布隆证明 = [此布隆过滤器中所有账户的地址，此布隆隶属的区块号]

    def check_pass_VPBpair(self, VPBpair, bloomPrf, blockchain, passIndexList, CKOwner, check_start_time): # 若存在check point时，则调用此函数
        value = VPBpair[0]
        valuePrf = VPBpair[1].prfList
        blockIndex = VPBpair[2]

        # recordOwner = None  # 此变量用于记录值流转的持有者
        # epochRealBList = []  # 记录epoch内的真实的B的信息，用于和VPB中的B进行对比
        BList = []  # 记录epoch内的VPB的B的信息，结构为：[(owner,[list of block index]), (...), (...), ...]用于进行对比验证
        oneEpochBList = [blockIndex[1 + passIndexList[-1]]]  # 结构为：[list of block index], 新的epoch的开头加进去
        orgSender = valuePrf[passIndexList[-1]].owner
        recordOwner = valuePrf[1 + passIndexList[-1]].owner  # 将记录的owner更新为CK的owner
        epochChangeList = []  # 记录epoch变化时的区块号

        ##############################
        ######## 3 检验proof的正确性 ###
        ##############################
        for index, prfUnit in enumerate(valuePrf, start=0):
            if index in passIndexList:
                continue

            isNewEpoch = False
            oneEpochBList.append(blockIndex[index])
            tmpSender = None # 记录每个epoch变更时的交易的发送者，以便验证bloom
            if index == passIndexList[-1]+1: # check point后的第一个检测需要特殊处理
                isNewEpoch = True # 直接进入一个新的epoch
                oneEpochBList.pop()  # pop后一个交易的区块号，否则有重复
                tmpSender = orgSender
            elif recordOwner != prfUnit.owner: # 说明 owner 已改变，该值进入下一个owner持有的epoch
                isNewEpoch = True
                lastBlockIndex = oneEpochBList.pop() # 获得最后一个交易的区块号
                # 更新epoch内的VPB的B的信息
                BList.append((copy.deepcopy(recordOwner), copy.deepcopy(oneEpochBList)))
                oneEpochBList = [lastBlockIndex]  # 为下一段证明保留最初的交易所在的区块号
                epochChangeList.append(lastBlockIndex)
                tmpSender = recordOwner
                recordOwner = prfUnit.owner  # 更新持有者信息

            ownerAccTxnsList = prfUnit.ownerAccTxnsList
            ownerMTreePrfList = prfUnit.ownerMTreePrfList

            # 检测：ownerAccTxnsList和ownerMTreePrfList的信息是相符的
            # 注意，这里的Encode()函数只对accTxns进行编码，因此可以设sender='sender'，senderID=None 结果不影响。
            uncheckedAccTxns = Transaction.AccountTxns(sender='sender', senderID=None, accTxns=ownerAccTxnsList)
            uncheckedMTreePrf = unit.MTreeProof(MTPrfList=ownerMTreePrfList)
            uncheckedAccTxns.set_digest()
            accTxnsDigest = uncheckedAccTxns.Digest
            # 检测：ownerMTreePrfList和主链此块中的root是相符的
            if not uncheckedMTreePrf.checkPrf(accTxnsDigest=accTxnsDigest,
                                            trueRoot=blockchain.chain[blockIndex[index]].get_mTreeRoot()):
                print("VPB检测报错：默克尔树检测未通过")
                return False  # 默克尔树检测未通过，固错误！

            if isNewEpoch:
                # 所有txn中应当有且仅有一个交易将值转移到新的owner手中
                SpendValueTxnList = []  # 记录在此accTxns中此值被转移的所有交易，合法的情况下，此list的长度应为1
                for txn in ownerAccTxnsList:
                    count = txn.count_value_in_value(value)
                    if count == 1:  # =0表示未转移该值，>1则表明在此交易内存在双花
                        if txn.Sender != txn.Recipient:  # 若不是转移给自己则计入值的花销列表
                            SpendValueTxnList.append(txn)
                    elif count > 1:
                        print("VPB检测报错：单个交易内存在双花！")
                        return False  # 存在双花！或者未转移值给owner！
                if len(SpendValueTxnList) != 1:
                    print("VPB检测报错：存在双花！或者未转移值给owner！")
                    return False  # 存在双花！或者未转移值给owner！
                if tmpSender != None and tmpSender not in blockchain.chain[blockIndex[index]].bloom:
                    print("VPB检测报错：值转移时的Bloom过滤器检测错误！")
                    return False
                if SpendValueTxnList[0].Recipient != recordOwner:
                    print("VPB检测报错：此值未转移给指定的owner")
                    return False  # 此值未转移给指定的owner
            else:
                # 未进入新epoch，即，此值尚未转移给新的owner
                for txn in ownerAccTxnsList:
                    if txn.count_value_intersect_txn(value) != 0:
                        if txn.Sender != txn.Recipient:
                            print("VPB检测报错：此值不应当在此处被提前花费")
                            return False  # 此值不应当在此处被花费！

        ##############################
        # 4 检测：每个epoch内的B和主链上的布隆过滤器的信息是相符的，即，epoch的owner没有在B上撒谎
        ##############################
        if len(BList) != len(epochChangeList):
            print("VPB检测报错：len(BList) != len(epochChangeList)")
            return False

        if passIndexList:
            oldEpochFlag = blockIndex[passIndexList[-1]+1]
        else:
            oldEpochFlag = 0

        for index, epochRecord in enumerate(BList, start=0):
            fullEpochBList = range(oldEpochFlag, epochChangeList[index])
            realEpochBlist = []
            (owner, uncheckedBList) = epochRecord

            if len(uncheckedBList) < 1:
                print("VPB检测报错：本段owner持有值没有记录")
                return False  # 本段owner持有值没有记录，固错误！

            # todo:判断uncheckedBList是否接上passList
            # if index == 0 and uncheckedBList[0] != blockIndex[passIndexList[-1]+1]:
                # print("VPB检测报错：检查点数据没有接上B list未检测数据")
                # return False

            ownerBegin = uncheckedBList[0]  # owner刚拥有该值时的block index
            ownerEnd = uncheckedBList[-1]  # owner将在下一个区块将此值转移给其他owner，即，最后一个持有此值的block index
            if ownerEnd < ownerBegin:
                print("VPB检测报错：owner持有值的区块号记录有误")
                return False  # owner持有值的区块号记录有误！

            for item in fullEpochBList:
                if owner in blockchain.chain[item].bloom:
                    realEpochBlist.append(item)

            # 不需要检验owner持有的第一个块，因为已在前面检测过
            if len(uncheckedBList) > 0 and uncheckedBList[0] == oldEpochFlag:
                uncheckedBList.pop(0) # 这里会改变BList
            if len(realEpochBlist) > 0 and realEpochBlist[0] == oldEpochFlag:
                realEpochBlist.pop(0)

            if uncheckedBList != realEpochBlist:
                # 若不同则需要检测bloom proof，排除被bloom过滤器“误伤”的可能
                if bloomPrf == []:
                    print("VPB检测报错：没有提供bloom proof")
                    return False  # 没有提供bloom proof，因此没有误伤，则说明owner提供的值持有记录和真实记录不同，错误！
                else:
                    # todo: 检测bloom proof
                    pass
            oldEpochFlag = epochChangeList[index]
        passRate = 1- (len(passIndexList) / len(valuePrf))
        PrfSize = (asizeof.asizeof(VPBpair) + asizeof.asizeof(bloomPrf)) * 8 * passRate # *8转换为以bit为单位
        # 记录程序结束时间
        check_end_time = time.time()
        # 计算程序运行时间
        VerTime = check_end_time - check_start_time
        self.verifyTimeCostList.append(VerTime)
        self.verifyStorageCostList.append(PrfSize)
        return True


    def check_VPBpair(self, VPBpair, bloomPrf, blockchain):
        # 先检测check point，若有无需检测的vpb则直接跳过
        ckList = self.VPBCheckPoints.findCKviaVPB(VPBpair)
        passIndexList = None
        CKOwner = None
        if ckList != []: # 找到了对应的check point
            ckOwner, ckBIndex = ckList[0]
            flagIndex = None # CK记录到了VPB的哪一位
            for index, item in enumerate(VPBpair[2],start=0):
                if item == ckBIndex[-1]:
                    flagIndex = index
            if flagIndex == None:
                raise ValueError('VPB检测报错：此VPB与检查点记录有冲突！')
            VPBOwner = VPBpair[1].prfList[flagIndex].owner
            if VPBOwner != ckOwner:
                raise ValueError('VPB检测报错：此VPB与检查点记录有冲突！')
            passIndexList = list(range(flagIndex+1))
            CKOwner = ckOwner

        # 统计验证消耗
        PrfSize = (asizeof.asizeof(VPBpair) + asizeof.asizeof(bloomPrf)) * 8 # *8转换为以bit为单位
        # 记录程序开始时间
        check_start_time = time.time()

        def hash(val):
            if type(val) == str:
                return hashlib.sha256(val.encode("utf-8")).hexdigest()
            else:
                return hashlib.sha256(val).hexdigest()

        ##############################
        ######## 1 检测数据类型：########
        ##############################
        if type(VPBpair[0]) != unit.Value or type(VPBpair[1]) != unit.Proof or type(VPBpair[2]) != list:
            print("VPB检测报错：数据结构错误")
            return False # 数据结构错误

        value = VPBpair[0]
        valuePrf = VPBpair[1].prfList
        blockIndex = VPBpair[2]

        if len(valuePrf) != len(blockIndex):
            print("VPB检测报错：证据和块索引非一一映射")
            return False # 证据和块索引非一一映射，固错误

        ##############################
        ######## 2 检测value的结构合法性：
        ##############################
        if not value.checkValue:
            print("VPB检测报错：value的结构合法性检测不通过")
            return False # value的结构合法性检测不通过




        if passIndexList:
            return self.check_pass_VPBpair(VPBpair, bloomPrf, blockchain, passIndexList, CKOwner, check_start_time)




        recordOwner = None # 此变量用于记录值流转的持有者
        epochRealBList = [] # 记录epoch内的真实的B的信息，用于和VPB中的B进行对比
        BList = [] # 记录epoch内的VPB的B的信息，结构为：[(owner,[list of block index]), (...), (...), ...]用于进行对比验证
        oneEpochBList = [] # 结构为：[list of block index]
        epochChangeList = [] # 记录epoch变化时的区块号

        ##############################
        ######## 3 检验proof的正确性 ###
        ##############################
        for index, prfUnit in enumerate(valuePrf, start=0):
            # 由于第一个prfUnit是创世块中的交易因此需要特殊的验证处理
            if index == 0: # 说明是创世块
                recordOwner = prfUnit.owner
                ownerAccTxnsList = prfUnit.ownerAccTxnsList
                ownerMTreePrfList = prfUnit.ownerMTreePrfList
                # 创世块的检测
                if ownerMTreePrfList == [blockchain.chain[0].get_mTreeRoot()]:  # 说明这是创世块
                    tmpGenesisAccTxns = Transaction.AccountTxns(GENESIS_SENDER, -1, ownerAccTxnsList)
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
                tmpSender = None # 记录每个epoch变更时的交易的发送者，以便验证bloom
                if recordOwner != prfUnit.owner: # 说明 owner 已改变，该值进入下一个owner持有的epoch
                    isNewEpoch = True
                    lastBlockIndex = oneEpochBList.pop() # 获得最后一个交易的区块号
                    # 更新epoch内的VPB的B的信息
                    BList.append((copy.deepcopy(recordOwner), copy.deepcopy(oneEpochBList)))
                    oneEpochBList = [lastBlockIndex] # 为下一段证明保留最初的交易所在的区块号
                    epochChangeList.append(lastBlockIndex)
                    tmpSender = recordOwner
                    recordOwner = prfUnit.owner  # 更新持有者信息

                ownerAccTxnsList = prfUnit.ownerAccTxnsList
                ownerMTreePrfList = prfUnit.ownerMTreePrfList

                # 检测：ownerAccTxnsList和ownerMTreePrfList的信息是相符的
                # 注意，这里的Encode()函数只对accTxns进行编码，因此可以设sender='sender'，senderID=None 结果不影响。
                uncheckedAccTxns = Transaction.AccountTxns(sender='sender', senderID=None, accTxns=ownerAccTxnsList)
                uncheckedMTreePrf = unit.MTreeProof(MTPrfList=ownerMTreePrfList)
                uncheckedAccTxns.set_digest()
                accTxnsDigest = uncheckedAccTxns.Digest
                # 检测：ownerMTreePrfList和主链此块中的root是相符的
                if not uncheckedMTreePrf.checkPrf(accTxnsDigest=accTxnsDigest, trueRoot=blockchain.chain[blockIndex[index]].get_mTreeRoot()):
                    print("VPB检测报错：默克尔树检测未通过")
                    return False # 默克尔树检测未通过，固错误！

                if isNewEpoch:
                    # 所有txn中应当有且仅有一个交易将值转移到新的owner手中
                    SpendValueTxnList = [] # 记录在此accTxns中此值被转移的所有交易，合法的情况下，此list的长度应为1
                    for txn in ownerAccTxnsList:
                        count = txn.count_value_in_value(value)
                        if count == 1: # =0表示未转移该值，>1则表明在此交易内存在双花
                            if txn.Sender != txn.Recipient:  # 若不是转移给自己则计入值的花销列表
                                SpendValueTxnList.append(txn)
                        elif count > 1:
                            print("VPB检测报错：单个交易内存在双花！")
                            return False  # 存在双花！或者未转移值给owner！
                    if len(SpendValueTxnList) != 1:
                        print("VPB检测报错：存在双花！或者未转移值给owner！")
                        return False # 存在双花！或者未转移值给owner！
                    if tmpSender != None and tmpSender not in blockchain.chain[blockIndex[index]].bloom:
                        print("VPB检测报错：值转移时的Bloom过滤器检测错误！")
                        return False
                    if SpendValueTxnList[0].Recipient != recordOwner:
                        print("VPB检测报错：此值未转移给指定的owner")
                        return False # 此值未转移给指定的owner
                else:
                    # 未进入新epoch，即，此值尚未转移给新的owner
                    for txn in ownerAccTxnsList:
                        if txn.count_value_intersect_txn(value) != 0:
                            if txn.Sender != txn.Recipient:
                                print("VPB检测报错：此值不应当在此处被提前花费")
                                return False # 此值不应当在此处被花费！
        ##############################
        # 4 检测：每个epoch内的B和主链上的布隆过滤器的信息是相符的，即，epoch的owner没有在B上撒谎
        ##############################
        if len(BList) != len(epochChangeList):
            print("VPB检测报错：len(BList) != len(epochChangeList)")
            return False
        oldEpochFlag = 0
        for index, epochRecord in enumerate(BList, start=0):
            fullEpochBList = range(oldEpochFlag, epochChangeList[index])
            realEpochBlist = []
            (owner, uncheckedBList) = epochRecord

            if len(uncheckedBList) < 1:
                print("VPB检测报错：本段owner持有值没有记录")
                return False  # 本段owner持有值没有记录，固错误！

            ownerBegin = uncheckedBList[0]  # owner刚拥有该值时的block index
            ownerEnd = uncheckedBList[-1]  # owner将在下一个区块将此值转移给其他owner，即，最后一个持有此值的block index
            if ownerEnd < ownerBegin:
                print("VPB检测报错：owner持有值的区块号记录有误")
                return False  # owner持有值的区块号记录有误！

            for item in fullEpochBList:
                if owner in blockchain.chain[item].bloom:
                    realEpochBlist.append(item)

            # 不需要检验owner持有的第一个块，因为已在前面检测过
            if len(uncheckedBList) > 0 and uncheckedBList[0] == oldEpochFlag:
                uncheckedBList.pop(0)
            if len(realEpochBlist) > 0 and realEpochBlist[0] == oldEpochFlag:
                realEpochBlist.pop(0)

            if uncheckedBList != realEpochBlist:
                # 若不同则需要检测bloom proof，排除被bloom过滤器“误伤”的可能
                if bloomPrf == []:
                    print("VPB检测报错：没有提供bloom proof")
                    return False  # 没有提供bloom proof，因此没有误伤，则说明owner提供的值持有记录和真实记录不同，错误！
                else:
                    # todo: 检测bloom proof
                    pass
            oldEpochFlag = epochChangeList[index]

        # 记录程序结束时间
        check_end_time = time.time()
        # 计算程序运行时间
        VerTime = check_end_time - check_start_time
        self.verifyTimeCostList.append(VerTime)
        self.verifyStorageCostList.append(PrfSize)

        return True

    def generate_txn_prf_when_use(self, begin_index, end_index): # begin_index, end_index分别表示此txn在本账户手中开始的区块号和结束的区块号
        # proof = 原证明 + 新生成的证明（在此account时期内的证明）
        # proof单元的数据结构：（区块号，mTree证明）
        # 生成new proof（在此account时期内的证明）
        new_proof = []
        pass
