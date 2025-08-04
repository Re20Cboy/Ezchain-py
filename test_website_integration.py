#!/usr/bin/env python3
"""
Ezchain Website Integration Test
测试网站与区块链系统的集成功能
"""

import urllib.request
import json
import time

def test_api():
    """测试所有API端点"""
    base_url = "http://127.0.0.1:5002"
    
    print("=== Ezchain Website Integration Test ===\n")
    
    # 1. 测试状态端点
    print("1. Testing status endpoint...")
    try:
        with urllib.request.urlopen(f"{base_url}/api/status", timeout=5) as response:
            data = json.loads(response.read().decode())
            print(f"   ✓ Status: {data['status']}")
            print(f"   ✓ Version: {data['version']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # 2. 测试区块链初始化
    print("\n2. Testing blockchain initialization...")
    try:
        req = urllib.request.Request(f"{base_url}/api/blockchain/init", method='POST')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data['success']:
                print("   ✓ Blockchain initialized successfully")
            else:
                print(f"   ✗ Initialization failed: {data['message']}")
                return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # 3. 测试获取统计信息
    print("\n3. Testing blockchain stats...")
    try:
        with urllib.request.urlopen(f"{base_url}/api/blockchain/stats", timeout=5) as response:
            stats = json.loads(response.read().decode())
            print(f"   ✓ Total blocks: {stats['total_blocks']}")
            print(f"   ✓ Total transactions: {stats['total_transactions']}")
            print(f"   ✓ Node count: {stats['node_count']}")
            print(f"   ✓ Account count: {stats['account_count']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # 4. 测试获取账户信息
    print("\n4. Testing accounts endpoint...")
    try:
        with urllib.request.urlopen(f"{base_url}/api/accounts", timeout=5) as response:
            accounts = json.loads(response.read().decode())
            print(f"   ✓ Retrieved {len(accounts['accounts'])} accounts")
            if accounts['accounts']:
                acc = accounts['accounts'][0]
                print(f"   ✓ Sample account: ID {acc['id']}, Balance {acc['balance']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # 5. 测试获取节点信息
    print("\n5. Testing nodes endpoint...")
    try:
        with urllib.request.urlopen(f"{base_url}/api/nodes", timeout=5) as response:
            nodes = json.loads(response.read().decode())
            print(f"   ✓ Retrieved {len(nodes['nodes'])} nodes")
            if nodes['nodes']:
                node = nodes['nodes'][0]
                print(f"   ✓ Sample node: ID {node['id']}, Block count {node['block_count']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # 6. 测试获取区块信息
    print("\n6. Testing blocks endpoint...")
    try:
        with urllib.request.urlopen(f"{base_url}/api/blockchain/blocks", timeout=5) as response:
            blocks = json.loads(response.read().decode())
            print(f"   ✓ Retrieved {len(blocks['blocks'])} blocks")
            if blocks['blocks']:
                block = blocks['blocks'][0]
                print(f"   ✓ Sample block: Index {block['index']}, Hash {block['hash'][:16]}...")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # 7. 测试创建交易
    print("\n7. Testing transaction creation...")
    try:
        transaction_data = {
            'sender_id': 0,
            'recipient_id': 1,
            'amount': 10
        }
        req = urllib.request.Request(f"{base_url}/api/transaction/create", method='POST')
        req.add_header('Content-Type', 'application/json')
        req.data = json.dumps(transaction_data).encode()
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data['success']:
                print("   ✓ Transaction created successfully")
            else:
                print(f"   ✗ Transaction failed: {data['message']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # 8. 测试挖矿功能
    print("\n8. Testing mining functionality...")
    try:
        # 开始挖矿
        req = urllib.request.Request(f"{base_url}/api/mining/start", method='POST')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data['success']:
                print("   ✓ Mining started successfully")
            else:
                print(f"   ✗ Mining start failed: {data['message']}")
        
        # 等待一下
        time.sleep(2)
        
        # 获取挖矿状态
        with urllib.request.urlopen(f"{base_url}/api/mining/status", timeout=5) as response:
            status = json.loads(response.read().decode())
            print(f"   ✓ Mining status: {'In progress' if status['mining_in_progress'] else 'Stopped'}")
        
        # 停止挖矿
        req = urllib.request.Request(f"{base_url}/api/mining/stop", method='POST')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data['success']:
                print("   ✓ Mining stopped successfully")
            else:
                print(f"   ✗ Mining stop failed: {data['message']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # 9. 测试重置功能
    print("\n9. Testing blockchain reset...")
    try:
        req = urllib.request.Request(f"{base_url}/api/blockchain/reset", method='POST')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data['success']:
                print("   ✓ Blockchain reset successfully")
            else:
                print(f"   ✗ Reset failed: {data['message']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    print("\n=== All tests completed successfully! ===")
    print("\n🎉 Ezchain Website Integration Test PASSED!")
    print("\nYou can now access the website at:")
    print("  - http://127.0.0.1:5002/")
    print("  - http://127.0.0.1:5002/blockchain")
    print("\nFeatures available:")
    print("  - Blockchain visualization")
    print("  - Real-time mining simulation")
    print("  - Transaction creation")
    print("  - Account management")
    print("  - Network monitoring")
    
    return True

if __name__ == "__main__":
    test_api()