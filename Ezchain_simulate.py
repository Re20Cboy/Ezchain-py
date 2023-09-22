import Blockchain
import Network
import Node
from const import *
import random
import time
import numpy as np
from pympler import asizeof

class EZsimulate:
    def __init__(self):
        self.blockchain = Blockchain.Blockchain()
        self.mineTime = []
        self.nodeList = []
        self.hashPower = []
        self.network = Network.Network()
        self.avgTPS = 0
        self.avgTxnDelay = 0
        self.hashDifficulty = HASH_DIFFICULTY
        self.nodeNum = NODE_NUM

    def random_generate_nodes(self, nodeNum = NODE_NUM):
        for i in range(nodeNum):
            tmpNode = Node.Node(id = i)
            self.nodeList.append(tmpNode)
            self.hashPower.append(HASH_POWER) #随机设置算力占比
        for i in range(nodeNum):
            self.nodeList[i].random_set_neighbors() #随机设置邻居

    def init_network(self):
        #初始化延迟二维数组
        self.network.random_set_delay_matrix(len(self.nodeList))

    def begin_mine(self): #模拟PoW算法
        def select_element(elements, probabilities):
            selected_element = random.choices(elements, probabilities, k=1)[0]
            return selected_element

        #随机winner的挖矿时间，并添加记录
        print('Begin mining...')
        mine_time_samples = np.random.geometric(self.hashDifficulty*self.hashPower[0], size=self.nodeNum)
        winner_mine_time = min(mine_time_samples)
        self.mineTime.append(winner_mine_time)
        winner_mine_time = 1 # 测试阶段统一使用1s
        time.sleep(winner_mine_time)
        #随机模拟出挖矿赢家，并打包需要广播的交易和区块
        winner = select_element(self.nodeList, self.hashPower)
        winner.create_new_block_body()
        winner.create_new_block()
        print('Winner is ' + str(winner.id))
        #模拟信息的广播
        print('Begin broadcast msg...')
        block_brd_delay = self.network.calculate_broadcast_time(nodeID=winner.id, msg=winner.tmpBlockMsg, nodeList=self.nodeList)

        print('Block broadcast cost ' + str(block_brd_delay) + 's')
        print('Add block to main chain...')
        self.blockchain.add_block(block=winner.tmpBlockMsg.info)

        block_body_brd_delay = self.network.calculate_broadcast_time(nodeID=winner.id, msg=winner.tmpBlockBodyMsg, nodeList=self.nodeList)
        print('Block body broadcast cost ' + str(block_body_brd_delay) + 's')

if __name__ == "__main__":
    #初始化设置
    EZsimulate = EZsimulate()
    print('blockchain:')
    print(EZsimulate.blockchain)
    EZsimulate.random_generate_nodes()
    print('nodes list:')
    print(EZsimulate.nodeList)
    print(EZsimulate.hashPower)
    EZsimulate.init_network()
    print('network:')
    print(EZsimulate.network.delay_matrix)

    # 记录程序开始时间
    start_time = time.time()
    #挖矿模拟
    EZsimulate.begin_mine()

    # 记录程序结束时间
    end_time = time.time()
    # 计算程序运行时间
    run_time = end_time - start_time