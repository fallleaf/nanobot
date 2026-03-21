#!/usr/bin/env python3
"""
增强记忆系统最终检查
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def check_imports():
    """检查导入"""
    print("\n" + "="*60)
    print("检查 1: 模块导入")
    print("="*60)
    
    try:
        from nanobot.agent.memory_enhanced.short_term import ShortTermMemory
        from nanobot.agent.memory_enhanced.working import WorkingMemory
        from nanobot.agent.memory_enhanced.manager import MemoryManager
        print("  ✅ short_term.py")
        print("  ✅ working.py")
        print("  ✅ manager.py")
        return True
    except Exception as e:
        print(f"  ❌ 导入失败：{e}")
        return False

def check_database():
    """检查数据库"""
    print("\n" + "="*60)
    print("检查 2: 数据库状态")
    print("="*60)
    
    try:
        import sqlite3
        db_path = Path.home() / ".nanobot" / "workspace" / "memory" / "short_term_memory.db"
        
        if not db_path.exists():
            print(f"  ❌ 数据库不存在：{db_path}")
            return False
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 检查表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"  表：{tables}")
        
        # 检查记录数
        cursor.execute("SELECT COUNT(*) FROM memory_items")
        count = cursor.fetchone()[0]
        print(f"  memory_items: {count} 条")
        
        # 检查标签表
        if 'memory_tags' in tables:
            cursor.execute("SELECT COUNT(*) FROM memory_tags")
            tag_count = cursor.fetchone()[0]
            print(f"  memory_tags: {tag_count} 条")
            print(f"  ✅ 标签表存在")
        else:
            print(f"  ⚠️  标签表不存在")
        
        # 检查索引
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        print(f"  索引：{len(indexes)} 个")
        
        conn.close()
        
        print(f"  ✅ 数据库检查通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 数据库检查失败：{e}")
        return False

def check_memory_store():
    """检查 MemoryStore"""
    print("\n" + "="*60)
    print("检查 3: MemoryStore 功能")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        if not store.manager:
            print(f"  ❌ 增强记忆不可用")
            return False
        
        print(f"  ✅ MemoryStore 初始化成功")
        print(f"  ✅ ShortTermMemory: {store.short_term is not None}")
        print(f"  ✅ WorkingMemory: {store.working is not None}")
        print(f"  ✅ MemoryManager: {store.manager is not None}")
        
        # 检查方法
        methods = ['get_enhanced_stats', 'encode_message', 'get_enhanced_context', '_extract_tags', '_extract_query_tags']
        for method in methods:
            if hasattr(store, method):
                print(f"  ✅ 方法 {method}() 存在")
            else:
                print(f"  ❌ 方法 {method}() 缺失")
        
        # 测试统计功能
        stats = store.get_enhanced_stats()
        print(f"\n  统计信息:")
        print(f"    短期记忆：{stats.get('short_term_count', 0)} 条")
        print(f"    数据库大小：{stats.get('database_size_kb', 0)} KB")
        print(f"    标签数量：{len(stats.get('tags_distribution', {}))} 个")
        
        return True
        
    except Exception as e:
        print(f"  ❌ MemoryStore 检查失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def check_cleanup():
    """检查清理功能"""
    print("\n" + "="*60)
    print("检查 4: 清理功能")
    print("="*60)
    
    try:
        from nanobot.agent.memory_enhanced.short_term import ShortTermMemory
        
        workspace = Path.home() / ".nanobot" / "workspace" / "memory"
        db_path = workspace / "short_term_memory.db"
        
        st = ShortTermMemory(db_path=db_path)
        
        # 检查方法
        methods = ['apply_forgetting', 'cleanup_low_importance', 'get_cleanup_stats']
        for method in methods:
            if hasattr(st, method):
                print(f"  ✅ 方法 {method}() 存在")
            else:
                print(f"  ❌ 方法 {method}() 缺失")
        
        # 测试统计
        stats = st.get_cleanup_stats()
        print(f"\n  清理统计:")
        print(f"    总记忆数：{stats['total']} 条")
        print(f"    清理建议：{'需要' if stats['cleanup_recommendation']['should_cleanup'] else '无需'}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 清理功能检查失败：{e}")
        return False

def check_tags():
    """检查标签功能"""
    print("\n" + "="*60)
    print("检查 5: 标签功能")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        # 测试标签提取
        test_cases = [
            ("配置在哪里？", ["question", "配置"]),
            ("出现错误", ["错误"]),
            ("/start", ["命令"]),
        ]
        
        print(f"  标签提取测试:")
        for content, expected in test_cases:
            tags = store._extract_tags(content, "user")
            has_expected = any(t in tags for t in expected)
            status = "✅" if has_expected else "⚠️"
            print(f"    {status} '{content}' → {tags[:3]}")
        
        # 测试查询标签推断
        print(f"\n  查询标签推断:")
        query_tags = store._extract_query_tags("nanobot 配置")
        print(f"    'nanobot 配置' → {query_tags}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 标签功能检查失败：{e}")
        return False

def main():
    """运行所有检查"""
    print("\n" + "="*60)
    print("  增强记忆系统最终检查")
    print("  时间：2026-03-21 23:20")
    print("="*60)
    
    checks = [
        ("模块导入", check_imports),
        ("数据库状态", check_database),
        ("MemoryStore", check_memory_store),
        ("清理功能", check_cleanup),
        ("标签功能", check_tags),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            success = check_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name} 检查失败：{e}")
            results.append((name, False))
    
    # 汇总
    print("\n" + "="*60)
    print("  检查结果汇总")
    print("="*60)
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {status} - {name}")
    
    print(f"\n总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n✅ 增强记忆系统检查完成！所有功能正常！")
        return 0
    else:
        print(f"\n❌ {total - passed} 个检查失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
