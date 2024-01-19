import os
import hashlib
import random
import copy
import transaction
import re

class txnsPool:
    def __init__(self):
        self.pool = [] # [[(accTxn's Digest, acc's sig for hash, acc's addr, acc's ID), ...], ...]
        self.sender_id = [] # list of acc nodes' uuid

    def freshPool(self, accounts, accTxns):
        # this func is used for NON-DST mode only
        for i in range(len(accTxns)):
            accTxns[i].sig_accTxn(accounts[i].privateKey) # 对accTxn进行签名
            self.pool.append(copy.deepcopy((accTxns[i].Digest, accTxns[i].Signature, accounts[i].addr, accounts[i].id)))

    def add_acc_txns_package_dst(self, acc_txns_package, uuid):
        # this func is designed for DST mode.
        # this func add the acc_txns_package & acc's uuid to self txns pool
        # the txns pool's form is :
        # self.sender_id = [uuid_1, uuid_2, uuid_3, ...]
        # self.pool = [[package_1_1, package_1_2, ...],[package_2_1, package_2_2, ...],[...], ...],
        # where package_i_j (j=1,2,3, ...) is sent by uuid_i.

        if self.sender_id == []:
            # no package recv, thus accept this package directly
            self.pool.append([acc_txns_package])
            self.sender_id.append(uuid)
        else:
            index_flag = None
            for index, send_uuid in enumerate(self.sender_id):
                if send_uuid == uuid:
                    index_flag = index
            if index_flag == None:
                # this uuid is new
                self.sender_id.append(uuid)
                self.pool.append([acc_txns_package])
            else:
                self.pool[index_flag].append(acc_txns_package)

    def get_packages_for_new_block_dst(self):
        # this func return a list of packages, which are built for the new block body
        lst_packages = []
        for acc_packages in self.pool:
            # pick the oldest package (i.e., acc_packages[0]), since it wait for the longest time.
            if acc_packages != []:
                # this acc_packages is not empty.
                lst_packages.append(acc_packages[0])
        return lst_packages

    def check_is_repeated_package(self, acc_txns_package, uuid):
        if self.txns_pool_is_empty():
            # if the pool is empty, this package must not be repeated.
            return False
        index_of_uuid = None
        for index, item in enumerate(self.sender_id):
            if item == uuid:
                index_of_uuid = index
        if index_of_uuid != None and self.pool[index_of_uuid] != []:
            for item in self.pool[index_of_uuid]:
                # item & acc_txns_package=(digest, sig, addr, global_id)
                if item[0] == acc_txns_package[0]:
                    return True
        return False

    def get_packages_num(self):
        return len(self.pool)

    def txns_pool_is_empty(self):
        if self.sender_id == []:
            return True
        for acc_packages in self.pool:
            if acc_packages != []:
                return False
        return True

    def clearPool(self):
        # this func is used for NON-DST mode
        self.pool = []
        self.sender_id = []

    def del_all_packages_in_pool(self):
        # this func del all packages in the txns pool,
        # but remains the send_id list.
        for acc_packages in self.pool:
            acc_packages.clear()

    def clear_pool_dst(self, acc_digests):
        # Logic of flash self txns pool:
        # if new block mined by other con node, self should delete the same package in local txns pool,
        # if self mine success, delete all package in the new block.

        # del_lst shape as {1:[1,3,6], 2:[3,5], ...}, where
        # 1:[1,3,6] means del self.pool[1][1], [1][3] and [1][6]

        del_lst = {}
        for acc_digest in acc_digests:
            for index_1, acc_packages in enumerate(self.pool):
                for index_2, acc_package in enumerate(acc_packages):
                    if acc_package[0] == acc_digest:
                        if index_1 in del_lst:
                            del_lst[index_1].append(index_2)
                        else:
                            del_lst[index_1] = [index_2]

        # reverse all del list, for correct delete
        for key, value in del_lst.items():
            del_lst[key] = reversed(value)

        # del the package in the pool
        for key, value in del_lst.items():
            if value != []:
                for del_index in value:
                    del self.pool[key][del_index]

    def print_tnxs_pool_dst(self):
        # show the txns pool
        for index, uuid in enumerate(self.sender_id):
            print(str(uuid) + ': ')
            print(self.pool[index])
            print('-----------')

