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


    def generate_random_account(self):
        # Generate a random address
        self.addr = ''.join(random.choices(string.ascii_letters + string.digits, k=42))  # Bitcoin address is 42 characters long
        # Generate a private key
        private_key = ec.generate_private_key(ec.SECP384R1())
        # Obtain the public key from the private key
        public_key = private_key.public_key()
        # Save the addresses of the public and private keys
        privatePath = ACCOUNT_PRIVATE_KEY_PATH + "private_key_node_"+str(self.id)+".pem"
        publicPath = ACCOUNT_PUBLIC_KEY_PATH + "public_key_node_"+str(self.id)+".pem"
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
        # 先检测check point，若有无需检测的vpb则直接跳过
        ckList = self.VPBCheckPoints.findCKviaVPB(VPBpair)
        passIndexList = None
        CKOwner = None
        if ckList != []: # 找到了对应的check point
            ckOwner, ckBIndex = ckList[0]
            flagIndex = None # CK记录到了VPB的哪一位
            for index, item in enumerate(VPBpair[2],start=0):
                if item == ckBIndex[-1]:
                    flagIndex = index
            if flagIndex == None:
                raise ValueError('VPB检测报错：此VPB与检查点记录有冲突！')
            VPBOwner = VPBpair[1].prfList[flagIndex].owner
            if VPBOwner != ckOwner:
                raise ValueError('VPB检测报错：此VPB与检查点记录有冲突！')
            passIndexList = list(range(flagIndex+1))
            CKOwner = ckOwner

        # 统计验证消耗
        PrfSize = (asizeof.asizeof(VPBpair) + asizeof.asizeof(bloomPrf)) * 8 # *8转换为以bit为单位
        # 记录程序开始时间
        check_start_time = time.time()

        def hash(val):
            if type(val) == str:
                return hashlib.sha256(val.encode("utf-8")).hexdigest()
            else:
                return hashlib.sha256(val).hexdigest()

        ##############################
        ######## 1 检测数据类型：########
        ##############################
        if type(VPBpair[0]) != unit.Value or type(VPBpair[1]) != unit.Proof or type(VPBpair[2]) != list:
            print("VPB检测报错：数据结构错误")
            return False # 数据结构错误

        value = VPBpair[0]
        valuePrf = VPBpair[1].prfList
        blockIndex = VPBpair[2]

        if len(valuePrf) != len(blockIndex):
            print("VPB检测报错：证据和块索引非一一映射")
            return False # 证据和块索引非一一映射，固错误

        ##############################
        ######## 2 检测value的结构合法性：
        ##############################
        if not value.checkValue:
            print("VPB检测报错：value的结构合法性检测不通过")
            return False # value的结构合法性检测不通过




        if passIndexList:
            return self.check_pass_VPBpair(VPBpair, bloomPrf, blockchain, passIndexList, CKOwner, check_start_time)




        recordOwner = None # 此变量用于记录值流转的持有者
        epochRealBList = [] # 记录epoch内的真实的B的信息，用于和VPB中的B进行对比
        BList = [] # 记录epoch内的VPB的B的信息，结构为：[(owner,[list of block index]), (...), (...), ...]用于进行对比验证
        oneEpochBList = [] # 结构为：[list of block index]
        epochChangeList = [] # 记录epoch变化时的区块号

        ##############################
        ######## 3 检验proof的正确性 ###
        ##############################
        for index, prfUnit in enumerate(valuePrf, start=0):
            # 由于第一个prfUnit是创世块中的交易因此需要特殊的验证处理
            if index == 0: # 说明是创世块
                recordOwner = prfUnit.owner
                ownerAccTxnsList = prfUnit.ownerAccTxnsList
                ownerMTreePrfList = prfUnit.ownerMTreePrfList
                # 创世块的检测
                if ownerMTreePrfList == [blockchain.chain[0].get_m_tree_root()]:  # 说明这是创世块
                    tmpGenesisAccTxns = transaction.AccountTxns(GENESIS_SENDER, -1, ownerAccTxnsList)
                    tmpEncode = tmpGenesisAccTxns.Encode()
                    if hash(tmpEncode) != blockchain.chain[0].get_m_tree_root():
                        print("VPB检测报错：交易集合哈希错误，节点伪造了创世块中的交易")
                        return False  # 树根值错误，说明节点伪造了创世块中的交易。
                    # 检测此value是否在创世块中且持有者是创世块中的接收者：
                    for genesisTxn in ownerAccTxnsList:
                        if genesisTxn.Recipient == recordOwner:
                            if not genesisTxn.Value.isInValue(value):
                                print("VPB检测报错：此值溯源到创世块中发现为非法值")
                                return False
                else:
                    print("VPB检测报错：proof中创世块树根检测错误")
                    return False
                oneEpochBList.append(blockIndex[index])

            else: # 非创世块检测
                isNewEpoch = False
                oneEpochBList.append(blockIndex[index])
                tmpSender = None # 记录每个epoch变更时的交易的发送者，以便验证bloom
                if recordOwner != prfUnit.owner: # 说明 owner 已改变，该值进入下一个owner持有的epoch
                    isNewEpoch = True
                    lastBlockIndex = oneEpochBList.pop() # 获得最后一个交易的区块号
                    # 更新epoch内的VPB的B的信息
                    BList.append((copy.deepcopy(recordOwner), copy.deepcopy(oneEpochBList)))
                    oneEpochBList = [lastBlockIndex] # 为下一段证明保留最初的交易所在的区块号
                    epochChangeList.append(lastBlockIndex)
                    tmpSender = recordOwner
                    recordOwner = prfUnit.owner  # 更新持有者信息

                ownerAccTxnsList = prfUnit.ownerAccTxnsList
                ownerMTreePrfList = prfUnit.ownerMTreePrfList

                # 检测：ownerAccTxnsList和ownerMTreePrfList的信息是相符的
                # 注意，这里的Encode()函数只对accTxns进行编码，因此可以设sender='sender'，senderID=None 结果不影响。
                uncheckedAccTxns = transaction.AccountTxns(sender='sender', senderID=None, accTxns=ownerAccTxnsList)
                uncheckedMTreePrf = unit.MTreeProof(MTPrfList=ownerMTreePrfList)
                uncheckedAccTxns.set_digest()
                accTxnsDigest = uncheckedAccTxns.Digest
                # 检测：ownerMTreePrfList和主链此块中的root是相符的
                if not uncheckedMTreePrf.checkPrf(accTxnsDigest=accTxnsDigest, trueRoot=blockchain.chain[blockIndex[index]].get_m_tree_root()):
                    print("VPB检测报错：默克尔树检测未通过")
                    return False # 默克尔树检测未通过，固错误！

                if isNewEpoch:
                    # 所有txn中应当有且仅有一个交易将值转移到新的owner手中
                    SpendValueTxnList = [] # 记录在此accTxns中此值被转移的所有交易，合法的情况下，此list的长度应为1
                    for txn in ownerAccTxnsList:
                        count = txn.count_value_in_value(value)
                        if count == 1: # =0表示未转移该值，>1则表明在此交易内存在双花
                            if txn.Sender != txn.Recipient:  # 若不是转移给自己则计入值的花销列表
                                SpendValueTxnList.append(txn)
                        elif count > 1:
                            print("VPB检测报错：单个交易内存在双花！")
                            return False  # 存在双花！或者未转移值给owner！
                    if len(SpendValueTxnList) != 1:
                        print("VPB检测报错：存在双花！或者未转移值给owner！")
                        return False # 存在双花！或者未转移值给owner！
                    if tmpSender != None and tmpSender not in blockchain.chain[blockIndex[index]].bloom:
                        print("VPB检测报错：值转移时的Bloom过滤器检测错误！")
                        return False
                    if SpendValueTxnList[0].Recipient != recordOwner:
                        print("VPB检测报错：此值未转移给指定的owner")
                        return False # 此值未转移给指定的owner
                else:
                    # 未进入新epoch，即，此值尚未转移给新的owner
                    for txn in ownerAccTxnsList:
                        if txn.count_value_intersect_txn(value) != 0:
                            if txn.Sender != txn.Recipient:
                                print("VPB检测报错：此值不应当在此处被提前花费")
                                return False # 此值不应当在此处被花费！
        ##############################
        # 4 检测：每个epoch内的B和主链上的布隆过滤器的信息是相符的，即，epoch的owner没有在B上撒谎
        ##############################
        if len(BList) != len(epochChangeList):
            print("VPB检测报错：len(BList) != len(epochChangeList)")
            return False
        oldEpochFlag = 0
        for index, epochRecord in enumerate(BList, start=0):
            fullEpochBList = range(oldEpochFlag, epochChangeList[index])
            realEpochBlist = []
            (owner, uncheckedBList) = epochRecord

            if len(uncheckedBList) < 1:
                print("VPB检测报错：本段owner持有值没有记录")
                return False  # 本段owner持有值没有记录，固错误！

            ownerBegin = uncheckedBList[0]  # owner刚拥有该值时的block index
            ownerEnd = uncheckedBList[-1]  # owner将在下一个区块将此值转移给其他owner，即，最后一个持有此值的block index
            if ownerEnd < ownerBegin:
                print("VPB检测报错：owner持有值的区块号记录有误")
                return False  # owner持有值的区块号记录有误！

            for item in fullEpochBList:
                if owner in blockchain.chain[item].bloom:
                    realEpochBlist.append(item)

            # 不需要检验owner持有的第一个块，因为已在前面检测过
            if len(uncheckedBList) > 0 and uncheckedBList[0] == oldEpochFlag:
                uncheckedBList.pop(0)
            if len(realEpochBlist) > 0 and realEpochBlist[0] == oldEpochFlag:
                realEpochBlist.pop(0)

            if uncheckedBList != realEpochBlist:
                # 若不同则需要检测bloom proof，排除被bloom过滤器“误伤”的可能
                if bloomPrf == []:
                    print("VPB检测报错：没有提供bloom proof")
                    return False  # 没有提供bloom proof，因此没有误伤，则说明owner提供的值持有记录和真实记录不同，错误！
                else:
                    # todo: 检测bloom proof
                    pass
            oldEpochFlag = epochChangeList[index]

        # 记录程序结束时间
        check_end_time = time.time()
        # 计算程序运行时间
        VerTime = check_end_time - check_start_time
        self.verifyTimeCostList.append(VerTime)
        self.verifyStorageCostList.append(PrfSize)

        return True

    def generate_txn_prf_when_use(self, begin_index, end_index): # begin_index, end_index分别表示此txn在本账户手中开始的区块号和结束的区块号
        # proof = 原证明 + 新生成的证明（在此account时期内的证明）
        # proof单元的数据结构：（区块号，mTree证明）
        # 生成new proof（在此account时期内的证明）
        new_proof = []
        pass