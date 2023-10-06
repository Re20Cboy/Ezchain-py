import hashlib
import pickle
import csv
from const import *

class AccountTxns:
    def __init__(self, sender, accTxns):
        self.Sender = sender
        self.AccTxnsHash = None
        self.AccTxns = accTxns

    def Encode(self):
        encoded_tx = pickle.dumps(self.AccTxns)
        return encoded_tx
    @staticmethod
    def Decode(to_decode):
        decoded_tx = pickle.loads(to_decode)
        return decoded_tx

    def checkTxns(self):
        #todo:1.保证交易的签名的正确性；2.保证交易在一个accTxns内无双花
        pass



class Transaction:
    def __init__(self, sender, recipient, nonce, signature, value, tx_hash, time):
        self.Sender = sender
        self.Recipient = recipient
        self.Nonce = nonce
        self.Signature = signature  # todo:not implemented now.
        self.Value = value
        self.TxHash = tx_hash
        self.Time = time


        #self.Relayed = False
        #self.HasBroker = False
        #self.SenderIsBroker = False
        #self.OriginalSender = None
        #self.FinalRecipient = None
        #self.RawTxHash = None

    def checkTxn(self): #todo:
        #验证数字签名是否正确
        return True

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