class checkedVPBList:
    def __init__(self):
        self.VPBCheckPoints = []

    def findCKviaVPB(self, VPB):
        # Input VPB and check if the V of this VPB is included in the checkpoint.
        # Note that it should be an "inclusion" relationship (i.e., checkpoint includes this value).

        # todo: re-write this func in dst mode, when fork appear, which need more blocks to confirm a txn.
        #  the logic of find-ck should be re-build.

        value = VPB[0]
        returnList = []
        indexList = []
        if self.VPBCheckPoints != []:
            for index, ck in enumerate(self.VPBCheckPoints):
                # un-package this vpb-ck
                ckValue = ck[0]
                ckOwner = ck[1]
                ckBIndex = ck[2]
                # check inclusion relationship between ck and value
                if ckValue.isInValue(value):
                    returnList.append((ckOwner, ckBIndex))
                    indexList.append(index)
            if len(returnList) > 1:
                raise ValueError("more than 1 ck is found !!!")
        return returnList

    def fresh_local_vpb_check_point_dst(self, will_sent_vpb_pairs):
        for vpb in will_sent_vpb_pairs:
            value = vpb[0]
            valuePrf = vpb[1].prfList
            blockIndex = vpb[2]
            LatestPrfUnit = valuePrf[-1]
            LatestOwner = LatestPrfUnit.owner

            if self.VPBCheckPoints != []:
                newVPBCP = [value, LatestOwner, blockIndex]
                RestVPBCPs = None
                delIndex = None
                for index, VPBCP in enumerate(self.VPBCheckPoints, start=0):
                    V = VPBCP[0]
                    VOwner = VPBCP[1]
                    BIndex = VPBCP[2]
                    intersectValueReslut = V.getIntersectValue(value)
                    if intersectValueReslut != None:
                        # The value in the newly held VPB intersects with the original checkpoint (v)
                        # and needs to be processed before adding a checkpoint
                        if delIndex:
                            raise ValueError('delIndex Err: There are multiple delIndices!')
                        IntersectValue, RestValues = intersectValueReslut
                        delIndex = index
                        RestVPBCPs = []
                        if RestValues != []:
                            for item in RestValues:
                                tmpRestVPBCP = [item, VOwner, BIndex]
                                RestVPBCPs.append(tmpRestVPBCP)
                        break
                if RestVPBCPs != None:
                    # If RestVPBCPs=[], it means that the entire value
                    # needs to be updated without splitting the remaining parts
                    self.VPBCheckPoints.append(copy.deepcopy(newVPBCP))
                    for item in RestVPBCPs:
                        self.VPBCheckPoints.append(copy.deepcopy(item))
                    # Delete split check points
                    del self.VPBCheckPoints[delIndex]
                else:  # This value is completely "foreign", i.e., "first time seen".
                    self.VPBCheckPoints.append(copy.deepcopy(newVPBCP))
            else:  # Add the first batch of VPB checkpoints
                VPBCP = [value, LatestOwner, blockIndex]
                self.VPBCheckPoints.append(copy.deepcopy(VPBCP))


    def addAndFreshCheckPoint(self, VPBPairs):
        for VPB in VPBPairs:
            value = VPB[0]
            valuePrf = VPB[1].prfList
            blockIndex = VPB[2]
            LatestPrfUnit = valuePrf[-1]
            LatestOwner = LatestPrfUnit.owner

            if self.VPBCheckPoints != []:
                newVPBCP = [value, LatestOwner, blockIndex]
                RestVPBCPs = None
                delIndex = None
                for index, VPBCP in enumerate(self.VPBCheckPoints, start=0):
                    V = VPBCP[0]
                    VOwner = VPBCP[1]
                    BIndex = VPBCP[2]
                    intersectValueReslut = V.getIntersectValue(value)
                    if intersectValueReslut != None:  # 新一轮持有的VPB中的value 和 原有的检查点（v） 有交集，需要处理后加入检查点
                        if delIndex:
                            raise ValueError('delIndex Err: 有多数个delIndex！')
                        IntersectValue, RestValues = intersectValueReslut
                        delIndex = index
                        RestVPBCPs = []
                        if RestValues != []:
                            for item in RestValues:
                                tmpRestVPBCP = [item, VOwner, BIndex]
                                RestVPBCPs.append(tmpRestVPBCP)
                        break
                if RestVPBCPs != None:  # 若RestVPBCPs = []则说明整个值都要更新，没有拆分剩下的部分
                    self.VPBCheckPoints.append(copy.deepcopy(newVPBCP))
                    for item in RestVPBCPs:
                        self.VPBCheckPoints.append(copy.deepcopy(item))
                    # 删除被拆分的check points
                    del self.VPBCheckPoints[delIndex]
                else:  # 说明此值完全是“外来”，“第一次见到”。
                    self.VPBCheckPoints.append(copy.deepcopy(newVPBCP))

            else:  # 添加第一批VPB检查点
                VPBCP = [value, LatestOwner, blockIndex]
                self.VPBCheckPoints.append(copy.deepcopy(VPBCP))


