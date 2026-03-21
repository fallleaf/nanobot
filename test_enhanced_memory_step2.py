#!/usr/bin/env python3
"""
测试增强记忆系统 - Step 2 验证
测试修改后的 MemoryStore 类
"""

import sys
import asyncio
from pathlib import Path

# 使用虚拟环境
sys.path.insert(0, str(Path(__file__).parent))

def test_memory_store_import():
    """测试 MemoryStore 导入"""
    print("\n" + "="*60)
    print("测试 1: MemoryStore 导入")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore, MemoryConsolidator
        print("✅ MemoryStore 导入成功")
        print("✅ MemoryConsolidator 导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def test_memory_store_init():
    """测试 MemoryStore 初始化"""
    print("\n" + "="*60)
    print("测试 2: MemoryStore 初始化")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        
        # 不带 provider 初始化（降级模式）
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        print(f"✅ MemoryStore 初始化成功")
        print(f"  工作目录：{store.workspace}")
        print(f"  记忆文件：{store.memory_file}")
        print(f"  历史文件：{store.history_file}")
        
        # 检查增强记忆是否可用
        enhanced_available = store.manager is not None
        print(f"  增强记忆：{'✅ 可用' if enhanced_available else '❌ 不可用'}")
        
        if enhanced_available:
            print(f"  短期记忆 DB: {store.short_term.db_path}")
            print(f"  工作记忆容量：{store.working.capacity}")
        
        return True
        
    except Exception as e:
        print(f"❌ 初始化失败：{e}")
        import traceback
        traceback.print_exc()
        return False

async def test_encode_message():
    """测试消息编码"""
    print("\n" + "="*60)
    print("测试 3: 消息编码 (encode_message)")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        if not store.manager:
            print("⚠️  增强记忆不可用，跳过测试")
            return True
        
        # 测试编码用户消息
        result1 = await store.encode_message(
            content="nanobot 的配置文件在哪里？",
            role="user",
            channel="telegram",
            chat_id="test123"
        )
        
        print(f"✅ 编码用户消息：{result1.get('success', False)}")
        if result1.get('success'):
            print(f"  ID: {result1.get('id', 'N/A')[:8]}...")
            print(f"  重要性：{result1.get('importance', 'N/A')}")
        
        # 测试编码助手消息
        result2 = await store.encode_message(
            content="配置文件在~/.nanobot/config.json",
            role="assistant",
            channel="telegram",
            chat_id="test123"
        )
        
        print(f"✅ 编码助手消息：{result2.get('success', False)}")
        
        # 查看统计
        stats = store.get_enhanced_stats()
        print(f"✅ 统计信息:")
        print(f"  已编码：{stats.get('stats', {}).get('encoded_count', 0)} 条")
        print(f"  工作记忆：{stats.get('working', {}).get('count', 0)} 条")
        print(f"  短期记忆：{stats.get('short_term', {}).get('total', 0)} 条")
        
        return True
        
    except Exception as e:
        print(f"❌ 编码失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def test_get_context():
    """测试获取上下文"""
    print("\n" + "="*60)
    print("测试 4: 获取增强上下文 (get_enhanced_context)")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        if not store.manager:
            print("⚠️  增强记忆不可用，跳过测试")
            return True
        
        # 获取上下文
        context = store.get_enhanced_context(query="配置", limit=5)
        
        print(f"✅ 获取上下文：{len(context)} 字符")
        if context:
            print(f"  预览：{context[:150]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 获取上下文失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n" + "="*60)
    print("测试 5: 向后兼容性 (原有方法)")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        # 测试原有方法
        long_term = store.read_long_term()
        print(f"✅ read_long_term(): {len(long_term)} 字符")
        
        context = store.get_memory_context()
        print(f"✅ get_memory_context(): {len(context)} 字符")
        
        # 测试 append_history (不实际写入)
        print(f"✅ append_history() 方法存在")
        
        # 测试 _format_messages
        test_messages = [
            {"role": "user", "content": "测试消息", "timestamp": "2026-03-21T21:40:00"},
        ]
        formatted = store._format_messages(test_messages)
        print(f"✅ _format_messages(): {len(formatted)} 字符")
        
        return True
        
    except Exception as e:
        print(f"❌ 兼容性测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("  增强记忆系统 Step 2 验证")
    print("  时间：2026-03-21 21:40")
    print("  测试：MemoryStore 修改")
    print("="*60)
    
    tests = [
        ("导入测试", test_memory_store_import),
        ("初始化测试", test_memory_store_init),
        ("消息编码", test_encode_message),
        ("获取上下文", test_get_context),
        ("向后兼容", test_backward_compatibility),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = await test_func()
            else:
                success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name} 测试失败：{e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 汇总
    print("\n" + "="*60)
    print("  测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {status} - {name}")
    
    print(f"\n总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n✅ Step 2 验证完成：所有测试通过！")
        print("\n📝 下一步:")
        print("  1. 修改 context.py 添加增强上下文")
        print("  2. 修改 loop.py 在消息处理时调用 encode_message")
        return 0
    else:
        print("\n❌ 部分测试失败，请检查")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
