# Control random generate txns or not
RANDOM_TXNS = True

# The interval duration of transaction generation
TXN_GENERATE_GAP_TIME = 20

# Max fork height
MAX_FORK_HEIGHT = 3 # bitcoin's max fork height = 6

# Total number of transactions in the CSV file
TNX_CSV_NUM = 300

# Number of randomly connected neighbor nodes
SAMPLE_NEIGHBORS_NUM = 30

# Delay between node and account (in seconds)
NODE_ACCOUNT_DELAY = 1.5

# Delay between accounts (in seconds)
ACC_ACC_DELAY = 1.5

# Number of simulated nodes
NODE_NUM = 5
DST_NODE_NUM = 2

# Number of simulated accounts
ACCOUNT_NUM = 5
DST_ACC_NUM = 2

# Number of max packages in con node's txns pool
MAX_PACKAGES = 2

# parm for dst mine
ONE_HASH_TIME = 0.5
ONE_HASH_SUCCESS_RATE = 0.03

# Number of transactions to package at once, theoretically should not exceed ACCOUNT_NUM^2 / 2
# (/2 because at least ACCOUNT_NUM/2 accounts participate in transactions randomly)
PICK_TXNS_NUM = int(ACCOUNT_NUM * ACCOUNT_NUM / 2)

# Number of mining rounds
SIMULATE_ROUND = 10

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

# compute time of one round hash
D_ONE_HASH_TIME = 0.01

# print the info of new thread
PRINT_THREAD = False

# True = periodic block generation, False = mine-block mode
PERIOD_MODE = False
PERIOD_SLEEP_TIME = 10 # one block / PERIOD_SLEEP_TIME sec
