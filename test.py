#!/usr/bin/env python3

import unittest
import socket
from unittest.mock import patch, MagicMock
from bloom import BloomFilter, BloomFilterEncoder
from block import Block
from Ezchain_simulate import EZsimulate
import json
import pickle
from Distributed_acc_node_i import DstAcc
import unit
import blockchain
import random

from p2p_network import send_tcp_message 

class TestTcpDial(unittest.TestCase):
    @patch('p2p_network.socket.create_connection')
    def test_tcp_dial_successful(self, mock_create_connection):
        # Mock the socket connection
        mock_conn = MagicMock()
        mock_create_connection.return_value = mock_conn

        # Test data
        test_addr = '192.168.2.1'
        test_context = b'test message'

        # Call the function
        status = send_tcp_message(test_context, test_addr)
        print(f"\nstatus is {status}")

        # Assert connection was created and message was sent
        mock_create_connection.assert_called_with((test_addr, 80))
        mock_conn.sendall.assert_called_with(test_context + b'\n')


    @patch('p2p_network.socket.create_connection')
    def test_tcp_dial_connection_error(self, mock_create_connection):
        # Simulate a connection error
        mock_create_connection.side_effect = socket.error("Mocked connection error")

        # Test data
        test_addr = '127.0.0.1'
        test_context = b'test message'

        # Call the function and assert it handles the error
        with self.assertLogs(level='ERROR') as cm:
            send_tcp_message(test_context, test_addr)
        
        # Check if appropriate error log is created
        self.assertIn('Connection error', cm.output[0])


    @patch('p2p_network.socket.create_connection', return_value=MagicMock())
    def test_tcp_dial_send_error(self, mock_create_connection):
        # Simulate a send error
        mock_conn = MagicMock()
        mock_conn.sendall.side_effect = socket.error("Mocked send error")
        mock_create_connection.return_value = mock_conn

        # Test data
        test_addr = '127.0.0.1'
        test_context = b'test message'

        # Call the function and assert it handles the error
        with self.assertLogs(level='ERROR') as cm:
            send_tcp_message(test_context, test_addr)

        # Check if appropriate error log is created
        self.assertIn('Error sending data', cm.output[0])

@unittest.skip("Skipping all tests in TestBloomFilter")
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

