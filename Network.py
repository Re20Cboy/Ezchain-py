import time
import sys

import Message
from const import *
import numpy as np
import random

class Network:
    def __init__(self, bandwidth = BANDWIDTH):
        self.delay_matrix = None #单位为s
        self.bandwidth = bandwidth

    def random_set_delay_matrix(self, nodeNum):
        array = np.array([[random.randint(1, 1000) for _ in range(nodeNum)] for _ in range(nodeNum)])
        self.delay_matrix = array / 1000 #单位换算为s

    def simulate_delay(self, message_size, link_delay): #模拟仿真每次传输的延迟, link_delay是连接链路的固定传输延迟
        # 计算传输时间（以秒为单位）
        transmission_time = message_size / self.bandwidth #根据msg大小计算出传输耗时
        # 模拟网络延迟
        delay_time = transmission_time + link_delay  # 这里简单地将传输时间乘以一个常数（2），可以根据实际需求进行调整
        # 等待延迟时间
        #time.sleep(delay_time)
        return delay_time

    def calculate_broadcast_time(self, nodeID, msg, nodeList):
        visited = set()
        delay = [0] * NODE_NUM
        visited.add(nodeID)

        def recursive_broadcast(current_node, brd_time):
            for neighbor in nodeList[current_node].neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)

                    neighbor_time = self.simulate_delay(msg.get_size(),
                                                        self.delay_matrix[current_node][neighbor])
                    if neighbor_time == None:
                        raise ValueError("neighbor_time未被定义！！！")

                    runTime = nodeList[neighbor].receive_msg(msg) # runTime是node处理及验证各类（block及blockBody）消息的时间
                    if runTime < 0:
                        return -1 #返回-1表示发现非法msg

                    if delay[neighbor] != 0:
                        delay[neighbor] = min(neighbor_time, delay[neighbor])
                    else:
                        delay[neighbor] = neighbor_time

                    recursive_broadcast(neighbor, brd_time + neighbor_time)

            return delay, max(delay)

        delayList, broadcast_time = recursive_broadcast(nodeID, 0)
        if type(msg) == Message.BlockMsg:
            for index, delay in enumerate(delayList, start=0):
                if delay != 0:
                    nodeList[index].blockBrdCostedTime.append(delay)
        elif type(msg) == Message.BlockBodyMsg:
            for index, delay in enumerate(delayList, start=0):
                if delay != 0:
                    nodeList[index].blockBodyBrdCostedTime.append(delay)
        return broadcast_time

    def p2p_broadcast(self, nodeID, msg, nodeList):
        visited = set()  # 用于存储已经访问的节点
        delay_list = set()
        new_visited = set() # 新一轮广播中被广播到的节点
        visited.add(nodeID)
        new_visited.add(nodeID)

        def recursive_broadcast(new_visited, brd_msg, pre_delay = 0):
            tmp_new_visited = set()
            for new_visited_node in new_visited:
                for neighbor in nodeList[new_visited_node].neighbors:
                    delay_time = pre_delay + self.simulate_delay(sys.getsizeof(brd_msg),
                                                                 self.delay_matrix[new_visited_node][neighbor])
                    visited.add(neighbor)
                    delay_list.add(delay_time)
                    tmp_new_visited.add(neighbor)
            new_visited = tmp_new_visited


        #递归遍历广播所有邻居节点
        def recursive_broadcast(current_node, brd_msg, pre_delay = 0):
            for neighbor in nodeList[current_node].neighbors:
                if neighbor not in visited:
                    # 此neighbor接收msg，并执行转发：
                    #todo: neighbor接收msg的处理逻辑
                    #print("Broadcasting message from node ", current_node, " to ", neighbor)
                    delay_time = pre_delay + self.simulate_delay(sys.getsizeof(brd_msg), self.delay_matrix[current_node][neighbor])
                    checkFlag = nodeList[neighbor].receive_msg(brd_msg)
                    if not checkFlag:
                        return -1
                    visited.add(neighbor)
                    delay_list.add(delay_time)
                    recursive_broadcast(neighbor, brd_msg, delay_time)

        recursive_broadcast(nodeID, msg)
        return max(delay_list) #返回最大的延迟，即，msg广播至所有节点的时间
