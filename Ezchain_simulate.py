import copy

import Block
import Blockchain
import Message
import Network
import Node
from const import *
import random
import time
import numpy as np
import Account
import Transaction
import unit

class EZsimulate:
    def __init__(self):
        self.blockchain = None
        self.mineTime = []
        self.nodeList = []
        self.hashPower = []
        self.network = Network.Network()
        self.avgTPS = 0
        self.avgTxnDelay = 0
        self.hashDifficulty = HASH_DIFFICULTY
        self.nodeNum = NODE_NUM
        self.accounts = []
        self.AccTxns = [] #以账户为单位的交易集合

    def random_generate_nodes(self, nodeNum = NODE_NUM):
        for i in range(nodeNum):
            tmpNode = Node.Node(id = i)
            self.nodeList.append(tmpNode)
            self.hashPower.append(HASH_POWER) #随机设置算力占比
        for i in range(nodeNum):
            self.nodeList[i].random_set_neighbors() #随机设置邻居

    def random_generate_accounts(self, accountNum = ACCOUNT_NUM):
        for i in range(accountNum):
            tmpAccount = Account.Account()
            tmpAccount.generate_random_account()
            self.accounts.append(tmpAccount)

    def init_network(self):
        #初始化延迟二维数组
        self.network.random_set_delay_matrix(len(self.nodeList))

    def random_generate_AccTxns(self, numTxns = PICK_TXNS_NUM):
        def distribute_transactions(X, Y): #将X个交易均匀分配给Y个账户
            base_allocation = X // Y
            remaining_transactions = X % Y
            allocations = [base_allocation] * Y
            for i in range(remaining_transactions):
                allocations[i] += 1
            return allocations

        randomAccNum = random.randrange(ACCOUNT_NUM // 2, ACCOUNT_NUM)  # 随机生成参与交易的账户数
        accountTxns = []
        accountTxnsRecipientList = []
        allocations = distribute_transactions(numTxns, randomAccNum)
        for i in range(randomAccNum):#随机本轮发起交易的账户数量
            allocTxnsNum = allocations[i] # 读取本次要读取的交易数量
            randomRecipientsIndexList = random.sample(range(len(self.accounts)), allocTxnsNum) # 随机生成本轮账户i需要转发的对象账户的索引
            randomRecipients = []
            for tmp in randomRecipientsIndexList:
                randomRecipients.append(self.accounts[tmp])
            tmpAccTxn = self.accounts[i].random_generate_txns(randomRecipients)
            accountTxns.append(Transaction.AccountTxns(self.accounts[i].addr, tmpAccTxn))
            self.accounts[i].accTxnsIndex = i # 设置账户对于其提交交易在区块中位置的索引
            accountTxnsRecipientList.append(randomRecipientsIndexList)
        return accountTxns, accountTxnsRecipientList

    def generate_GenesisBlock(self):
        v_genesis_begin = '0x77777777777777777777777777777777777777777777777777777777777777777' # 65位16进制
        v_genesis_num = 100000000 # 初始化每个账户1亿个token（最小单位）
        genesisAccTxns = []
        for i in range(len(self.accounts)):
            if i > 0:
                v_genesis_begin = int(v_genesis_begin, 16) + v_genesis_num*i + 1
                v_genesis_begin = hex(v_genesis_begin)
            V = unit.Value(beginIndex=v_genesis_begin, valueNum=v_genesis_num)
            Txn = Transaction.Transaction(sender=GENESIS_SENDER, recipient=self.accounts[i].addr,
                                                         nonce=0, signature='GENESIS_SIG', value=V,
                                                         tx_hash=0, time=0)
            genesisAccTxns.append(Txn)
        # 生成创世块
        GAccTxns = Transaction.AccountTxns(GENESIS_SENDER, genesisAccTxns)
        encodedGAccTxns = [GAccTxns.Encode()]
        preBlockHash = '0x7777777'
        blockIndex = 0
        genesisMTree = unit.MerkleTree(encodedGAccTxns, isGenesisBlcok=True)
        mTreeRoot = genesisMTree.getRootHash()
        genesisBlock = Block.Block(index=blockIndex, mTreeRoot = mTreeRoot, miner = GENESIS_MINER_ID, prehash = preBlockHash)
        # genesisBlockMsg = Message.BlockMsg(genesisBlock)
        # genesisBlockBodyMsg = Message.BlockBodyMsg(genesisMTree, genesisAccTxns)
        # 将创世块加入区块链中
        self.blockchain = Blockchain.Blockchain(genesisBlock)
        # 生成每个创世块中的proof
        for count, acc in enumerate(self.accounts, start=0):
            tmpPrfUnit = unit.ProofUnit(owner=acc.addr, ownerAccTxnsList=GAccTxns.AccTxns ,ownerMTreePrfList=[genesisMTree.root.value])
            tmpPrf = unit.Proof([tmpPrfUnit])
            tmpVPBPair = [genesisAccTxns[count].Value, tmpPrf, [genesisBlock.index]] # V-P-B对
            acc.add_VPBpair(tmpVPBPair)

    def generate_block(self):
        pass

    def generate_block_body(self):
        new_block_body = Message.BlockBodyMsg()
        encodeAccTxns = []
        for item in self.AccTxns:
            encodeAccTxns.append(item.Encode())
        new_block_body.random_generate_mTree(encodeAccTxns, self.AccTxns)
        return new_block_body

    def begin_mine(self, blockBodyMsg): #模拟PoW算法
        def select_element(elements, probabilities):
            selected_element = random.choices(elements, probabilities, k=1)[0]
            return selected_element

        def brd_txn_prf_2_acc():
            pass

        #随机winner的挖矿时间，并添加记录
        print('Begin mining...')
        mine_time_samples = np.random.geometric(self.hashDifficulty*self.hashPower[0], size=self.nodeNum)
        winner_mine_time = min(mine_time_samples)
        self.mineTime.append(winner_mine_time)
        winner_mine_time = 1 # 测试阶段统一使用1s
        time.sleep(winner_mine_time)
        #随机模拟出挖矿赢家，并打包需要广播的交易和区块
        winner = select_element(self.nodeList, self.hashPower)
        winner.tmpBlockBodyMsg = blockBodyMsg
        winner.create_new_block()
        print('Winner is ' + str(winner.id))
        #模拟信息的广播
        print('Begin broadcast msg...')
        block_brd_delay = self.network.calculate_broadcast_time(nodeID=winner.id, msg=winner.tmpBlockMsg, nodeList=self.nodeList)
        if block_brd_delay < 0:
            print('!!!!! Illegal msg !!!!!')
        else:
            print('Block broadcast cost ' + str(block_brd_delay) + 's')
            print('Add block to main chain...')
            self.blockchain.add_block(block=winner.tmpBlockMsg.info)
            block_body_brd_delay = self.network.calculate_broadcast_time(nodeID=winner.id, msg=winner.tmpBlockBodyMsg, nodeList=self.nodeList)
            if block_body_brd_delay < 0:
                print('!!!!! Illegal msg !!!!!')
            else:
                print('Block body broadcast cost ' + str(block_body_brd_delay) + 's')

            # 将区块中的证据广播给相应的用户

    def updateSenderVPBpair(self, mTree):

        def get_elements_not_in_B(A, B): # 工具函数：返回在list A中但不在list B中的元素列表
            return [element for element in A if element not in B]

        count = 0 # 用于跟踪记录prfList的index
        # todo: 这里简化了获取VPB中B的流程，真实情况应是：等待区块上链，查看是否包含自身的交易，再确定区块号
        blockIndex = self.blockchain.get_latest_block().index  # 获取最新快的index

        for i, accTxns in enumerate(self.AccTxns, start=0):
            sender = accTxns.Sender # sender的account类型为self.accounts[i]
            senderTxns = accTxns.AccTxns
            # 提取senderTxns中的每个交易涉及到的每个值
            owner = sender
            ownerAccTxnsList = senderTxns
            ownerMTreePrfList = mTree.prfList[count]
            count += 1
            costValueIndex = [] # 用于记录本轮中所有参与交易的值的VPB对的index

            for txn in senderTxns:
                # 交易会引起所有Value的prf的变化
                recipient = txn.Recipient
                # 此交易中所有存在VPB中的值（注意，有些可能不存在VPB中!!!!!）
                txnVsinVPB = txn.Value
                first_elements_list = [t[0] for t in self.accounts[i].ValuePrfBlockPair]
                # todo:这里用交集 & 计算符号是错误的，因为这样是比对内存一致的value，在值转移（深拷贝）多次后，可能出现地址不统一的情况
                # intersection = set(txnVsinVPB) & set(first_elements_list)
                intersectionVlist = []
                for value in txnVsinVPB:
                    for valueHold in first_elements_list:
                        if value.isSameValue(valueHold):
                            intersectionVlist.append(value)

                if intersectionVlist != []: # 若==，则说明此值不在VPB中，是被分裂的值（不应存在的值）
                    # 找出此txn中所有值的在sender中的index
                    index = self.accounts[i].find_VPBpair_via_V(intersectionVlist)
                    unrecordedIndex = get_elements_not_in_B(A=index, B=costValueIndex)
                    if unrecordedIndex != []:
                        costValueIndex += unrecordedIndex
                        # 为index中每个value添加新的prfUnit
                        for item in unrecordedIndex:
                            prfUnit = unit.ProofUnit(owner=recipient, ownerAccTxnsList=ownerAccTxnsList,
                                                    ownerMTreePrfList=ownerMTreePrfList)

                            self.accounts[i].ValuePrfBlockPair[item][1].add_prf_unit(prfUnit)
                            self.accounts[i].ValuePrfBlockPair[item][2].append(copy.deepcopy(blockIndex))
                            # 测试是否有重复值加入
                            test = self.accounts[i].ValuePrfBlockPair[item][2]
                            if len(test)>2 and test[-1]==test[-2]:
                                raise ValueError("发现VPB添加错误！！！！")

            for j, VPBpair in enumerate(self.accounts[i].ValuePrfBlockPair, start=0):
                if j not in costValueIndex:
                    prfUnit = unit.ProofUnit(owner=owner, ownerAccTxnsList=ownerAccTxnsList,
                                             ownerMTreePrfList=ownerMTreePrfList)
                    self.accounts[i].ValuePrfBlockPair[j][1].add_prf_unit(prfUnit)
                    self.accounts[i].ValuePrfBlockPair[j][2].append(copy.deepcopy(blockIndex))
                    # 测试是否有重复值加入
                    test = self.accounts[i].ValuePrfBlockPair[j][2]
                    if len(test) > 2 and test[-1] == test[-2]:
                        raise ValueError("发现VPB添加错误！！！！")

    def updateBloomPrf(self):
        txnAccNum = len(self.AccTxns) # 参与本轮交易的账户的数量
        txnAccList = [item.addr for item in self.accounts]
        txnAccList = txnAccList[:txnAccNum] # 参与本轮交易的账户的地址列表
        unTxnAccNum = len(self.accounts) - txnAccNum # 未参与交易的账户的数量
        for i in range(unTxnAccNum):
            index = -(i+1) # 获得未参与交易的账户的索引
            latestBlock = self.blockchain.get_latest_block()
            self.accounts[index].updateBloomPrf(latestBlock.get_bloom(), txnAccList, latestBlock.get_index())

    def sendPrfAndCheck(self, ACTxnsRecipientList):
        def find_accID_via_accAddr(addr, recipientList):
            for item in recipientList:
                if self.accounts[item].addr == addr:
                    return item
            raise ValueError("未找到此地址对应的账户ID！")

        # 思路：根据account先持有的每个Value，查看其owner，若owner不再是自己则传输给新owner，并删除本地备份
        for acc in self.accounts:
            del_value_index = [] # 记录需要删除的value的index
            if type(acc.ValuePrfBlockPair) != list or acc.ValuePrfBlockPair == []:
                raise ValueError("VPB类型或内容错误！")
            for j, VPBpair in enumerate(acc.ValuePrfBlockPair,start=0):
                latestOwner = VPBpair[1].prfList[-1].owner
                if latestOwner != acc.addr: # owner不再是自己，则传输给新owner，并删除本地备份
                    # 根据新owner的地址找到新owner的id
                    accID = find_accID_via_accAddr(latestOwner, acc.recipientList)
                    # 新owner添加此VPB
                    newVPBpair = copy.deepcopy(VPBpair)
                    # 新owner需要检测此VPB的合法性
                    if self.accounts[accID].check_VPBpair(newVPBpair, acc.bloomPrf, self.blockchain):
                        self.accounts[accID].add_VPBpair(newVPBpair)
                    # acc删除本地VPB备份，不能直接删除，否则循环中已加载的value会出问题
                    del_value_index.append(j)
            # 将需要删除的位置按照降序排序，以免删除元素之后影响后续元素的索引
            del_value_index.sort(reverse=True)
            for i in del_value_index:
                acc.delete_VPBpair(i)

    def clearOldInfo(self): # 进入下一轮挖矿时，清空一些不必要信息
        for acc in self.accounts:
            acc.clear_info()


if __name__ == "__main__":
    #初始化设置
    EZsimulate = EZsimulate()
    print('blockchain:')
    print(EZsimulate.blockchain)

    EZsimulate.random_generate_nodes()
    #print('nodes list:')
    #print(EZsimulate.nodeList)
    #print(EZsimulate.hashPower)

    EZsimulate.random_generate_accounts()
    #print('accounts:')

    # 初始化p2p网络
    EZsimulate.init_network()
    print('network:')
    print(EZsimulate.network.delay_matrix)

    # 根据账户生成创世块（给每个账户分发token），并更新account本地的数据（V-P-B pair）
    EZsimulate.generate_GenesisBlock()

    for round in range(SIMULATE_ROUND):
        # 账户节点随机生成交易（可能有一些账户没有交易，因为参加交易的账户的数量是随机的）
        EZsimulate.AccTxns, ACTxnsRecipientList = EZsimulate.random_generate_AccTxns()
        for i in range(len(EZsimulate.AccTxns)):
            EZsimulate.accounts[i].accTxns = EZsimulate.AccTxns[i]
            EZsimulate.accounts[i].recipientList = ACTxnsRecipientList[i]
        # Node打包收集所有交易形成区块body（可以理解为简单的打包交易）
        blockBodyMsg = EZsimulate.generate_block_body()
        # 挖矿模拟
        EZsimulate.begin_mine(blockBodyMsg)
        # sender将交易添加至自己的本地数据库中，并更新所有在持值的proof（V-P-B pair）
        EZsimulate.updateSenderVPBpair(blockBodyMsg.info)
        # 更新account的bloomPrf信息
        EZsimulate.updateBloomPrf()
        # sender将证明发送给recipient，且recipient对VPB进行验证
        EZsimulate.sendPrfAndCheck(ACTxnsRecipientList)
        # 重置account中的信息
        EZsimulate.clearOldInfo()

    # 打印链
    EZsimulate.blockchain.print_chain()