import copy
import datetime
import hashlib
import random
import string
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pympler import asizeof

from const import *
import transaction
import unit
from utils import ensure_directory_exists
from collections import defaultdict

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key


class Account:
    def __init__(self, ID):
        self.addr = None
        self.id = ID
        self.privateKeyPath = None  # Address to store the private key
        self.publicKeyPath = None  # Address to store the public key
        self.privateKey = None  # Private key
        self.publicKey = None  # Public key
        self.ValuePrfBlockPair = []  # The values owned by the account and corresponding proofs, block numbers, and their index pairs in the list
        # self.prfChain = []  # Collection of all proofs for this account, i.e., all prf related to this account on the public chain
        self.bloomPrf = []  # Evidence provided when "mistakenly injured" by the bloom filter (which accounts can generate this bloom) to prove innocence
        self.accTxns = []  # Collection of transactions submitted by this account in the current round
        self.accTxnsIndex = None  # The index position of this account's transactions in the blockbody, used for extracting transaction proofs
        self.balance = 0  # Calculate the account balance from Value
        self.costedValuesAndRecipes = []  # Records the Values spent in this round, type as [(value, new owner i.e., transaction recipient), (..., ...), ...]
        self.recipientList = []
        self.verifyTimeCostList = []  # Records the various consumption values for verifying a transaction (proof capacity size)
        self.verifyStorageCostList = []  # Records the various consumption values for verifying a transaction (verification time), in bits
        self.acc2nodeDelay = []  # Records the delay in delivering accTxn to the transaction pool
        self.VPBCheckPoints = unit.checkedVPBList()  # Records the verified VPB logs to reduce the cost of transmission, storage, and verification of the account
        self.accRoundVPBCostList = []  # Records the storage cost of VPB for this node each round
        self.accRoundCKCostList = []  # Records the storage cost of CK for this node each round
        self.accRoundAllCostList = []  # Records the total storage cost of VPB+CK for this node each round
        self.delete_vpb_list = []


    def test(self):
        test = copy.deepcopy(self.ValuePrfBlockPair)
        for i, vpb in enumerate(self.ValuePrfBlockPair):
            v = vpb[0]
            p = vpb[1].prfList
            b = vpb[2]
            for j, item in enumerate(test):
                if i == j:
                    continue
                v2 = item[0]
                p2 = item[1].prfList
                b2 = item[2]
                flag = v.isIntersectValue(v2)
                if flag:
                    print("There are duplicate records in VPB!")

    def clear_and_fresh_info(self):
        self.accTxns = []
        self.accTxnsIndex = None
        self.costedValuesAndRecipes = []
        self.recipientList = []
        # Check for duplicates in vpb of each round
        # self.test()
        # Update check points based on this round's VPBpairs
        self.VPBCheckPoints.addAndFreshCheckPoint(self.ValuePrfBlockPair)
        # Update storage cost information for acc
        self.freshStorageCost()

    def freshStorageCost(self):
        accRoundVPBCost = asizeof.asizeof(self.ValuePrfBlockPair) / 1048576
        accRoundCKCost = asizeof.asizeof(self.VPBCheckPoints) / 1048576
        self.accRoundVPBCostList.append(accRoundVPBCost)  # Convert to MB
        self.accRoundCKCostList.append(accRoundCKCost)  # Convert to MB
        self.accRoundAllCostList.append(accRoundVPBCost + accRoundCKCost)  # Convert to MB

    def add_VPBpair(self, item):
        self.ValuePrfBlockPair.append(item)
        # Update the balance
        self.balance += item[0].valueNum

    def add_VPBpair_dst(self, item):
        # design add VPB pair func for DST mode
        # the VPB add in DST mode should be re-design since distribute network
        self.ValuePrfBlockPair.append(item)
        # Update the balance
        self.balance += item[0].valueNum

    def delete_VPBpair(self, index):
        # Update the balance
        self.balance -= self.ValuePrfBlockPair[index][0].valueNum
        del self.ValuePrfBlockPair[index]
        # Update the index
        # for item in self.ValuePrfBlockPair:
            # item[0][1] = self.ValuePrfBlockPair.index(item)

    def get_VPB_index_via_VPB(self, VPBpair):
        for index, item in enumerate(self.ValuePrfBlockPair, start=0):
            if item == VPBpair:
                return index
        raise ValueError("This VPB was not found in this account!")

    def update_balance(self):
        balance = 0
        for VBPpair in self.ValuePrfBlockPair:
            balance += VBPpair[0].valueNum
        self.balance = balance

    def find_VPBpair_via_V(self, V):  # Note that V is a list of Values
        index = []
        for value in V:
            for i, VPBpair in enumerate(self.ValuePrfBlockPair, start=0):
                if VPBpair[0].isSameValue(value):
                    index.append(i)
                    break
        if index != []:
            return index
        else:
            raise ValueError("The corresponding Value was not found")


    def generate_random_account(self, file_id=0):
        # Generate a random address
        self.addr = ''.join(random.choices(string.ascii_letters + string.digits, k=42))  # Bitcoin address is 42 characters long
        # Generate a private key
        private_key = ec.generate_private_key(ec.SECP384R1())
        # Obtain the public key from the private key
        public_key = private_key.public_key()
        # Save the addresses of the public and private keys
        if file_id == 0: # for EZ simulate
            privatePath = ACCOUNT_PRIVATE_KEY_PATH + "private_key_node_"+str(self.id)+".pem"
            publicPath = ACCOUNT_PUBLIC_KEY_PATH + "public_key_node_"+str(self.id)+".pem"
        else: # for dst simulate
            privatePath = ACCOUNT_PRIVATE_KEY_PATH + "private_key_node_" + str(file_id) + ".pem"
            publicPath = ACCOUNT_PUBLIC_KEY_PATH + "public_key_node_" + str(file_id) + ".pem"
        self.privateKeyPath = privatePath
        self.publicKeyPath = publicPath
        self.privateKey = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        self.publicKey = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        # Save the private key to a file (operate with caution to avoid leaking the private key)
        ensure_directory_exists(privatePath)
        with open(privatePath, "wb") as f:
            f.write(self.privateKey)
        # Save the public key to a file (the public key can be distributed to those who need to verify it)
        ensure_directory_exists(publicPath)
        with open(publicPath, "wb") as f:
            f.write(self.publicKey)

    def generate_txn_dst(self, addr_lst, amount_lst):
        def pick_values_and_generate_txns(V, tmpSender, tmpRecipient, tmpNonce, tmpTxnHash, tmpTime):
            # V is an integer, the total amount of value to pick
            if V < 1:
                raise ValueError("The value of V cannot be less than 1")
            tmpCost = 0  # Dynamically record how much value is to be consumed
            costList = []  # Record the index of the consumed Value
            changeValueIndex = -1  # Record the index of the change value
            txn_2_sender = None
            txn_2_recipient = None
            value_Enough = False
            for i, VPBpair in enumerate(self.ValuePrfBlockPair, start=0):
                value = VPBpair[0]
                if value in [i[0] for i in self.costedValuesAndRecipes]:
                    continue
                tmpCost += value.valueNum
                if tmpCost >= V:  # The demand for value is met, spend up to this value
                    changeValueIndex = i
                    costList.append(i)
                    value_Enough = True
                    break
                changeValueIndex = i
                costList.append(i)

            # Check if the balance is sufficient
            if not value_Enough:
                raise ValueError("Insufficient balance!")

            change = tmpCost - V  # Calculate the change

            if change > 0:  # Change needed, split the value
                V1, V2 = self.ValuePrfBlockPair[changeValueIndex][0].split_value(change)  # V2 is the change
                # Create a transaction for change
                txn_2_sender = transaction.Transaction(sender=tmpSender, recipient=tmpSender,
                                                       nonce=tmpNonce, signature=None, value=[V2],
                                                       tx_hash=tmpTxnHash, time=tmpTime)
                txn_2_sender.sig_txn(self.privateKey)
                txn_2_recipient = transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                          nonce=tmpNonce, signature=None, value=[V1],
                                                          tx_hash=tmpTxnHash, time=tmpTime)
                txn_2_recipient.sig_txn(self.privateKey)
                self.costedValuesAndRecipes.append((V1, tmpRecipient))
            else:
                changeValueIndex = -1
            return costList, changeValueIndex, txn_2_sender, txn_2_recipient

        # todo: Rewrite the change logic to maximize the use of change
        accTxns = []
        tmpBalance = self.balance

        for index, addr in enumerate(addr_lst, start=0):
            tmpTime = str(datetime.datetime.now())
            tmpTxnHash = '0x19f1df2c7ee6b464720ad28e903aeda1a5ad8780afc22f0b960827bd4fcf656d'  # todo: Transaction hash is temporarily fixed, to be implemented
            tmpSender = self.addr
            tmpRecipient = addr
            tmpNonce = 0  # To be completed
            # tmpSig = unit.generate_signature(tmpSender)
            tmpV = amount_lst[index]
            if tmpBalance <= tmpV:  # Can only transact if the balance is more than 0!
                raise ValueError("Insufficient balance!!!")
            else:
                tmpBalance -= tmpV

            # costList is a list of indexes of the values spent (including change value), changeValueIndex is the index of the unique change value (already included in costList)
            costList, changeValueIndex, changeTxn2Sender, changeTxn2Recipient = pick_values_and_generate_txns(tmpV, tmpSender, tmpRecipient, tmpNonce, tmpTxnHash, tmpTime)  # Values spent and change
            if changeValueIndex < 0:  # No change needed
                tmpValues = []
                for index in costList:
                    tmpValues.append(self.ValuePrfBlockPair[index][0])
                    self.costedValuesAndRecipes.append((self.ValuePrfBlockPair[index][0], tmpRecipient))
                    # Delete this value
                    # self.delete_VPBpair(i)
                tmpTxn = transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                 nonce=tmpNonce, signature=None, value=tmpValues,
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                tmpTxn.sig_txn(load_private_key=self.privateKey)
                accTxns.append(tmpTxn)
            else:  # Change needed
                tmpValues = []
                for i in costList:
                    if i != changeValueIndex:  # Means i is spent and is not the only change value
                        tmpValues.append(self.ValuePrfBlockPair[i][0])
                        self.costedValuesAndRecipes.append((self.ValuePrfBlockPair[i][0], tmpRecipient))

                if tmpValues != []:  # Non-change values that are spent
                    tmpTxn = transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                     nonce=tmpNonce, signature=None, value=tmpValues,
                                                     tx_hash=tmpTxnHash, time=tmpTime)
                    tmpTxn.sig_txn(load_private_key=self.privateKey)
                    accTxns.append(tmpTxn)

                tmpP = self.ValuePrfBlockPair[changeValueIndex][1]
                tmpB = self.ValuePrfBlockPair[changeValueIndex][2]
                self.delete_VPBpair(changeValueIndex)
                self.add_VPBpair([changeTxn2Recipient.Value[0], copy.deepcopy(tmpP), copy.deepcopy(tmpB)])  # V1 cannot be used in subsequent transactions in this round
                self.add_VPBpair([changeTxn2Sender.Value[0], copy.deepcopy(tmpP), copy.deepcopy(tmpB)])

                accTxns.append(changeTxn2Sender)
                accTxns.append(changeTxn2Recipient)

        self.accTxns = accTxns
        self.acc2nodeDelay.append(asizeof.asizeof(accTxns) * 8 / BANDWIDTH + NODE_ACCOUNT_DELAY)
        return accTxns

    def random_generate_txns(self, randomRecipients):
        def pick_values_and_generate_txns(V, tmpSender, tmpRecipient, tmpNonce, tmpTxnHash, tmpTime): 
            # V is an integer, the total amount of value to pick
            if V < 1:
                raise ValueError("The value of V cannot be less than 1")
            tmpCost = 0  # Dynamically record how much value is to be consumed
            costList = []  # Record the index of the consumed Value
            changeValueIndex = -1  # Record the index of the change value
            txn_2_sender = None
            txn_2_recipient = None
            value_Enough = False
            for i, VPBpair in enumerate(self.ValuePrfBlockPair, start=0):
                value = VPBpair[0]
                if value in [i[0] for i in self.costedValuesAndRecipes]:
                    continue
                tmpCost += value.valueNum
                if tmpCost >= V:  # The demand for value is met, spend up to this value
                    changeValueIndex = i
                    costList.append(i)
                    value_Enough = True
                    break
                changeValueIndex = i
                costList.append(i)

            # Check if the balance is sufficient
            if not value_Enough:
                raise ValueError("Insufficient balance!")

            change = tmpCost - V  # Calculate the change

            if change > 0:  # Change needed, split the value
                V1, V2 = self.ValuePrfBlockPair[changeValueIndex][0].split_value(change)  # V2 is the change
                # Create a transaction for change
                txn_2_sender = transaction.Transaction(sender=tmpSender, recipient=tmpSender,
                                                       nonce=tmpNonce, signature=None, value=[V2],
                                                       tx_hash=tmpTxnHash, time=tmpTime)
                txn_2_sender.sig_txn(self.privateKey)
                txn_2_recipient = transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                          nonce=tmpNonce, signature=None, value=[V1],
                                                          tx_hash=tmpTxnHash, time=tmpTime)
                txn_2_recipient.sig_txn(self.privateKey)
                self.costedValuesAndRecipes.append((V1, tmpRecipient))
            else:
                changeValueIndex = -1
            return costList, changeValueIndex, txn_2_sender, txn_2_recipient

        # todo: Rewrite the change logic to maximize the use of change
        accTxns = []
        tmpBalance = self.balance

        for item in randomRecipients:
            tmpTime = str(datetime.datetime.now())
            tmpTxnHash = '0x19f1df2c7ee6b464720ad28e903aeda1a5ad8780afc22f0b960827bd4fcf656d'  # todo: Transaction hash is temporarily fixed, to be implemented
            tmpSender = self.addr
            tmpRecipient = item.addr
            tmpNonce = 0  # To be completed
            # tmpSig = unit.generate_signature(tmpSender)
            tmpV = random.randint(1, 1000)
            if tmpBalance <= tmpV:  # Can only transact if the balance is more than 0!
                raise ValueError("Insufficient balance!!!")
            else:
                tmpBalance -= tmpV

            # costList is a list of indexes of the values spent (including change value), changeValueIndex is the index of the unique change value (already included in costList)
            costList, changeValueIndex, changeTxn2Sender, changeTxn2Recipient = pick_values_and_generate_txns(tmpV, tmpSender, tmpRecipient, tmpNonce, tmpTxnHash, tmpTime)  # Values spent and change
            if changeValueIndex < 0:  # No change needed
                tmpValues = []
                for index in costList:
                    tmpValues.append(self.ValuePrfBlockPair[index][0])
                    self.costedValuesAndRecipes.append((self.ValuePrfBlockPair[index][0], tmpRecipient))
                tmpTxn = transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                 nonce=tmpNonce, signature=None, value=tmpValues,
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                tmpTxn.sig_txn(load_private_key=self.privateKey)
                accTxns.append(tmpTxn)
            else:  # Change needed
                tmpValues = []
                for i in costList:
                    if i != changeValueIndex:  # Means i is spent and is not the only change value
                        tmpValues.append(self.ValuePrfBlockPair[i][0])
                        self.costedValuesAndRecipes.append((self.ValuePrfBlockPair[i][0], tmpRecipient))

                if tmpValues != []:  # Non-change values that are spent
                    tmpTxn = transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                     nonce=tmpNonce, signature=None, value=tmpValues,
                                                     tx_hash=tmpTxnHash, time=tmpTime)
                    tmpTxn.sig_txn(load_private_key=self.privateKey)
                    accTxns.append(tmpTxn)

                tmpP = self.ValuePrfBlockPair[changeValueIndex][1]
                tmpB = self.ValuePrfBlockPair[changeValueIndex][2]

                self.delete_VPBpair(changeValueIndex)
                self.add_VPBpair([changeTxn2Recipient.Value[0], copy.deepcopy(tmpP), copy.deepcopy(tmpB)])  # V1 cannot be used in subsequent transactions in this round
                self.add_VPBpair([changeTxn2Sender.Value[0], copy.deepcopy(tmpP), copy.deepcopy(tmpB)])

                accTxns.append(changeTxn2Sender)
                accTxns.append(changeTxn2Recipient)

        self.accTxns = accTxns
        self.acc2nodeDelay.append(asizeof.asizeof(accTxns) * 8 / BANDWIDTH + NODE_ACCOUNT_DELAY)
        return accTxns

    def optimized_generate_txns(self, randomRecipients):
        def pick_values_and_generate_txns(V, tmpSender, tmpRecipient, tmpNonce, tmpTxnHash, tmpTime): 
            # V is an integer, the total amount of value to be picked
            if V < 1:
                raise ValueError("The parameter V cannot be less than 1")
            tmpCost = 0  # Dynamically records the amount of value to be consumed
            costList = []  # Records the index of the Value to be consumed
            changeValueIndex = -1  # Records the index of the change value
            txn_2_sender = None
            txn_2_recipient = None
            value_Enough = False
            for i, VPBpair in enumerate(self.ValuePrfBlockPair, start=0):
                value = VPBpair[0]
                if value in [i[0] for i in self.costedValuesAndRecipes]:
                    continue
                tmpCost += value.valueNum
                if tmpCost >= V:  # If the value demand is met, stop at this value
                    changeValueIndex = i
                    costList.append(i)
                    value_Enough = True
                    break
                changeValueIndex = i
                costList.append(i)

            # Check if the balance is sufficient
            if not value_Enough:
                raise ValueError("Insufficient balance!")

            change = tmpCost - V  # Calculate the change

            if change > 0:  # If change is needed, split the value
                V1, V2 = self.ValuePrfBlockPair[changeValueIndex][0].split_value(change)  # V2 is the change
                # Create a transaction for the change
                txn_2_sender = transaction.Transaction(sender=tmpSender, recipient=tmpSender,
                                                       nonce=tmpNonce, signature=None, value=[V2],
                                                       tx_hash=tmpTxnHash, time=tmpTime)
                txn_2_sender.sig_txn(self.privateKey)
                txn_2_recipient = transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                          nonce=tmpNonce, signature=None, value=[V1],
                                                          tx_hash=tmpTxnHash, time=tmpTime)
                txn_2_recipient.sig_txn(self.privateKey)
                self.costedValuesAndRecipes.append((V1, tmpRecipient))
            else:
                changeValueIndex = -1
            return costList, changeValueIndex, txn_2_sender, txn_2_recipient

        # todo: Rewrite the logic for making change to maximize the use of small denominations
        accTxns = []
        tmpBalance = self.balance

        for item in randomRecipients:
            tmpTime = str(datetime.datetime.now())
            tmpTxnHash = '0x19f1df2c7ee6b464720ad28e903aeda1a5ad8780afc22f0b960827bd4fcf656d'  # todo: The transaction hash is temporarily a fixed value, to be implemented
            tmpSender = self.addr
            tmpRecipient = item.addr
            tmpNonce = 0  # To be completed
            # tmpSig = unit.generate_signature(tmpSender)
            tmpV = random.randint(1, 1000)
            if tmpBalance <= tmpV:  # Can only transact if the balance is more than 0!
                raise ValueError("Insufficient balance!!!")
            else:
                tmpBalance -= tmpV

            # costList is a list of indexes of the values spent (including change value), changeValueIndex is the index of the unique change value (already included in costList)
            costList, changeValueIndex, changeTxn2Sender, changeTxn2Recipient = pick_values_and_generate_txns(tmpV, tmpSender, tmpRecipient, tmpNonce, tmpTxnHash, tmpTime)  # Values spent and change
            if changeValueIndex < 0:  # No change needed
                tmpValues = []
                for index in costList:
                    tmpValues.append(self.ValuePrfBlockPair[index][0])
                    self.costedValuesAndRecipes.append((self.ValuePrfBlockPair[index][0], tmpRecipient))
                    # Delete this value
                    # self.delete_VPBpair(i)
                tmpTxn = transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                 nonce=tmpNonce, signature=None, value=tmpValues,
                                                 tx_hash=tmpTxnHash, time=tmpTime)
                tmpTxn.sig_txn(load_private_key=self.privateKey)
                accTxns.append(tmpTxn)
            else:  # Change needed
                tmpValues = []
                for i in costList:
                    if i != changeValueIndex:  # Means i is spent and is not the only change value
                        tmpValues.append(self.ValuePrfBlockPair[i][0])
                        self.costedValuesAndRecipes.append((self.ValuePrfBlockPair[i][0], tmpRecipient))

                if tmpValues != []:  # Non-change values that are spent
                    tmpTxn = transaction.Transaction(sender=tmpSender, recipient=tmpRecipient,
                                                     nonce=tmpNonce, signature=None, value=tmpValues,
                                                     tx_hash=tmpTxnHash, time=tmpTime)
                    tmpTxn.sig_txn(load_private_key=self.privateKey)
                    accTxns.append(tmpTxn)

                tmpP = self.ValuePrfBlockPair[changeValueIndex][1]
                tmpB = self.ValuePrfBlockPair[changeValueIndex][2]
                self.delete_VPBpair(changeValueIndex)
                self.add_VPBpair([changeTxn2Recipient.Value[0], copy.deepcopy(tmpP), copy.deepcopy(tmpB)])  # V1 cannot be used in subsequent transactions in this round
                self.add_VPBpair([changeTxn2Sender.Value[0], copy.deepcopy(tmpP), copy.deepcopy(tmpB)])

                accTxns.append(changeTxn2Sender)
                accTxns.append(changeTxn2Recipient)

        self.accTxns = accTxns
        self.acc2nodeDelay.append(asizeof.asizeof(accTxns) * 8 / BANDWIDTH + NODE_ACCOUNT_DELAY)
        return accTxns

    def receipt_txn_and_prf(self):
        pass

    def updateBloomPrf(self, bloom, txnAccList, blockIndex):
        if self.costedValuesAndRecipes == [] and self.addr in bloom:
            # If wrongly identified by bloom, perform the addition of bloom proof operation
            self.bloomPrf.append([copy.deepcopy(txnAccList), copy.deepcopy(blockIndex)])  # Bloom proof = [Addresses of all accounts in this bloom filter, block number to which this bloom belongs]

    def check_pass_VPBpair(self, VPBpair, bloomPrf, blockchain, passIndexList, CKOwner, check_start_time):  # Called when there is a checkpoint
        value = VPBpair[0]
        valuePrf = VPBpair[1].prfList
        blockIndex = VPBpair[2]

        BList = []  # Records the B information of the VPB within each epoch, structured as: [(owner, [list of block index]), (...), (...), ...] for comparison and verification
        oneEpochBList = [blockIndex[1 + passIndexList[-1]]]  # Structure: [list of block index], adding the start of a new epoch
        orgSender = valuePrf[passIndexList[-1]].owner
        recordOwner = valuePrf[1 + passIndexList[-1]].owner  # Update the recorded owner to CK's owner
        epochChangeList = []  # Records the block number at the time of epoch change

        ##############################
        ######## 3 Check the correctness of proof ###
        ##############################
        for index, prfUnit in enumerate(valuePrf, start=0):
            if index in passIndexList:
                continue

            isNewEpoch = False
            oneEpochBList.append(blockIndex[index])
            tmpSender = None  # Records the sender of the transaction at each epoch change for verifying bloom
            if index == passIndexList[-1] + 1:  # Special handling for the first check after the checkpoint
                isNewEpoch = True  # Directly enter a new epoch
                oneEpochBList.pop()  # pop the block number of the next transaction, otherwise, there are duplicates
                tmpSender = orgSender
            elif recordOwner != prfUnit.owner:  # Indicates that the owner has changed, the value enters the epoch held by the next owner
                isNewEpoch = True
                lastBlockIndex = oneEpochBList.pop()  # Get the block number of the last transaction
                # Update the B information of the VPB within the epoch
                BList.append((copy.deepcopy(recordOwner), copy.deepcopy(oneEpochBList)))
                oneEpochBList = [lastBlockIndex]  # Reserve the block number of the first transaction for the next proof segment
                epochChangeList.append(lastBlockIndex)
                tmpSender = recordOwner
                recordOwner = prfUnit.owner  # Update owner information

            ownerAccTxnsList = prfUnit.ownerAccTxnsList
            ownerMTreePrfList = prfUnit.ownerMTreePrfList

            # Check: The information of ownerAccTxnsList and ownerMTreePrfList matches
            uncheckedAccTxns = transaction.AccountTxns(sender='sender', senderID=None, accTxns=ownerAccTxnsList)
            uncheckedMTreePrf = unit.MTreeProof(MTPrfList=ownerMTreePrfList)
            uncheckedAccTxns.set_digest()
            accTxnsDigest = uncheckedAccTxns.Digest
            # Check: ownerMTreePrfList and the root of the block in the main chain match
            if not uncheckedMTreePrf.checkPrf(accTxnsDigest=accTxnsDigest,
                                              trueRoot=blockchain.chain[blockIndex[index]].get_m_tree_root()):
                print("VPB check error: Merkle tree check failed")
                return False  # Merkle tree check failed, hence error!

            if isNewEpoch:
                # All txns should have only one transaction that transfers the value to the new owner
                SpendValueTxnList = []  # Records all transactions in this accTxns where this value is transferred; under legal conditions, the length of this list should be 1
                for txn in ownerAccTxnsList:
                    count = txn.count_value_in_value(value)
                    if count == 1:  # =0 means the value is not transferred, >1 indicates double-spending in this transaction
                        if txn.Sender != txn.Recipient:  # If not transferred to oneself, then it counts as value spending
                            SpendValueTxnList.append(txn)
                    elif count > 1:
                        print("VPB check error: Double-spending within a single transaction!")
                        return False  # Double-spending! Or the value is not transferred to the owner!
                if len(SpendValueTxnList) != 1:
                    print("VPB check error: Double-spending! Or the value is not transferred to the owner!")
                    return False  # Double-spending! Or the value is not transferred to the owner!
                if tmpSender != None and tmpSender not in blockchain.chain[blockIndex[index]].bloom:
                    print("VPB check error: Error in Bloom filter check during value transfer!")
                    return False
                if SpendValueTxnList[0].Recipient != recordOwner:
                    print("VPB check error: This value was not transferred to the specified owner")
                    return False  # This value was not transferred to the specified owner
            else:
                # Not entered a new epoch yet, i.e., the value has not yet been transferred to the new owner
                for txn in ownerAccTxnsList:
                    if txn.count_value_intersect_txn(value) != 0:
                        if txn.Sender != txn.Recipient:
                            print("VPB check error: This value should not be spent here in advance")
                            return False  # This value should not be spent here!

        ##############################
        # 4 Check: The B information within each epoch matches the bloom filter information on the main chain, i.e., the epoch owner did not lie on B
        ##############################
        if len(BList) != len(epochChangeList):
            print("VPB check error: len(BList) != len(epochChangeList)")
            return False

        if passIndexList:
            oldEpochFlag = blockIndex[passIndexList[-1] + 1]
        else:
            oldEpochFlag = 0

        for index, epochRecord in enumerate(BList, start=0):
            fullEpochBList = range(oldEpochFlag, epochChangeList[index])
            realEpochBlist = []
            (owner, uncheckedBList) = epochRecord

            if len(uncheckedBList) < 1:
                print("VPB check error: This owner has no value record")
                return False  # This owner has no value record, hence error!

            # todo: Determine if uncheckedBList connects to passList
            # if index == 0 and uncheckedBList[0] != blockIndex[passIndexList[-1] + 1]:
                # print("VPB check error: Checkpoint data did not connect to unchecked B list data")
                # return False

            ownerBegin = uncheckedBList[0]  # The block index when the owner first owned the value
            ownerEnd = uncheckedBList[-1]  # The owner will transfer this value to another owner in the next block, i.e., the last block index holding this value
            if ownerEnd < ownerBegin:
                print("VPB check error: Incorrect block number records of owner holding the value")
                return False  # Incorrect block number records of owner holding the value!

            for item in fullEpochBList:
                if owner in blockchain.chain[item].bloom:
                    realEpochBlist.append(item)

            # No need to verify the first block owned by the owner, as it has been checked before
            if len(uncheckedBList) > 0 and uncheckedBList[0] == oldEpochFlag:
                uncheckedBList.pop(0)  # This will change BList
            if len(realEpochBlist) > 0 and realEpochBlist[0] == oldEpochFlag:
                realEpochBlist.pop(0)

            if uncheckedBList != realEpochBlist:
                # If different, need to check bloom proof to exclude the possibility of being "misjudged" by the bloom filter
                if bloomPrf == []:
                    print("VPB check error: No bloom proof provided")
                    return False  # No bloom proof provided, hence no misjudgment, indicating that the owner's value holding records and the actual records are different, error!
                else:
                    # todo: Check bloom proof
                    pass
            oldEpochFlag = epochChangeList[index]
        passRate = 1 - (len(passIndexList) / len(valuePrf))
        PrfSize = (asizeof.asizeof(VPBpair) + asizeof.asizeof(bloomPrf)) * 8 * passRate  # *8 to convert to bit unit
        # Record program end time
        check_end_time = time.time()
        # Calculate program run time
        VerTime = check_end_time - check_start_time
        self.verifyTimeCostList.append(VerTime)
        self.verifyStorageCostList.append(PrfSize)
        return True


    def check_VPBpair(self, VPBpair, bloomPrf, blockchain):
        # First check the checkpoint; if there are VPBs that don't need to be checked, skip directly
        ckList = self.VPBCheckPoints.findCKviaVPB(VPBpair)
        passIndexList = None
        CKOwner = None
        if ckList != []:  # Found the corresponding checkpoint
            ckOwner, ckBIndex = ckList[0]
            flagIndex = None  # Indicates up to which position in VPB is recorded by CK
            for index, item in enumerate(VPBpair[2], start=0):
                if item == ckBIndex[-1]:
                    flagIndex = index
            if flagIndex == None:
                raise ValueError('VPB check error: Conflict between this VPB and checkpoint record!')
            VPBOwner = VPBpair[1].prfList[flagIndex].owner
            if VPBOwner != ckOwner:
                raise ValueError('VPB check error: Conflict between this VPB and checkpoint record!')
            passIndexList = list(range(flagIndex + 1))
            CKOwner = ckOwner

        # Calculate verification cost
        PrfSize = (asizeof.asizeof(VPBpair) + asizeof.asizeof(bloomPrf)) * 8  # *8 to convert to bit unit
        # Record program start time
        check_start_time = time.time()

        def hash(val):
            if type(val) == str:
                return hashlib.sha256(val.encode("utf-8")).hexdigest()
            else:
                return hashlib.sha256(val).hexdigest()

        ##############################
        ######## 1 Check data type: ########
        ##############################
        if type(VPBpair[0]) != unit.Value or type(VPBpair[1]) != unit.Proof or type(VPBpair[2]) != list:
            print("VPB check error: Data structure error")
            return False  # Data structure error

        value = VPBpair[0]
        valuePrf = VPBpair[1].prfList
        blockIndex = VPBpair[2]

        if len(valuePrf) != len(blockIndex):
            print("VPB check error: Evidence and block index not one-to-one mapping")
            return False  # Evidence and block index not one-to-one mapping, hence error

        ##############################
        ######## 2 Check the structural legality of value: ########
        ##############################
        if not value.checkValue:
            print("VPB check error: Value structure legality check failed")
            return False  # Value structure legality check failed

        if passIndexList:
            return self.check_pass_VPBpair(VPBpair, bloomPrf, blockchain, passIndexList, CKOwner, check_start_time)

        recordOwner = None  # This variable is used to record the owner of value transfer
        epochRealBList = []  # Records the real B information within the epoch, used to compare with B in VPB
        BList = []  # Records the B information of VPB within each epoch, structured as: [(owner, [list of block index]), (...), (...), ...] for comparison and verification
        oneEpochBList = []  # Structure: [list of block index]
        epochChangeList = []  # Records the block number at the time of epoch change


        ##############################
        ######## 3 Check the correctness of proof ###
        ##############################
        for index, prfUnit in enumerate(valuePrf, start=0):
            # Since the first prfUnit is a transaction in the genesis block, it needs special verification
            if index == 0: # Indicates it's the genesis block
                recordOwner = prfUnit.owner
                ownerAccTxnsList = prfUnit.ownerAccTxnsList
                ownerMTreePrfList = prfUnit.ownerMTreePrfList
                # Detection of the genesis block
                if ownerMTreePrfList == [blockchain.chain[0].get_m_tree_root()]:  # Indicates this is the genesis block
                    tmpGenesisAccTxns = transaction.AccountTxns(GENESIS_SENDER, -1, ownerAccTxnsList)
                    tmpEncode = tmpGenesisAccTxns.Encode()
                    if hash(tmpEncode) != blockchain.chain[0].get_m_tree_root():
                        print("VPB detection error: Transaction set hash error, node forged transactions in the genesis block")
                        return False  # Root value error, indicates node forged transactions in the genesis block.
                    # Check if this value is in the genesis block and the holder is the recipient in the genesis block:
                    for genesisTxn in ownerAccTxnsList:
                        if genesisTxn.Recipient == recordOwner:
                            if not genesisTxn.Value.isInValue(value):
                                print("VPB detection error: This value traced back to the genesis block is found to be illegal")
                                return False
                else:
                    print("VPB detection error: Genesis block tree root check error in proof")
                    return False
                oneEpochBList.append(blockIndex[index])
        
            else: # Non-genesis block detection
                isNewEpoch = False
                oneEpochBList.append(blockIndex[index])
                tmpSender = None # Record the sender of the transaction at each epoch change for bloom verification
                if recordOwner != prfUnit.owner: # Indicates the owner has changed, this value enters the next epoch held by the new owner
                    isNewEpoch = True
                    lastBlockIndex = oneEpochBList.pop() # Get the block number of the last transaction
                    # Update the B information of VPB within the epoch
                    BList.append((copy.deepcopy(recordOwner), copy.deepcopy(oneEpochBList)))
                    oneEpochBList = [lastBlockIndex] # Reserve the block number of the initial transaction for the next proof segment
                    epochChangeList.append(lastBlockIndex)
                    tmpSender = recordOwner
                    recordOwner = prfUnit.owner  # Update owner information
        
                ownerAccTxnsList = prfUnit.ownerAccTxnsList
                ownerMTreePrfList = prfUnit.ownerMTreePrfList
        
                # Check: Information of ownerAccTxnsList and ownerMTreePrfList matches
                # Note, here the Encode() function only encodes accTxns, so you can set sender='sender', senderID=None without affecting the result.
                uncheckedAccTxns = transaction.AccountTxns(sender='sender', senderID=None, accTxns=ownerAccTxnsList)
                uncheckedMTreePrf = unit.MTreeProof(MTPrfList=ownerMTreePrfList)
                uncheckedAccTxns.set_digest()
                accTxnsDigest = uncheckedAccTxns.Digest
                # Check: ownerMTreePrfList and the root of this block in the main chain match
                if not uncheckedMTreePrf.checkPrf(accTxnsDigest=accTxnsDigest, trueRoot=blockchain.chain[blockIndex[index]].get_m_tree_root()):
                    print("VPB detection error: Merkle tree check failed")
                    return False # Merkle tree check failed, therefore error!
        
                if isNewEpoch:
                    # All txns should have exactly one transaction transferring the value to the new owner
                    SpendValueTxnList = [] # Records all transactions transferring this value in this accTxns, legally this list should have a length of 1
                    for txn in ownerAccTxnsList:
                        count = txn.count_value_in_value(value)
                        if count == 1: # =0 indicates the value is not transferred, >1 indicates double spending in this transaction
                            if txn.Sender != txn.Recipient:  # If it's not transferring to oneself, then add to the value spending list
                                SpendValueTxnList.append(txn)
                        elif count > 1:
                            print("VPB detection error: Double spending in a single transaction!")
                            return False  # Double spending exists! Or the value is not transferred to the owner!
                    if len(SpendValueTxnList) != 1:
                        print("VPB detection error: Double spending exists! Or the value is not transferred to the owner!")
                        return False # Double spending exists! Or the value is not transferred to the owner!
                    if tmpSender != None and tmpSender not in blockchain.chain[blockIndex[index]].bloom:
                        print("VPB detection error: Bloom filter check error during value transfer!")
                        return False
                    if SpendValueTxnList[0].Recipient != recordOwner:
                        print("VPB detection error: This value is not transferred to the specified owner")
                        return False # This value is not transferred to the specified owner
                else:
                    # Not entering a new epoch, i.e., this value has not yet been transferred to a new owner
                    for txn in ownerAccTxnsList:
                        if txn.count_value_intersect_txn(value) != 0:
                            if txn.Sender != txn.Recipient:
                                print("VPB detection error: This value should not be prematurely spent here")
                                return False # This value should not be spent here!

        ##############################
        # 4 Check: The information of B in each epoch matches the bloom filter information on the main chain, i.e., the epoch's owner did not lie on B
        ##############################
        if len(BList) != len(epochChangeList):
            print("VPB detection error: len(BList) != len(epochChangeList)")
            return False
        oldEpochFlag = 0
        for index, epochRecord in enumerate(BList, start=0):
            fullEpochBList = range(oldEpochFlag, epochChangeList[index])
            realEpochBlist = []
            (owner, uncheckedBList) = epochRecord
        
            if len(uncheckedBList) < 1:
                print("VPB detection error: No record of this owner holding the value")
                return False  # No record of this owner holding the value, therefore an error!
        
            ownerBegin = uncheckedBList[0]  # Block index when the owner first had the value
            ownerEnd = uncheckedBList[-1]  # Owner will transfer this value to another owner in the next block, i.e., the last block index holding this value
            if ownerEnd < ownerBegin:
                print("VPB detection error: Incorrect block number record for owner holding the value")
                return False  # Incorrect block number record for owner holding the value!
        
            for item in fullEpochBList:
                if owner in blockchain.chain[item].bloom:
                    realEpochBlist.append(item)
        
            # No need to verify the first block of the owner, as it has been checked before
            if len(uncheckedBList) > 0 and uncheckedBList[0] == oldEpochFlag:
                uncheckedBList.pop(0)
            if len(realEpochBlist) > 0 and realEpochBlist[0] == oldEpochFlag:
                realEpochBlist.pop(0)
        
            if uncheckedBList != realEpochBlist:
                # If different, need to check bloom proof, to exclude the possibility of being "accidentally hit" by the bloom filter
                if bloomPrf == []:
                    print("VPB detection error: No bloom proof provided")
                    return False  # No bloom proof provided, so no accidental hit, therefore, the owner's record of holding the value and the real record differ, error!
                else:
                    # todo: Check bloom proof
                    pass
            oldEpochFlag = epochChangeList[index]
        
        # Record program end time
        check_end_time = time.time()
        # Calculate program running time
        VerTime = check_end_time - check_start_time
        self.verifyTimeCostList.append(VerTime)
        self.verifyStorageCostList.append(PrfSize)
        
        return True

        def generate_txn_prf_when_use(self, begin_index, end_index): # begin_index, end_index respectively indicate the block number where this txn starts and ends in this account
            # proof = Original proof + Newly generated proof (proof within this account period)
            # Data structure of proof unit: (Block number, mTree proof)
            # Generate new proof (proof within this account period)
            new_proof = []
            pass

    def check_VPB_pair_self_dst(self, VPBpair, blockchain):
        # this block_index means added and unchecked VPB pair's latest B (block_index),
        # where the value is confirmed on the longest chain

        # this func is self check for VPB pair, which is prepared to be sent
        # without VPB self check, some proof may be loss in distribute network

        block_index_lst = VPBpair[2]
        latest_block_index = block_index_lst[-1]
        # traverse longest chain, and check if some proof be loss
        if latest_block_index > blockchain.get_latest_block_index():
            return False
        # find the block index when this value first recv by this acc node
        start_index = None
        self_addr = self.addr
        if VPBpair[1].prfList[-2].owner != self_addr: # in the latest prf unit, value has been transfered to new owner, [-2] must be self
            return False # if not self, means that some proofs are loss
        latest_prf_index = len(VPBpair[1].prfList) - 2 # index of latest prf, where self owns this value
        end_index = len(VPBpair[1].prfList) - 2
        while latest_prf_index >= 0:
            if VPBpair[1].prfList[latest_prf_index].owner != self_addr:
                # find the first block index where self recv this value
                start_index = latest_prf_index + 1
            latest_prf_index -= 1
        # check blockchain's bloom (include self addr?) within [blockchain.chain[VPBpair[2][start_index]], blockchain.chain[VPBpair[2][end_index]]]
        index = VPBpair[2][start_index]
        real_block_index = []
        while index <= VPBpair[2][end_index]:
            if self_addr in blockchain.chain[index].bloom:
                real_block_index.append(index)
        if real_block_index != block_index_lst[start_index: end_index + 1]:
            # blockchain's bloom does not match the block index list in VPBpair
            return False


    def check_block_sig(self, block, signature, load_public_key):
        # 从公钥路径加载公钥
        # with open(load_public_key_path, "rb") as key_file:
        public_key = load_pem_public_key(load_public_key)
        # 使用SHA256哈希算法计算区块的哈希值
        block_hash = hashes.Hash(hashes.SHA256())
        block_hash.update(block.block_to_str().encode('utf-8'))
        digest = block_hash.finalize()
        signature_algorithm = ec.ECDSA(hashes.SHA256())
        # 验证签名
        try:
            public_key.verify(
                signature,
                digest,
                signature_algorithm
            )
            return True
        except:
            return False

    def update_VPB_pairs_dst(self, mTree_proof, block_index, costed_values_and_recipes, blockchain):
        # this function update self VPB pair, and return the value index that need to be sent
        # *** the mTree_proof is immutable since it has experienced at least MAX_FORK_HEIGHT blocks
        sender = self.addr
        owner = sender
        ownerAccTxnsList = self.accTxns
        ownerMTreePrfList = mTree_proof
        costValueIndex = []  # record the VPB's index can be sent
        cost_value_recipient = [] # record the list of recipient of VPB (that will be sent).
        added_value_index = [] # record the VPB's index which have been added new VPB

        VList = [t[0] for t in self.ValuePrfBlockPair]
        # the value in costed lst should be processed specially
        for (costedV, recipient) in costed_values_and_recipes:
            # for all: values and recipients in this acc_txns_package
            for item, V in enumerate(VList, start=0):
                # for all: values that self owns
                if V.isSameValue(costedV):
                    # create proof unit
                    prfUnit = unit.ProofUnit(owner=recipient, ownerAccTxnsList=ownerAccTxnsList,
                                             ownerMTreePrfList=ownerMTreePrfList)
                    # update VPB pair (since this value will be sent, the vpb info should be added in the latest position)
                    self.ValuePrfBlockPair[item][1].add_prf_unit(prfUnit)
                    self.ValuePrfBlockPair[item][2].append(copy.deepcopy(block_index))
                    # test: if the value's block index is added repeatedly
                    # the longest chain's record of value's block index CANNOT be repeated
                    test = self.ValuePrfBlockPair[item][2]
                    if len(test) > 2 and test[-1] == test[-2]:
                        raise ValueError("ERR: add VPB failed!")
                    # update added_value_index
                    added_value_index.append(item)
                    # check if this VPB can pass recipient's test
                    if self.check_VPB_pair_self_dst(VPBpair=self.ValuePrfBlockPair[item],
                                                 blockchain=blockchain):
                        # this value's P&B is checked and can be sent to recipient
                        costValueIndex.append(item)
                        cost_value_recipient.append(recipient)
                    else:
                        # this value is still missing some proof (due to distributed transfer delay or other reason)
                        pass

        # process the value not in costed lst
        for item, VPBpair in enumerate(self.ValuePrfBlockPair, start=0):
            if item not in added_value_index: # not the values that have been added
                # NOT change the owner
                prfUnit = unit.ProofUnit(owner=owner, ownerAccTxnsList=ownerAccTxnsList,
                                         ownerMTreePrfList=ownerMTreePrfList)
                # can not add vpb info directly, should confirm the added position
                self.add_one_VPB_dst(vbp_index=item, add_prfUnit=prfUnit, add_block_index=block_index)
                # test: if the value is added repeatedly
                test = self.ValuePrfBlockPair[item][2]
                if len(test) > 2 and test[-1] == test[-2]:
                    raise ValueError("ERR: add VPB failed!")
                # check that if the VPB can be sent to recipient after update?
                if owner != self.ValuePrfBlockPair[item][1].get_latest_prf_unit_owner_dst():
                    # latest owner is NOT self, thus this vpb should be sent to recipient
                    # check if this VPB can pass recipient's test
                    if self.check_VPB_pair_self_dst(VPBpair=self.ValuePrfBlockPair[item],
                                                    blockchain=blockchain):
                        # this value's P&B is checked and can be sent to recipient
                        costValueIndex.append(item)
                        cost_value_recipient.append(self.ValuePrfBlockPair[item][1].get_latest_prf_unit_owner_dst())
                    else:
                        # this value is still missing some proof (due to distributed transfer delay or other reason)
                        pass
        return costValueIndex, cost_value_recipient

    def add_one_VPB_dst(self, vbp_index, add_prfUnit, add_block_index):
        # add one VPB in DST mode
        # if success added, return True, otherwise, return False
        # find the position where this vpb should be added in the block index list
        block_index_lst = self.ValuePrfBlockPair[vbp_index][2]
        index = len(block_index_lst) - 1
        add_position = None
        while index >= 0:
            if block_index_lst[index] == add_block_index:
                # this block index has been added, so ignore this vpb
                return False
            if block_index_lst[index] < add_block_index:
                # this position should be added
                add_position = index + 1
        if add_position == None:
            return False
        # add P & B to self VPB pairs
        self.ValuePrfBlockPair[vbp_index][1].add_prf_unit_dst(prfUnit=add_prfUnit, add_position=add_position)
        self.ValuePrfBlockPair[vbp_index][2].insert(add_position, add_block_index)
        return True

    def tool_for_send_VPB_pairs_dst(self, recipients, vpb_index):
        # make recipient and the values will be sent to him as:
        # unique_recipients = [recipient_1, recipient_2, ...],
        # new_vpb_index = [[value_1_1, value_1_2, ...], [value_2_1, value_2_2, ...], ...],
        # where value_i_j (j=1,2,...) will be sent to recipient_i.
        # e.g., input: recipient = [1,3,3,1,2]; vpb_index = [1,2,3,4,5]
        # output: unique_recipients = [1, 3, 2]; new_vpb_index = [[1, 4], [2, 3], [5]]
        if len(recipients) != len(vpb_index):
            raise ValueError('ERR: len(recipients) != len(vpb_index)')
        merged_dict = defaultdict(list)
        for index, value in enumerate(recipients):
            merged_dict[value].append(vpb_index[index])
        unique_recipients = list(merged_dict.keys())
        new_vpb_index = [merged_dict[element] for element in unique_recipients]
        return unique_recipients, new_vpb_index

    def del_vpb_pair_dst(self):
        if self.delete_vpb_list != []:
            for index in self.delete_vpb_list:
                self.delete_VPBpair(index)
            self.delete_vpb_list = []

    def send_VPB_pairs_dst(self, sent_vpb_index, recipient_addr):
        # return data struct:
        # unique_recipients = [recipient_1, recipient_2, ...],
        # new_vpb_index = [[value_1_1, value_1_2, ...], [value_2_1, value_2_2, ...], ...],
        # where value_i_j (j=1,2,...) will be sent to recipient_i.
        del_value_index = copy.deepcopy(sent_vpb_index)  # Record the index of the value that needs to be deleted
        for index, VPBpair in enumerate(self.ValuePrfBlockPair, start=0):
            if index in sent_vpb_index:
                del_value_index.append(index)
        # 将需要删除的位置按照降序排序，以免删除元素之后影响后续元素的索引
        del_value_index.sort(reverse=True)
        self.delete_vpb_list = del_value_index # wait for send
        """for i in del_value_index:
            self.delete_VPBpair(i)"""
        (unique_recipients, new_vpb_index) = self.tool_for_send_VPB_pairs_dst(recipient_addr, sent_vpb_index)
        return unique_recipients, new_vpb_index

    def clear_and_fresh_info_dst(self):
        self.accTxns = []
        self.accTxnsIndex = None
        self.costedValuesAndRecipes = []
        self.recipientList = []
        # Check for duplicates in vpb of each round
        # self.test()
        # Update check points based on this round's VPBpairs
        self.del_vpb_pair_dst()
        self.VPBCheckPoints.addAndFreshCheckPoint(self.ValuePrfBlockPair)
        # Update storage cost information for acc
        self.freshStorageCost()