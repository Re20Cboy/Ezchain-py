#!/usr/bin/env python3

import unittest
from bloom import BloomFilter, BloomFilterEncoder
from block import Block
from Ezchain_simulate import EZsimulate
import json
import pickle
from Distributed_acc_node_i import DstAcc
import unit
import blockchain

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

class test_dst_acc(unittest.TestCase):
    def test_sort_and_get_positions(self):
        uuid = [5, 2, 9, 3, 7]
        positions = unit.sort_and_get_positions(uuid)
        print(positions) # [2, 0, 4, 1, 3] means that 5 in 2-th position, 2 in 0-th position, 9 in 4-th position, ...

class TestForkBlockchain(unittest.TestCase):
    def setUp(self):
        EZs = EZsimulate()
        # generate genesis block
        genesis_block = EZs.generate_GenesisBlock()
        self.fork_bc = blockchain.Blockchain(dst=True)
        # add genesis block
        self.fork_bc.add_block(genesis_block)

    def test_add_main_chain_block(self, add_round=5): # add block belong to main (longest) chain
        for i in range(add_round):
            new_index = self.fork_bc.get_latest_block_index() + 1
            new_pre_hash = self.fork_bc.get_latest_block().get_hash()
            # random generate a new block belong to main chain
            new_block = Block(index=new_index, m_tree_root='test_merkel_tree_root', miner='test_miner',
                              pre_hash=new_pre_hash)
            self.fork_bc.add_block(new_block)
        self.fork_bc.print_real_chain_dst(fork_block=self.fork_bc.real_chain)

    def test_longest_chain_is_vaild(self):
        if self.fork_bc.is_valid():
            print('longest chain is vaild.')
        else:
            print('longest chain is NOT vaild.')

    def test_add_fork_block(self, main_block_num=10, fork_num=3, block_num_in_one_fork=3):
        # init main chain
        for i in range(main_block_num):
            new_index = self.fork_bc.get_latest_block_index() + 1
            new_pre_hash = self.fork_bc.get_latest_block().get_hash()
            # random generate a new block belong to main chain
            new_block = Block(index=new_index, m_tree_root='test_merkel_tree_root', miner='test_miner',
                              pre_hash=new_pre_hash)
            self.fork_bc.add_block(new_block)
        # add fork block to main chain
        for i in range(fork_num):
            entry_block = self.fork_bc.chain[i]
            for j in range(block_num_in_one_fork):
                new_index = self.fork_bc.chain[i].get_index() + 1 + j
                new_pre_hash = entry_block.get_hash()
                new_block = Block(index=new_index, m_tree_root='test_merkel_tree_root', miner='test_miner',
                                  pre_hash=new_pre_hash)
                entry_block = new_block
                self.fork_bc.add_block(new_block)
        # print fork chain
        self.fork_bc.print_real_chain_dst(fork_block=self.fork_bc.real_chain)

    def test_add_fork_fork_block(self):
        pass

if __name__ == '__main__':
    unittest.main()