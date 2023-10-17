import os
import hashlib
import random
import copy
import Transaction
import re

class ProofUnit: # 一个值在一个区块内的证明
    def __init__(self, owner, ownerAccTxnsList, ownerMTreePrfList):
        self.owner = owner
        self.ownerAccTxnsList = ownerAccTxnsList # 在此区块内的ownTxns
        self.ownerMTreePrfList = ownerMTreePrfList # ownTxns对应的mTreePrf

class Proof:
    def __init__(self, prfList):
        self.prfList = prfList
    def add_prf_unit(self, prfUint):
        self.prfList.append(prfUint)

class Value: # 针对VCB区块链的专门设计的值结构，总量2^259 = 16^65
    def __init__(self, beginIndex, valueNum): # beginIndex是16进制str，valueNum是10进制int
        self.beginIndex = beginIndex
        self.valueNum = valueNum
        self.endIndex = self.getEndIndex(beginIndex, valueNum)

    def get_decimal_beginIndex(self):
        return int(self.beginIndex, 16)
    def get_decimal_endIndex(self):
        return int(self.endIndex, 16)

    def split_value(self, change): # 对此值进行分割
        V1 = Value(self.beginIndex, self.valueNum-change)
        tmpIndex = hex(V1.get_decimal_endIndex()+1)
        V2 = Value(tmpIndex, change)
        return V1, V2 # V2是找零

    def getEndIndex(self, beginIndex, valueNum):
        decimal_number = int(beginIndex, 16)
        result = decimal_number + valueNum
        return hex(result)
    def checkValue(self): # 检测Value的合法性
        def is_hexadecimal(string):
            pattern = r"^0x[0-9A-Fa-f]+$"
            return re.match(pattern, string) is not None
        if self.valueNum <= 0:
            return False
        if not is_hexadecimal(self.beginIndex):
            return False
        if not is_hexadecimal(self.endIndex):
            return False
        if self.endIndex != self.getEndIndex(self.beginIndex, self.valueNum):
            return False
        return True

    def isInValue(self, target): # target是Value类型, 判断target是否和本value有交集
        decimal_targetBegin = int(target.beginIndex, 16)
        decimal_targetEnd = int(target.endIndex, 16)
        decimal_beginIndex = self.get_decimal_beginIndex()
        decimal_endIndex = self.get_decimal_endIndex()
        return decimal_endIndex >= decimal_targetBegin and decimal_targetEnd >= decimal_beginIndex

