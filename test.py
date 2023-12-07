#!/usr/bin/env python3

import unittest
from bloom import BloomFilter, BloomFilterEncoder
from block import Block
from Distributed_con_node import ConNode
from Ezchain_simulate import EZsimulate
import json
import pickle

class TestBloomFilter(unittest.TestCase):
    def setUp(self):
        self.bloom_filter = BloomFilter(size=1024 * 1024, hash_count=5)

    def test_add_and_check(self):
        item = "test_item"
        self.bloom_filter.add(item)
        self.assertIn(item, self.bloom_filter)

    def test_nonexistent_item(self):
        self.assertNotIn("nonexistent_item", self.bloom_filter)

    def test_false_positive_rate(self):
        items_added = {"item1", "item2", "item3"}
        for item in items_added:
            self.bloom_filter.add(item)

        false_positives = 0
        for i in range(1000):
            item = f"test{i}"
            if item not in items_added and item in self.bloom_filter:
                false_positives += 1

        expected_false_positive_rate = 0.01  # Adjust based on your requirements
        actual_false_positive_rate = false_positives / 1000
        self.assertLessEqual(actual_false_positive_rate, expected_false_positive_rate)
    def test_bloom_to_json(self):
        bloom_filter = BloomFilter()
        # Convert BloomFilter instance to JSON
        serialized_bloom_filter = json.dumps(bloom_filter, cls=BloomFilterEncoder, indent=4)
        print(serialized_bloom_filter)
class TestBlock(unittest.TestCase):

    def setUp(self):
        # Initialize a Block instance for testing
        self.block = Block(index=1, m_tree_root="root", miner="miner_id", pre_hash="000000")

    def test_block_creation(self):
        # Test if the block is created with the correct attributes
        self.assertEqual(self.block.index, 1)
        self.assertEqual(self.block.m_tree_root, "root")
        self.assertEqual(self.block.miner, "miner_id")
        self.assertEqual(self.block.pre_hash, "000000")
        # Additional checks for other attributes can be added here

    def test_block_to_string(self):
        # Test if the block's string representation is correct
        block_str = self.block.block_to_str()
        self.assertIn("Index: 1", block_str)
        self.assertIn("Merkle Tree Root: root", block_str)
        # Additional checks for the string representation of other attributes

    def test_bloom_filter_integration(self):
        # Test the integration of the Bloom Filter in the block
        # Ensure that an item can be added and checked within the Bloom Filter
        item = "test_item"
        self.block.add_item_to_bloom(item)
        self.assertTrue(self.block.is_in_bloom(item))
        self.assertFalse(self.block.is_in_bloom("nonexistent_item"))

    def test_block_hash(self):
        # Test if the hash of the block is generated correctly
        block_hash = self.block.get_hash()
        self.assertIsNotNone(block_hash)
        # Further checks can be added to verify the format of the generated hash

class TestDConNode(unittest.TestCase):
    def init_con_node(self):
        # 初始化一些必要的用于test的信息，输入到con node中
        pass
    def test_create_new_block_body(self):
        # creat a new con node
        con_node = ConNode()

        # creat a new txn pool
        # random creat acc node
        EZs = EZsimulate()
        EZs.random_generate_accounts()
        # 根据账户生成创世块（给每个账户分发token）
        EZs.generate_GenesisBlock()
        # 账户节点随机生成交易（可能有一些账户没有交易，因为参加交易的账户的数量是随机的）
        EZs.AccTxns, ACTxnsRecipientList = EZs.random_generate_AccTxns()
        for i in range(len(EZs.AccTxns)):
            EZs.accounts[i].accTxns = EZs.AccTxns[i]
            EZs.accounts[i].recipientList = ACTxnsRecipientList[i]
        # 更新交易池
        EZs.txnsPool.freshPool(EZs.accounts, EZs.AccTxns)
        # set con node's txnpool
        con_node.set_txnsPool(EZs.txnsPool)
        # Node打包收集所有交易形成区块body（可以理解为简单的打包交易）
        con_node.create_new_block_body()

        print(str(con_node.tmpBlockBodyMsg))
        return con_node

    def test_create_new_block(self):
        # create a con node with a new block body
        con_node = self.test_create_new_block_body()
        # test: con node create new block via block body
        new_block = con_node.create_new_block()
        new_block.print_block()
        return con_node, new_block

    def test_get_block_from_json(self):
        con_node, new_block = self.test_create_new_block()
        # pickle block
        pickled_block = new_block.block_to_pickle()
        # rebuild block
        re_block = con_node.get_block_from_pickle(pickled_block)
        # print rebuild block
        re_block.print_block()
class simulate_env_4_con_node(unittest.TestCase):
    def save_data_to_file(self, data, filename):
        with open(filename, 'wb') as file:
            pickle.dump(data, file)

    def load_data_from_file(self, filename):
        with open(filename, 'rb') as file:
            data = pickle.load(file)
        return data
    def test_generate_random_genesis_block_and_EZ(self):
        # init genesis block
        EZs = EZsimulate()
        EZs.random_generate_accounts()
        # 根据账户生成创世块（给每个账户分发token）
        genesis_block = EZs.generate_GenesisBlock()
        # save genesis_block & EZs
        self.save_data_to_file(genesis_block, 'genesis_block_data.pkl')
        self.save_data_to_file(EZs, 'EZs_data.pkl')
        return (genesis_block, EZs)

    def test_read_genesis_block_and_EZ(self):
        # read genesis_block & EZs
        loaded_genesis_block = self.load_data_from_file('genesis_block_data.pkl')
        loaded_EZs = self.load_data_from_file('EZs_data.pkl')
        return (loaded_genesis_block, loaded_EZs)


if __name__ == '__main__':
    unittest.main()

