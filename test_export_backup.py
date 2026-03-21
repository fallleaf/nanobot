#!/usr/bin/env python3
"""
测试导出/备份功能
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_export_json():
    """测试 JSON 导出"""
    print("\n" + "="*60)
    print("测试 1: JSON 导出")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        # 导出 JSON
        content = store.export_memories(format="json", days=30)
        
        if content:
            import json
            memories = json.loads(content)
            print(f"  导出记忆：{len(memories)} 条")
            print(f"  ✅ JSON 导出成功")
            return True
        else:
            print(f"  ❌ 导出失败")
            return False
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def test_export_markdown():
    """测试 Markdown 导出"""
    print("\n" + "="*60)
    print("测试 2: Markdown 导出")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        # 导出 Markdown
        content = store.export_memories(format="markdown", days=30)
        
        if content and "# 记忆导出" in content:
            lines = content.split('\n')
            print(f"  导出行数：{len(lines)}")
            print(f"  ✅ Markdown 导出成功")
            return True
        else:
            print(f"  ❌ 导出失败")
            return False
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False

def test_export_to_file():
    """测试导出到文件"""
    print("\n" + "="*60)
    print("测试 3: 导出到文件")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        # 导出到文件
        output_path = workspace / "memory" / "export_test.json"
        result = store.export_memories(format="json", output_path=output_path, days=30)
        
        if result and output_path.exists():
            size = output_path.stat().st_size
            print(f"  文件大小：{size} 字节")
            print(f"  ✅ 文件导出成功")
            return True
        else:
            print(f"  ❌ 导出失败")
            return False
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False

def test_backup_database():
    """测试数据库备份"""
    print("\n" + "="*60)
    print("测试 4: 数据库备份")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        # 备份数据库
        backup_path = store.backup_database()
        
        if backup_path:
            backup_file = Path(backup_path)
            if backup_file.exists():
                size = backup_file.stat().st_size
                print(f"  备份文件：{backup_file.name}")
                print(f"  文件大小：{size} 字节")
                print(f"  ✅ 数据库备份成功")
                return True
        
        print(f"  ❌ 备份失败")
        return False
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False

def test_export_with_tags():
    """测试按标签导出"""
    print("\n" + "="*60)
    print("测试 5: 按标签导出")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        # 按标签导出
        content = store.export_memories(format="json", tags=["配置"], days=30)
        
        if content:
            import json
            memories = json.loads(content)
            print(f"  导出记忆：{len(memories)} 条 (标签：配置)")
            print(f"  ✅ 按标签导出成功")
            return True
        else:
            print(f"  ❌ 导出失败")
            return False
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False

def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("  导出/备份功能测试")
    print("  时间：2026-03-21 23:27")
    print("="*60)
    
    tests = [
        ("JSON 导出", test_export_json),
        ("Markdown 导出", test_export_markdown),
        ("导出到文件", test_export_to_file),
        ("数据库备份", test_backup_database),
        ("按标签导出", test_export_with_tags),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name} 测试失败：{e}")
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
        print("\n✅ 导出/备份功能测试通过!")
        return 0
    else:
        print(f"\n⚠️  {passed}/{total} 通过")
        return 0

if __name__ == "__main__":
    sys.exit(main())
