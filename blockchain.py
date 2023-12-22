import block
import hashlib
from const import *

class ForkBlock: # unit of blockchain's fork
    def __init__(self):
        self.pre_block = None
        self.block = None
        self.next_blocks = []

    def find_pre_block_traversal_fork_blocks(self, block):
        if self.block.is_valid_next_block(block):
            return self
        else:
            if self.next_blocks != []:
                for next_block in self.next_blocks:
                    result = next_block.find_pre_block_traversal_fork_blocks(block)
                    if result:
                        return result
            else:
                return False
            return None

class ForkChain: # blockchain with fork
    def __init__(self):
        self.longest_chain = None
        self.fork_lst = []

    def find_pre_block_within_max_fork_height(self, block):
        # is in main chain?
        main_chain_index = self.longest_chain.get_latest_block_index()
        for i in range(min(MAX_FORK_HEIGHT, len(self.longest_chain))):
            if i == 0: # skip the latest block
                continue
            main_chain_index -= i
            if self.longest_chain.chain[main_chain_index].is_valid_next_block(block):
                # the pre block is in the main chain
                return self.longest_chain.chain[main_chain_index]

        for fork in self.fork_lst:
            # todo:
            pass



    def add_block(self, block):
        if self.longest_chain.is_valid_block(block):
            self.longest_chain.add_block(block)
        else: # fork block
            # todo:
            pass

    def flash_fork(self): # del old fork
        # todo:
        pass

class Blockchain:
    def __init__(self, GenesisBlock = None, dst=False): # dst means distribute simulate
        self.chain = []  # List to store blocks in the blockchain
        if not dst:
            if GenesisBlock is None:
                GenesisBlock = block.Block(index=0, m_tree_root=hash(0), miner=0, pre_hash=hash(0))
            self.chain.append(GenesisBlock)

    def add_block(self, block):
        self.chain.append(block)

    def get_latest_block(self):
        return self.chain[-1]

    def get_latest_block_hash(self):
        return self.chain[-1].get_hash()

    def get_latest_block_index(self):
        return self.chain[-1].get_index()

    def is_valid(self): #遍历链看所有块的hash链接是否正确
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            if current_block.pre_hash != previous_block.get_hash():
                return False
        return True

    def is_valid_block(self, block):
        if block.get_pre_hash() != self.get_latest_block_hash():
            return False
        if block.index != len(self.chain):
            return False
        return True

    def print_chain(self):
        print("///////////////// Blockchain /////////////////")
        for block in self.chain:
            print(f"Block {block.index}")
            print(f"Timestamp: {block.time}")
            print(f"Miner: {block.miner}")
            if block.index != 0:
                print(f"Previous Hash: {block.pre_hash}")
            else:
                print(f"Previous Hash: {block.pre_hash}")
            print(f"Merkle Tree Root: {block.m_tree_root}")
            print(f"Nonce: {block.nonce}")
            print(f"Bloom Filter Size: {len(block.bloom)}")
            print(f"Signature: {block.sig}")
            print("---------------------")