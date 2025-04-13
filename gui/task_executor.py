from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import re
from datetime import datetime
import threading
import time
from queue import Queue
import schedule
from typing import Dict, List, Optional
import queue
import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from message_transfer import MessageTransfer
from message_scheduler import MessageScheduler
from wcferry import WxMsg  # 添加 WxMsg 的导入

class TaskExecutor(QObject):
    # 定义信号
    task_started = pyqtSignal(str)  # task_name
    task_stopped = pyqtSignal(str)  # task_name
    task_error = pyqtSignal(str, str)  # task_name, error_message
    stats_updated = pyqtSignal(str, dict)  # task_name, stats
    status_changed = pyqtSignal(str, bool)  # task_name, is_running
    
    def __init__(self, robot):
        """初始化任务执行器"""
        super().__init__()
        self.robot = robot
        self.wcf = robot.wcf
        self.running = True
        self.tasks = {}  # 存储所有任务的配置和状态
        self.message_scheduler = MessageScheduler(self)
        self.message_transfer = MessageTransfer(self.wcf, robot)
        
        # 消息处理队列和线程
        self.message_queue = queue.Queue()
        self.message_thread = threading.Thread(target=self._process_messages)
        self.message_thread.daemon = True
        
        # 调度线程
        self.scheduler_thread = None
        
        # 锁，防止并发访问任务
        self.task_lock = threading.Lock()
        self.message_lock = threading.Lock()
        
        # 启动消息处理线程
        self.message_thread.start()
        
        # 启动定时任务调度线程
        self.start_scheduler()
        
    def start_scheduler(self):
        """启动定时任务调度线程"""
        if self.scheduler_thread is None or not self.scheduler_thread.is_alive():
            self.scheduler_thread = threading.Thread(target=self.message_scheduler.run)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            print(f"已启动定时任务调度线程")
        else:
            print(f"定时任务调度线程已在运行中")
        
    def sync_task_groups_to_config(self):
        """从tasks.json中提取所有任务涉及的来源群并同步到config.json中的TASK_GROUPS数组"""
        try:
            print("开始同步任务群组到配置...")
            # 加载任务配置
            tasks_path = os.path.join("config", "tasks.json")
            if not os.path.exists(tasks_path):
                print("任务配置文件不存在，跳过同步")
                return
                
            with open(tasks_path, "r", encoding="utf-8") as f:
                tasks = json.load(f)
                
            print(f"已加载 {len(tasks)} 个任务配置")
                
            # 提取所有任务涉及的来源群名称
            task_groups = set()
            for task in tasks:
                if task.get("type") == "transfer" and task.get("source_type") == "群聊":
                    source_group = task.get("source")
                    if source_group:
                        task_groups.add(source_group)
                        print(f"找到任务 '{task.get('name')}' 的来源群: {source_group}")
            
            print(f"从任务配置中提取出 {len(task_groups)} 个任务来源群")
            
            if not task_groups:
                print("未找到任务涉及的来源群，跳过同步")
                return
                
            # 将群名称转换为wxid
            group_wxids = set()
            for group_name in task_groups:
                # 在allGroups中查找对应的wxid
                found = False
                for wxid, name in self.robot.allGroups.items():
                    if name == group_name:
                        group_wxids.add(wxid)
                        print(f"找到群 '{group_name}' 的wxid: {wxid}")
                        found = True
                        break
                if not found:
                    print(f"警告: 未找到群 '{group_name}' 的wxid，请检查群名称是否正确")
            
            print(f"成功找到 {len(group_wxids)} 个群的wxid")
            
            # 获取当前配置的任务群组（如果不存在则创建空列表）
            if hasattr(self.robot.config, 'TASK_GROUPS'):
                task_config_groups = set(self.robot.config.TASK_GROUPS)
                print(f"当前配置中已有 {len(task_config_groups)} 个任务群组")
            else:
                task_config_groups = set()
                print("当前配置中没有任务群组")
            
            # 合并并更新配置
            old_groups = set(task_config_groups)
            updated_groups = list(task_config_groups.union(group_wxids))
            new_groups = set(updated_groups) - old_groups
            
            print(f"需要新增 {len(new_groups)} 个群组到配置中")
            for group in new_groups:
                group_name = self.robot.allGroups.get(group, "未知群名")
                print(f"- 新增群组: {group_name} ({group})")
            
            # 设置TASK_GROUPS属性（如果不存在则创建）
            setattr(self.robot.config, 'TASK_GROUPS', updated_groups)
            
            # 添加get_task_groups方法（如果不存在）
            if not hasattr(self.robot.config, 'get_task_groups'):
                print("为配置对象添加get_task_groups方法")
                setattr(self.robot.config, 'get_task_groups', lambda: getattr(self.robot.config, 'TASK_GROUPS', []))
            
            # 确保配置保存方法会保存新属性
            self.robot.config.save()
            
            # 打印最终结果
            print(f"已同步任务群组到配置文件的TASK_GROUPS数组，共 {len(updated_groups)} 个群组")
            for wxid in updated_groups:
                group_name = self.robot.allGroups.get(wxid, "未知群名")
                print(f"- 群组: {group_name} ({wxid})")
                
            # 验证get_task_groups方法是否正常工作
            if hasattr(self.robot.config, 'get_task_groups'):
                task_groups = self.robot.config.get_task_groups()
                print(f"通过get_task_groups方法获取到 {len(task_groups)} 个群组")
                
        except Exception as e:
            print(f"同步任务群组到配置失败: {e}")
            import traceback
            traceback.print_exc()
        
    def check_wechat_file_dir(self) -> bool:
        """检查微信文件目录是否已正确设置
        
        Returns:
            bool: 目录是否有效
        """
        print("检查微信文件目录设置...")
        wechat_files_dir = self.message_transfer.wechat_files_dir
        
        # 检查目录是否已设置且存在
        if not wechat_files_dir or not os.path.exists(wechat_files_dir):
            print(f"微信文件目录未设置或不存在: {wechat_files_dir}")
            # 发送错误信号，提示用户设置目录
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            # 线程安全地发送信号，请求显示设置对话框
            parent = self.parent()
            if parent:
                QMetaObject.invokeMethod(parent, "show_wechat_file_settings_required", 
                                       Qt.QueuedConnection)
            return False
        
        print(f"微信文件目录已设置: {wechat_files_dir}")
        return True
        
    def start_task(self, task_config: Dict) -> bool:
        """启动任务"""
        try:
            print(f"开始启动任务，配置：{task_config}")
            task_name = task_config.get("name")
            task_type = task_config.get("type")
            
            if not task_name:
                print("任务配置中缺少任务名称")
                return False
            
            # 如果是转发任务，检查微信文件目录是否已设置
            if task_type == "transfer":
                if not self.check_wechat_file_dir():
                    self.task_error.emit(task_name, "微信文件目录未设置或不存在")
                    print(f"任务 {task_name} 启动失败: 微信文件目录未设置")
                    task_config["status"] = "stopped"  # 将任务状态设为停止
                    return False
                
            if task_name in self.tasks:
                print(f"任务 {task_name} 已存在，更新现有任务状态")
                task_exists = True
            else:
                task_exists = False
                
            # 从配置中读取状态
            status = task_config.get("status", "stopped")
            is_running = status == "running"
            
            # 保存上一次的状态到last_state
            task_config["last_state"] = is_running
            
            # 确保状态为"running"
            task_config["status"] = "running"
            is_running = True  # 强制设置为运行状态
                
            # 初始化任务状态
            if not task_exists:
                self.tasks[task_name] = {
                    "config": task_config,
                    "running": is_running,
                    "stats": {
                        "processed": 0,
                        "succeeded": 0,
                        "failed": 0
                    }
                }
            else:
                # 更新现有任务的配置和状态
                self.tasks[task_name]["config"] = task_config
                self.tasks[task_name]["running"] = is_running
                
            print(f"已初始化任务状态：{self.tasks[task_name]}")
            
            # 根据任务类型设置不同的处理逻辑
            if not task_type:
                print("任务配置中缺少任务类型")
                if not task_exists:  # 只在新任务的情况下删除
                    del self.tasks[task_name]
                return False
                
            print(f"任务类型：{task_type}")
            
            if task_type == "transfer":
                # 消息转发任务不需要额外设置
                print("已设置消息转发任务")
            elif task_type == "reply":
                # 消息回复任务不需要额外设置
                print("已设置消息回复任务")
            elif task_type == "schedule":
                # 确保调度线程已启动
                self.start_scheduler()
                
                # 设置定时任务
                setup_success = self.message_scheduler.setup_task(task_config)
                if not setup_success:
                    print(f"设置定时任务失败: {task_name}")
                    # 打印更多详细信息
                    print(f"目标类型: {task_config.get('target_type')}, 目标: {task_config.get('target')}")
                    
                    # 尝试查找目标
                    if task_config.get('target_type') == "好友":
                        target_name = task_config.get('target')
                        if target_name:
                            try:
                                target_wxid = self.message_scheduler.find_user_by_name(target_name)
                                print(f"查找目标结果: {target_name} -> {target_wxid}")
                            except Exception as e:
                                print(f"查找目标时出错: {e}")
                    
                    # 设置失败，但仍保留任务记录
                    self.tasks[task_name]["running"] = False
                    task_config["status"] = "stopped"
                    task_config["last_state"] = False
                    self.status_changed.emit(task_name, False)
                    print(f"任务 {task_name} 保留但状态设为已停止")
                    
                    # 如果是新任务，可以选择删除
                    # if not task_exists:
                    #     del self.tasks[task_name]
                    return False
                
                print(f"定时任务 {task_name} 设置成功")
            else:
                print(f"不支持的任务类型：{task_type}")
                if not task_exists:  # 只在新任务的情况下删除
                    del self.tasks[task_name]
                return False
                    
            # 确保任务状态为运行
            self.tasks[task_name]["running"] = True
            print(f"任务 {task_name} 状态设置为运行中 (running=True)")
            
            self.task_started.emit(task_name)
            self.status_changed.emit(task_name, True)  # 发送状态为运行中
            print(f"任务 {task_name} 启动成功")
            return True
            
        except Exception as e:
            print(f"启动任务失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            if task_name in self.tasks and not task_exists:
                del self.tasks[task_name]
            return False
            
    def stop_task(self, task_name: str) -> bool:
        """停止任务"""
        try:
            if task_name not in self.tasks:
                return False
                
            task = self.tasks[task_name]
            task["running"] = False
            
            # 保存任务状态到配置中
            task["config"]["status"] = "stopped"
            task["config"]["last_state"] = False
            
            # 根据任务类型清理资源
            task_type = task["config"]["type"]
            if task_type == "schedule":
                # 不再完全移除定时任务，只取消调度
                # self.message_scheduler.remove_task(task_name)
                # 改为仅清除调度但保留任务记录
                schedule.clear(task_name)
                print(f"已停止定时任务: {task_name} (仅取消调度，保留任务记录)")
                
            del self.tasks[task_name]
            self.task_stopped.emit(task_name)
            self.status_changed.emit(task_name, False)
            return True
        except Exception as e:
            print(f"停止任务失败: {e}")
            return False
            
    def toggle_task_status(self, task_name: str, new_status: bool) -> bool:
        """切换任务状态"""
        try:
            if task_name not in self.tasks:
                return False
                
            task = self.tasks[task_name]
            task["running"] = new_status
            
            # 更新任务配置
            task["config"]["status"] = "running" if new_status else "stopped"
            task["config"]["last_state"] = new_status
            
            # 发送状态变更信号
            self.status_changed.emit(task_name, new_status)
            return True
        except Exception as e:
            print(f"切换任务状态失败: {e}")
            return False
            
    def add_message(self, message: Dict):
        """添加消息到队列"""
        self.message_queue.put(message)
        
    def _process_messages(self):
        """处理消息队列中的消息"""
        while self.running:
            try:
                # 获取一条消息
                message = self.message_queue.get(timeout=1)
                
                # 使用 _handle_message 处理消息
                with self.message_lock:
                    self._handle_message(message)
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"处理消息时出错: {e}")
                continue
                
    def _handle_message(self, msg):
        """处理接收到的消息"""
        try:
            # 将消息转换为字典格式（如果还不是字典）
            if isinstance(msg, WxMsg):  # 如果是 WxMsg 对象
                msg_dict = {
                    "type": msg.type,
                    "content": msg.content,
                    "sender": msg.sender,
                    "roomid": msg.roomid,
                    "is_group": msg.from_group(),  # 使用 WxMsg 类提供的方法
                    "timestamp": msg.ts,  # 使用正确的属性名
                    "xml": msg.xml,
                    "id": msg.id  # 添加消息ID
                }
            else:  # 如果已经是字典
                msg_dict = msg
                # 简化检查：直接设置is_group属性
                if "is_group" not in msg_dict:
                    # 如果消息中有roomid或room_wxid，则认为是群消息
                    msg_dict["is_group"] = bool(msg_dict.get("roomid") or msg_dict.get("room_wxid"))
                    
                    # 如果有room_wxid但没有roomid，则复制一份到roomid
                    if not msg_dict.get("roomid") and msg_dict.get("room_wxid"):
                        msg_dict["roomid"] = msg_dict["room_wxid"]
            
            # 获取群名称和发送者名称
            room_name = None
            sender_name = None
            
            if msg_dict.get("is_group", False):
                # 从群组列表中查找群名称
                roomid = msg_dict.get("roomid")
                if roomid and isinstance(self.robot.allGroups, dict):
                    # 直接通过群ID获取群名称
                    room_name = self.robot.allGroups.get(roomid)
                    if not room_name:
                        # 如果没找到，尝试反向查找
                        for wxid, name in self.robot.allGroups.items():
                            if wxid == roomid:
                                room_name = name
                                break
                
                # 从群成员列表中查找发送者名称
                sender_wxid = msg_dict.get("sender")
                if sender_wxid and room_name:
                    # 首先尝试从群成员列表中获取
                    if hasattr(self.robot, 'group_members') and room_name in self.robot.group_members:
                        for member in self.robot.group_members[room_name]:
                            if member.get("wxid") == sender_wxid:
                                sender_name = member.get("name")
                                break
                    
                    # 如果没找到，尝试从联系人列表中获取
                    if not sender_name:
                        if isinstance(self.robot.contacts, list):
                            for contact in self.robot.contacts:
                                if isinstance(contact, dict) and contact.get("wxid") == sender_wxid:
                                    sender_name = contact.get("name") or contact.get("remark") or sender_wxid
                                    break
            else:
                # 从联系人列表中查找发送者名称
                sender_wxid = msg_dict.get("sender")
                if sender_wxid:
                    if isinstance(self.robot.contacts, list):
                        for contact in self.robot.contacts:
                            if isinstance(contact, dict) and contact.get("wxid") == sender_wxid:
                                sender_name = contact.get("name") or contact.get("remark") or sender_wxid
                                break
            
            # 如果还是没找到名称，使用wxid作为显示名称
            if not room_name and msg_dict.get("roomid"):
                room_name = msg_dict["roomid"]
            if not sender_name and msg_dict.get("sender"):
                sender_name = msg_dict["sender"]
            
            # 只获取消息内容，但不直接打印
            content = msg_dict.get("content", "")
            
            # 检查是否是配置中的群或任务相关群
            roomid = msg_dict.get("roomid")
            is_in_groups = roomid in self.robot.config.get_groups()
            is_in_task_groups = roomid in self.robot.config.get_task_groups()
            
            # 只对配置中的群打印详细消息，减少日志量
            if content and (is_in_groups or is_in_task_groups):
                if msg_dict.get("is_group", False):
                    print(f"[群聊] {room_name} - {sender_name}: {content[:50]}{'...' if len(content) > 50 else ''}")
                else:
                    print(f"[私聊] {sender_name}: {content[:50]}{'...' if len(content) > 50 else ''}")
            
            # 打印可用任务列表
            print(f"当前可用任务: {len(self.tasks)} 个")
            for task_name, task in self.tasks.items():
                task_type = task.get("config", {}).get("type", "未知")
                task_status = "运行中" if task.get("running", False) else "已停止"
                print(f"  - {task_name} ({task_type}) [{task_status}]")
            
            # 处理消息
            tasks_matched = 0
            for task_name, task in self.tasks.items():
                if task.get("running", False):  # 只处理运行中的任务
                    task_config = task["config"]
                    print(f"检查任务 {task_name} 是否匹配消息...")
                    if self.message_transfer.check_message_match(msg_dict, task_config):
                        tasks_matched += 1
                        if task_config["type"] == "transfer":
                            print(f"匹配到转发任务: {task_name}, 开始转发")
                            if self.message_transfer.process_task(msg_dict, task_config):
                                task["stats"]["succeeded"] += 1
                                print(f"转发成功: {task_name}")
                            else:
                                task["stats"]["failed"] += 1
                                print(f"转发失败: {task_name}")
                            task["stats"]["processed"] += 1
                            self.stats_updated.emit(task_name, task["stats"])
                        elif task_config["type"] == "reply":
                            print(f"匹配到回复任务: {task_name}, 开始回复")
                            self._handle_reply_task(msg_dict, task)
            
            if tasks_matched == 0:
                print(f"消息未匹配任何任务")
                
        except Exception as e:
            print(f"消息处理错误: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def _handle_reply_task(self, message: Dict, task: Dict):
        """处理回复任务"""
        try:
            task_name = task["config"]["name"]
            reply_content = task["config"]["reply_content"]
            reply_type = task["config"]["reply_type"]
            
            # 检查消息是否匹配回复条件
            if not self._check_message_match(message, task["config"]):
                return
                
            # 获取回复目标
            target_wxid = message.get("roomid")
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
                if self.wcf.send_text(reply_content, target_wxid):
                    task["stats"]["succeeded"] += 1
                else:
                    task["stats"]["failed"] += 1
            elif reply_type == "图片":
                if self.wcf.send_image(reply_content, target_wxid):
                    task["stats"]["succeeded"] += 1
                else:
                    task["stats"]["failed"] += 1
                    
            task["stats"]["processed"] += 1
            self.stats_updated.emit(task_name, task["stats"])
                    
        except Exception as e:
            print(f"处理回复任务失败: {e}")
            
    def _check_message_match(self, message: Dict, task_config: Dict) -> bool:
        """检查消息是否匹配任务条件"""
        try:
            # 不同任务类型有不同的匹配条件
            task_type = task_config["type"]
            
            if task_type == "transfer":
                return self.message_transfer.check_message_match(message, task_config)
                
            elif task_type == "reply":
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
            
    def stop(self):
        """停止任务执行器"""
        print("正在停止任务执行器...")
        self.running = False
        
        try:
            # 清空消息队列，防止阻塞
            try:
                while not self.message_queue.empty():
                    try:
                        self.message_queue.get_nowait()
                    except:
                        break
            except Exception as e:
                print(f"清理消息队列时出错: {e}")
            
            # 直接通知消息调度器停止
            if hasattr(self, 'message_scheduler'):
                try:
                    self.message_scheduler.running = False
                except Exception as e:
                    print(f"停止消息调度器时出错: {e}")
            
            # 尝试终止处理线程
            if hasattr(self, 'process_thread') and self.process_thread and self.process_thread.is_alive():
                print("等待消息处理线程结束...")
                # 只等待有限时间
                self.process_thread.join(2.0)
                if self.process_thread.is_alive():
                    print("消息处理线程未能正常结束")
            
            print("任务执行器已停止")
        except Exception as e:
            print(f"任务执行器停止过程中出错: {e}")
            import traceback
            traceback.print_exc()

    def get_task_stats(self, task_name: str) -> Dict:
        """获取任务统计信息"""
        if task_name in self.tasks:
            return self.tasks[task_name]["stats"]
        elif task_name in self.message_scheduler.get_all_tasks():
            task_status = self.message_scheduler.get_task_status(task_name)
            return {
                "processed": task_status["success_count"] + task_status["error_count"],
                "succeeded": task_status["success_count"],
                "failed": task_status["error_count"]
            }
        return {
            "processed": 0,
            "succeeded": 0,
            "failed": 0
        }
        
    def is_task_running(self, task_name: str) -> bool:
        """检查任务是否正在运行"""
        if task_name not in self.tasks:
            return False
        return self.tasks[task_name].get("running", False)

    def delete_task(self, task_name: str) -> bool:
        """彻底删除任务
        
        与stop_task不同，这个方法会彻底从系统中移除任务，
        包括从scheduler中清除以及从配置中删除
        
        Args:
            task_name: 任务名称
            
        Returns:
            bool: 是否成功删除
        """
        try:
            # 先确保任务已停止
            if task_name in self.tasks and self.tasks[task_name]["running"]:
                # 如果任务正在运行，先停止它
                self.stop_task(task_name)
            
            # 根据任务类型处理
            task_config = None
            for task in self.robot.config.tasks:
                if task.get("name") == task_name:
                    task_config = task
                    break
                
            if task_config:
                task_type = task_config.get("type")
                
                # 根据任务类型清理资源
                if task_type == "schedule":
                    # 彻底移除定时任务
                    self.message_scheduler.remove_task(task_name)
                    print(f"已删除定时任务: {task_name}")
                    
                # 从配置中删除任务
                self.robot.config.tasks.remove(task_config)
                
                # 保存配置
                self.robot.save_config()
                
                # 发送任务已删除的信号
                self.task_stopped.emit(task_name)
                
                return True
            else:
                print(f"警告: 未找到要删除的任务 {task_name}")
                return False
                
        except Exception as e:
            print(f"删除任务失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_tasks(self):
        """从文件加载任务配置"""
        try:
            tasks_path = os.path.join("config", "tasks.json")
            if not os.path.exists(tasks_path):
                print("任务配置文件不存在，无法加载任务")
                return
            
            with open(tasks_path, "r", encoding="utf-8") as f:
                tasks = json.load(f)
            
            print(f"已加载 {len(tasks)} 个任务")
            for task_config in tasks:
                task_name = task_config.get("name")
                if not task_name:
                    print("警告: 任务配置中缺少任务名称，跳过该任务")
                    continue
                
                task_type = task_config.get("type")
                if not task_type:
                    print(f"警告: 任务 {task_name} 缺少类型定义，跳过该任务")
                    continue
                    
                # 获取任务状态，优先使用status字段，默认为stopped
                status = task_config.get("status", "stopped")
                is_running = status == "running"
                
                # 获取上次任务状态，默认为False
                last_state = task_config.get("last_state", False)
                
                print(f"加载任务: {task_name}, 类型: {task_type}, 当前状态: {status}, 上次状态: {'运行' if last_state else '停止'}")
                    
                # 初始化任务状态
                self.tasks[task_name] = {
                    "config": task_config,
                    "running": is_running,  # 使用当前状态而非默认False
                    "stats": {
                        "processed": 0,
                        "succeeded": 0,
                        "failed": 0
                    }
                }
                
                # 如果任务之前是启动状态，则自动启动
                if last_state:
                    print(f"自动启动任务: {task_name}（上次状态为运行）")
                    time.sleep(0.2)  # 稍微延迟，避免同时启动太多任务
                    self.start_task(task_config)
                else:
                    print(f"不自动启动任务: {task_name}（上次状态为停止）")
            
            # 检查任务加载情况
            if not self.tasks:
                print("警告: 没有成功加载任何任务")
            else:
                print("成功加载的任务列表:")
                for task_name, task in self.tasks.items():
                    status = "运行中" if task["running"] else "已停止"
                    task_type = task["config"]["type"]
                    print(f"  - {task_name} ({task_type}) [{status}]")
            
            # 加载完成后同步任务群组到配置
            self.sync_task_groups_to_config()
        except Exception as e:
            print(f"加载任务失败: {e}")
            import traceback
            traceback.print_exc()

    def update_task(self, task_name: str, updated_task: dict) -> bool:
        """更新任务配置
        
        Args:
            task_name: 任务名称
            updated_task: 更新后的任务配置
            
        Returns:
            bool: 是否成功更新
        """
        try:
            print(f"开始更新任务: {task_name}")
            print(f"新配置: {updated_task}")
            
            # 检查任务是否存在
            if task_name not in self.tasks:
                print(f"任务 {task_name} 不存在，自动创建新任务")
                # 当任务不存在时，使用start_task方法创建新任务
                return self.start_task(updated_task)
            
            # 获取当前任务配置
            current_task = self.tasks[task_name]
            current_config = current_task["config"]
            print(f"当前配置: {current_config}")
            
            # 保存原始运行状态
            original_running = current_task["running"]
            
            # 更新任务配置
            current_task["config"] = updated_task
            
            # 检查状态是否改变
            status = updated_task.get("status", "stopped")
            is_running = status == "running"
            
            # 如果状态改变，则更新运行状态
            if original_running != is_running:
                current_task["running"] = is_running
                # 发送状态变更信号
                self.status_changed.emit(task_name, is_running)
                print(f"任务状态已更新: {is_running}")
            
            # 如果是定时任务且配置发生改变，需要重新设置调度
            if updated_task.get("type") == "schedule":
                # 需要重新设置的字段
                schedule_fields = ["time", "repeat_type", "interval_hours", "start_time", "week_days"]
                
                # 检查是否需要重新设置调度
                need_reschedule = False
                for field in schedule_fields:
                    if updated_task.get(field) != current_config.get(field):
                        need_reschedule = True
                        print(f"字段 {field} 已更改，需要重新设置调度")
                        break
                
                # 如果需要重新设置调度，则重新设置
                if need_reschedule:
                    print("需要重新设置定时任务调度")
                    schedule.clear(task_name)  # 清除原有调度
                    # 重新设置定时任务
                    if self.message_scheduler.setup_task(updated_task):
                        print(f"成功重新设置定时任务 {task_name}")
                    else:
                        print(f"重新设置定时任务 {task_name} 失败")
                        return False
            
            print(f"任务 {task_name} 更新成功")
            return True
            
        except Exception as e:
            print(f"更新任务失败: {e}")
            import traceback
            traceback.print_exc()
            return False

