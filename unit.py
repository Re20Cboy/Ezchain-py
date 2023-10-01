import os
import hashlib
import random


class MerkleTreeNode:
    def __init__(self, left, right, value, content = None):
        self.left = left
        self.right = right
        self.value = value
        self.content = content

    def hash(val):
        #return hashlib.sha256(val.encode("utf-8")).hexdigest()
        if type(val) == str:
            return hashlib.sha256(val.encode("utf-8")).hexdigest()
        else:
            return hashlib.sha256(val).hexdigest()

    def __str__(self):
        return (str(self.value))


class MerkleTree:
    def __init__(self, values):
        self.buildTree(values)
        #self.leavesNum = 0
        self.testNum = 0
        #self.checkTree() #自检查



    def buildTree(self, leaves):
        leaves = [MerkleTreeNode(None, None, MerkleTreeNode.hash(e), e) for e in leaves]
        while len(leaves) > 1:
            length = len(leaves)
            for i in range(length // 2):
                left = leaves.pop(0)
                right = leaves.pop(0)
                value: str = MerkleTreeNode.hash(left.value + right.value)

                """
                print('left.value = ' + str(left.value))
                print('rigth.value = ' + str(right.value))
                print('left.value + right.value = ' + str(left.value + right.value))
                print('hash(L+R) = ' + str(MerkleTreeNode.hash(left.value + right.value)))
                print('value = ' + value)
                
                #test-9-22 for varify：
                #if len(leaves) == 2:

                #print('value:  ', value)
                #content: str = left.content + '+' + right.content
                """

                leaves.append(MerkleTreeNode(left, right, value))
            if length % 2 == 1:
                leaves.append(leaves.pop(0))
            #print('leaves')
            #print(leaves)
            #print()
        self.root = leaves[0]

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

if __name__ == "__main__":
    elems = ['1', '2', '3', '4']
    print('构造树')
    mtree = MerkleTree(elems)
    print('打印根哈希值')
    print("Root Hash: " + mtree.getRootHash() + "\n")
    print('打印默克尔树')
    mtree.printTree(mtree.root)

#elems = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
#print('构造树')
#mtree = MerkleTree(elems)
#print('打印根哈希值')
#print("Root Hash: " + mtree.getRootHash() + "\n")
#print('打印默克尔树')
#mtree.printTree(mtree.root)