@unittest.skip("Skipping all tests in test dst")
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

    def flash_fork_bc(self):
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
        # init parm for next test
        random_longest_chain_block_hash = None
        random_fork_chain_block_hash = None
        random_longest_flag = random.randint(1, main_block_num) # create random test block index in longest chain
        random_fork_flag_1 = random.randint(0, fork_num-1) # create random test fork index
        random_fork_flag_2 = random.randint(0, block_num_in_one_fork-1) # create random test block index in fork chain

        # init main chain
        for i in range(main_block_num):
            new_index = self.fork_bc.get_latest_block_index() + 1
            new_pre_hash = self.fork_bc.get_latest_block().get_hash()
            # random generate a new block belong to main chain
            # ***: miner='test_miner_'+str(i), where str(i) can avoid same block hash
            new_block = Block(index=new_index, m_tree_root='test_merkel_tree_root', miner='test_miner_'+str(i),
                              pre_hash=new_pre_hash)
            self.fork_bc.add_block(new_block)
            # create test block hash for next test
            if i+1 == random_longest_flag:
                print('ans of longest chain block: ' + str(new_block))
                random_longest_chain_block_hash = new_block.get_hash()
                print('ans of hash: ' + str(random_longest_chain_block_hash))
        # add fork block to main chain
        for i in range(fork_num):
            pre_block_hash = self.fork_bc.chain[i].get_hash()
            for j in range(block_num_in_one_fork):
                new_index = self.fork_bc.chain[i].get_index() + 1 + j
                # ***: miner='test_miner_'+str(i)+str(j), where str(i) can avoid same block hash
                new_block = Block(index=new_index, m_tree_root='test_merkel_tree_root', miner='test_miner_'+str(i)+str(j),
                                  pre_hash=pre_block_hash)
                pre_block_hash = new_block.get_hash()
                self.fork_bc.add_block(new_block)
                if i == random_fork_flag_1 and j == random_fork_flag_2:
                    print('ans of fork chain block: ' + str(new_block))
                    random_fork_chain_block_hash = new_block.get_hash()
                    print('ans of hash: ' + str(random_fork_chain_block_hash))
        # print fork chain
        self.fork_bc.print_real_chain_dst(fork_block=self.fork_bc.real_chain)
        # return generated fork chain
        return self.fork_bc, random_longest_chain_block_hash, random_fork_chain_block_hash, random_longest_flag, random_fork_flag_1, random_fork_flag_2

    def test_add_fork_fork_block(self):
        pass

    def test_find_fork_block_via_block_hash_dst(self, main_block_num=10, fork_num=3, block_num_in_one_fork=3):
        # generate blockchain and random block hash for test
        fork_bc, random_longest_chain_block_hash, random_fork_chain_block_hash, random_longest_flag, random_fork_flag_1, random_fork_flag_2 = (
            self.test_add_fork_block(main_block_num, fork_num, block_num_in_one_fork))
        result_fork_chain_block = fork_bc.find_fork_block_via_block_hash_dst(block_hash=random_fork_chain_block_hash,root=fork_bc.real_chain)
        # print result
        print("-------------------")
        print("ANS: random_fork_chain_block_hash = " + str(random_fork_chain_block_hash))
        print("random_fork_1 = " + str(random_fork_flag_1) + " and random_fork_flag_2 = " + str(random_fork_flag_2))
        print("result_fork_chain_block: " + str(result_fork_chain_block))
        print("and its hash = " + str(result_fork_chain_block.get_hash()))

    def test_find_block_via_block_hash_dst(self, main_block_num=10, fork_num=3, block_num_in_one_fork=3):
        # generate blockchain and random block hash for test
        fork_bc, random_longest_chain_block_hash, random_fork_chain_block_hash, random_longest_flag, random_fork_flag_1, random_fork_flag_2 = (
            self.test_add_fork_block(main_block_num, fork_num, block_num_in_one_fork))
        result_longest_chain_block = fork_bc.find_block_via_block_hash_dst(random_longest_chain_block_hash)
        result_fork_chain_block = fork_bc.find_block_via_block_hash_dst(random_fork_chain_block_hash)
        # print result
        print("-------------------")
        print("ANS: random_longest_chain_block_hash = " + str(random_longest_chain_block_hash))
        print("random_longest_flag = " + str(random_longest_flag))
        print("result_longest_chain_block: "+str(result_longest_chain_block))
        print("and its hash = " + str(result_longest_chain_block.get_hash()))
        print("-------------------")
        print("ANS: random_fork_chain_block_hash = " + str(random_fork_chain_block_hash))
        print("random_fork_1 = " + str(random_fork_flag_1) + " and random_fork_flag_2 = " + str(random_fork_flag_2))
        print("result_fork_chain_block: " + str(result_fork_chain_block))
        print("and its hash = " + str(result_fork_chain_block.get_hash()))

    def test_check_block_hash_is_in_longest_chain(self, main_block_num=10, fork_num=2, block_num_in_one_fork=2):
        # generate blockchain and random block hash for test
        for _ in range(100):
            fork_bc, random_longest_chain_block_hash, random_fork_chain_block_hash, random_longest_flag, random_fork_flag_1, random_fork_flag_2 = (
                self.test_add_fork_block(main_block_num, fork_num, block_num_in_one_fork))
            result_longest_chain_block = fork_bc.check_block_hash_is_in_longest_chain(random_longest_chain_block_hash)
            result_fork_chain_block = fork_bc.check_block_hash_is_in_longest_chain(random_fork_chain_block_hash)
            #print("random_longest_flag = " + str(random_longest_flag))
            #print("result_longest_chain_block = " + str(result_longest_chain_block))
            #print("random_fork_1 = " + str(random_fork_flag_1) + " and random_fork_flag_2 = " + str(random_fork_flag_2))
            #print("result_fork_chain_block = " + str(result_fork_chain_block))
            if result_longest_chain_block == False or result_fork_chain_block != False:
                print("random_longest_flag = " + str(random_longest_flag))
                print("result_longest_chain_block = " + str(result_longest_chain_block))
                print("random_fork_1 = " + str(random_fork_flag_1) + " and random_fork_flag_2 = " + str(random_fork_flag_2))
                print("result_fork_chain_block = " + str(result_fork_chain_block))
                break
            self.flash_fork_bc()

if __name__ == '__main__':
    unittest.main()