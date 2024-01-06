#!/usr/bin/env python3

import copy
import matplotlib.pyplot as plt
import block
import blockchain
import message
import network
import node
from const import *
import random
import time
import numpy as np
import account
import transaction
import unit
from pympler import asizeof
import datetime #系统时间作为文件名，防止记录时同文件名覆盖
import cProfile # 分析性能
import csv #将实验结果存储在csv表格中
from datetime import datetime
from utils import ensure_directory_exists

class EZsimulate:
    def __init__(self):
        self.blockchain = None
        self.nodeList = []
        self.hashPower = []
        self.network = network.Network()
        self.avgTPS = 0
        self.TPSList = [] # 记录每轮的TPS
        self.TxnsNumList = [] # 记录每轮交易的总数
        self.mineTimeList = [] # 记录两个区块间的间隔时间
        self.avgTxnDelay = 0
        self.hashDifficulty = HASH_DIFFICULTY
        self.nodeNum = NODE_NUM
        self.accounts = []
        self.AccTxns = [] #以账户为单位的交易集合
        self.simulateRound = 0
        self.transVNumList = [] # 记录每轮转移的值的数量
        self.accountsPublicKeyList = [] # 记录所有账户的公钥列表
        self.NodesPublicKeyList = [] # 记录所有节点的公钥列表
        self.txnsPool = unit.txnsPool() # 用于存放本轮的所有交易
        self.blockBrdTimeLst = [] # 记录区块的广播时间
        self.blockBodyBrdTimeLst = [] # 记录区块体的广播时间

    def random_generate_nodes(self, nodeNum = NODE_NUM):
        for i in range(nodeNum):
            tmpNode = node.Node(id = i)
            self.nodeList.append(tmpNode)
            self.hashPower.append(HASH_POWER) #随机设置算力占比
            # 将公钥添加进公钥列表
            self.NodesPublicKeyList.append(tmpNode.publicKey)
        for i in range(nodeNum):
            self.nodeList[i].random_set_neighbors() #随机设置邻居

    def random_generate_accounts(self, accountNum = ACCOUNT_NUM):
        for i in range(accountNum):
            tmpAccount = account.Account(ID=i)
            tmpAccount.generate_random_account()
            self.accounts.append(tmpAccount)
            # 将公钥添加进公钥列表
            self.accountsPublicKeyList.append(tmpAccount.publicKey)

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

        randomAccNum = random.randrange(ACCOUNT_NUM // 2 + 1, ACCOUNT_NUM)  # 随机生成参与交易的账户数
        self.TxnsNumList.append(numTxns)
        accountTxns = []
        accountTxnsRecipientList = []
        allocations = distribute_transactions(numTxns, randomAccNum)
        thisRoundAllTransValueNum = 0 # 记录所有账户本轮动用的值的数量
        for i in range(randomAccNum): # 随机本轮发起交易的账户数量
            allocTxnsNum = allocations[i] # 读取本次要读取的交易数量
            randomRecipientsIndexList = random.sample(range(len(self.accounts)), allocTxnsNum) # 随机生成本轮账户i需要转发的对象账户的索引
            if i in randomRecipientsIndexList:
                randomRecipientsIndexList.remove(i) # 账户i不能向自己发起交易，因此需要删除i自己
            randomRecipients = []
            for tmp in randomRecipientsIndexList:
                randomRecipients.append(self.accounts[tmp])
            tmpAccTxn = self.accounts[i].random_generate_txns(randomRecipients)
            # 添加每个账户本轮动用的值的数量
            for txn in tmpAccTxn:
                tmpVNum = len(txn.Value)
                thisRoundAllTransValueNum += tmpVNum
            accountTxns.append(transaction.AccountTxns(self.accounts[i].addr, i, tmpAccTxn))
            self.accounts[i].accTxnsIndex = i # 设置账户对其提交交易在区块中位置的索引
            accountTxnsRecipientList.append(randomRecipientsIndexList)
        self.transVNumList.append(thisRoundAllTransValueNum)
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
            Txn = transaction.Transaction(sender=GENESIS_SENDER, recipient=self.accounts[i].addr,
                                                         nonce=0, signature='GENESIS_SIG', value=V,
                                                         tx_hash=0, time=0)
            genesisAccTxns.append(Txn)
        # 生成创世块
        GAccTxns = transaction.AccountTxns(sender=GENESIS_SENDER, senderID=None, accTxns=genesisAccTxns)
        encodedGAccTxns = [GAccTxns.Encode()]
        preBlockHash = '0x7777777'
        blockIndex = 0
        genesisMTree = unit.MerkleTree(encodedGAccTxns, isGenesisBlcok=True)
        m_tree_root = genesisMTree.getRootHash()
        genesisBlock = block.Block(index=blockIndex, m_tree_root = m_tree_root, miner = GENESIS_MINER_ID, pre_hash = preBlockHash)

        # 将创世块加入区块链中
        self.blockchain = blockchain.Blockchain(genesisBlock)
        # 生成每个创世块中的proof
        for count, acc in enumerate(self.accounts, start=0):
            tmpPrfUnit = unit.ProofUnit(owner=acc.addr, ownerAccTxnsList=GAccTxns.AccTxns ,ownerMTreePrfList=[genesisMTree.root.value])
            tmpPrf = unit.Proof([tmpPrfUnit])
            tmpVPBPair = [genesisAccTxns[count].Value, tmpPrf, [genesisBlock.index]] # V-P-B对
            acc.add_VPBpair(tmpVPBPair)
        return genesisBlock

    def generate_GenesisBlock_for_Dst(self, Dst_accounts):
        v_genesis_begin = '0x77777777777777777777777777777777777777777777777777777777777777777' # 65位16进制
        v_genesis_num = 100000000 # 初始化每个账户1亿个token（最小单位）
        genesisAccTxns = []
        for i in range(len(Dst_accounts)):
            if i > 0:
                v_genesis_begin = int(v_genesis_begin, 16) + v_genesis_num*i + 1
                v_genesis_begin = hex(v_genesis_begin)
            V = unit.Value(beginIndex=v_genesis_begin, valueNum=v_genesis_num)
            Txn = transaction.Transaction(sender=GENESIS_SENDER, recipient=Dst_accounts[i].addr,
                                                         nonce=0, signature='GENESIS_SIG', value=V,
                                                         tx_hash=0, time=0)
            genesisAccTxns.append(Txn)
        # 生成创世块
        GAccTxns = transaction.AccountTxns(sender=GENESIS_SENDER, senderID=None, accTxns=genesisAccTxns)
        encodedGAccTxns = [GAccTxns.Encode()]
        preBlockHash = '0x7777777'
        blockIndex = 0
        genesisMTree = unit.MerkleTree(encodedGAccTxns, isGenesisBlcok=True)
        m_tree_root = genesisMTree.getRootHash()
        fixed_time = datetime(2022, 12, 31, 18, 30, 0)
        genesisBlock = block.Block(index=blockIndex, m_tree_root = m_tree_root, miner = GENESIS_MINER_ID, pre_hash = preBlockHash, time = fixed_time)

        # 生成每个创世块中的proof
        for count, acc in enumerate(Dst_accounts, start=0):
            tmpPrfUnit = unit.ProofUnit(owner=acc.addr, ownerAccTxnsList=GAccTxns.AccTxns ,ownerMTreePrfList=[genesisMTree.root.value])
            tmpPrf = unit.Proof([tmpPrfUnit])
            tmpVPBPair = [genesisAccTxns[count].Value, tmpPrf, [genesisBlock.index]] # V-P-B对
            if type(acc) == account.Account: # dst acc only add its own vpb pair
                acc.add_VPBpair(tmpVPBPair)

        # add acc node to genesis block's bloom
        for i in range(len(Dst_accounts)):
            genesisBlock.add_item_to_bloom(item=Dst_accounts[i].addr)

        return genesisBlock

    def generate_block(self):
        pass

    def generate_block_body(self):
        new_block_body = message.BlockBodyMsg()
        DigestAccTxns = []
        for item in self.txnsPool.pool:
            DigestAccTxns.append(item[0])
        new_block_body.random_generate_mTree(DigestAccTxns, self.txnsPool.pool)
        return new_block_body

    def begin_mine(self, blockBodyMsg): #模拟PoW算法
        def select_element(elements, probabilities):
            selected_element = random.choices(elements, probabilities, k=1)[0]
            return selected_element

        #随机winner的挖矿时间，并添加记录
        print('Begin mining...')
        mine_time_samples = np.random.geometric(self.hashDifficulty*self.hashPower[0], size=self.nodeNum)
        mine_result_time = [0]*self.nodeNum
        if self.simulateRound == 1: # 第一轮模拟，node还没有广播和验证延迟
            mine_result_time = mine_time_samples
        else:
            if len(mine_time_samples) > len(self.nodeList):
                raise ValueError("len(mine_time_samples) > len(self.nodeList)")
            new_mine_result_time = [0]*self.nodeNum
            for index, item in enumerate(mine_time_samples, start=0):
                if len(self.nodeList[index].blockBrdCostedTime) > 0 and len(self.nodeList[index].blockCheckCostedTime) > 0:
                    new_mine_result_time[index] = item + self.nodeList[index].blockBrdCostedTime[-1] + self.nodeList[index].blockCheckCostedTime[-1]
                else:
                    new_mine_result_time[index] = item
                mine_result_time = new_mine_result_time
        winner_mine_time = min(mine_result_time)
        self.mineTimeList.append(winner_mine_time)
        # time.sleep(winner_mine_time)
        #随机模拟出挖矿赢家，并打包需要广播的交易和区块
        winner = select_element(self.nodeList, self.hashPower)
        winner.tmpBlockBodyMsg = blockBodyMsg
        winner.create_new_block()
        # 添加winner的各项的指标时间
        winner.blockBrdCostedTime.append(0)
        winner.blockBodyBrdCostedTime.append(0)
        winner.blockCheckCostedTime.append(0)
        winner.blockBodyCheckCostedTime.append(0)

        print('Winner is ' + str(winner.id))
        #模拟信息的广播
        print('Begin broadcast msg...')
        block_brd_delay = self.network.calculate_broadcast_time(nodeID=winner.id, msg=winner.tmpBlockMsg, nodeList=self.nodeList, PKList=self.NodesPublicKeyList, accPKList=self.accountsPublicKeyList)
        if block_brd_delay < 0:
            print('!!!!! Illegal msg !!!!!')
        else:
            self.blockBrdTimeLst.append(block_brd_delay)
            print('Block broadcast cost ' + str(block_brd_delay) + 's')
            print('Add block to main chain...')
            self.blockchain.add_block(block=winner.tmpBlockMsg.info)
            block_body_brd_delay = self.network.calculate_broadcast_time(nodeID=winner.id, msg=winner.tmpBlockBodyMsg, nodeList=self.nodeList, PKList=self.NodesPublicKeyList, accPKList=self.accountsPublicKeyList)
            if block_body_brd_delay < 0:
                print('!!!!! Illegal msg !!!!!')
            else:
                self.blockBodyBrdTimeLst.append(block_body_brd_delay)
                print('Block body broadcast cost ' + str(block_body_brd_delay) + 's')

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

            VList = [t[0] for t in self.accounts[i].ValuePrfBlockPair]
            costedValueAndRecipeList = self.accounts[i].costedValuesAndRecipes
            for (costedV, recipient) in costedValueAndRecipeList: # 账户i本轮花费的值
                for item, V in enumerate(VList, start=0): # 账户i当前持有的值
                    if V.isSameValue(costedV):
                        prfUnit = unit.ProofUnit(owner=recipient, ownerAccTxnsList=ownerAccTxnsList,
                                                 ownerMTreePrfList=ownerMTreePrfList)
                        self.accounts[i].ValuePrfBlockPair[item][1].add_prf_unit(prfUnit)
                        self.accounts[i].ValuePrfBlockPair[item][2].append(copy.deepcopy(blockIndex))
                        costValueIndex.append(item)
                        # 测试是否有重复值加入
                        test = self.accounts[i].ValuePrfBlockPair[item][2]
                        if len(test) > 2 and test[-1] == test[-2]:
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
            if len(acc.ValuePrfBlockPair) < 1:
                raise ValueError("len(acc.ValuePrfBlockPair) < 1")
            for j, VPBpair in enumerate(acc.ValuePrfBlockPair, start=0):
                latestOwner = VPBpair[1].prfList[-1].owner
                if latestOwner != acc.addr: # owner不再是自己，则传输给新owner，并删除本地备份
                    # 根据新owner的地址找到新owner的id
                    accID = find_accID_via_accAddr(latestOwner, acc.recipientList)
                    # 新owner添加此VPB
                    newVPBpair = copy.deepcopy(VPBpair)
                    # 新owner需要检测此VPB的合法性
                    if self.accounts[accID].check_VPBpair(newVPBpair, acc.bloomPrf, self.blockchain):
                        self.accounts[accID].add_VPBpair(newVPBpair)
                    else:
                        raise ValueError("VPB检测错误！！！")
                    # acc删除本地VPB备份，不能直接删除，否则循环中已加载的value会出问题
                    del_value_index.append(j)
            # 将需要删除的位置按照降序排序，以免删除元素之后影响后续元素的索引
            del_value_index.sort(reverse=True)
            for i in del_value_index:
                acc.delete_VPBpair(i)

    def clearOldInfo(self): # 进入下一轮挖矿时，清空一些不必要信息
        # 清空交易池中的信息
        self.txnsPool.clearPool()
        # 清空account内的信息
        for acc in self.accounts:
            acc.clear_and_fresh_info()

    def calculateRoundTPS(self):
        thisRoundTime = self.mineTimeList[self.simulateRound-1]
        thisRoundTxnNum = self.TxnsNumList[self.simulateRound-1]
        self.TPSList.append(thisRoundTxnNum / thisRoundTime)

    def calculateAvgTPS(self):
        sumTxnNum = 0
        for item in self.TxnsNumList:
            sumTxnNum += item

        sumTimeSum = 0
        for item in self.mineTimeList:
            sumTimeSum += item

        self.avgTPS = sumTxnNum / sumTimeSum

    def calculateNodeStorageCost(self):
        storageCost = []
        currStorageCost = 0
        for i in range(len(self.blockchain.chain)):
            currStorageCost += asizeof.asizeof(self.blockchain.chain[i])/1048576
            storageCost.append(currStorageCost)
        currMineTime = 0
        mineTimeList = [currMineTime]
        for item in self.mineTimeList:
            currMineTime += item
            mineTimeList.append(currMineTime)
        return mineTimeList, storageCost

    def calculateNodeVerifyCost(self):
        verifyCostList = []
        for index in range(self.simulateRound):
            avgOneRoundVerTime = 0  # 计算每轮挖矿中，所有Node的平均验证时长
            for node in self.nodeList:
                avgOneRoundVerTime += node.blockCheckCostedTime[index]
            avgOneRoundVerTime = avgOneRoundVerTime / self.nodeNum
            verifyCostList.append(avgOneRoundVerTime)
        return verifyCostList

    def showPerformance(self):
        current_time = datetime.now().strftime("%Y%m%d%H%M%S")  # 获取当前时间
        current_const = str(NODE_NUM)+'Nodes_'+str(ACCOUNT_NUM)+'Accs_'+str(SIMULATE_ROUND)+'Rounds'
        # # # # # # # # 绘制TPS图像 # # # # # # # #
        # 创建一个Figure对象和一个子图
        fig1, ax1 = plt.subplots()
        # 绘制柱状图
        ax1.bar(range(len(self.TPSList)), self.TPSList)
        # 添加平均值水平线
        ax1.axhline(y=self.avgTPS, color='r', linestyle='--')
        # 设置x轴标签
        ax1.set_xlabel("sys run round")
        # 设置y轴标签
        ax1.set_ylabel("TPS")
        # 设置标题
        ax1.set_title("run round and TPS")
        # 添加图例
        ax1.legend(['Avg', 'TPS'])
        # 显示网格线
        ax1.grid(True)
        # 保存图像到本地文件
        ensure_directory_exists("./SimulateFig/")
        plt.savefig('SimulateFig/TPS图像_{}_{}.png'.format(current_time, current_const))
        ### 存储到csv表格中 ###
        ensure_directory_exists("./SimulateCSV/")
        csv_name = 'SimulateCSV/TPS_{}_{}.csv'.format(current_time, current_const)
        # 打开一个CSV文件进行写入
        with open(csv_name, 'w', newline='') as file:
            writer = csv.writer(file)
            # 写入列表中的每个元素作为一行
            for item in self.TPSList:
                writer.writerow([item])

        # # # # # # # # 绘制挖矿耗时图像 # # # # # # # #
        # 创建一个Figure对象和一个子图
        fig2, ax2 = plt.subplots()
        # 绘制柱状图
        ax2.bar(range(len(self.mineTimeList)), self.mineTimeList)
        # 设置x轴标签
        ax2.set_xlabel("block index")
        # 设置y轴标签
        ax2.set_ylabel("mine time(s)")
        # 设置标题
        ax2.set_title("EZchain sys mine time")
        # 保存图像到本地文件
        plt.savefig('SimulateFig/挖矿耗时_{}_{}.png'.format(current_time, current_const))
        ### 存储到csv表格中 ###
        csv_name = 'SimulateCSV/Mine_time_{}_{}.csv'.format(current_time, current_const)
        # 打开一个CSV文件进行写入
        with open(csv_name, 'w', newline='') as file:
            writer = csv.writer(file)
            # 写入列表中的每个元素作为一行
            for item in self.mineTimeList:
                writer.writerow([item])

        # # # # # # # # 绘制Node存储成本图像 # # # # # # # #
        mineTimeList, storageCost = self.calculateNodeStorageCost()
        # 创建一个Figure对象和一个子图
        fig3, ax3 = plt.subplots()
        ax3.plot(mineTimeList, storageCost)
        # 设置横轴和纵轴的标签
        ax3.set_xlabel('sys run time')
        ax3.set_ylabel('Con-node storage cost (MB)')
        # 设置标题
        ax3.set_title('Con-node storage cost and sys run time')
        # 保存图像到本地文件
        plt.savefig('SimulateFig/Node存储成本_{}_{}.png'.format(current_time, current_const))
        ### 存储到csv表格中 ###
        csv_name = 'SimulateCSV/Node_S_Cost_{}_{}.csv'.format(current_time, current_const)
        # 打开一个CSV文件进行写入
        # 打开CSV文件并创建一个写入器对象
        with open(csv_name, 'w', newline='') as file:
            writer = csv.writer(file)
            # 写入表头
            writer.writerow(['mineTimeList', 'storageCostList'])
            # 将列表逐行写入CSV文件
            for item1, item2 in zip(mineTimeList, storageCost):
                writer.writerow([item1, item2])

        # # # # # # # # 绘制Node验证成本图像 # # # # # # # #
        verifyCostList = self.calculateNodeVerifyCost()
        # 创建一个Figure对象和一个子图
        fig4, ax4 = plt.subplots()
        # 绘制柱状图
        ax4.plot(range(len(verifyCostList)), verifyCostList)
        # 设置x轴标签
        ax4.set_xlabel("sys run round")
        # 设置y轴标签
        ax4.set_ylabel("Con-node verify time(s)")
        # 设置标题
        ax4.set_title("Con-node verify time with sys run round")
        # 保存图像到本地文件
        plt.savefig('SimulateFig/Node验证成本_{}_{}.png'.format(current_time, current_const))
        ### 存储到csv表格中 ###
        csv_name = 'SimulateCSV/Node_VerBlock_time_{}_{}.csv'.format(current_time, current_const)
        # 打开一个CSV文件进行写入
        with open(csv_name, 'w', newline='') as file:
            writer = csv.writer(file)
            # 写入列表中的每个元素作为一行
            for item in verifyCostList:
                writer.writerow([item])

        # # # # # # # # 绘制account验证存储成本图像 # # # # # # # #
        # viewNodeIndex = 0  # 以哪个账户为观察视角观察消耗的验证时间
        def bitList2MBList(bitList):
            MBList = []
            for item in bitList:
                MBList.append(item / 8388608)  # 从bit转化为MB
            return MBList

        # 创建一个Figure对象和一个子图
        fig5, ax5 = plt.subplots()
        # 抽取前五个acc作为观察对象，绘制其存验证储成本曲线
        maxIndex = min(len(self.accounts), 1)
        sumStorageCostList = []
        avgStorageCostList = []
        minIndex = None
        for index in range(maxIndex):
            accStorageCostList = bitList2MBList(self.accounts[index].verifyStorageCostList)  # 从bit转化为MB
            # ax5.plot(range(len(accStorageCostList)), accStorageCostList)
            if minIndex == None:
                minIndex = len(accStorageCostList)
            else:
                minIndex = min(len(accStorageCostList), minIndex)
            if index == 0:
                sumStorageCostList = accStorageCostList
            else:
                for i in range(minIndex):
                    sumStorageCostList[i] += accStorageCostList[i]
        for i in sumStorageCostList:
            avgStorageCostList.append(i / maxIndex)

        # 计算阶段平均值
        Fig5_newAvgLst = [0]
        Fig5_newAvgLstX = [0]
        Fig5_phase = 50
        Fig5_index = 0
        Fig5_tmpRound = int(len(avgStorageCostList) / Fig5_phase)
        for r in range(Fig5_tmpRound):
            tmpSun = 0
            for i in range(Fig5_phase):
                tmpIndex = Fig5_index + i
                tmpSun += avgStorageCostList[tmpIndex]
            Fig5_newAvgLst.append(tmpSun/Fig5_phase)
            Fig5_index += Fig5_phase
            Fig5_newAvgLstX.append(Fig5_index)
        ax5.plot(range(len(avgStorageCostList)), avgStorageCostList, color='r')
        ax5.plot(Fig5_newAvgLstX, Fig5_newAvgLst, color='black')

        # 设置x轴标签
        ax5.set_xlabel("reciped value number")
        # 设置y轴标签
        ax5.set_ylabel("Acc reciped VPB's size(MB)")
        # 设置标题
        ax5.set_title("Acc reciped VPB's size with reciped value number")
        # 添加图例
        ax5.legend(['newAvgLst', 'avgStorageCostList'])
        # 保存图像到本地文件
        plt.savefig('SimulateFig/account验证存储成本_{}_{}.png'.format(current_time, current_const))
        ### 存储到csv表格中 ###
        csv_name = 'SimulateCSV/Acc_recipe_VPB_size(NewAvg)_{}_{}.csv'.format(current_time, current_const)
        # 打开一个CSV文件进行写入
        with open(csv_name, 'w', newline='') as file:
            writer = csv.writer(file)
            # 写入表头
            writer.writerow(['newAvgLst_X', 'newAvgLst_Y'])
            # 将列表逐行写入CSV文件
            for item1, item2 in zip(Fig5_newAvgLstX, Fig5_newAvgLst):
                writer.writerow([item1, item2])

        ### 存储到csv表格中 ###
        csv_name2 = 'SimulateCSV/Acc_recipe_VPB_size(Avg)_{}_{}.csv'.format(current_time, current_const)
        # 打开一个CSV文件进行写入
        with open(csv_name2, 'w', newline='') as file:
            writer = csv.writer(file)
            # 写入表头
            writer.writerow(['AvgLst_X', 'AvgLst_Y'])
            # 将列表逐行写入CSV文件
            for item1, item2 in zip(range(len(avgStorageCostList)), avgStorageCostList):
                writer.writerow([item1, item2])


        # # # # # # # # 绘制account验证时间成本图像 # # # # # # # #
        acc0_VerTimeCostList = [] # 用于记录acc[0]的验证成本，并存储在csv表格中
        # 创建一个Figure对象和一个子图
        fig6, ax6 = plt.subplots()
        # 抽取前五个acc作为观察对象，绘制其验证时间成本曲线
        maxIndex = min(len(self.accounts), 5)
        sumVerTimeList = []
        avgVerTimeCostList = []
        minIndex = None
        for index in range(maxIndex):
            accVerTimeCostList = self.accounts[index].verifyTimeCostList
            if index == 0:
                acc0_VerTimeCostList = accVerTimeCostList
            ax6.plot(range(len(accVerTimeCostList)), accVerTimeCostList)
            if minIndex == None:
                minIndex = len(accVerTimeCostList)
            else:
                minIndex = min(len(accVerTimeCostList), minIndex)
            if index == 0:
                sumVerTimeList = accVerTimeCostList
            else:
                for i in range(minIndex):
                    sumVerTimeList[i] += accVerTimeCostList[i]
        for i in sumVerTimeList:
            avgVerTimeCostList.append(i / maxIndex)
        ax6.plot(range(len(avgVerTimeCostList)), avgVerTimeCostList, color='black')
        # 设置x轴标签
        ax6.set_xlabel("reciped value number")
        # 设置y轴标签
        ax6.set_ylabel("account verify time(s)")
        # 设置标题
        ax6.set_title("account verify time with reciped value number")
        # 保存图像到本地文件
        plt.savefig('SimulateFig/account验证时间成本_{}_{}.png'.format(current_time, current_const))

        # 计算阶段平均值
        Fig6_newAvgLst = [0]
        Fig6_newAvgLstX = [0]
        Fig6_phase = 50
        Fig6_index = 0
        Fig6_tmpRound = int(len(acc0_VerTimeCostList) / Fig6_phase)
        for r in range(Fig6_tmpRound):
            tmpSun = 0
            for i in range(Fig6_phase):
                tmpIndex = Fig6_index + i
                tmpSun += acc0_VerTimeCostList[tmpIndex]
            Fig6_newAvgLst.append(tmpSun / Fig6_phase)
            Fig6_index += Fig6_phase
            Fig6_newAvgLstX.append(Fig6_index)

        ### 存储到csv表格中 ###
        csv_name = 'SimulateCSV/Acc_ver_vpb_time(acc_0_avg)_{}_{}.csv'.format(current_time, current_const)
        # 打开一个CSV文件进行写入
        with open(csv_name, 'w', newline='') as file:
            writer = csv.writer(file)
            # 写入表头
            writer.writerow(['acc0_ver_vpb_avg_time_x', 'acc0_ver_vpb_avg_time_y'])
            # 将列表逐行写入CSV文件
            for item1, item2 in zip(Fig6_newAvgLstX, Fig6_newAvgLst):
                writer.writerow([item1, item2])

        ### 存储到csv表格中 ###
        csv_name = 'SimulateCSV/Acc_ver_vpb_time(acc_0)_{}_{}.csv'.format(current_time, current_const)
        # 打开一个CSV文件进行写入
        with open(csv_name, 'w', newline='') as file:
            writer = csv.writer(file)
            # 写入列表中的每个元素作为一行
            for item in acc0_VerTimeCostList:
                writer.writerow([item])

        ### 存储到csv表格中 ###
        csv_name = 'SimulateCSV/Acc_ver_vpb_time(all_avg)_{}_{}.csv'.format(current_time, current_const)
        # 打开一个CSV文件进行写入
        with open(csv_name, 'w', newline='') as file:
            writer = csv.writer(file)
            # 写入列表中的每个元素作为一行
            for item in avgVerTimeCostList:
                writer.writerow([item])

        # # # # # # # # 绘制每轮交易数和转移的值的数量图像 # # # # # # # #
        # 创建一个Figure对象和一个子图
        fig7, ax7 = plt.subplots()
        ax7.plot(range(len(self.TxnsNumList)), self.TxnsNumList)
        ax7.plot(range(len(self.transVNumList)), self.transVNumList)
        # 设置x轴标签
        ax7.set_xlabel("sys run round")
        # 设置y轴标签
        ax7.set_ylabel("txn or value num")
        # 添加图例
        ax7.legend(['Txns Num', 'Values Num'])
        # 保存图像到本地文件
        plt.savefig('SimulateFig/交易数和转移的值_{}_{}.png'.format(current_time, current_const))
        ### 存储到csv表格中 ###
        csv_name = 'SimulateCSV/Txn_and_Value_Num_1R_{}_{}.csv'.format(current_time, current_const)
        # 打开一个CSV文件进行写入
        with open(csv_name, 'w', newline='') as file:
            writer = csv.writer(file)
            # 写入表头
            writer.writerow(['TxnsNum1R', 'ValuesNum1R'])
            # 将列表逐行写入CSV文件
            for item1, item2 in zip(self.TxnsNumList, self.transVNumList):
                writer.writerow([item1, item2])


        # # # # # # # # 安全情况下账户对于交易的确认延迟图像 # # # # # # # #
        viewNodeIndex = 0  # 以哪个账户为观察视角观察消耗的验证时间
        accVerCost = self.accounts[viewNodeIndex].verifyTimeCostList
        accStorageCost = self.accounts[viewNodeIndex].verifyStorageCostList
        acc2accDelayList = []
        for item in accStorageCost:
            acc2accDelayList.append(item / BANDWIDTH + ACC_ACC_DELAY)
        acc2nodeDelayList = self.accounts[viewNodeIndex].acc2nodeDelay
        minIndex = min(len(acc2nodeDelayList), len(self.mineTimeList), len(acc2accDelayList), len(accVerCost))
        confirmTime = []
        for index in range(minIndex):
            tmpTime = acc2nodeDelayList[index] + self.mineTimeList[index] + acc2accDelayList[index] + accVerCost[index]
            confirmTime.append(tmpTime)
        # 创建一个Figure对象和一个子图
        fig8, ax8 = plt.subplots()
        ax8.plot(range(len(confirmTime)), confirmTime)
        # 设置x轴标签
        ax8.set_xlabel("sys run round")
        # 设置y轴标签
        ax8.set_ylabel("acc[0]'s txn confirm time")
        # 保存图像到本地文件
        plt.savefig('SimulateFig/acc确认延迟_{}_{}.png'.format(current_time, current_const))
        ### 存储到csv表格中 ###
        csv_name = 'SimulateCSV/Acc_confirm_time_{}_{}.csv'.format(current_time, current_const)
        # 打开一个CSV文件进行写入
        with open(csv_name, 'w', newline='') as file:
            writer = csv.writer(file)
            # 写入列表中的每个元素作为一行
            for item in confirmTime:
                writer.writerow([item])

        # # # # # # # # 平均分叉率图像 # # # # # # # #
        fig9, ax9 = plt.subplots()
        # 添加水平线
        forkRate = self.forkRate()
        ax9.axhline(y=forkRate, color='r', linestyle='--')
        # 添加文字标签
        ax9.text(0.5, forkRate + 1, str(forkRate), color='r')
        # 保存图像到本地文件
        plt.savefig('SimulateFig/平均分叉率_{}_{}.png'.format(current_time, current_const))

        # # # # # # # # acc每轮存储成本图像 # # # # # # # #
        fig10, ax10 = plt.subplots()
        viewNodeIndex = 0  # 以哪个账户为观察视角观察消耗的验证时间
        accRoundVPBCostList = self.accounts[viewNodeIndex].accRoundVPBCostList
        accRoundCKCostList = self.accounts[viewNodeIndex].accRoundCKCostList
        accRoundAllCostList = self.accounts[viewNodeIndex].accRoundAllCostList

        ax10.plot(range(len(accRoundVPBCostList)), accRoundVPBCostList, color='r')
        ax10.plot(range(len(accRoundCKCostList)), accRoundCKCostList, color='blue')
        ax10.plot(range(len(accRoundAllCostList)), accRoundAllCostList, color='black')

        # 计算阶段平均值
        Fig10_newAvgLst = [0]
        Fig10_newAvgLstX = [0]
        Fig10_phase = 50
        Fig10_index = 0
        Fig10_tmpRound = int(len(accRoundVPBCostList) / Fig10_phase)
        for r in range(Fig10_tmpRound):
            tmpSun = 0
            for i in range(Fig10_phase):
                tmpIndex = Fig10_index + i
                tmpSun += accRoundVPBCostList[tmpIndex]
            Fig10_newAvgLst.append(tmpSun / Fig10_phase)
            Fig10_index += Fig10_phase
            Fig10_newAvgLstX.append(Fig10_index)
        ax10.plot(Fig10_newAvgLstX, Fig10_newAvgLst, color='green')

        # 设置x轴标签
        ax10.set_xlabel("sys run round")
        # 设置y轴标签
        ax10.set_ylabel("Acc Storage Cost(MB)")
        # 添加图例
        ax10.legend(['VPB', 'CK', 'All', 'Avg'])
        # 保存图像到本地文件
        plt.savefig('SimulateFig/acc每轮存储成本_{}_{}.png'.format(current_time, current_const))
        ### 存储到csv表格中 ###
        csv_name = 'SimulateCSV/Acc_S_cost(VPB_CK_ALL)_{}_{}.csv'.format(current_time, current_const)
        # 打开一个CSV文件进行写入
        with open(csv_name, 'w', newline='') as file:
            writer = csv.writer(file)
            # 写入表头
            writer.writerow(['VPB', 'CK', 'All'])
            # 将列表逐行写入CSV文件
            for item1, item2, item3 in zip(accRoundVPBCostList, accRoundCKCostList, accRoundAllCostList):
                writer.writerow([item1, item2, item3])

        ### 存储到csv表格中 ###
        csv_name = 'SimulateCSV/Acc_S_cost(NewAvg)_{}_{}.csv'.format(current_time, current_const)
        # 打开一个CSV文件进行写入
        with open(csv_name, 'w', newline='') as file:
            writer = csv.writer(file)
            # 写入表头
            writer.writerow(['NewAvg_X', 'NewAvg_Y'])
            # 将列表逐行写入CSV文件
            for item1, item2 in zip(Fig10_newAvgLstX, Fig10_newAvgLst):
                writer.writerow([item1, item2])


        # # # # # # # # 共识节点广播耗时图像 # # # # # # # #
        fig11, ax11 = plt.subplots()
        blockBrdTimeLst = self.blockBrdTimeLst
        blockBodyBrdTimeLst = self.blockBodyBrdTimeLst

        ax11.plot(range(len(blockBrdTimeLst)), blockBrdTimeLst, color='r')
        ax11.plot(range(len(blockBodyBrdTimeLst)), blockBodyBrdTimeLst, color='blue')
        # 设置x轴标签
        ax11.set_xlabel("sys run round")
        # 设置y轴标签
        ax11.set_ylabel("Con-Node p2p broadcast time")
        # 添加图例
        ax11.legend(['block', 'block body'])
        # 保存图像到本地文件
        plt.savefig('SimulateFig/共识节点广播耗时_{}_{}.png'.format(current_time, current_const))
        ### 存储到csv表格中 ###
        csv_name = 'SimulateCSV/Node_brd_time_{}_{}.csv'.format(current_time, current_const)
        # 打开一个CSV文件进行写入
        with open(csv_name, 'w', newline='') as file:
            writer = csv.writer(file)
            # 写入表头
            writer.writerow(['block_brd_time', 'body_brd_time'])
            # 将列表逐行写入CSV文件
            for item1, item2 in zip(blockBrdTimeLst, blockBodyBrdTimeLst):
                writer.writerow([item1, item2])


        # 显示图形
        plt.show()

    def forkRate(self): # 模拟计算当前情况下的链分叉率
        def oneRoundForkSimulate():
            mine_time_samples = np.random.geometric(self.hashDifficulty * self.hashPower[0], size=self.nodeNum)
            # 提取最小值和第二小的值
            sorted_samples = np.sort(mine_time_samples)  # 对数组进行排序
            min_value = sorted_samples[0]  # 最小值
            second_min_value = sorted_samples[1]  # 第二小的值
            # 设置延迟网络矩阵
            array = np.array([random.randint(1, 1000) for _ in range(self.nodeNum)])
            delay_matrix = array / 1000  # 单位换算为s
            maxTransDelay = max(delay_matrix)
            if min_value + maxTransDelay > second_min_value:
                return 1
            else:
                return 0

        forkCount = 0
        for _ in range(FORK_SIMULATE_ROUND):
            forkCount += oneRoundForkSimulate()
        forkRate = forkCount / FORK_SIMULATE_ROUND
        return forkRate

if __name__ == "__main__":
    def oneRoundSimulate():
        EZsimulate.simulateRound += 1  # 模拟轮次+1
        # 账户节点随机生成交易（可能有一些账户没有交易，因为参加交易的账户的数量是随机的）
        EZsimulate.AccTxns, ACTxnsRecipientList = EZsimulate.random_generate_AccTxns()
        for i in range(len(EZsimulate.AccTxns)):
            EZsimulate.accounts[i].accTxns = EZsimulate.AccTxns[i]
            EZsimulate.accounts[i].recipientList = ACTxnsRecipientList[i]
        # 更新交易池
        EZsimulate.txnsPool.freshPool(EZsimulate.accounts, EZsimulate.AccTxns)
        # Node打包收集所有交易形成区块body（可以理解为简单的打包交易）
        blockBodyMsg = EZsimulate.generate_block_body()
        # 挖矿模拟
        EZsimulate.begin_mine(blockBodyMsg)
        # 计算并更新上轮的TPS数据
        EZsimulate.calculateRoundTPS()
        # sender将交易添加至自己的本地数据库中，并更新所有在持值的proof（V-P-B pair）
        EZsimulate.updateSenderVPBpair(blockBodyMsg.info)
        # 更新account的bloomPrf信息
        EZsimulate.updateBloomPrf()
        # sender将证明发送给recipient，且recipient对VPB进行验证
        EZsimulate.sendPrfAndCheck(ACTxnsRecipientList)
        # 重置account中的信息
        EZsimulate.clearOldInfo()

    #初始化设置
    EZsimulate = EZsimulate()
    print('blockchain:')
    print(EZsimulate.blockchain)
    EZsimulate.random_generate_nodes()
    EZsimulate.random_generate_accounts()
    # 初始化p2p网络
    EZsimulate.init_network()
    print('network:')
    print(EZsimulate.network.delay_matrix)
    # 根据账户生成创世块（给每个账户分发token），并更新account本地的数据（V-P-B pair）
    EZsimulate.generate_GenesisBlock()

    for round in range(SIMULATE_ROUND):
        print("==========ROUND " + str(round) + "==========")
        # 创建一个cProfile对象
        # profiler = cProfile.Profile()
        # 启动性能分析器
        # profiler.enable()
        # 调用要分析的函数
        oneRoundSimulate()
        # 停止性能分析器
        # profiler.disable()
        # 打印性能分析结果
        # profiler.print_stats()

    # 打印链
    EZsimulate.blockchain.print_chain()
    # 计算平均TPS
    EZsimulate.calculateAvgTPS()
    # 打印性能结果
    EZsimulate.showPerformance()
    # 模拟当前的分叉率
    EZsimulate.forkRate()
