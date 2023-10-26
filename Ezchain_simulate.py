import copy
import matplotlib.pyplot as plt
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
from pympler import asizeof

class EZsimulate:
    def __init__(self):
        self.blockchain = None
        self.nodeList = []
        self.hashPower = []
        self.network = Network.Network()
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

    def random_generate_nodes(self, nodeNum = NODE_NUM):
        for i in range(nodeNum):
            tmpNode = Node.Node(id = i)
            self.nodeList.append(tmpNode)
            self.hashPower.append(HASH_POWER) #随机设置算力占比
        for i in range(nodeNum):
            self.nodeList[i].random_set_neighbors() #随机设置邻居

    def random_generate_accounts(self, accountNum = ACCOUNT_NUM):
        for i in range(accountNum):
            tmpAccount = Account.Account(ID=i)
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
        #randomAccNum = random.randrange(ACCOUNT_NUM-1, ACCOUNT_NUM) # 随机生成参与交易的账户数
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
            accountTxns.append(Transaction.AccountTxns(self.accounts[i].addr, i, tmpAccTxn))
            self.accounts[i].accTxnsIndex = i # 设置账户对于其提交交易在区块中位置的索引
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
            Txn = Transaction.Transaction(sender=GENESIS_SENDER, recipient=self.accounts[i].addr,
                                                         nonce=0, signature='GENESIS_SIG', value=V,
                                                         tx_hash=0, time=0)
            genesisAccTxns.append(Txn)
        # 生成创世块
        GAccTxns = Transaction.AccountTxns(sender=GENESIS_SENDER, senderID=None, accTxns=genesisAccTxns)
        encodedGAccTxns = [GAccTxns.Encode()]
        preBlockHash = '0x7777777'
        blockIndex = 0
        genesisMTree = unit.MerkleTree(encodedGAccTxns, isGenesisBlcok=True)
        mTreeRoot = genesisMTree.getRootHash()
        genesisBlock = Block.Block(index=blockIndex, mTreeRoot = mTreeRoot, miner = GENESIS_MINER_ID, prehash = preBlockHash)

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
                new_mine_result_time[index] = item + self.nodeList[index].blockBrdCostedTime[-1] + self.nodeList[index].blockCheckCostedTime[-1]
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
        """
            for txn in senderTxns:
                # 交易会引起所有Value的prf的变化
                recipient = txn.Recipient
                # 此交易中所有存在VPB中的值（注意，有些可能不存在VPB中!!!!!）
                VsinTxn = txn.Value
                first_elements_list = [t[0] for t in self.accounts[i].ValuePrfBlockPair]
                # todo:这里用交集 & 计算符号是错误的，因为这样是比对内存一致的value，在值转移（深拷贝）多次后，可能出现地址不统一的情况
                # intersection = set(txnVsinVPB) & set(first_elements_list)
                intersectionVlist = []
                for value in VsinTxn:
                    for valueHold in first_elements_list:
                        if value.isSameValue(valueHold): # todo:这里使用isSameValue的判断逻辑是正确的嘛？
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
        """

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
        for acc in self.accounts:
            acc.clear_info()

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

        # # # # # # # # 绘制account存储成本图像 # # # # # # # #
        def divide_list_elements(lst, divisor, StoOrVer):
            result = []
            for num in lst:
                result.append(num[StoOrVer] / divisor)
            return result

        viewNodeIndex = 0 # 以哪个账户为观察视角观察消耗的存储空间
        accStorageCost = divide_list_elements([acc.verifyCostList[viewNodeIndex] for acc in self.accounts], 1048576, 0)
        # 创建一个Figure对象和一个子图
        fig5, ax5 = plt.subplots()
        # 绘制柱状图
        ax5.plot(range(len(accStorageCost)), accStorageCost)
        # 设置x轴标签
        ax5.set_xlabel("reciped value number")
        # 设置y轴标签
        ax5.set_ylabel("Acc reciped VPB's size(MB)")
        # 设置标题
        ax5.set_title("Acc reciped VPB's size with reciped value number")

        # # # # # # # # 绘制account验证成本图像 # # # # # # # #
        viewNodeIndex = 0  # 以哪个账户为观察视角观察消耗的验证时间
        accVerCost = divide_list_elements([acc.verifyCostList[viewNodeIndex] for acc in self.accounts], 1, 1)
        # 创建一个Figure对象和一个子图
        fig6, ax6 = plt.subplots()
        # 绘制柱状图
        ax6.plot(range(len(accVerCost)), accVerCost)
        # 设置x轴标签
        ax6.set_xlabel("reciped value number")
        # 设置y轴标签
        ax6.set_ylabel("account verify time(s)")
        # 设置标题
        ax6.set_title("account verify time with reciped value number")

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
        ax1.legend(['Txns Num', 'Values Num'])

        # # # # # # # # 安全情况下账户对于交易的确认延迟图像 # # # # # # # #
        viewNodeIndex = 0  # 以哪个账户为观察视角观察消耗的验证时间
        accVerCost = divide_list_elements([acc.verifyCostList[viewNodeIndex] for acc in self.accounts], 1, 1)
        accStorageCost = 8 * divide_list_elements([acc.verifyCostList[viewNodeIndex] for acc in self.accounts], 1, 0)
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
        print("=========== forkRate = "+str(forkRate) + " ===========")

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
        EZsimulate.simulateRound += 1 # 模拟轮次+1
        # 账户节点随机生成交易（可能有一些账户没有交易，因为参加交易的账户的数量是随机的）
        EZsimulate.AccTxns, ACTxnsRecipientList = EZsimulate.random_generate_AccTxns()
        for i in range(len(EZsimulate.AccTxns)):
            EZsimulate.accounts[i].accTxns = EZsimulate.AccTxns[i]
            EZsimulate.accounts[i].recipientList = ACTxnsRecipientList[i]
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

    # 打印链
    EZsimulate.blockchain.print_chain()
    # 计算平均TPS
    EZsimulate.calculateAvgTPS()
    # 打印性能结果
    EZsimulate.showPerformance()
    # 模拟当前的分叉率
    EZsimulate.forkRate()