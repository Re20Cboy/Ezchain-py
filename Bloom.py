# -*- coding: utf-8 -*-#

# 提供二进制向量
from bitarray import bitarray
# 提供hash函数mmh3.hash()
import mmh3


class BloomFilter(set): #set是bloom的父类
    """
    size: 二进制向量长度
    hash_count: hash函数个数

    一般来说，hash函数的个数要满足（hash函数个数=二进制长度*ln2/插入的元素个数）
    """
    def __init__(self, size = 1024 * 1024, hash_count = 5): # hash_count的作用是确定使用多少个不同的哈希函数来插入和查询元素。
        super(BloomFilter, self).__init__() #调用父类set的构造函数
        self.bit_array = bitarray(size)
        self.bit_array.setall(0)
        self.size = size
        self.hash_count = hash_count # hash_count = size * ln(2) / num_elements，哈希函数的个数应该满足布隆过滤器的大小、预期的元素数量以及允许的误判率之间的关系
        #当size = 1024 * 1024 时，假设插入元素也为1024 * 1024，则hash_count推荐设置为：5
    def __len__(self):
        return self.size

    # 使得BloomFilter可迭代
    def __iter__(self):
        return iter(self.bit_array)

    def add(self, item):
        for ii in range(self.hash_count):
            # 假设hash完的值是22，size为20，那么取模结果为2，将二进制向量第2位置为1
            index = mmh3.hash(item, ii) % self.size
            self.bit_array[index] = 1

        return self

    # 可以使用 xx in BloomFilter方式来判断元素是否在过滤器内（有小概率会误判不存在的元素也存在, 但是已存在的元素绝对不会误判为不存在）
    def __contains__(self, item):
        out = True
        for ii in range(self.hash_count):
            index = mmh3.hash(item, ii) % self.size
            if self.bit_array[index] == 0:
                out = False

        return out