class ProofUnit:  # 一个值在一个区块内的证明
    def __init__(self, owner, ownerAccTxnsList, ownerMTreePrfList):
        self.owner = owner
        self.ownerAccTxnsList = ownerAccTxnsList  # 在此区块内的ownTxns
        self.ownerMTreePrfList = ownerMTreePrfList  # ownTxns对应的mTreePrf

    def print_proof_unit(self):
        ownerMTreePrfList_str = ''
        for index, item in enumerate(self.ownerMTreePrfList):
            ownerMTreePrfList_str += '  ' + str(index) + ': ' + str(item) + '\n'
        print('owner: ' + str(self.owner) + '; ownerAccTxnsList: ' + str(self.ownerAccTxnsList))
        print('ownerMTreePrfList: ' + '\n' + ownerMTreePrfList_str)

class Proof:
    def __init__(self, prfList):
        self.prfList = prfList

    def add_prf_unit(self, prfUint):
        self.prfList.append(prfUint)

    def add_prf_unit_dst(self, prfUnit, add_position):
        self.prfList.insert(add_position, prfUnit)

    def get_latest_prf_unit_owner_dst(self):
        return self.prfList[-1].owner

    def print_proof(self):
        for index, item in enumerate(self.prfList):
            print('#'+str(index)+' prf_unit: ')
            item.print_proof_unit()
            print('--------------------')

class Value:  # 针对VCB区块链的专门设计的值结构，总量2^259 = 16^65
    def __init__(self, beginIndex, valueNum):  # beginIndex是16进制str，valueNum是10进制int
        # 值的开始和结束index都包含在值内
        self.beginIndex = beginIndex
        self.valueNum = valueNum
        self.endIndex = self.getEndIndex(beginIndex, valueNum)

    def print_value(self):
        print('value #begin:' + str(self.beginIndex))
        print('value #end:' + str(self.endIndex))
        print('value num:' + str(self.valueNum))

    def get_decimal_beginIndex(self):
        return int(self.beginIndex, 16)

    def get_decimal_endIndex(self):
        return int(self.endIndex, 16)

    def split_value(self, change):  # 对此值进行分割
        V1 = Value(self.beginIndex, self.valueNum - change)
        tmpIndex = hex(V1.get_decimal_endIndex() + 1)
        V2 = Value(tmpIndex, change)
        return V1, V2  # V2是找零

    def getEndIndex(self, beginIndex, valueNum):
        decimal_number = int(beginIndex, 16)
        result = decimal_number + valueNum - 1
        return hex(result)

    def checkValue(self):  # 检测Value的合法性
        def is_hexadecimal(string):
            pattern = r"^0x[0-9A-Fa-f]+$"
            return re.match(pattern, string) != None

        if self.valueNum <= 0:
            return False
        if not is_hexadecimal(self.beginIndex):
            return False
        if not is_hexadecimal(self.endIndex):
            return False
        if self.endIndex != self.getEndIndex(self.beginIndex, self.valueNum):
            return False
        return True

    def getIntersectValue(self, target):  # target是Value类型, 获取和target有交集的值的部分
        decimal_targetBegin = int(target.beginIndex, 16)
        decimal_targetEnd = int(target.endIndex, 16)
        decimal_beginIndex = self.get_decimal_beginIndex()
        decimal_endIndex = self.get_decimal_endIndex()
        IntersectBegin = max(decimal_targetBegin, decimal_beginIndex)
        IntersectEnd = min(decimal_targetEnd, decimal_endIndex)
        if IntersectBegin <= IntersectEnd:
            IntersectValueNum = IntersectEnd - IntersectBegin + 1
            tmp1 = IntersectBegin - decimal_beginIndex
            tmp2 = decimal_endIndex - IntersectEnd
            IntersectValue = Value(hex(IntersectBegin), IntersectValueNum)
            RestValues = []
            if tmp1 != 0:
                if tmp2 != 0:
                    tmpV1 = Value(hex(decimal_beginIndex), tmp1)
                    tmpV2 = Value(hex(IntersectEnd + 1), tmp2)
                    RestValues.append(tmpV1)
                    RestValues.append(tmpV2)
                else:  # tmp1 != 0; tmp2 = 0
                    tmpV1 = Value(hex(decimal_beginIndex), tmp1)
                    RestValues.append(tmpV1)
            else:  # tmp1 = 0
                if tmp2 != 0:
                    tmpV2 = Value(hex(IntersectEnd + 1), tmp2)
                    RestValues.append(tmpV2)
                else:  # tmp1 = 0; tmp2 = 0
                    pass
            return (IntersectValue, RestValues)
        else:
            return None

    def isIntersectValue(self, target):  # target是Value类型, 判断target是否和本value有交集
        decimal_targetBegin = int(target.beginIndex, 16)
        decimal_targetEnd = int(target.endIndex, 16)
        decimal_beginIndex = self.get_decimal_beginIndex()
        decimal_endIndex = self.get_decimal_endIndex()
        if decimal_endIndex >= decimal_targetBegin:
            if decimal_targetEnd >= decimal_beginIndex:
                return True
        return False
        # return ((decimal_endIndex >= decimal_targetBegin) and (decimal_targetEnd >= decimal_beginIndex))

    def isInValue(self, target):  # target是Value类型, 判断target是否在本value内
        decimal_targetBegin = int(target.beginIndex, 16)
        decimal_targetEnd = int(target.endIndex, 16)
        decimal_beginIndex = self.get_decimal_beginIndex()
        decimal_endIndex = self.get_decimal_endIndex()
        return decimal_targetBegin >= decimal_beginIndex and decimal_targetEnd <= decimal_endIndex

    def isSameValue(self, target):  # target是Value类型, 判断target是否就是本value
        if type(target) != Value:
            print('ERR: func isSameValue get illegal input!')
            return False
        if target.beginIndex == self.beginIndex and target.endIndex == self.endIndex and target.valueNum == self.valueNum:
            return True
        else:
            return False


