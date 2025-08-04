from flask import Flask, render_template, request, jsonify, render_template_string
import os
import sys
import json
import threading
import time
import random
import string
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain import Blockchain
from block import Block
from transaction import Transaction
from node import Node
from account import Account
import unit

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# 全局变量存储区块链状态
blockchain_state = {
    'blockchain': None,
    'nodes': [],
    'accounts': [],
    'transactions': [],
    'mining_in_progress': False,
    'mining_thread': None,
    'stats': {
        'total_blocks': 0,
        'total_transactions': 0,
        'mining_speed': 0,
        'network_hashrate': 0
    }
}

def init_blockchain():
    """初始化区块链系统"""
    # 创建创世区块
    genesis_block = Block(
        index=0,
        m_tree_root=hash(0),
        miner=0,
        pre_hash=hash(0)
    )
    
    # 初始化区块链
    blockchain_state['blockchain'] = Blockchain(GenesisBlock=genesis_block)
    
    # 创建节点
    for i in range(5):
        node = Node(id=i)
        blockchain_state['nodes'].append(node)
    
    # 创建账户
    for i in range(5):
        account = Account(ID=i)
        account.generate_random_account()
        blockchain_state['accounts'].append(account)
    
    # 初始化统计信息
    blockchain_state['stats']['total_blocks'] = 1
    blockchain_state['stats']['network_hashrate'] = 1000  # 假设的算力

def mine_block():
    """模拟挖矿过程"""
    while blockchain_state['mining_in_progress']:
        # 模拟挖矿延迟
        time.sleep(random.uniform(1, 3))
        
        if not blockchain_state['mining_in_progress']:
            break
        
        # 创建新区块
        latest_block = blockchain_state['blockchain'].get_latest_block()
        new_block = Block(
            index=latest_block.get_index() + 1,
            m_tree_root=hash(random.randint(1, 1000)),
            miner=random.randint(0, len(blockchain_state['nodes']) - 1),
            pre_hash=latest_block.get_hash()
        )
        
        # 添加到区块链
        blockchain_state['blockchain'].add_block(new_block)
        blockchain_state['stats']['total_blocks'] += 1
        
        # 更新挖矿速度
        blockchain_state['stats']['mining_speed'] = random.uniform(0.5, 2.0)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/documentation')
def documentation():
    return render_template('documentation.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/blockchain')
def blockchain_page():
    return render_template('blockchain.html')

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'running',
        'version': '1.0.0',
        'name': 'Ezchain Website'
    })

@app.route('/api/blockchain/init', methods=['POST'])
def init_blockchain_api():
    """初始化区块链"""
    try:
        init_blockchain()
        return jsonify({
            'success': True,
            'message': 'Blockchain initialized successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to initialize blockchain: {str(e)}'
        })

@app.route('/api/blockchain/stats')
def get_blockchain_stats():
    """获取区块链统计信息"""
    return jsonify(blockchain_state['stats'])

@app.route('/api/blockchain/blocks')
def get_blocks():
    """获取区块链信息"""
    if blockchain_state['blockchain'] is None:
        return jsonify({'blocks': []})
    
    blocks = []
    for block in blockchain_state['blockchain'].chain:
        blocks.append({
            'index': block.get_index(),
            'hash': block.get_hash(),
            'pre_hash': block.get_pre_hash(),
            'miner': block.miner,
            'time': block.time,
            'nonce': block.nonce,
            'm_tree_root': block.m_tree_root
        })
    
    return jsonify({'blocks': blocks})

@app.route('/api/mining/start', methods=['POST'])
def start_mining():
    """开始挖矿"""
    if blockchain_state['mining_in_progress']:
        return jsonify({
            'success': False,
            'message': 'Mining is already in progress'
        })
    
    blockchain_state['mining_in_progress'] = True
    blockchain_state['mining_thread'] = threading.Thread(target=mine_block)
    blockchain_state['mining_thread'].start()
    
    return jsonify({
        'success': True,
        'message': 'Mining started successfully'
    })

@app.route('/api/mining/stop', methods=['POST'])
def stop_mining():
    """停止挖矿"""
    blockchain_state['mining_in_progress'] = False
    
    if blockchain_state['mining_thread']:
        blockchain_state['mining_thread'].join(timeout=1)
    
    return jsonify({
        'success': True,
        'message': 'Mining stopped successfully'
    })

@app.route('/api/mining/status')
def mining_status():
    """获取挖矿状态"""
    return jsonify({
        'mining_in_progress': blockchain_state['mining_in_progress'],
        'stats': blockchain_state['stats']
    })

@app.route('/api/transaction/create', methods=['POST'])
def create_transaction():
    """创建交易"""
    data = request.get_json()
    
    if not data or 'sender' not in data or 'recipient' not in data or 'amount' not in data:
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        })
    
    try:
        # 创建模拟交易
        transaction_id = ''.join(random.choices(string.hexdigits, k=16))
        transaction_data = {
            'id': transaction_id,
            'sender': data['sender'],
            'recipient': data['recipient'],
            'amount': data['amount'],
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        blockchain_state['transactions'].append(transaction_data)
        blockchain_state['stats']['total_transactions'] += 1
        
        return jsonify({
            'success': True,
            'message': 'Transaction created successfully',
            'transaction': transaction_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to create transaction: {str(e)}'
        })

@app.route('/api/transactions')
def get_transactions():
    """获取交易列表"""
    return jsonify({
        'transactions': blockchain_state['transactions']
    })

@app.route('/api/accounts')
def get_accounts():
    """获取账户列表"""
    accounts = []
    for account in blockchain_state['accounts']:
        accounts.append({
            'id': account.ID,
            'address': account.addr,
            'balance': random.randint(1000, 10000)  # 模拟余额
        })
    
    return jsonify({'accounts': accounts})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)