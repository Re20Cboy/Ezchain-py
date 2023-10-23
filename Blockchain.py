import Block

class Blockchain:
    def __init__(self, GenesisBlock = None):
        self.chain = []  # List to store blocks in the blockchain
        if GenesisBlock is None:
            GenesisBlock = Block.Block(index=0, mTreeRoot=hash(0), miner=0, prehash=hash(0))
        self.chain.append(GenesisBlock)

    def add_block(self, block):
        self.chain.append(block)

    def get_latest_block(self):
        return self.chain[-1]

    def get_latest_block_hash(self):
        return self.chain[-1].get_hash()

    def is_valid(self): #遍历链看所有块的hash链接是否正确
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            if current_block.preHash != previous_block.get_hash():
                return False
        return True

    def print_chain(self):
        print("///////////////// Blockchain /////////////////")
        for block in self.chain:
            print(f"Block {block.index}")
            print(f"Timestamp: {block.time}")
            print(f"Miner: {block.miner}")
            print(f"Previous Hash: {str(block.preHash)}")
            print(f"Merkle Tree Root: {block.mTreeRoot}")
            print(f"Nonce: {block.nonce}")
            print(f"Bloom Filter Size: {len(block.bloom)}")
            print(f"Signature: {block.sig}")
            print("---------------------")