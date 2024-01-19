import block
import hashlib
from const import *


def find_pre_block_traversal_fork_blocks(root, block):
    if root is None:
        return None
    if root.block.is_valid_next_block_dst(block):
        return root
    if root.next_blocks == []:
        return None
    for next_block in root.next_blocks:
        result = find_pre_block_traversal_fork_blocks(next_block, block)
        if result is not None:
            return result
    return None

class ForkBlock: # unit of blockchain's fork
    def __init__(self, block):
        self.pre_block = None
        self.block = block
        self.next_blocks = []

class Blockchain:
    def __init__(self, GenesisBlock = None, dst=False): # dst means distribute simulate
        self.chain = []  # lst of longest chain
        self.dst = dst # flag of DST mode
        self.real_chain = None # chain with fork (only available in DST mode)
        self.latest_fork_block = None # mark the latest block in longest chain
        if not dst:
            if GenesisBlock is None:
                GenesisBlock = block.Block(index=0, m_tree_root=hash(0), miner=0, pre_hash=hash(0))
            self.chain.append(GenesisBlock)

    def add_to_longest_chain(self, block):
        if self.chain[-1].get_hash() != block.get_pre_hash() or self.chain[-1].get_index() + 1 != block.get_index():
            raise ValueError('add to longest chain FAIL!')
        self.chain.append(block)

    def add_to_real_chain(self, pre_fork_block, fork_block):
        if pre_fork_block.block.get_hash() != fork_block.block.get_pre_hash() or pre_fork_block.block.get_index() + 1 != fork_block.block.get_index():
            raise ValueError('add to real chain FAIL!')
        fork_block.pre_block = pre_fork_block
        pre_fork_block.next_blocks.append(fork_block)

    def get_latest_confirmed_block_index(self):
        # get the index of latest confirmed block chain
        latest_block_index = self.get_latest_block_index()
        confirmed_latest_block_index = latest_block_index - MAX_FORK_HEIGHT + 1
        if confirmed_latest_block_index > 0:
            return confirmed_latest_block_index
        # if no block has been confirmed, return None
        return None


    def add_block(self, block):
        if not self.dst: # ez simulate mode
            self.chain.append(block)
        else: # DST mode
            # set longest chain flash flag
            longest_chain_flash_flag = False
            # make fork block
            fork_block = ForkBlock(block)
            # genesis block
            if block.index == 0 and self.chain == [] and self.real_chain == None and self.latest_fork_block == None:
                self.chain.append(block)
                self.latest_fork_block = fork_block
                self.real_chain = fork_block
                longest_chain_flash_flag = True
            # non-genesis block
            else:
                # new block match the longest chain
                if fork_block.block.get_pre_hash() == self.get_latest_block_hash():
                    # check latest_fork_block and longest chain
                    if self.latest_fork_block.block.get_hash() != self.get_latest_block().get_hash():
                        raise ValueError('latest_fork_block and longest chain NOT match!')
                    # is the longest chain's next block
                    # add block to longest chain
                    self.add_to_longest_chain(block)
                    # add fork block to fork chain
                    self.add_to_real_chain(self.latest_fork_block, fork_block)
                    # flash latest fork block
                    self.latest_fork_block = fork_block
                    # flash flag
                    longest_chain_flash_flag = True
                else: # new block NOT match the longest chain
                    print('may FORK...')
                    try:
                        pre_fork_block = find_pre_block_traversal_fork_blocks(root=self.real_chain, block=block)
                    except Exception as e:
                        print(f'ERR in find_pre_block_traversal_fork_blocks: {e}')
                    if pre_fork_block == None:
                        raise ValueError('NOT find pre fork block!')
                    # add fork block to fork chain
                    self.add_to_real_chain(pre_fork_block, fork_block)
                    # is longest chain needs to be flashed ?
                    if fork_block.block.get_index() > self.get_latest_block_index():
                        self.flash_longest_chain(fork_block)
                        self.latest_fork_block = fork_block
                        # flash flag
                        longest_chain_flash_flag = True
            return longest_chain_flash_flag

    def flash_longest_chain(self, entry_fork_block):
        tmp_pre_block = entry_fork_block.pre_block
        block_lst_need_to_add = [entry_fork_block.block]
        while tmp_pre_block.block not in self.chain:
            block_lst_need_to_add.append(tmp_pre_block.block)
            tmp_pre_block = tmp_pre_block.pre_block
        # the unchanged latest block's index
        unchanged_index = tmp_pre_block.block.get_index()
        # cut longest chain
        self.chain = self.chain[:unchanged_index+1]
        # reverse order of block_lst_need_to_add
        block_lst_need_to_add.reverse()
        # add new chain part
        for new_block in block_lst_need_to_add:
            self.add_to_longest_chain(new_block)

    def find_fork_block_via_block_hash_dst(self, block_hash, root):
        # traversal fork chain to find aim fork block
        # root is genesis block in fork chain
        if root is None:
            return None
        if root.block.get_hash() == block_hash:
            return root.block
        if root.next_blocks == []:
            return None
        for next_block in root.next_blocks:
            result = self.find_fork_block_via_block_hash_dst(block_hash=block_hash, root=next_block)
            if result is not None:
                return result
        return None

    def find_block_via_block_hash_dst(self, block_hash):
        # fast find aim block in longest chain,
        # if not find, then traversal fork chain.
        latest_block_index = self.get_latest_block_index()
        index = 0
        # check this block hash is in longest chain
        while latest_block_index-index >= 0:
            if self.chain[latest_block_index-index].get_hash() == block_hash:
                return self.chain[latest_block_index-index]
            else:
                index += 1
        # check this block hash is in fork chain
        return self.find_fork_block_via_block_hash_dst(block_hash=block_hash, root=self.real_chain)

    def check_block_hash_is_in_longest_chain(self, block_hash):
        latest_block_index = self.get_latest_block_index()
        index = 0
        # check this block hash is in longest chain
        while latest_block_index - index >= 0:
            if self.chain[latest_block_index - index].get_hash() == block_hash:
                return latest_block_index - index
            else:
                index += 1
        return False

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

    def print_real_chain_dst(self, fork_block=None, indent=0): # for DST mode only
        print('-' * indent + 'Index: ' + str(fork_block.block.get_index()) + ', Block: ' + str(fork_block))
        if fork_block.next_blocks != []:
            for next_fork_block in fork_block.next_blocks:
                self.print_real_chain_dst(next_fork_block, indent + 2)

    def print_longest_chain_hash_lst_dst(self):
        # print the hash of block in the longest chain
        print('-------------longest chain-------------')
        for index, block in enumerate(self.chain):
            print('block #'+str(index)+' : '+block.get_hash())
        print('-------------longest chain-------------')

    def print_latest_block_hash_lst_dst(self):
        # print the hash of block in the longest chain
        print('-------------latest block-------------')
        print('block #'+str(self.get_latest_block_index())+' : '+self.get_latest_block_hash())