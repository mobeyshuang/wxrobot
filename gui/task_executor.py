from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtCore import QTimer
import re
from datetime import datetime
import threading
import time
from queue import Queue
import schedule
from typing import Dict, List, Optional
import queue

class TaskExecutor(QObject):
    status_changed = pyqtSignal(str, str)  # 任务名称, 状态
    stats_updated = pyqtSignal(str, dict)  # 任务名称, 统计数据
    
    def __init__(self, robot):
        super().__init__()
        self.robot = robot
        self.tasks = {}  # 任务字典
        self.message_queue = Queue()  # 消息队列
        self.running = True
        self.message_lock = threading.Lock()
        
        # 启动消息处理线程
        self.message_thread = threading.Thread(target=self._process_messages)
        self.message_thread.daemon = True
        self.message_thread.start()
        
        # 启动定时任务检查线程
        self.schedule_thread = threading.Thread(target=self._check_schedule)
        self.schedule_thread.daemon = True
        self.schedule_thread.start()
        
    def start_task(self, task_config: Dict) -> bool:
        """启动任务"""
        try:
            task_name = task_config["name"]
            if task_name in self.tasks:
                return False
                
            # 初始化任务状态
            self.tasks[task_name] = {
                "config": task_config,
                "running": True,
                "stats": {
                    "processed": 0,
                    "succeeded": 0,
                    "failed": 0
                }
            }
            
            # 根据任务类型设置不同的处理逻辑
            task_type = task_config["type"]
            if task_type == "消息转发任务":
                # 注册消息回调
                pass  # 改用队列方式，不需要回调
            elif task_type == "消息回复任务":
                # 注册消息回调
                pass  # 改用队列方式，不需要回调
            elif task_type == "定时消息任务":
                # 设置定时任务
                self._setup_scheduled_task(task_config)
                
            self.status_changed.emit(task_name, "运行中")
            return True
        except Exception as e:
            print(f"启动任务失败: {e}")
            return False
            
    def stop_task(self, task_name: str) -> bool:
        """停止任务"""
        try:
            if task_name not in self.tasks:
                return False
                
            task = self.tasks[task_name]
            task["running"] = False
            
            # 根据任务类型清理资源
            task_type = task["config"]["type"]
            if task_type in ["消息转发任务", "消息回复任务"]:
                # 不需要取消回调，改用队列方式
                pass
            elif task_type == "定时消息任务":
                # 取消定时任务
                schedule.clear(task_name)
                
            del self.tasks[task_name]
            self.status_changed.emit(task_name, "已停止")
            return True
        except Exception as e:
            print(f"停止任务失败: {e}")
            return False
            
    def add_message(self, message: Dict):
        """添加消息到队列"""
        self.message_queue.put(message)
        
    def _process_messages(self):
        """处理消息队列"""
        while self.running:
            try:
                message = self.message_queue.get(timeout=1)
                with self.message_lock:
                    self._handle_message(message)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"处理消息失败: {e}")
                
    def _handle_message(self, msg):
        """处理单条消息"""
        try:
            # 转换WxMsg对象为字典格式
            if hasattr(msg, 'sender'):  # 是WxMsg对象
                message = {
                    "sender": msg.sender,
                    "content": msg.content,
                    "room_wxid": msg.roomid,
                    "id": getattr(msg, 'id', None),
                    "type": getattr(msg, 'type', 0),
                    "sender_name": msg.sender_name if hasattr(msg, 'sender_name') else "",
                    "room_name": msg.room_name if hasattr(msg, 'room_name') else ""
                }
            else:  # 已经是字典
                message = msg
            
            # 遍历所有运行中的任务
            for task_name, task in list(self.tasks.items()):
                if not task["running"]:
                    continue
                    
                task_config = task["config"]
                task_type = task_config["type"]
                
                # 检查消息是否匹配任务条件
                if not self._check_message_match(message, task_config):
                    continue
                    
                # 根据任务类型处理消息
                if task_type == "消息转发任务":
                    self._handle_forward_task(message, task)
                elif task_type == "消息回复任务":
                    self._handle_reply_task(message, task)
                    
        except Exception as e:
            print(f"处理消息失败: {e}")
            
    def _check_message_match(self, message: Dict, task_config: Dict) -> bool:
        """检查消息是否匹配任务条件"""
        try:
            # 不同任务类型有不同的匹配条件
            task_type = task_config["type"]
            
            if task_type == "消息转发任务":
                # 检查群聊
                source_group = task_config.get("source_group", "")
                if not source_group or source_group != message.get("room_name"):
                    return False
                
                # 检查成员
                member = task_config.get("member", "全部")
                if member != "全部" and member != message.get("sender_name"):
                    return False
                
                # 检查消息匹配条件
                match_type = task_config.get("match_type", "")
                match_content = task_config.get("match_content", "")
                
                if match_type == "包含":
                    return match_content in message.get("content", "")
                elif match_type == "等于":
                    return match_content == message.get("content", "")
                elif match_type == "正则":
                    return bool(re.search(match_content, message.get("content", "")))
                elif match_type == "文件类型":
                    file_type = task_config.get("file_type", "")
                    if file_type == "图片":
                        return message.get("type") == 3
                    elif file_type == "文件":
                        return message.get("type") == 49
                    elif file_type == "视频":
                        return message.get("type") == 43
                
            elif task_type == "消息回复任务":
                # 检查群聊
                reply_group = task_config.get("reply_group", "")
                if not reply_group or reply_group != message.get("room_name"):
                    return False
                
                # 检查成员
                reply_member = task_config.get("reply_member", "全部")
                if reply_member != "全部" and reply_member != message.get("sender_name"):
                    return False
                
                # 检查消息匹配条件
                reply_match_type = task_config.get("reply_match_type", "")
                reply_match_content = task_config.get("reply_match_content", "")
                
                if reply_match_type == "包含":
                    return reply_match_content in message.get("content", "")
                elif reply_match_type == "等于":
                    return reply_match_content == message.get("content", "")
                elif reply_match_type == "正则":
                    return bool(re.search(reply_match_content, message.get("content", "")))
                
            return False
        except Exception as e:
            print(f"检查消息匹配失败: {e}")
            return False
            
    def _handle_forward_task(self, message: Dict, task: Dict):
        """处理转发任务"""
        try:
            task_name = task["config"]["name"]
            target = task["config"]["target"]
            
            # 获取target对应的wxid
            target_wxid = None
            if target in self.robot.allGroups:
                # 如果是群名称，转换为wxid
                target_wxid = self.robot.allGroups[target]
            else:
                # 尝试在好友中查找
                for friend in self.robot.wcf.get_friends():
                    if friend["name"] == target:
                        target_wxid = friend["wxid"]
                        break
                        
            if not target_wxid:
                print(f"未找到转发目标: {target}")
                task["stats"]["failed"] += 1
                task["stats"]["processed"] += 1
                self.stats_updated.emit(task_name, task["stats"])
                return
            
            # 转发消息
            msg_id = message.get("id")
            if not msg_id:
                print("消息ID为空，无法转发")
                task["stats"]["failed"] += 1
                task["stats"]["processed"] += 1
                self.stats_updated.emit(task_name, task["stats"])
                return
                
            if self.robot.wcf.forward_message(msg_id, target_wxid):
                task["stats"]["succeeded"] += 1
            else:
                task["stats"]["failed"] += 1
                
            task["stats"]["processed"] += 1
            self.stats_updated.emit(task_name, task["stats"])
            
        except Exception as e:
            print(f"处理转发任务失败: {e}")
            
    def _handle_reply_task(self, message: Dict, task: Dict):
        """处理回复任务"""
        try:
            task_name = task["config"]["name"]
            reply_content = task["config"]["reply_content"]
            reply_type = task["config"]["reply_type"]
            
            # 获取回复目标
            target_wxid = message.get("room_wxid")
            if not target_wxid:
                target_wxid = message.get("sender")
                
            if not target_wxid:
                print("无法确定回复目标")
                task["stats"]["failed"] += 1
                task["stats"]["processed"] += 1
                self.stats_updated.emit(task_name, task["stats"])
                return
            
            # 发送回复
            if reply_type == "文本":
                if self.robot.wcf.send_text(reply_content, target_wxid):
                    task["stats"]["succeeded"] += 1
                else:
                    task["stats"]["failed"] += 1
            elif reply_type == "图片":
                if self.robot.wcf.send_image(reply_content, target_wxid):
                    task["stats"]["succeeded"] += 1
                else:
                    task["stats"]["failed"] += 1
                    
            task["stats"]["processed"] += 1
            self.stats_updated.emit(task_name, task["stats"])
            
        except Exception as e:
            print(f"处理回复任务失败: {e}")
            
    def _setup_scheduled_task(self, task_config: Dict):
        """设置定时任务"""
        try:
            task_name = task_config["name"]
            send_time = task_config.get("send_time", "")
            repeat_type = task_config.get("repeat_type", "")
            timer_target = task_config.get("timer_target", "")
            content = task_config.get("content", "")
            content_type = task_config.get("content_type", "")
            attachment = task_config.get("attachment", "")
            
            if not send_time or not timer_target:
                print(f"定时任务配置不完整: {task_name}")
                return
                
            # 获取target对应的wxid
            target_wxid = None
            # 先检查是否是群名称
            for group_name, group_wxid in self.robot.allGroups.items():
                if group_name == timer_target:
                    target_wxid = group_wxid
                    break
                    
            # 如果不是群名称，尝试在好友中查找
            if not target_wxid:
                for friend in self.robot.wcf.get_friends():
                    if friend["name"] == timer_target:
                        target_wxid = friend["wxid"]
                        break
                        
            if not target_wxid:
                print(f"未找到定时消息目标: {timer_target}")
                return
            
            def send_message():
                try:
                    print(f"执行定时任务: {task_name}")
                    if content_type == "文本":
                        self.robot.wcf.send_text(content, target_wxid)
                    elif content_type == "图片":
                        self.robot.wcf.send_image(attachment, target_wxid)
                    elif content_type == "文件":
                        self.robot.wcf.send_file(attachment, target_wxid)
                    
                    # 更新统计信息
                    if task_name in self.tasks:
                        self.tasks[task_name]["stats"]["processed"] += 1
                        self.tasks[task_name]["stats"]["succeeded"] += 1
                        self.stats_updated.emit(task_name, self.tasks[task_name]["stats"])
                except Exception as e:
                    print(f"发送定时消息失败: {e}")
                    # 更新统计信息
                    if task_name in self.tasks:
                        self.tasks[task_name]["stats"]["processed"] += 1
                        self.tasks[task_name]["stats"]["failed"] += 1
                        self.stats_updated.emit(task_name, self.tasks[task_name]["stats"])
                    
            # 设置定时任务
            time_parts = send_time.split(":")
            if len(time_parts) != 2:
                print(f"时间格式不正确: {send_time}")
                return
                
            hour, minute = time_parts
            
            if repeat_type == "每天":
                schedule.every().day.at(f"{hour.zfill(2)}:{minute.zfill(2)}").do(send_message).tag(task_name)
            elif repeat_type == "每周":
                schedule.every().week.at(f"{hour.zfill(2)}:{minute.zfill(2)}").do(send_message).tag(task_name)
            elif repeat_type == "每月":
                # schedual库不直接支持每月，可以自行实现
                current_time = datetime.now()
                day_of_month = current_time.day
                
                # 创建每天的任务，但只在当月的特定日期执行
                def monthly_job():
                    now = datetime.now()
                    if now.day == day_of_month:
                        send_message()
                
                schedule.every().day.at(f"{hour.zfill(2)}:{minute.zfill(2)}").do(monthly_job).tag(task_name)
            else:  # 仅一次
                # 计算下一次执行时间
                now = datetime.now()
                target_time = now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
                if target_time < now:
                    target_time = target_time.replace(day=target_time.day + 1)
                
                # 计算延迟秒数
                delay_seconds = (target_time - now).total_seconds()
                
                # 创建一次性任务
                timer = threading.Timer(delay_seconds, send_message)
                timer.daemon = True
                timer.start()
                
        except Exception as e:
            print(f"设置定时任务失败: {e}")
            
    def _check_schedule(self):
        """检查定时任务"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                print(f"运行定时任务失败: {e}")
                time.sleep(5)  # 出错后等待更长时间
                
    def stop(self):
        """停止所有任务"""
        self.running = False
        for task_name in list(self.tasks.keys()):
            self.stop_task(task_name) 