class MTreeProof:
    def __init__(self, MTPrfList = []):
        self.MTPrfList = MTPrfList

    def checkPrf(self, accTxns, trueRoot): #accTxns为待检查的账户交易集合. trueRoot是公链上的mTree root信息
        def hash(val):
            # return hashlib.sha256(val.encode("utf-8")).hexdigest()
            if type(val) == str:
                return hashlib.sha256(val.encode("utf-8")).hexdigest()
            else:
                return hashlib.sha256(val).hexdigest()

        encodeAccTxns = accTxns.Encode()
        hashedEncodeAccTxns = hash(encodeAccTxns)

        if hashedEncodeAccTxns is not self.MTPrfList[0] and hashedEncodeAccTxns is not self.MTPrfList[1]:
            return False
        if self.MTPrfList[-1] is not trueRoot:
            return False
        lastHash = None
        for i in range(len(self.MTPrfList) // 2):
            lastHash = self.MTPrfList[2*i+2]
            if hash(self.MTPrfList[2*i]+self.MTPrfList[2*i+1]) is not lastHash:
                return False
        if lastHash is not self.MTPrfList[-1]:
            return False
        return True


class MerkleTreeNode:
    def __init__(self, left, right, value, content = None, path = [], leafIndex = None):
        self.left = left
        self.right = right
        self.value = value
        self.content = content
        self.path = path
        self.leafIndex = leafIndex # 叶子节点的编号，用于跟踪叶子节点，便于制造prfList
        self.father = None # 用于记录节点的父亲节点

    def hash(val):
        #return hashlib.sha256(val.encode("utf-8")).hexdigest()
        if type(val) == str:
            return hashlib.sha256(val.encode("utf-8")).hexdigest()
        else:
            return hashlib.sha256(val).hexdigest()

    def __str__(self):
        return (str(self.value))


class MerkleTree:
    def __init__(self, values, isGenesisBlcok=False):
        self.prfList = None # 这里的prf是针对每轮每个参与交易的account产生一个proof list
        self.buildTree(values, isGenesisBlcok)
        self.leaves = None

    def buildTree(self, leaves, isGenesisBlcok):
        leaves = [MerkleTreeNode(None, None, MerkleTreeNode.hash(e), e, leafIndex=index) for index, e in enumerate(leaves, start=0)]
        self.leaves = leaves # 记录叶子节点的备份
        if isGenesisBlcok:
            self.root = leaves[0] # 创世块的仅记录树根信息
            return
        OrgLeavesLen = len(leaves) # 原始AccTxns的长度
        popLeaveNum = 0 #记录生成mTree时pop了多少叶子节点
        PrfList = [] #记录mTree的生成路径用于追踪以生成prf

        while len(leaves) > 1:
            length = len(leaves)
            for i in range(length // 2):
                if leaves[0].content is not None: #是叶子节点
                    leaves[0].path = [popLeaveNum] # 用.append添加会造成所有节点的path都同步变化！！# 可能是python的指针机制导致的
                    popLeaveNum += 1
                left = leaves.pop(0)
                if leaves[0].content is not None: #是叶子节点
                    leaves[0].path = [popLeaveNum]
                    popLeaveNum += 1
                right = leaves.pop(0)
                value: str = MerkleTreeNode.hash(left.value + right.value)
                comPath = left.path+right.path
                left.path = comPath
                right.path = comPath
                newMTreeNode = MerkleTreeNode(left, right, value, path=comPath)
                left.father = newMTreeNode # 添加父节点信息
                right.father = newMTreeNode # 添加父节点信息
                leaves.append(newMTreeNode)
            if length % 2 == 1:
                leaves.append(leaves.pop(0))

        self.root = leaves[0]

        # 对每个accTxns生成对应的的proof trace
        tmpList = []
        for i in range(OrgLeavesLen): # 添加root节点到所有prflist中
            PrfList.append(copy.deepcopy(tmpList))

        for leaf in self.leaves:
            PrfList[leaf.leafIndex].append(leaf.value)
            father = leaf.father
            fatherRightChild = father.right
            fatherLeftChild = father.left
            anotherChild = None
            if fatherRightChild == leaf:
                anotherChild = fatherLeftChild
            if fatherLeftChild == leaf:
                anotherChild = fatherRightChild
            PrfList[leaf.leafIndex].append(anotherChild.value)
            PrfList[leaf.leafIndex].append(father.value)
            
        """
        def add_given_path_2_prfList(node, givenIndex):
            if node.left is not None and node.right is not None:
                add_given_path_2_prfList(node.left, givenIndex)
                add_given_path_2_prfList(node.right, givenIndex)
            if givenIndex in node.path:
                PrfList[givenIndex].append(node.value)

        for leafIndex in range(OrgLeavesLen):
            add_given_path_2_prfList(self.root.left, leafIndex)
            add_given_path_2_prfList(self.root.right, leafIndex)
            PrfList[leafIndex].append(copy.deepcopy(self.root.value))
        """

        self.prfList = PrfList

    #测试mTree的叶子节点数
    def find_leaves_num(self, node): #调用时赋node = self.root
        if node.content is None:
            self.find_leaves_num(node.left)
            self.find_leaves_num(node.right)
        else:
            self.testNum += 1

    def printTree(self, node) -> None:
        if node != None:
            if node.left != None:
                print("Left: " + str(node.left))
                print("Right: " + str(node.right))
            else:
                print("Input")
            print("Value: " + str(node.value))
            #print("Content: " + str(node.content))
            print("")
            self.printTree(node.left)
            self.printTree(node.right)

    def getRootHash(self) -> str:
        return self.root.value

    def checkTree(self, node = None):
        if node is None:
            node = self.root
        if node.left != None and node.right != None: #不是叶子节点
            #tmp = MerkleTreeNode.hash(node.left.value + node.right.value)
            #tmp2 = node.value
            if node.value != MerkleTreeNode.hash(node.left.value + node.right.value):
                return False
            else:
                return (self.checkTree(node=node.left) and self.checkTree(node=node.right))
        else: #是叶子节点
            if node.value != MerkleTreeNode.hash(node.content):
                return False
        return True


def generate_signature(address):
    # 生成随机数
    random_number = random.randint(1, 100000)
    # 将随机数与地址连接起来
    data = str(random_number) + str(address)
    # 使用SHA256哈希函数计算数据的摘要
    hash_object = hashlib.sha256(data.encode())
    signature = hash_object.hexdigest()
    return signature

import random
#随机生成固定长度的16进制数字

def generate_random_hex(length):
    hex_digits = "0123456789ABCDEF"
    hex_number = "0x"
    for _ in range(length):
        hex_number += random.choice(hex_digits)
    return hex_number

if __name__ == "__main__":
    elems = ['1', '2', '3', '4', '5', '6']
    print('构造树')
    mtree = MerkleTree(elems)
    print('打印根哈希值')
    print("Root Hash: " + mtree.getRootHash() + "\n")
    print('打印默克尔树')
    mtree.printTree(mtree.root)
    print('打印所有proof')
    print(mtree.prfList)
    prf = MTreeProof(MTPrfList=mtree.prfList)

    print('======================')
    v_begin = generate_random_hex(65)
    print("v_begin:"+v_begin)
    v_num = 777
    print("v_num:" + str(v_num))
    v = Value(v_begin, v_num)
    print("v_end:"+v.endIndex)
    traget_num =9999
    t = Value(v.getEndIndex(v.endIndex, 0), traget_num)
    flag1 = v.checkValue()
    flag2 = v.isInValue(t)
    print("flag1:"+str(flag1))
    print("flag2:" + str(flag2))

#elems = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
#print('构造树')
#mtree = MerkleTree(elems)
#print('打印根哈希值')
#print("Root Hash: " + mtree.getRootHash() + "\n")
#print('打印默克尔树')
#mtree.printTree(mtree.root)
