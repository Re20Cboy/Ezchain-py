#!/usr/bin/env python3

"""
Ezchain Web集成测试脚本
"""

import sys
import os

# 添加网站目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'website'))

def test_imports():
    """测试导入是否正常"""
    try:
        print("测试导入Ezchain API...")
        from ezchain_api import ezchain_api
        print("✓ Ezchain API导入成功")
        
        print("测试导入Flask应用...")
        from app import app
        print("✓ Flask应用导入成功")
        
        return True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False

def test_blockchain_initialization():
    """测试区块链初始化"""
    try:
        from ezchain_api import ezchain_api
        
        print("测试区块链初始化...")
        success, message = ezchain_api.initialize_blockchain(node_num=3, account_num=3)
        
        if success:
            print("✓ 区块链初始化成功")
            print(f"  消息: {message}")
            
            # 测试获取统计信息
            stats = ezchain_api.get_blockchain_stats()
            print(f"  节点数: {stats['node_count']}")
            print(f"  账户数: {stats['account_count']}")
            print(f"  区块数: {stats['total_blocks']}")
            
            # 测试获取账户信息
            accounts = ezchain_api.get_accounts()
            print(f"  账户详情: {len(accounts)} 个账户")
            for acc in accounts[:2]:  # 只显示前两个
                print(f"    账户 {acc['id']}: 余额 {acc['balance']}")
            
            return True
        else:
            print(f"✗ 区块链初始化失败: {message}")
            return False
            
    except Exception as e:
        print(f"✗ 区块链初始化测试失败: {e}")
        return False

def test_transaction_creation():
    """测试交易创建"""
    try:
        from ezchain_api import ezchain_api
        
        print("测试交易创建...")
        
        # 确保区块链已初始化
        if not ezchain_api.is_initialized:
            print("  先初始化区块链...")
            success, message = ezchain_api.initialize_blockchain(node_num=3, account_num=3)
            if not success:
                print(f"✗ 区块链初始化失败: {message}")
                return False
        
        # 创建交易
        success, message = ezchain_api.create_transaction(sender_id=0, recipient_id=1, amount=100)
        
        if success:
            print("✓ 交易创建成功")
            print(f"  消息: {message}")
            
            # 检查账户余额变化
            accounts = ezchain_api.get_accounts()
            print(f"  发送方余额: {accounts[0]['balance']}")
            print(f"  接收方余额: {accounts[1]['balance']}")
            
            return True
        else:
            print(f"✗ 交易创建失败: {message}")
            return False
            
    except Exception as e:
        print(f"✗ 交易创建测试失败: {e}")
        return False

def test_mining():
    """测试挖矿功能"""
    try:
        from ezchain_api import ezchain_api
        
        print("测试挖矿功能...")
        
        # 确保区块链已初始化
        if not ezchain_api.is_initialized:
            print("  先初始化区块链...")
            success, message = ezchain_api.initialize_blockchain(node_num=3, account_num=3)
            if not success:
                print(f"✗ 区块链初始化失败: {message}")
                return False
        
        # 开始挖矿
        print("  开始挖矿...")
        success, message = ezchain_api.start_mining()
        
        if success:
            print("✓ 挖矿开始成功")
            
            # 等待一小段时间
            import time
            time.sleep(2)
            
            # 停止挖矿
            success, message = ezchain_api.stop_mining()
            if success:
                print("✓ 挖矿停止成功")
                
                # 获取挖矿状态
                status = ezchain_api.get_mining_status()
                print(f"  当前轮次: {status['current_round']}")
                print(f"  挖矿状态: {'进行中' if status['mining_in_progress'] else '已停止'}")
                
                return True
            else:
                print(f"✗ 挖矿停止失败: {message}")
                return False
        else:
            print(f"✗ 挖矿开始失败: {message}")
            return False
            
    except Exception as e:
        print(f"✗ 挖矿测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 50)
    print("Ezchain Web集成测试")
    print("=" * 50)
    
    tests = [
        ("导入测试", test_imports),
        ("区块链初始化", test_blockchain_initialization),
        ("交易创建", test_transaction_creation),
        ("挖矿功能", test_mining)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n【{test_name}】")
        try:
            if test_func():
                passed += 1
            else:
                print(f"✗ {test_name} 测试失败")
        except Exception as e:
            print(f"✗ {test_name} 测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("✓ 所有测试通过！Ezchain Web集成成功！")
        return True
    else:
        print("✗ 部分测试失败，请检查配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)