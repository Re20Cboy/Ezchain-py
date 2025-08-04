from flask import Flask, render_template, request, jsonify, render_template_string
import os
import sys

# 导入Ezchain API封装
from ezchain_api import ezchain_api

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

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
        success, message = ezchain_api.initialize_blockchain()
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to initialize blockchain: {str(e)}'
        })

@app.route('/api/blockchain/stats')
def get_blockchain_stats():
    """获取区块链统计信息"""
    stats = ezchain_api.get_blockchain_stats()
    return jsonify(stats)

@app.route('/api/blockchain/blocks')
def get_blocks():
    """获取区块链信息"""
    blocks = ezchain_api.get_blocks()
    return jsonify({'blocks': blocks})

@app.route('/api/mining/start', methods=['POST'])
def start_mining():
    """开始挖矿"""
    success, message = ezchain_api.start_mining()
    return jsonify({
        'success': success,
        'message': message
    })

@app.route('/api/mining/stop', methods=['POST'])
def stop_mining():
    """停止挖矿"""
    success, message = ezchain_api.stop_mining()
    return jsonify({
        'success': success,
        'message': message
    })

@app.route('/api/mining/status')
def mining_status():
    """获取挖矿状态"""
    status = ezchain_api.get_mining_status()
    return jsonify(status)

@app.route('/api/transaction/create', methods=['POST'])
def create_transaction():
    """创建交易"""
    data = request.get_json()
    
    if not data or 'sender_id' not in data or 'recipient_id' not in data or 'amount' not in data:
        return jsonify({
            'success': False,
            'message': 'Missing required fields: sender_id, recipient_id, amount'
        })
    
    try:
        sender_id = int(data['sender_id'])
        recipient_id = int(data['recipient_id'])
        amount = int(data['amount'])
        
        success, message = ezchain_api.create_transaction(sender_id, recipient_id, amount)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to create transaction: {str(e)}'
        })

@app.route('/api/transactions')
def get_transactions():
    """获取交易列表"""
    # 获取所有账户的交易
    transactions = []
    accounts = ezchain_api.get_accounts()
    
    for account in accounts:
        # 这里简化处理，实际需要从账户中提取交易信息
        pass
    
    return jsonify({
        'transactions': transactions
    })

@app.route('/api/accounts')
def get_accounts():
    """获取账户列表"""
    accounts = ezchain_api.get_accounts()
    return jsonify({'accounts': accounts})

@app.route('/api/nodes')
def get_nodes():
    """获取节点列表"""
    nodes = ezchain_api.get_nodes()
    return jsonify({'nodes': nodes})

@app.route('/api/blockchain/reset', methods=['POST'])
def reset_blockchain():
    """重置区块链"""
    success, message = ezchain_api.reset_blockchain()
    return jsonify({
        'success': success,
        'message': message
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)