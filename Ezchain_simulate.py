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
import csv
from pympler import asizeof

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
        encodedGAccTxns = []
        for item in GAccTxns.AccTxns:
            encodedGAccTxns.append(item.Encode())
        preBlockHash = '0x7777777'
        blockIndex = 0
        genesisMTree = unit.MerkleTree(encodedGAccTxns)
        mTreeRoot = genesisMTree.getRootHash()
        genesisBlock = Block.Block(index=blockIndex, mTreeRoot = mTreeRoot, miner = GENESIS_MINER_ID, prehash = preBlockHash)
        genesisBlockMsg = Message.BlockMsg(genesisBlock)
        genesisBlockBodyMsg = Message.BlockBodyMsg(genesisMTree, genesisAccTxns)
        # 将创世块加入区块链中
        self.blockchain = Blockchain.Blockchain(genesisBlock)
        # 生成每个创世块中的proof
        for count, acc in enumerate(self.accounts, start=0):
            tmpPrfUnit = unit.ProofUnit(owner=acc.addr, ownerAccTxnsList=GAccTxns ,ownerMTreePrfList=genesisMTree.prfList[count])
            tmpPrf = unit.Proof([tmpPrfUnit])
            tmpVPBPair = [genesisAccTxns[count].Value, tmpPrf, genesisBlock.index] # V-P-B对
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

        count = 0 # 用于跟踪记录prfList的index
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
                # 此交易中所有存在VPB中的值（注意，有些可能不存在VPB中）
                txnVsinVPB = txn.Value
                first_elements_list = [t[0] for t in self.accounts[i].ValuePrfBlockPair]
                intersection = set(txnVsinVPB) & set(first_elements_list)
                intersectionVlist = list(intersection)
                if intersectionVlist != []: # 若==，则说明此值不在VPB中，是被分裂的值（不应存在的值）
                    # 找出此txn中所有值的在sender中的index
                    index = self.accounts[i].find_VPBpair_via_V(intersectionVlist)
                    costValueIndex += index
                    # 为此txn中每个value添加新的prfUnit
                    for v in txn.Value:
                        prfUnit = unit.ProofUnit(owner=recipient, ownerAccTxnsList=ownerAccTxnsList,
                                                 ownerMTreePrfList=ownerMTreePrfList)
                        item = index.pop(0) # 删除并返回第一个元素，即，v对应的index
                        self.accounts[i].ValuePrfBlockPair[item][1].add_prf_unit(prfUnit)
            for j, VPBpair in enumerate(self.accounts[i].ValuePrfBlockPair, start=0):
                if j not in costValueIndex:
                    prfUnit = unit.ProofUnit(owner=owner, ownerAccTxnsList=ownerAccTxnsList,
                                             ownerMTreePrfList=ownerMTreePrfList)
                    self.accounts[i].ValuePrfBlockPair[j][1].add_prf_unit(prfUnit)

    def sendPrf(self, ACTxnsRecipientList):
        def sendPrfUnit(senderIndx, recipeIndex, VPBlist): # 将sender持有的在VPBlist中的VPB对转移给recipe
            for i in VPBlist:
                self.accounts[recipeIndex].add_VPBpair(self.accounts[senderIndx].ValuePrfBlockPair[i])
            # 删除sender本地的VPB对
            newSenerVPB = [x for j, x in enumerate(self.accounts[senderIndx].ValuePrfBlockPair) if j not in VPBlist]
            self.accounts[senderIndx].ValuePrfBlockPair = newSenerVPB
            # 更新balance
            self.accounts[senderIndx].update_balance()

        for i in range(len(self.AccTxns)):
            for recipient in ACTxnsRecipientList[i]: # 账户i的所有recipient
                costedVPBpairList = self.accounts[i].find_VPBpair_via_V(self.accounts[i].costedValues)
                sendPrfUnit(i, recipient, costedVPBpairList)


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

    # 根据账户生成创世块（给每个账户分发token），并更新account本地的数据（V-P-B pair）
    EZsimulate.generate_GenesisBlock()

    # 账户节点随机生成交易（可能有一些账户没有交易，因为参加交易的账户的数量是随机的）
    # EZsimulate.AccTxns = EZsimulate.old_random_generate_AccTxns() # 弃用
    # EZsimulate.AccTxns为AccountTxns的list
    EZsimulate.AccTxns, ACTxnsRecipientList = EZsimulate.random_generate_AccTxns()
    for i in range(len(EZsimulate.AccTxns)):
        EZsimulate.accounts[i].accTxns = EZsimulate.AccTxns[i]

    # Node打包收集所有交易形成区块body（可以理解为简单的打包交易）
    blockBodyMsg = EZsimulate.generate_block_body()

    # 初始化p2p网络
    EZsimulate.init_network()
    print('network:')
    print(EZsimulate.network.delay_matrix)

    # 挖矿模拟
    EZsimulate.begin_mine(blockBodyMsg)

    # sender将交易添加至自己的本地数据库中
    # 更新所有在持值的proof（V-P-B pair）
    EZsimulate.updateSenderVPBpair(blockBodyMsg.info)

    # sender将证明发送给recipient
    EZsimulate.sendPrf(ACTxnsRecipientList)

    # recipients验证prf的合法性
    for recipients in ACTxnsRecipientList: #每个ACTxns中包含的recipients的集合
        for recipe in recipients: #每个recipe
            EZsimulate.accounts[recipe].receipt_txn_and_prf()
