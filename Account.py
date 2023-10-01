import random
import string


class Account:
    def __init__(self):
        self.addr = None
        self.prf = []
        self.privateKey = None
        self.publicKey = None
        self.accTxns = None

    def generate_random_account(self):
        # 生成随机地址
        self.addr = ''.join(random.choices(string.ascii_letters + string.digits, k=42)) #bitcoin地址字符数为42
        # 生成随机公钥
        public_key_prefix = '0x04'
        public_key_coordinates = ''.join(random.choices(string.hexdigits, k=128))
        self.publicKey = public_key_prefix + public_key_coordinates
        # 生成随机私钥
        self.privateKey = ''.join(random.choices(string.hexdigits, k=64))
        #生成prf
        #...
