#!/usr/bin/env python3
"""
测试增强记忆系统 - Step 3 验证
测试修改后的 ContextBuilder 类
"""

import sys
import asyncio
from pathlib import Path

# 使用虚拟环境
sys.path.insert(0, str(Path(__file__).parent))

def test_context_builder_import():
    """测试 ContextBuilder 导入"""
    print("\n" + "="*60)
    print("测试 1: ContextBuilder 导入")
    print("="*60)
    
    try:
        from nanobot.agent.context import ContextBuilder
        print("✅ ContextBuilder 导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def test_context_builder_init():
    """测试 ContextBuilder 初始化"""
    print("\n" + "="*60)
    print("测试 2: ContextBuilder 初始化")
    print("="*60)
    
    try:
        from nanobot.agent.context import ContextBuilder
        
        workspace = Path.home() / ".nanobot" / "workspace"
        
        # 带 provider 初始化
        builder = ContextBuilder(workspace, provider=None, model="qwen3.5-plus")
        
        print(f"✅ ContextBuilder 初始化成功")
        print(f"  工作目录：{builder.workspace}")
        print(f"  MemoryStore: {type(builder.memory).__name__}")
        print(f"  增强记忆可用：{builder.memory.manager is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ 初始化失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def test_build_system_prompt():
    """测试构建系统提示词"""
    print("\n" + "="*60)
    print("测试 3: 构建系统提示词 (build_system_prompt)")
    print("="*60)
    
    try:
        from nanobot.agent.context import ContextBuilder
        
        workspace = Path.home() / ".nanobot" / "workspace"
        builder = ContextBuilder(workspace, provider=None, model="qwen3.5-plus")
        
        # 构建系统提示词
        prompt = builder.build_system_prompt(
            skill_names=None,
            include_enhanced_context=True
        )
        
        print(f"✅ 系统提示词构建成功")
        print(f"  总长度：{len(prompt)} 字符")
        
        # 检查是否包含增强记忆上下文
        if "Enhanced Memory Context" in prompt:
            print(f"  ✅ 包含增强记忆上下文")
        else:
            print(f"  ⚠️  未包含增强记忆上下文（可能无数据）")
        
        # 检查基本部分
        checks = [
            ("nanobot", "身份标识"),
            ("Memory", "长期记忆"),
            ("AGENTS.md", "Bootstrap 文件"),
        ]
        
        for keyword, desc in checks:
            if keyword in prompt:
                print(f"  ✅ 包含 {desc}")
            else:
                print(f"  ⚠️  缺少 {desc}")
        
        return True
        
    except Exception as e:
        print(f"❌ 构建系统提示词失败：{e}")
        import traceback
        traceback.print_exc()
        return False

async def test_build_messages_with_enhanced():
    """测试构建消息（包含增强记忆）"""
    print("\n" + "="*60)
    print("测试 4: 构建消息 (build_messages)")
    print("="*60)
    
    try:
        from nanobot.agent.context import ContextBuilder
        
        workspace = Path.home() / ".nanobot" / "workspace"
        builder = ContextBuilder(workspace, provider=None, model="qwen3.5-plus")
        
        # 先编码一些测试消息
        await builder.memory.encode_message(
            content="用户询问 nanobot 配置",
            role="user",
            channel="telegram",
            chat_id="test123"
        )
        
        await builder.memory.encode_message(
            content="配置文件在~/.nanobot/config.json",
            role="assistant",
            channel="telegram",
            chat_id="test123"
        )
        
        # 构建消息
        history = []
        messages = builder.build_messages(
            history=history,
            current_message="nanobot 的配置在哪里？",
            channel="telegram",
            chat_id="760250069"
        )
        
        print(f"✅ 消息列表构建成功")
        print(f"  消息数量：{len(messages)}")
        print(f"  System 消息长度：{len(messages[0]['content'])} 字符")
        
        # 检查系统提示词
        system_prompt = messages[0]['content']
        
        if "Enhanced Memory Context" in system_prompt:
            print(f"  ✅ 包含增强记忆上下文")
            # 提取增强记忆部分
            start = system_prompt.find("# Enhanced Memory Context")
            if start > 0:
                enhanced_section = system_prompt[start:start+300]
                print(f"  预览：{enhanced_section[:150]}...")
        else:
            print(f"  ⚠️  未包含增强记忆上下文")
        
        # 检查用户消息
        user_msg = messages[-1]
        print(f"  用户消息角色：{user_msg['role']}")
        print(f"  用户消息长度：{len(user_msg['content'])} 字符")
        
        return True
        
    except Exception as e:
        print(f"❌ 构建消息失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n" + "="*60)
    print("测试 5: 向后兼容性")
    print("="*60)
    
    try:
        from nanobot.agent.context import ContextBuilder
        
        workspace = Path.home() / ".nanobot" / "workspace"
        
        # 测试旧式初始化（不带 provider）
        builder = ContextBuilder(workspace)
        
        print(f"✅ 旧式初始化兼容")
        
        # 测试不带参数的 build_system_prompt
        prompt = builder.build_system_prompt()
        print(f"✅ build_system_prompt() 兼容：{len(prompt)} 字符")
        
        # 测试 build_messages
        messages = builder.build_messages(
            history=[],
            current_message="测试消息"
        )
        print(f"✅ build_messages() 兼容：{len(messages)} 条消息")
        
        return True
        
    except Exception as e:
        print(f"❌ 兼容性测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("  增强记忆系统 Step 3 验证")
    print("  时间：2026-03-21 21:42")
    print("  测试：ContextBuilder 修改")
    print("="*60)
    
    tests = [
        ("导入测试", test_context_builder_import),
        ("初始化测试", test_context_builder_init),
        ("系统提示词", test_build_system_prompt),
        ("消息构建", test_build_messages_with_enhanced),
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
        print("\n✅ Step 3 验证完成：所有测试通过！")
        print("\n📝 下一步:")
        print("  修改 loop.py 在消息处理时调用 encode_message")
        return 0
    else:
        print("\n❌ 部分测试失败，请检查")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
