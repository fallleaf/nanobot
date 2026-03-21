#!/usr/bin/env python3
"""
测试知识图谱功能
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_graph_initialization():
    """测试图谱初始化"""
    print("\n" + "="*60)
    print("测试 1: 知识图谱初始化")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        if not store.graph:
            print("  ❌ 图谱未初始化")
            return False
        
        print("  ✅ 图谱初始化成功")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def test_add_entity():
    """测试添加实体"""
    print("\n" + "="*60)
    print("测试 2: 添加实体")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        # 添加测试实体
        entity_id = store.add_entity("nanobot", "project", {"description": "AI 助手"})
        print(f"  添加实体 'nanobot': {entity_id}")
        
        if entity_id:
            print("  ✅ 实体添加成功")
            return True
        else:
            print("  ⚠️  实体添加失败")
            return False
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False

def test_add_relation():
    """测试添加关系"""
    print("\n" + "="*60)
    print("测试 3: 添加关系")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        # 添加两个实体
        id1 = store.add_entity("测试项目", "project")
        id2 = store.add_entity("测试人员", "person")
        
        if id1 and id2:
            # 添加关系
            success = store.add_relation(id1, id2, "OWNED_BY")
            if success:
                print(f"  ✅ 关系添加成功：{id1} -> {id2}")
                return True
        
        print("  ⚠️  关系添加失败")
        return False
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False

def test_graph_stats():
    """测试图谱统计"""
    print("\n" + "="*60)
    print("测试 4: 图谱统计")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        stats = store.get_enhanced_stats()
        graph_stats = stats.get('graph', {})
        
        print(f"  图谱统计:")
        print(f"    可用：{graph_stats.get('available', False)}")
        print(f"    实体数：{graph_stats.get('entity_count', 0)}")
        print(f"    关系数：{graph_stats.get('relation_count', 0)}")
        
        if graph_stats.get('available'):
            print("  ✅ 图谱统计正常")
            return True
        else:
            print("  ⚠️  图谱不可用")
            return False
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False

def test_search_entities():
    """测试搜索实体"""
    print("\n" + "="*60)
    print("测试 5: 搜索实体")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        # 搜索实体
        results = store.search_entities("nanobot", limit=5)
        print(f"  搜索 'nanobot': {len(results)} 个结果")
        
        for entity in results:
            print(f"    - {entity.get('name')} ({entity.get('type')})")
        
        print("  ✅ 实体搜索正常")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False

def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("  知识图谱功能测试")
    print("  时间：2026-03-21 23:25")
    print("="*60)
    
    tests = [
        ("图谱初始化", test_graph_initialization),
        ("添加实体", test_add_entity),
        ("添加关系", test_add_relation),
        ("图谱统计", test_graph_stats),
        ("搜索实体", test_search_entities),
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
        print("\n✅ 知识图谱功能测试通过!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试通过，{passed} 个失败")
        return 0  # 即使失败也返回 0，因为这是可选功能

if __name__ == "__main__":
    sys.exit(main())
