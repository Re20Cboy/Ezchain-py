import random
import string
# 使用ECC椭圆密码
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import datetime
import unit
import Transaction

class Account:
    def __init__(self):
        self.addr = None
        self.privateKey = None
        self.publicKey = None
        self.ValuePrfPair = [] # 当前账户拥有的值和对应的证据对
        # self.prfChain = [] # 此账户所有证明的集合，即，公链上所有和本账户相关的prf集合
        self.bloomPrf = [] # 被bloom过滤器“误伤”时，提供证据（哪些账户可以生成此bloom）表明自己的“清白”。
        self.accTxns = [] # 本账户本轮提交的交易集合
        self.accTxnsIndex = None # 本账户本轮提交的交易集合在blockbody中的编号位置，用于提取交易证明


    def generate_random_account(self):
        # 生成随机地址
        self.addr = ''.join(random.choices(string.ascii_letters + string.digits, k=42)) #bitcoin地址字符数为42
        # 生成随机公钥和私钥
        private_key = ec.generate_private_key(ec.SECP256K1())
        self.privateKey = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        self.publicKey = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def random_generate_txns(self, randomRecipients):
        accTxns = []
        for item in randomRecipients:
            tmpTime = str(datetime.datetime.now())
            tmpTxnHash = '0x19f1df2c7ee6b464720ad28e903aeda1a5ad8780afc22f0b960827bd4fcf656d' # todo: 交易哈希暂用定值，待实现
            tmpSender = self.addr
            tmpRecipient = item.addr
            tmpNonce = 0  # 待补全
            tmpSig = unit.generate_signature(tmpSender)  # todo: 交易的签名待补全
            tmpValue = random.randint(1, 1000)  # 原来为row[8]，根据值转移思想，现改为随机生成一个1-1000的整数
            tmpTxn = Transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                             nonce=tmpNonce, signature=tmpSig, value=tmpValue,
                                             tx_hash=tmpTxnHash, time=tmpTime)
            accTxns.append(tmpTxn)
        self.accTxns = accTxns
        return accTxns

    def receipt_txn_and_prf(self):
        # todo:接收函数的后续处理
        pass
    def generate_txn_prf_when_use(self, begin_index, end_index): # begin_index, end_index分别表示此txn在本账户手中开始的区块号和结束的区块号
        # todo: 根据交易、区块等input，生成目标交易的proof。
        # proof = 原证明 + 新生成的证明（在此account时期内的证明）
        # proof单元的数据结构：（区块号，mTree证明）
        # 生成new proof（在此account时期内的证明）
        new_proof = []

        pass
