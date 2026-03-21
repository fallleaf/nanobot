#!/usr/bin/env python3
"""
Task Reminder Module

任务提醒：自动从对话中提取任务并设置提醒
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable
from pathlib import Path
import sys
import re

sys.path.insert(0, str(Path(__file__).parent))


class TaskReminder:
    """
    任务提醒设置器
    
    从 LLM 提取的任务中自动设置 cron 提醒
    """
    
    # 时间关键词映射
    TIME_KEYWORDS = {
        "明天": 1,
        "后天": 2,
        "下周": 7,
        "下周一": lambda: (7 - datetime.now().weekday()) % 7 + 7,
        "下周二": lambda: (7 - datetime.now().weekday()) % 7 + 8,
        "下周三": lambda: (7 - datetime.now().weekday()) % 7 + 9,
        "下周四": lambda: (7 - datetime.now().weekday()) % 7 + 10,
        "下周五": lambda: (7 - datetime.now().weekday()) % 7 + 11,
        "周末": lambda: (5 - datetime.now().weekday()) % 7 + 2,
    }
    
    # 提醒触发关键词
    REMINDER_KEYWORDS = [
        "提醒我", "记得", "别忘了", "设置提醒", "提醒",
        "明天", "后天", "下周", "上午", "下午", "晚上",
        "点", ":", "：",
    ]
    
    def __init__(self, cron_callback: Optional[Callable] = None):
        """
        初始化提醒器
        
        Args:
            cron_callback: cron 设置回调函数
        """
        self.cron_callback = cron_callback
        self._stats = {
            "tasks_processed": 0,
            "reminders_set": 0,
            "reminders_failed": 0,
        }
    
    def detect_reminder_intent(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        检测是否需要设置提醒
        
        Args:
            query: 用户查询
            
        Returns:
            (是否有提醒意图，提醒内容)
        """
        # 检测提醒关键词
        has_keyword = any(kw in query for kw in self.REMINDER_KEYWORDS)
        
        if not has_keyword:
            return False, None
        
        # 检测时间表达
        time_patterns = [
            (r"明天.*?(\d+)[点時]", "tomorrow"),
            (r"后天.*?(\d+)[点時]", "day_after"),
            (r"下周.*?(\d+)[点時]", "next_week"),
            (r"(\d+月\d+日)", "month_day"),
            (r"(\d{1,2}:\d{2})", "time"),
        ]
        
        has_time = any(re.search(p[0], query) for p in time_patterns)
        
        if has_keyword and has_time:
            return True, query
        
        return False, None
    
    def parse_time(self, text: str) -> Optional[datetime]:
        """
        解析时间表达（增强版）
        
        支持的时间表达：
        - 明天/后天/大后天 + 时间
        - 下周一到周日
        - 上午/下午/晚上 + 时间
        - X 小时后/X 天后
        - 月日格式
        - 具体时间 (HH:MM)
        
        Args:
            text: 包含时间的文本
            
        Returns:
            解析后的时间
        """
        now = datetime.now()
        
        # ========== 辅助函数 ==========
        
        def extract_time(text: str) -> Tuple[int, int]:
            """提取时间（小时，分钟），处理上午/下午/晚上/半"""
            hour = 9  # 默认
            minute = 0
            
            # 检查时段
            is_pm = "下午" in text or "晚上" in text
            
            # 检查半点
            is_half = "半" in text
            
            # 提取小时和分钟 - 支持多种格式
            # 格式 1: HH 点 MM 分
            time_match = re.search(r"(\d{1,2})\s*[点時]\s*(\d{1,2})\s*分", text)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
            else:
                # 格式 2: HH 点 (可能带半)
                time_match = re.search(r"(\d{1,2})\s*[点時]", text)
                if time_match:
                    hour = int(time_match.group(1))
                    if is_half:
                        minute = 30
            
            # 处理下午/晚上
            if is_pm and hour < 12:
                hour += 12
            
            return hour, minute
        
        def extract_date_offset(text: str) -> int:
            """提取日期偏移量（天数）"""
            # 注意顺序：先检查大后天，再后天，再明天（避免误匹配）
            if "大后天" in text:
                return 3
            if "后天" in text:
                return 2
            if "明天" in text:
                return 1
            # 下周 X
            weekdays = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7, "天": 7}
            for day_name, day_num in weekdays.items():
                if f"下周{day_name}" in text:
                    days_ahead = (day_num - now.weekday() - 1) % 7 + 7
                    return days_ahead
            return 0
        
        # ========== 绝对日期（优先匹配） ==========
        
        # 月日格式 (支持多种格式) - 优先于相对日期
        match = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
        if match:
            month, day = int(match.group(1)), int(match.group(2))
            hour, minute = extract_time(text)
            return now.replace(month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
        
        # ========== 相对日期 + 时间 ==========
        
        # 明天/后天/大后天/下周 X
        if any(kw in text for kw in ["明天", "后天", "大后天", "下周"]):
            days_offset = extract_date_offset(text)
            hour, minute = extract_time(text)
            target_date = now + timedelta(days=days_offset)
            return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # ========== 时段 + 时间 ==========
        
        # 上午/早上 + 时间
        match = re.search(r"(?:上午 | 早上)\s*(\d{1,2})\s*[点時](\d{0,2})?", text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # 下午 + 时间 (转换为 24 小时制)
        match = re.search(r"下午\s*(\d{1,2})\s*[点時](\d{0,2})?", text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            if hour < 12:
                hour += 12
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # 晚上 + 时间 (转换为 24 小时制)
        match = re.search(r"晚上\s*(\d{1,2})\s*[点時](\d{0,2})?", text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            if hour < 12:
                hour += 12
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # 中午 + 时间
        match = re.search(r"中午\s*(\d{1,2})\s*[点時](\d{0,2})?", text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            if hour < 12:
                hour = 12
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # ========== 相对时间 ==========
        
        # X 小时后
        match = re.search(r"(\d+)\s*小时后", text)
        if match:
            hours = int(match.group(1))
            return now + timedelta(hours=hours)
        
        # X 天后
        match = re.search(r"(\d+)\s*天后", text)
        if match:
            days = int(match.group(1))
            return now + timedelta(days=days)
        
        # 半小时后
        if "半小时后" in text or "半个小时后" in text:
            return now + timedelta(minutes=30)
        
        # 一小时后
        if "一小时后" in text or "一个钟头后" in text:
            return now + timedelta(hours=1)
        
        # ========== 绝对日期 ==========
        
        # 日期格式 YYYY-MM-DD
        match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
        if match:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return now.replace(year=year, month=month, day=day, hour=9, minute=0, second=0, microsecond=0)
        
        # ========== 具体时间 ==========
        
        # HH:MM 格式
        match = re.search(r"(\d{1,2}):(\d{2})", text)
        if match:
            hour, minute = int(match.group(1)), int(match.group(2))
            reminder_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if reminder_time < now:
                reminder_time += timedelta(days=1)
            return reminder_time
        
        # HH 点 MM 分
        match = re.search(r"(\d{1,2})\s*[点時]\s*(\d{1,2})\s*分", text)
        if match:
            hour, minute = int(match.group(1)), int(match.group(2))
            reminder_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if reminder_time < now:
                reminder_time += timedelta(days=1)
            return reminder_time
        
        return None
    
    async def set_reminder(
        self,
        task: Dict[str, Any],
        channel: str = "telegram",
        chat_id: str = ""
    ) -> Tuple[bool, str]:
        """
        为任务设置提醒
        
        Args:
            task: 任务字典 {content, priority, deadline}
            channel: 提醒频道
            chat_id: 聊天 ID
            
        Returns:
            (是否成功，消息)
        """
        content = task.get("content", "")
        deadline_str = task.get("deadline")
        priority = task.get("priority", "medium")
        
        # 解析截止时间
        reminder_time = None
        
        if deadline_str:
            try:
                reminder_time = datetime.fromisoformat(deadline_str)
            except:
                reminder_time = self.parse_time(deadline_str)
        
        # 从内容中解析时间
        if not reminder_time:
            reminder_time = self.parse_time(content)
        
        # 默认明天上午 9 点
        if not reminder_time:
            reminder_time = datetime.now() + timedelta(days=1, hours=9)
            reminder_time = reminder_time.replace(minute=0, second=0)
        
        # 设置提醒
        if self.cron_callback:
            try:
                await self.cron_callback(
                    action="add",
                    at=reminder_time.isoformat(),
                    message=f"[{priority.upper()}] {content}",
                    channel=channel,
                    chat_id=chat_id
                )
                
                self._stats["reminders_set"] += 1
                
                return True, f"已设置提醒：{reminder_time.strftime('%Y-%m-%d %H:%M')}"
                
            except Exception as e:
                self._stats["reminders_failed"] += 1
                return False, f"设置提醒失败：{e}"
        else:
            # 没有回调，仅记录
            self._stats["reminders_set"] += 1
            return True, f"[模拟] 已设置提醒：{reminder_time.strftime('%Y-%m-%d %H:%M')}"
    
    async def process_tasks(
        self,
        tasks: List[Dict[str, Any]],
        channel: str,
        chat_id: str
    ) -> Dict[str, Any]:
        """
        批量处理任务
        
        Args:
            tasks: 任务列表
            channel: 频道
            chat_id: 聊天 ID
            
        Returns:
            处理结果
        """
        results = {
            "total": len(tasks),
            "success": 0,
            "failed": 0,
            "reminders": [],
            "details": []
        }
        
        for task in tasks:
            self._stats["tasks_processed"] += 1
            
            success, message = await self.set_reminder(task, channel, chat_id)
            
            if success:
                results["success"] += 1
                results["reminders"].append(task)
            else:
                results["failed"] += 1
            
            results["details"].append({
                "task": task.get("content", "")[:50],
                "success": success,
                "message": message
            })
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return self._stats


# ============================================================================
# 集成到 LLM 巩固
# ============================================================================

async def consolidate_with_reminders(
    llm_consolidator,
    items: List[Any],
    reminder: TaskReminder,
    channel: str = "telegram",
    chat_id: str = ""
) -> Dict[str, Any]:
    """
    使用 LLM 巩固并设置任务提醒
    
    Args:
        llm_consolidator: LLM 巩固器
        items: 记忆项列表
        reminder: 任务提醒器
        channel: 频道
        chat_id: 聊天 ID
        
    Returns:
        巩固结果（包含提醒信息）
    """
    # LLM 巩固
    result = await llm_consolidator.consolidate(items)
    
    # 处理任务提醒
    if result.get("tasks"):
        task_results = await reminder.process_tasks(
            result["tasks"],
            channel,
            chat_id
        )
        result["task_reminders"] = task_results
    
    return result


# ============================================================================
# 测试
# ============================================================================

async def test_task_reminder():
    """测试任务提醒"""
    print("=" * 60)
    print("Task Reminder 测试")
    print("=" * 60)
    
    # 创建提醒器（使用模拟回调）
    async def mock_cron_callback(**kwargs):
        print(f"   [Cron] {kwargs}")
    
    reminder = TaskReminder(cron_callback=mock_cron_callback)
    
    # 测试 1: 检测提醒意图
    print("\n1. 检测提醒意图")
    test_queries = [
        "明天上午 9 点提醒我开会",
        "别忘了下午 3 点提交报告",
        "下周一提醒我参加周例会",
        "你好",
        "谢谢",
    ]
    
    for query in test_queries:
        has_intent, content = reminder.detect_reminder_intent(query)
        status = "✓" if has_intent else "✗"
        print(f"   {status} {query[:30]}... → {has_intent}")
    
    # 测试 2: 解析时间
    print("\n2. 解析时间表达")
    test_times = [
        "明天上午 9 点",
        "后天下午 3 点",
        "下周一 10 点",
        "3 月 25 日",
        "14:30",
    ]
    
    for text in test_times:
        parsed = reminder.parse_time(text)
        if parsed:
            print(f"   ✓ {text} → {parsed.strftime('%Y-%m-%d %H:%M')}")
        else:
            print(f"   ✗ {text} → 无法解析")
    
    # 测试 3: 设置提醒
    print("\n3. 设置任务提醒")
    test_tasks = [
        {
            "content": "参加周例会",
            "priority": "high",
            "deadline": None
        },
        {
            "content": "提交项目报告",
            "priority": "medium",
            "deadline": "2026-03-25"
        },
        {
            "content": "明天上午 9 点提醒我开会",
            "priority": "high",
            "deadline": None
        },
    ]
    
    results = await reminder.process_tasks(
        test_tasks,
        channel="telegram",
        chat_id="test123"
    )
    
    print(f"   总任务：{results['total']}")
    print(f"   成功：{results['success']}")
    print(f"   失败：{results['failed']}")
    
    for detail in results["details"]:
        status = "✓" if detail["success"] else "✗"
        print(f"   {status} {detail['task'][:30]}... → {detail['message'][:50]}")
    
    # 测试 4: 统计
    print("\n4. 统计信息")
    stats = reminder.get_stats()
    print(f"   处理任务：{stats['tasks_processed']}")
    print(f"   设置提醒：{stats['reminders_set']}")
    print(f"   失败：{stats['reminders_failed']}")
    
    # 验证
    success = results["success"] > 0
    
    return success


async def main():
    """主测试函数"""
    success = await test_task_reminder()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ 项目 3 测试通过！")
        print("\n下一步：实施项目 4 - 图记忆")
    else:
        print("✗ 项目 3 测试失败，请修复")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
