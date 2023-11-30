# Total number of transactions in the CSV file
TNX_CSV_NUM = 300

# Number of randomly connected neighbor nodes
SAMPLE_NEIGHBORS_NUM = 30

# Delay between node and account (in seconds)
NODE_ACCOUNT_DELAY = 1.5

# Delay between accounts (in seconds)
ACC_ACC_DELAY = 1.5

# Number of simulated nodes
NODE_NUM = 70

# Number of simulated accounts
ACCOUNT_NUM = 120

# Number of transactions to package at once, theoretically should not exceed ACCOUNT_NUM^2 / 2
# (/2 because at least ACCOUNT_NUM/2 accounts participate in transactions randomly)
PICK_TXNS_NUM = int(ACCOUNT_NUM * ACCOUNT_NUM / 2)

# Number of mining rounds
SIMULATE_ROUND = 4

# Network bandwidth (bytes)
BANDWIDTH = 1024 * 1024 * 1

# Mining difficulty, i.e., the probability of successful mining in one hash operation
HASH_DIFFICULTY = 0.0005

# Hash power, indicating the number of hash operations per second
HASH_POWER = 100

# Number of rounds for fork simulation
FORK_SIMULATE_ROUND = 100

# Genesis block sender address
GENESIS_SENDER = '0x259'

# Genesis block miner ID
GENESIS_MINER_ID = -1

# Path to store node private keys
NODE_PRIVATE_KEY_PATH = "node_private_key/"

# Path to store node public keys
NODE_PUBLIC_KEY_PATH = "node_public_key/"

# Path to store account private keys
ACCOUNT_PRIVATE_KEY_PATH = "account_private_key/"

# Path to store account public keys
ACCOUNT_PUBLIC_KEY_PATH = "account_public_key/"
