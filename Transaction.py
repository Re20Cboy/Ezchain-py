import hashlib
import pickle
import datetime
# 签名所需引用
import string
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key

class AccountTxns:
    def __init__(self, sender, senderID, accTxns):
        self.Sender = sender
        self.SenderID = senderID
        self.AccTxnsHash = None
        self.AccTxns = accTxns
        self.time = str(datetime.datetime.now()) # 记录时间戳

    def Encode(self): # 这里encode的只有真正的txn的list
        encoded_tx = pickle.dumps(self.AccTxns)
        return encoded_tx
    @staticmethod
    def Decode(to_decode):
        decoded_tx = pickle.loads(to_decode)
        return decoded_tx


class Transaction:
    def __init__(self, sender, recipient, nonce, signature, value, tx_hash, time):
        self.Sender = sender
        self.Recipient = recipient
        self.Nonce = nonce
        self.Signature = signature
        self.Value = value
        self.TxHash = tx_hash
        self.Time = time

    def txn2str(self):
        txn_str = f"Sender: {self.Sender}\n"
        txn_str += f"Recipient: {self.Recipient}\n"
        txn_str += f"Nonce: {str(self.Nonce)}\n"
        txn_str += f"Value: {self.Value}\n"
        txn_str += f"TxHash: {str(self.TxHash)}\n"
        txn_str += f"Time: {self.Time}\n"
        return txn_str

    def sig_txn(self, load_private_key_path):
        # 从私钥路径加载私钥
        with open(load_private_key_path, "rb") as key_file:
            private_key = load_pem_private_key(key_file.read(), password=None)
        # 使用SHA256哈希算法计算区块的哈希值
        block_hash = hashes.Hash(hashes.SHA256())
        block_hash.update(self.txn2str().encode('utf-8'))
        digest = block_hash.finalize()
        signature_algorithm = ec.ECDSA(hashes.SHA256())
        # 对区块哈希值进行签名
        signature = private_key.sign(data=digest, signature_algorithm=signature_algorithm)
        self.Signature = signature

    def check_txn_sig(self, load_public_key_path):
        # 从公钥路径加载公钥
        with open(load_public_key_path, "rb") as key_file:
            public_key = load_pem_public_key(key_file.read())
        # 使用SHA256哈希算法计算区块的哈希值
        block_hash = hashes.Hash(hashes.SHA256())
        block_hash.update(self.txn2str().encode('utf-8'))
        digest = block_hash.finalize()
        signature_algorithm = ec.ECDSA(hashes.SHA256())
        # 验证签名
        try:
            public_key.verify(
                self.Signature,
                digest,
                signature_algorithm
            )
            return True
        except:
            return False

    def PrintTx(self):
        vals = [self.Sender, self.Recipient, self.Value, self.TxHash]
        res = f"{vals}\n"
        return res

    def Encode(self):
        encoded_tx = pickle.dumps(self)
        return encoded_tx

    @staticmethod
    def Decode(to_decode):
        decoded_tx = pickle.loads(to_decode)
        return decoded_tx

    @staticmethod
    def NewTransaction(sender, recipient, value, nonce):
        tx = Transaction(
            sender=sender,
            recipient=recipient,
            nonce=nonce,
            signature=None,
            value=value,
            tx_hash=None,
            time=None
        )
        encoded_tx = tx.Encode()
        tx_hash = hashlib.sha256(encoded_tx).digest()
        tx.TxHash = tx_hash
        #tx.Relayed = False
        #tx.FinalRecipient = ""
        #tx.OriginalSender = ""
        #tx.RawTxHash = None
        #tx.HasBroker = False
        #tx.SenderIsBroker = False
        return tx

    def count_value_intersect_txn(self, value): # 计算value值的任意子集在此交易中被转移的总次数
        count = 0 # 用于计数有多少个与此value有交集的交易
        for V in self.Value:
            if V.isIntersectValue(value):
                count += 1
        return count

    def count_value_in_value(self, value): # 检测value是否完整地（作为完全相同的值或者被包含在一个更大的值内）在此交易中被转移仅一次
        count = 0  # 用于计数
        for V in self.Value:
            if V.isInValue(value):
                count += 1
        return count