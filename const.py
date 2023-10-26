TNX_CSV_PATH = 'D:/EZchain-V2/Ezchain-py/300Txs.csv'
TNX_CSV_NUM = 300 #csv文件中交易的总数量

SAMPLE_NEIGHBORS_NUM = 5 #随机链接的邻居节点的数量

NODE_ACCOUNT_DELAY = 1.5 # node和acc之间的延迟
ACC_ACC_DELAY = 1.5 # acc和acc之间的延迟

NODE_NUM = 20 #模拟节点的数量
ACCOUNT_NUM = 20 #模拟账户数量

PICK_TXNS_NUM = int(ACCOUNT_NUM*ACCOUNT_NUM / 2) #一次打包的交易的数量，理论上不应当超过 ACCOUNT_NUM^2 / 2 （/2是因为随机时最少有ACCOUNT_NUM/ 2个账户参与交易）

SIMULATE_ROUND = 3 # 挖矿轮数

BANDWIDTH = 1024 * 1024 * 5 #网络带宽
HASH_DIFFICULTY = 0.0001 #挖矿难度，即，一次hash运算挖矿成功的概率
HASH_POWER = 100 #哈希算力，表示每秒钟执行的hash次数

FORK_SIMULATE_ROUND = 100

GENESIS_SENDER = '0x259'
GENESIS_MINER_ID = -1

NODE_PRIVATE_KEY_PATH = "node_private_key/"
NODE_PUBLIC_KEY_PATH = "node_public_key/"
ACCOUNT_PRIVATE_KEY_PATH = "account_private_key/"
ACCOUNT_PUBLIC_KEY_PATH = "account_public_key/"