class MTreeProof:
    def __init__(self, MTPrfList=[]):
        self.MTPrfList = MTPrfList

    def checkPrf(self, accTxnsDigest, trueRoot):  # accTxns为待检查的账户交易集合. trueRoot是公链上的mTree root信息
        def hash(val):
            if type(val) == str:
                return hashlib.sha256(val.encode("utf-8")).hexdigest()
            else:
                return hashlib.sha256(val).hexdigest()

        # check_flag is used for de-bug
        check_flag = True
        hashedEncodeAccTxns = hash(accTxnsDigest)

        if len(self.MTPrfList) == 1:
            # this mTree proof only includes one acc_txn
            if (hashedEncodeAccTxns != self.MTPrfList[0] or trueRoot != self.MTPrfList[0] or
                    trueRoot != hashedEncodeAccTxns):
                check_flag = False
            return check_flag

        if hashedEncodeAccTxns != self.MTPrfList[0] and hashedEncodeAccTxns != self.MTPrfList[1]:
            check_flag = False
            #return False
        if self.MTPrfList[-1] != trueRoot:
            check_flag = False
            #return False
        lastHash = None
        for i in range(len(self.MTPrfList) // 2):
            lastHash = self.MTPrfList[2 * i + 2]
            if hash(self.MTPrfList[2 * i] + self.MTPrfList[2 * i + 1]) != lastHash and hash(
                    self.MTPrfList[2 * i + 1] + self.MTPrfList[2 * i]) != lastHash:
                check_flag = False
                #return False
        if lastHash != self.MTPrfList[-1]:
            check_flag = False
            #return False
        return check_flag
        #return True


class MerkleTreeNode:
    def __init__(self, left, right, value, content=None, path=[], leafIndex=None):
        self.left = left
        self.right = right
        self.value = value
        self.content = content
        self.path = path
        self.leafIndex = leafIndex  # 叶子节点的编号，用于跟踪叶子节点，便于制造prfList
        self.father = None  # 用于记录节点的父亲节点

    def hash(val): # val is self
        # return hashlib.sha256(val.encode("utf-8")).hexdigest()
        if type(val) == str:
            return hashlib.sha256(val.encode("utf-8")).hexdigest()
        else:
            return hashlib.sha256(val).hexdigest()

    def __str__(self):
        return (str(self.value))


class MerkleTree:
    def __init__(self, values, isGenesisBlcok=False):
        self.leaves = []
        self.prfList = None  # 这里的prf是针对每轮每个参与交易的account产生一个proof list
        self.buildTree(values, isGenesisBlcok)

    def buildTree(self, leaves, isGenesisBlcok):
        leaves = [MerkleTreeNode(None, None, MerkleTreeNode.hash(e), e, leafIndex=index) for index, e in
                enumerate(leaves, start=0)]

        for item in leaves:
            self.leaves.append(item)  # 记录叶子节点的备份

        if isGenesisBlcok:
            self.root = leaves[0]  # 创世块的仅记录树根信息
            return
        OrgLeavesLen = len(leaves)  # 原始AccTxns的长度
        popLeaveNum = 0  # 记录生成mTree时pop了多少叶子节点
        PrfList = []  # 记录mTree的生成路径用于追踪以生成prf

        while len(leaves) > 1:
            length = len(leaves)
            for i in range(length // 2):
                if leaves[0].content != None:  # 是叶子节点
                    leaves[0].path = [popLeaveNum]  # 用.append添加会造成所有节点的path都同步变化！！# 可能是python的指针机制导致的
                    popLeaveNum += 1
                left = leaves.pop(0)
                if leaves[0].content != None:  # 是叶子节点
                    leaves[0].path = [popLeaveNum]
                    popLeaveNum += 1
                right = leaves.pop(0)
                value: str = MerkleTreeNode.hash(left.value + right.value)
                comPath = left.path + right.path
                left.path = comPath
                right.path = comPath
                newMTreeNode = MerkleTreeNode(left, right, value, path=comPath)
                left.father = newMTreeNode  # 添加父节点信息
                right.father = newMTreeNode  # 添加父节点信息
                leaves.append(newMTreeNode)
            if length % 2 == 1:
                leaves.append(leaves.pop(0))

        self.root = leaves[0]

        # 对每个accTxns生成对应的的proof trace
        tmpList = []
        for i in range(OrgLeavesLen):  # 添加root节点到所有prflist中
            PrfList.append(copy.deepcopy(tmpList))

        def addUnitPrfList(tmpPrfList, nowNode, roundIndex):
            father = nowNode.father
            fatherRightChild = father.right
            fatherLeftChild = father.left
            anotherChild = None
            if fatherRightChild == nowNode:
                anotherChild = fatherLeftChild
            if fatherLeftChild == nowNode:
                anotherChild = fatherRightChild
            tmpPrfList[roundIndex].append(anotherChild.value)
            tmpPrfList[roundIndex].append(father.value)

        for leaf in self.leaves:
            # 添加叶子节点
            PrfList[leaf.leafIndex].append(leaf.value)
            nowNode = leaf
            while nowNode != self.root:
                addUnitPrfList(tmpPrfList=PrfList, nowNode=nowNode, roundIndex=leaf.leafIndex)
                nowNode = nowNode.father

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

    # 测试mTree的叶子节点数
    def find_leaves_num(self, node):  # 调用时赋node = self.root
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
            print("")
            self.printTree(node.left)
            self.printTree(node.right)

    def getRootHash(self) -> str:
        return self.root.value

    def checkTree(self, node=None):
        if node is None:
            node = self.root
        if node.left != None and node.right != None:  # 不是叶子节点
            # tmp = MerkleTreeNode.hash(node.left.value + node.right.value)
            # tmp2 = node.value
            if node.value != MerkleTreeNode.hash(node.left.value + node.right.value):
                return False
            else:
                return (self.checkTree(node=node.left) and self.checkTree(node=node.right))
        else:  # 是叶子节点
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


def generate_random_hex(length):
    hex_digits = "0123456789ABCDEF"
    hex_number = "0x"
    for _ in range(length):
        hex_number += random.choice(hex_digits)
    return hex_number


def sort_and_get_positions(A):
    sorted_A = sorted(A)
    positions = [sorted_A.index(x) for x in A]
    return positions

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
    print("v_begin:" + v_begin)
    v_num = 777
    print("v_num:" + str(v_num))
    v = Value(v_begin, v_num)
    print("v_end:" + v.endIndex)
    traget_num = 9999
    t = Value(v.getEndIndex(v.endIndex, 0), traget_num)
    flag1 = v.checkValue()
    flag2 = v.isInValue(t)
    print("flag1:" + str(flag1))
    print("flag2:" + str(flag2))

# elems = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
# print('构造树')
# mtree = MerkleTree(elems)
# print('打印根哈希值')
# print("Root Hash: " + mtree.getRootHash() + "\n")
# print('打印默克尔树')
# mtree.printTree(mtree.root)
