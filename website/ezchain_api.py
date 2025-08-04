"""
Ezchain Web API Wrapper
将网页界面与原有的Ezchain区块链功能连接起来
"""

import os
import sys
import threading
import time
import json
import copy
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Ezchain_simulate
import block
import blockchain
import transaction
import node
import account
import unit
from const import *

class EzchainWebAPI:
    """Ezchain Web API 封装类"""
    
    def __init__(self):
        self.simulator = None
        self.is_initialized = False
        self.mining_thread = None
        self.mining_in_progress = False
        self.current_round = 0
        self.lock = threading.Lock()
        
    def initialize_blockchain(self, node_num=NODE_NUM, account_num=ACCOUNT_NUM):
        """初始化区块链系统"""
        try:
            with self.lock:
                if self.is_initialized:
                    return False, "Blockchain already initialized"
                
                # 创建模拟器实例
                self.simulator = Ezchain_simulate.EZsimulate()
                
                # 设置参数
                self.simulator.nodeNum = node_num
                self.simulator.accounts = []
                self.simulator.nodeList = []
                self.simulator.hashPower = []
                self.simulator.current_round = 0
                
                # 生成节点
                self.simulator.random_generate_nodes(node_num)
                
                # 生成账户
                self.simulator.random_generate_accounts(account_num)
                
                # 初始化网络
                self.simulator.init_network()
                
                # 生成创世区块
                self.simulator.generate_GenesisBlock()
                
                self.is_initialized = True
                self.current_round = 0
                
                return True, "Blockchain initialized successfully"
                
        except Exception as e:
            return False, f"Initialization failed: {str(e)}"
    
    def get_blockchain_stats(self):
        """获取区块链统计信息"""
        if not self.is_initialized or not self.simulator:
            return {
                'total_blocks': 0,
                'total_transactions': 0,
                'mining_speed': 0,
                'network_hashrate': 0,
                'node_count': 0,
                'account_count': 0,
                'current_round': 0
            }
        
        # 计算总交易数
        total_transactions = 0
        if self.simulator.blockchain and self.simulator.blockchain.chain:
            for block in self.simulator.blockchain.chain:
                # 这里简化计算，实际需要从区块中提取交易信息
                total_transactions += len(self.simulator.accounts) * 2  # 估算值
        
        return {
            'total_blocks': len(self.simulator.blockchain.chain) if self.simulator.blockchain else 0,
            'total_transactions': total_transactions,
            'mining_speed': 1.0 / HASH_DIFFICULTY if self.mining_in_progress else 0,
            'network_hashrate': HASH_POWER * len(self.simulator.nodeList),
            'node_count': len(self.simulator.nodeList),
            'account_count': len(self.simulator.accounts),
            'current_round': self.current_round
        }
    
    def get_blocks(self):
        """获取区块列表"""
        if not self.is_initialized or not self.simulator or not self.simulator.blockchain:
            return []
        
        blocks = []
        for block in self.simulator.blockchain.chain:
            blocks.append({
                'index': block.get_index(),
                'hash': block.get_hash(),
                'pre_hash': block.get_pre_hash(),
                'miner': block.miner,
                'time': block.time,
                'nonce': block.nonce,
                'm_tree_root': block.m_tree_root,
                'bloom_size': len(block.bloom) if hasattr(block, 'bloom') else 0,
                'signature': str(block.sig) if hasattr(block, 'sig') else ''
            })
        
        return blocks
    
    def get_accounts(self):
        """获取账户列表"""
        if not self.is_initialized or not self.simulator:
            return []
        
        accounts = []
        for acc in self.simulator.accounts:
            accounts.append({
                'id': acc.ID,
                'address': acc.addr,
                'balance': acc.balance,
                'public_key': str(acc.publicKey)[:100] + '...' if acc.publicKey else '',
                'transaction_count': len(acc.accTxns)
            })
        
        return accounts
    
    def get_nodes(self):
        """获取节点列表"""
        if not self.is_initialized or not self.simulator:
            return []
        
        nodes = []
        for node in self.simulator.nodeList:
            nodes.append({
                'id': node.id,
                'address': node.addr,
                'neighbor_count': len(node.neighbors),
                'block_count': len(node.blockchain.chain) if node.blockchain else 0,
                'public_key': str(node.publicKey)[:100] + '...' if node.publicKey else ''
            })
        
        return nodes
    
    def start_mining(self):
        """开始挖矿"""
        if not self.is_initialized:
            return False, "Blockchain not initialized"
        
        if self.mining_in_progress:
            return False, "Mining already in progress"
        
        self.mining_in_progress = True
        self.mining_thread = threading.Thread(target=self._mining_worker)
        self.mining_thread.start()
        
        return True, "Mining started successfully"
    
    def stop_mining(self):
        """停止挖矿"""
        if not self.mining_in_progress:
            return False, "Mining not in progress"
        
        self.mining_in_progress = False
        
        if self.mining_thread:
            self.mining_thread.join(timeout=5)
        
        return True, "Mining stopped successfully"
    
    def _mining_worker(self):
        """挖矿工作线程"""
        while self.mining_in_progress and self.current_round < SIMULATE_ROUND:
            try:
                # 生成交易
                account_txns, _ = self.simulator.random_generate_AccTxns(PICK_TXNS_NUM)
                
                # 将交易添加到交易池
                self.simulator.txnsPool.freshPool(self.simulator.accounts, account_txns)
                
                # 生成区块体
                block_body = self.simulator.generate_block_body()
                
                # 模拟挖矿过程
                time.sleep(HASH_DIFFICULTY * 10)  # 模拟挖矿时间
                
                if not self.mining_in_progress:
                    break
                
                # 选择矿工（简化版，实际应该基于算力）
                miner_index = self.current_round % len(self.simulator.nodeList)
                miner_node = self.simulator.nodeList[miner_index]
                
                # 创建新区块
                miner_node.tmpBlockBodyMsg = block_body
                miner_node.create_new_block()
                
                # 广播区块给所有节点
                for node in self.simulator.nodeList:
                    if node.id != miner_index:
                        node.blockchain.add_block(miner_node.tmpBlockMsg.block)
                
                # 清空交易池
                self.simulator.txnsPool.clearPool()
                
                # 更新账户状态
                for acc in self.simulator.accounts:
                    acc.clear_and_fresh_info()
                
                self.current_round += 1
                
            except Exception as e:
                print(f"Mining error: {e}")
                break
    
    def create_transaction(self, sender_id, recipient_id, amount):
        """创建交易"""
        if not self.is_initialized:
            return False, "Blockchain not initialized"
        
        try:
            # 验证账户ID
            if sender_id < 0 or sender_id >= len(self.simulator.accounts):
                return False, "Invalid sender ID"
            
            if recipient_id < 0 or recipient_id >= len(self.simulator.accounts):
                return False, "Invalid recipient ID"
            
            sender = self.simulator.accounts[sender_id]
            recipient = self.simulator.accounts[recipient_id]
            
            # 验证余额
            if sender.balance < amount:
                return False, "Insufficient balance"
            
            # 创建Value对象
            v_genesis_begin = '0x77777777777777777777777777777777777777777777777777777777777777777'
            v_genesis_num = amount
            V = unit.Value(beginIndex=v_genesis_begin, valueNum=v_genesis_num)
            
            # 创建交易
            tx = transaction.Transaction(
                sender=sender.addr,
                recipient=recipient.addr,
                nonce=len(sender.accTxns),
                signature=None,
                value=V,
                tx_hash=0,
                time=datetime.now()
            )
            
            # 对交易进行签名
            tx.sig_txn(sender.privateKey)
            
            # 添加到发送者的交易列表
            sender.accTxns.append(tx)
            
            # 更新余额（简化处理）
            sender.balance -= amount
            recipient.balance += amount
            
            return True, f"Transaction created successfully from account {sender_id} to {recipient_id}"
            
        except Exception as e:
            return False, f"Failed to create transaction: {str(e)}"
    
    def get_mining_status(self):
        """获取挖矿状态"""
        return {
            'mining_in_progress': self.mining_in_progress,
            'current_round': self.current_round,
            'max_rounds': SIMULATE_ROUND,
            'stats': self.get_blockchain_stats()
        }
    
    def reset_blockchain(self):
        """重置区块链"""
        try:
            with self.lock:
                self.stop_mining()
                self.simulator = None
                self.is_initialized = False
                self.current_round = 0
                return True, "Blockchain reset successfully"
        except Exception as e:
            return False, f"Failed to reset blockchain: {str(e)}"

# 全局API实例
ezchain_api = EzchainWebAPI()