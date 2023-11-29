#!/usr/bin/env python3

import unittest
from bloom import BloomFilter
from block import Block

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

if __name__ == '__main__':
    unittest.main()

