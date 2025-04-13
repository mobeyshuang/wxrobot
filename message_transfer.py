import os
import time
import logging
import datetime
import glob
from typing import Dict, List, Optional, Tuple
import re
from wcferry import Wcf
import json

# 设置日志记录
def setup_logging(debug_mode=False):
    """设置日志记录器"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_file = os.path.join(log_dir, f"message_transfer_{datetime.datetime.now().strftime('%Y%m%d')}.log")
    
    # 创建日志记录器
    logger = logging.getLogger("MessageTransfer")
    # 根据debug模式设置日志级别
    logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # 清除现有的处理器（避免重复记录）
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)
    
    # 使用TimedRotatingFileHandler按天滚动日志
    from logging.handlers import TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',      # 每天午夜滚动
        interval=1,           # 间隔1天
        backupCount=2,        # 保留2天的日志
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # 控制台只显示INFO及以上级别
    
    # 设置更简洁的日志格式
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 创建日志记录器 - 默认为INFO级别，只有在明确需要时才开启DEBUG
logger = setup_logging(debug_mode=False)

# 清理过期日志文件
def cleanup_expired_logs(days=2):
    """
    清理超过指定天数的日志文件
    
    Args:
        days: 保留的天数，默认2天
    """
    try:
        log_dir = "logs"
        if not os.path.exists(log_dir):
            return
            
        # 计算截止时间
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        # 获取所有日志文件
        log_files = glob.glob(f"{log_dir}/*.*")
        
        # 检查每个文件的修改时间
        for file_path in log_files:
            # 获取文件的修改时间
            file_mtime = os.path.getmtime(file_path)
            if file_mtime < cutoff_time:
                try:
                    os.remove(file_path)
                    logger.info(f"已删除过期日志文件: {file_path}")
                except Exception as e:
                    logger.error(f"删除过期日志文件 {file_path} 失败: {e}")
    except Exception as e:
        logger.error(f"清理过期日志文件时出错: {e}")

# 启动时清理过期日志
cleanup_expired_logs(2)

class MessageTransfer:
    def __init__(self, wcf: Wcf, robot):
        self.wcf = wcf
        self.robot = robot
        self.tasks = []
        self.matched_message_id = None
        self.matched_filename = None  # 保存匹配成功的文件名
        self.file_size_threshold = 3 * 1024 * 1024  # 3MB，大于这个大小的文件使用下载-重发模式
        
        # 初始化微信文件目录
        self.wechat_files_dir = None
        if hasattr(self.robot, 'config') and hasattr(self.robot.config, 'get'):
            self.wechat_files_dir = self.robot.config.get("WECHAT_FILES_DIR", "")
            
        logger.info(f"MessageTransfer初始化完成，微信文件目录: {self.wechat_files_dir}")
        
    def get_current_month_dir(self) -> str:
        """获取当前月份目录名"""
        return time.strftime("%Y-%m", time.localtime())
    
    def wait_for_file(self, filename: str, initial_wait: float = 5.0) -> bool:
        """
        等待文件出现在微信目录中
        
        Args:
            filename: 要等待的文件名
            initial_wait: 等待时间（秒）
            
        Returns:
            bool: 文件是否出现
        """
        # 使用计时器方式等待
        logger.info(f"等待 {initial_wait} 秒后开始检查文件")
        time.sleep(initial_wait)
        
        # 直接检查文件是否存在
        current_month = self.get_current_month_dir()
        search_dirs = [
            os.path.join(self.wechat_files_dir, current_month),
            self.wechat_files_dir
        ]
        
        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue
                
            for root, _, files in os.walk(search_dir):
                for file in files:
                    if filename.lower() in file.lower():
                        logger.info(f"文件 {filename} 已出现在目录中")
                        return True
        
        logger.warning(f"等待后未找到文件 {filename}")
        return False
        
    def find_file_in_wechat_dir(self, filename: str, max_retries: int = 3, retry_interval: float = 1.0) -> Optional[str]:
        """
        在微信文件目录中查找指定文件，支持重试机制
        
        Args:
            filename: 要查找的文件名
            max_retries: 最大重试次数
            retry_interval: 重试间隔时间（秒）
            
        Returns:
            Optional[str]: 找到的文件完整路径，未找到返回None
        """
        try:
            # 检查微信文件目录是否已设置
            if not self.wechat_files_dir or not os.path.exists(self.wechat_files_dir):
                logger.warning(f"微信文件目录未设置或不存在: {self.wechat_files_dir}")
                return None
                
            logger.debug(f"开始在微信目录查找文件: {filename}")
            
            # 获取当前月份目录
            current_month = self.get_current_month_dir()
            
            # 统一使用正斜杠，避免路径问题
            wechat_files_dir = self.wechat_files_dir.replace('\\', '/')
            
            # 构建当月完整路径
            month_dir = os.path.join(wechat_files_dir, current_month).replace('\\', '/')
            
            # 检查月份目录是否存在
            if not os.path.exists(month_dir):
                logger.debug(f"当月目录不存在: {month_dir}，将在根目录中查找")
                # 直接使用根目录
                month_dir = wechat_files_dir
            else:
                logger.debug(f"使用当月目录: {month_dir}")
                
            # 使用重试机制查找文件
            for attempt in range(max_retries):
                # 等待文件出现并检查
                found = self.wait_for_file(filename)
                if found:
                    # 如果文件已找到，重新在目录中查找具体路径
                    search_dirs = [
                        os.path.join(self.wechat_files_dir, current_month),
                        self.wechat_files_dir
                    ]
                    
                    for search_dir in search_dirs:
                        if not os.path.exists(search_dir):
                            continue
                            
                        for root, _, files in os.walk(search_dir):
                            root = root.replace('\\', '/')  # 统一使用正斜杠
                            for file in files:
                                # 简单的文件名匹配，忽略大小写
                                if filename.lower() in file.lower():
                                    file_path = os.path.join(root, file).replace('\\', '/')
                                    logger.info(f"找到文件: {file_path}")
                                    return file_path
                
                if attempt < max_retries - 1:
                    logger.debug(f"第 {attempt + 1} 次查找失败，等待 {retry_interval} 秒后重试")
                    time.sleep(retry_interval)
                    
            logger.warning(f"经过 {max_retries} 次尝试后仍未找到匹配的文件: {filename}")
            return None
                
        except Exception as e:
            logger.error(f"查找文件过程中出错: {e}")
            import traceback
            logger.debug(traceback.format_exc())  # 完整堆栈改为DEBUG级别
            return None
        
    def add_task(self, task_config):
        """添加转发任务"""
        self.tasks.append(task_config)
        
    def remove_task(self, task_name):
        """移除转发任务"""
        self.tasks = [task for task in self.tasks if task["name"] != task_name]
        
    def check_message_match(self, message: Dict, task_config: Dict) -> bool:
        """检查消息是否匹配任务配置"""
        try:
            task_name = task_config.get("name", "未命名任务")
            logger.debug(f"检查任务 [{task_name}] 匹配")
            
            # 获取消息来源
            if hasattr(message, 'roomid'):  # 如果是WxMsg对象
                room_wxid = message.roomid
            else:  # 如果是字典
                room_wxid = message.get('roomid') or message.get('room_wxid')  # 兼容两种格式
                
            if not room_wxid:
                logger.debug("消息没有群聊ID")
                return False
                
            # 获取群名
            group_name = None
            if not hasattr(self.robot, 'allGroups'):
                logger.warning("robot对象没有allGroups属性")
                return False
                
            groups = self.robot.allGroups
            if not isinstance(groups, dict):
                logger.warning(f"allGroups不是字典类型，而是{type(groups)}")
                return False
                
            # 首先尝试直接通过wxid查找
            if room_wxid in groups:
                group_name = groups[room_wxid]
            else:
                # 如果找不到，尝试反向查找
                for wxid, name in groups.items():
                    if name == room_wxid:
                        group_name = name
                        room_wxid = wxid  # 更新为正确的wxid
                        break
                            
            if not group_name:
                logger.debug(f"无法找到群聊ID {room_wxid} 对应的群名")
                return False
                
            logger.debug(f"当前群聊: {group_name} (wxid: {room_wxid})")
            
            # 获取任务配置中的源群
            source = task_config.get("source", "")
            logger.debug(f"任务配置中的源群: {source}")
            
            # 检查是否来自指定群（支持群名和群ID两种格式）
            # 如果source是群ID（包含@chatroom），直接与room_wxid比较
            if "@chatroom" in source:
                if source != room_wxid:
                    logger.debug(f"消息来自群ID {room_wxid}，不是目标群ID {source}")
                    return False
            # 否则认为source是群名，与group_name比较
            else:
                if group_name != source:
                    logger.debug(f"消息来自群 {group_name}，不是目标群 {source}")
                    return False
                    
            # 检查发送者是否匹配（如果任务配置中指定了member且不是"全部"）
            member = task_config.get("member", "全部")
            if member != "全部":
                # 获取发送者ID
                if hasattr(message, 'sender'):  # 如果是WxMsg对象
                    sender_wxid = message.sender
                else:  # 如果是字典
                    sender_wxid = message.get('sender')
                    
                if not sender_wxid:
                    logger.debug("消息没有发送者ID")
                    return False
                    
                # 获取发送者在群内的昵称
                sender_name = None
                try:
                    sender_name = self.robot.wcf.get_alias_in_chatroom(sender_wxid, room_wxid)
                except Exception as e:
                    logger.debug(f"获取发送者昵称出错: {e}")
                    
                # 如果取不到群内昵称，尝试从联系人列表获取
                if not sender_name:
                    if isinstance(self.robot.contacts, list):
                        for contact in self.robot.contacts:
                            if isinstance(contact, dict) and contact.get("wxid") == sender_wxid:
                                sender_name = contact.get("name") or contact.get("remark") or sender_wxid
                                break
                
                # 如果还是取不到，使用wxid作为发送者标识
                if not sender_name:
                    sender_name = sender_wxid
                    
                logger.debug(f"发送者: {sender_name} (wxid: {sender_wxid})")
                
                # 检查发送者是否匹配
                if member != sender_name and member != sender_wxid:
                    logger.debug(f"发送者 {sender_name} 不匹配指定成员 {member}")
                    return False
                    
                logger.debug(f"发送者 {sender_name} 匹配指定成员 {member}")
                
            # 检查消息类型
            message_type = None
            if hasattr(message, 'type'):  # 如果是WxMsg对象
                message_type = message.type
            else:  # 如果是字典
                message_type = message.get('type', 0)
                
            # 获取消息内容
            content = None
            if hasattr(message, 'content'):  # 如果是WxMsg对象
                content = message.content
            else:  # 如果是字典
                content = message.get('content', '')
                
            logger.debug(f"消息类型: {message_type}, 内容长度: {len(content) if content else 0}")
            
            # 根据消息类型进行匹配
            # 简化日志，只在DEBUG模式下显示长XML内容
            if content and len(content) > 200 and ('<' in content and '>' in content):
                # 只记录有限长度的内容
                logger.debug(f"消息内容(截断): {content[:50]}...{content[-50:] if len(content) > 100 else ''}")
            elif content:
                logger.debug(f"消息内容: {content[:200]}")
            
            # 获取任务配置中的文件类型筛选条件
            file_type = task_config.get("file_type", "")
            logger.debug(f"文件类型筛选条件: {file_type}")
            
            # 判断消息是否含有文件（类型6或49）
            if message_type in [6, 49]:  # 6是文件，49是链接/文件
                logger.debug("消息含有文件或链接")
                
            # 获取转发类型
            forward_type = task_config.get('forward_type', 'text')
            logger.debug(f"任务转发类型: {forward_type}")
            
            # 新增：判断消息类型与转发类型是否匹配
            is_file_message = message_type in [6, 49]  # 6是文件，49是链接/文件
            
            # 如果是文本转发任务但收到的是文件消息，直接跳过
            if forward_type == 'text' and is_file_message:
                logger.debug(f"任务为文本转发类型，但收到的是文件消息（类型:{message_type}），跳过")
                return False
            
            # 如果是文件转发任务但收到的不是文件消息，直接跳过
            if forward_type == 'file' and not is_file_message:
                logger.debug(f"任务为文件转发类型，但收到的不是文件消息（类型:{message_type}），跳过")
                return False
            
            # 如果是文本转发
            if forward_type == 'text':
                # 检查匹配类型和内容
                match_type = task_config.get('match_type', '包含')
                match_content = task_config.get('match_content', '')
                
                logger.debug(f"文本匹配类型: {match_type}, 匹配内容: {match_content}")
                logger.debug(f"消息内容: {content[:100]}...")  # 仅显示前100个字符
                
                if match_type == '包含':
                    if match_content not in content:
                        logger.debug(f"消息内容不包含匹配条件: {match_content}")
                        return False
                    else:
                        logger.debug(f"匹配成功: 消息内容包含 '{match_content}'")
                elif match_type == '等于':
                    if match_content != content:
                        logger.debug(f"消息内容不等于匹配条件: {match_content}")
                        return False
                    else:
                        logger.debug(f"匹配成功: 消息内容等于 '{match_content}'")
                elif match_type == '正则':
                    if not re.search(match_content, content):
                        logger.debug(f"消息内容不匹配正则表达式: {match_content}")
                        return False
                    else:
                        logger.debug(f"匹配成功: 消息内容匹配正则 '{match_content}'")
                        
            # 如果是文件转发
            elif forward_type == 'file':
                logger.debug(f"文件消息类型: {message_type}")
                # 检查是否是文件消息
                if not is_file_message:
                    logger.debug(f"消息类型 {message_type} 不是文件消息")
                    return False
                    
                # 记录XML内容便于调试
                logger.debug("消息XML内容:")
                logger.debug("-" * 80)
                if len(content) > 5000:
                    logger.debug(f"{content[:2500]}...{content[-2500:]}")  # 过长时只显示前后部分
                else:
                    logger.debug(content)
                logger.debug("-" * 80)
                    
                # 检查文件类型
                if file_type:
                    # 从消息内容中提取文件信息
                    file_info = None
                    try:
                        # 尝试解析消息中的文件信息
                        if content and ('<msgsource>' in content or '<appmsg>' in content):
                            # 提取文件名
                            import re
                            filename_match = re.search(r'<title>(.*?)</title>', content)
                            if filename_match:
                                file_info = filename_match.group(1)
                                logger.debug(f"从<title>标签解析到文件名: {file_info}")
                            else:
                                # 尝试从其他位置提取
                                filename_match = re.search(r'<des>文件: (.*?)</des>', content)
                                if filename_match:
                                    file_info = filename_match.group(1)
                                    logger.debug(f"从<des>标签解析到文件名: {file_info}")
                    except Exception as e:
                        logger.warning(f"解析文件信息失败: {e}")
                    
                    # 根据文件类型进行筛选
                    if file_info:
                        if file_type == "文档" and not any(file_info.lower().endswith(ext) for ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf', '.txt']):
                            logger.debug(f"文件 {file_info} 不是文档类型")
                            return False
                        elif file_type == "图片" and not any(file_info.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']):
                            logger.debug(f"文件 {file_info} 不是图片类型")
                            return False
                        elif file_type == "视频" and not any(file_info.lower().endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv']):
                            logger.debug(f"文件 {file_info} 不是视频类型")
                            return False
                        else:
                            logger.debug(f"文件 {file_info} 符合类型 {file_type}")
                
                # 检查文件匹配条件
                file_match_type = task_config.get('file_match_type', '')
                file_match_content = task_config.get('file_match_content', '')
                logger.debug(f"文件匹配类型: {file_match_type}, 匹配内容: {file_match_content}")
                
                if file_match_type and file_match_content:
                    # 从消息内容中提取文件名
                    filename = None
                    all_matches = []
                    
                    try:
                        # 尝试解析消息中的文件名
                        if content:
                            import re
                            # 尝试多种可能的XML标签格式
                            patterns = [
                                r'<title>(.*?)</title>',
                                r'<des>文件: (.*?)</des>',
                                r'文件名称：(.*?)(\(|<)',
                                r'filename="(.*?)"'
                            ]
                            
                            for pattern in patterns:
                                matches = re.findall(pattern, content)
                                if matches:
                                    for match in matches:
                                        if isinstance(match, tuple):
                                            match = match[0]  # 取正则表达式的第一个捕获组
                                        all_matches.append(match.strip())
                                    
                            # 获取第一个匹配结果作为文件名
                            if all_matches:
                                filename = all_matches[0].strip()
                                logger.debug(f"最终提取到的文件名: {filename}")
                                logger.debug(f"所有提取到的文件相关信息: {all_matches}")
                    except Exception as e:
                        logger.warning(f"提取文件名失败: {e}")
                        import traceback
                        logger.warning(traceback.format_exc())
                    
                    # 如果提取到文件名，进行匹配检查
                    if filename:
                        # 检查文件名中是否包含匹配内容（不区分大小写）
                        filename_lower = filename.lower()
                        match_content_lower = file_match_content.lower()
                        
                        if file_match_type == "包含":
                            if match_content_lower not in filename_lower:
                                logger.debug(f"文件名 '{filename}' 不包含匹配内容 '{file_match_content}'")
                                # 检查其他提取到的信息是否包含匹配内容
                                for info in all_matches:
                                    if match_content_lower in info.lower():
                                        logger.debug(f"但在提取到的其他信息 '{info}' 中包含匹配内容")
                                return False
                            else:
                                logger.debug(f"文件名 '{filename}' 包含匹配内容 '{file_match_content}'，匹配成功")
                                # 保存匹配成功的文件名，供后续下载使用
                                self.matched_filename = filename
                        elif file_match_type == "等于":
                            if filename_lower != match_content_lower:
                                logger.debug(f"文件名 '{filename}' 不等于匹配内容 '{file_match_content}'")
                                return False
                            else:
                                logger.debug(f"文件名 '{filename}' 等于匹配内容 '{file_match_content}'，匹配成功")
                                self.matched_filename = filename
                        elif file_match_type == "正则":
                            if not re.search(file_match_content, filename):
                                logger.debug(f"文件名 '{filename}' 不匹配正则表达式 '{file_match_content}'")
                                return False
                            else:
                                logger.debug(f"文件名 '{filename}' 匹配正则表达式 '{file_match_content}'，匹配成功")
                                self.matched_filename = filename
                    else:
                        logger.warning(f"无法从消息中提取文件名，跳过文件名匹配检查")
                        return False  # 如果文件名无法提取但有匹配条件，则认为不匹配
                
            # 保存消息ID
            if hasattr(message, 'id'):  # 如果是WxMsg对象
                self.matched_message_id = message.id
            else:  # 如果是字典
                self.matched_message_id = message.get('id')
                
            logger.debug(f"==== 任务 [{task_name}] 匹配成功 ====")
            return True
            
        except Exception as e:
            logger.error(f"检查消息匹配失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    def forward_message(self, message: dict, target: str) -> bool:
        """转发消息到指定目标"""
        try:
            logger.info(f"\n开始转发消息到: {target}")
            
            # 获取消息类型
            msg_type = message.get('type', 0)
            logger.info(f"消息类型: {msg_type}")
            
            # 获取目标wxid
            target_wxid = None
            if '@chatroom' in target:
                target_wxid = target
            else:
                # 如果是群名，查找对应的wxid
                for wxid, name in self.robot.allGroups.items():
                    if name.strip() == target.strip():
                        target_wxid = wxid
                        break
                    
            if not target_wxid:
                logger.warning(f"未找到目标 '{target}' 对应的wxid")
                return False
            
            # 使用匹配成功时保存的消息ID
            msg_id = self.matched_message_id
            if not msg_id:
                logger.warning("无法获取消息ID")
                return False
            
            # 如果是文件消息（类型6或49）且有文件名，尝试下载-重发模式
            is_file_message = msg_type in [6, 49]  # 6是文件，49是链接/文件
            
            if is_file_message and self.matched_filename:
                logger.info(f"文件消息: {self.matched_filename}，尝试下载-重发模式")
                
                # 检查微信文件目录是否已设置
                if not self.wechat_files_dir or not os.path.exists(self.wechat_files_dir):
                    logger.warning("微信文件目录未设置，无法使用下载-重发模式")
                    logger.info("请在设置菜单中设置微信文件目录")
                    
                    # 尝试使用原始转发方法
                    logger.info("使用标准转发方法")
                    try:
                        result = self.robot.wcf.forward_msg(msg_id, target_wxid)
                        if result == 1:
                            logger.info("消息转发成功")
                            return True
                        else:
                            logger.warning(f"消息转发失败，返回码: {result}")
                            return False
                    except Exception as e:
                        logger.error(f"转发消息时出错: {e}")
                        return False
                
                # 查找文件
                file_path = self.find_file_in_wechat_dir(self.matched_filename)
                
                if file_path and os.path.exists(file_path):
                    logger.info(f"找到文件: {file_path}，使用直接发送文件的方式")
                    
                    # 获取文件大小
                    try:
                        file_size = os.path.getsize(file_path)
                        logger.info(f"文件大小: {file_size / 1024 / 1024:.2f} MB")
                        
                        # 对大文件使用直接发送模式
                        if file_size > self.file_size_threshold:
                            logger.info("文件大小超过阈值，使用send_file方法发送")
                            
                            try:
                                # 正确的参数顺序是 (path, receiver)
                                logger.info(f"发送文件 {file_path} 到 {target_wxid}")
                                result = self.robot.wcf.send_file(file_path, target_wxid)
                                
                                # 根据返回结果确定是否成功
                                if result == 0:
                                    logger.info(f"文件发送成功: {file_path}")
                                    return True
                                else:
                                    logger.error(f"文件发送失败，错误码: {result}")
                                    
                                    # 尝试使用标准转发方法作为后备
                                    logger.info("尝试使用标准转发方法作为备选")
                                    fallback_result = self.robot.wcf.forward_msg(msg_id, target_wxid)
                                    if fallback_result == 1:
                                        logger.info("使用标准转发成功")
                                        return True
                                    else:
                                        logger.warning(f"标准转发也失败，返回码: {fallback_result}")
                                        return False
                            except Exception as e:
                                logger.error(f"发送文件时发生异常: {e}")
                                import traceback
                                logger.error(traceback.format_exc())
                                logger.info("由于异常，尝试使用标准转发方法")
                                try:
                                    fallback_result = self.robot.wcf.forward_msg(msg_id, target_wxid)
                                    if fallback_result == 1:
                                        logger.info("使用标准转发成功")
                                        return True
                                    else:
                                        logger.warning(f"标准转发也失败，返回码: {fallback_result}")
                                except Exception as e2:
                                    logger.error(f"标准转发也出错: {e2}")
                                return False
                    except Exception as e:
                        logger.error(f"获取文件大小或发送文件时出错: {e}")
                        logger.info("由于异常，尝试使用标准转发方法")
                        try:
                            fallback_result = self.robot.wcf.forward_msg(msg_id, target_wxid)
                            if fallback_result == 1:
                                logger.info("使用标准转发成功")
                                return True
                        except Exception as e2:
                            logger.error(f"标准转发也出错: {e2}")
                        return False
                else:
                    logger.warning(f"在微信目录中未找到文件或文件不存在: {self.matched_filename}")
                    logger.info("使用标准转发方法")
                    try:
                        result = self.robot.wcf.forward_msg(msg_id, target_wxid)
                        if result == 1:
                            logger.info("标准转发成功")
                            return True
                        else:
                            logger.warning(f"标准转发失败，返回码: {result}")
                            return False
                    except Exception as e:
                        logger.error(f"标准转发出错: {e}")
                        return False
            
            # 如果没有匹配的文件或文件类型不是文件消息，使用原始转发方法
            logger.info("使用标准转发方法")
            try:
                result = self.robot.wcf.forward_msg(msg_id, target_wxid)
                if result == 1:
                    logger.info("消息转发成功")
                    return True
                else:
                    logger.warning(f"消息转发失败，返回码: {result}")
                    # 尝试使用备用方法重新发送
                    logger.info("尝试使用备用方法发送")
                    
                    # 对于文本消息，可以重新发送内容
                    if not is_file_message and hasattr(message, 'content'):
                        content = message.get('content', '')
                        if content:
                            result = self.robot.wcf.send_text(target_wxid, content)
                            if result:
                                logger.info("使用备用方法发送文本成功")
                                return True
                    
                    return False
            except Exception as e:
                logger.error(f"转发消息时出错: {e}")
                return False
            
        except Exception as e:
            logger.error(f"转发消息时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    def process_task(self, message: Dict, task_config: Dict):
        """处理一个任务配置"""
        task_name = task_config.get("name", "未命名任务")
        logger.info(f"处理转发任务: {task_name}")
        logger.debug(f"任务详情: {json.dumps(task_config, ensure_ascii=False)}")
        
        # 获取目标群 - 使用target字段(单数形式)
        target = task_config.get("target", "")
        if not target:
            logger.warning(f"任务 {task_name} 未设置转发目标")
            return False

        # 获取消息内容
        content = None
        if hasattr(message, 'content'):  # 如果是WxMsg对象
            content = message.content
        else:  # 如果是字典
            content = message.get('content', '')
            
        # 获取发送者ID和名称
        sender_wxid = None
        sender_name = None
        room_wxid = None
        
        # 提取发送者ID
        if hasattr(message, 'sender'):  # 如果是WxMsg对象
            sender_wxid = message.sender
        else:  # 如果是字典
            sender_wxid = message.get('sender')
            
        # 提取群ID
        if hasattr(message, 'roomid'):  # 如果是WxMsg对象
            room_wxid = message.roomid
        else:  # 如果是字典
            room_wxid = message.get('roomid') or message.get('room_wxid')  # 兼容两种格式
            
        # 获取发送者昵称
        if sender_wxid and room_wxid:
            try:
                sender_name = self.robot.wcf.get_alias_in_chatroom(sender_wxid, room_wxid) or "未知用户"
            except Exception as e:
                logger.debug(f"获取发送者昵称出错: {e}")
                sender_name = "未知用户"
                
        # 获取源群名称
        group_name = None
        if room_wxid and hasattr(self.robot, 'allGroups'):
            groups = self.robot.allGroups
            if isinstance(groups, dict) and room_wxid in groups:
                group_name = groups[room_wxid]
                
        # 记录消息来源信息
        source_info = f"[{group_name or room_wxid}] 的 [{sender_name or sender_wxid}]"
        logger.info(f"转发消息来自: {source_info}")
        
        # 构建消息前缀
        prefix_type = task_config.get("prefix_type", "无")
        prefix_content = task_config.get("prefix_content", "")
        
        # 根据前缀类型构建实际前缀
        actual_prefix = ""
        if prefix_type == "无":
            pass  # 不添加前缀
        elif prefix_type == "固定":
            actual_prefix = prefix_content
        elif prefix_type == "来源":
            actual_prefix = f"消息来自 {source_info}:"
        elif prefix_type == "来源+固定":
            actual_prefix = f"消息来自 {source_info}:\n{prefix_content}"
            
        logger.debug(f"使用前缀: '{actual_prefix}'")
        
        # 获取消息类型
        message_type = None
        if hasattr(message, 'type'):  # 如果是WxMsg对象
            message_type = message.type
        else:  # 如果是字典
            message_type = message.get('type', 0)
            
        # 获取转发类型
        forward_type = task_config.get("forward_type", "text")
        logger.debug(f"转发类型: {forward_type}, 消息类型: {message_type}")
        
        # 处理目标群
        success = False
        logger.info(f"开始向 {target} 转发消息")
        
        # 查找目标群ID
        target_wxid = None
        if "@chatroom" in target:  # 如果目标是wxid格式
            target_wxid = target
        else:  # 如果目标是群名
            # 查找对应的wxid
            if hasattr(self.robot, 'allGroups'):
                groups = self.robot.allGroups
                if isinstance(groups, dict):
                    for wxid, name in groups.items():
                            if name == target:
                                target_wxid = wxid
                                break
            
            if not target_wxid:
                logger.warning(f"找不到目标群 {target} 的wxid，无法转发")
                return False
            
        # 根据消息类型进行转发
        if forward_type == "text":
            # 文本消息直接转发
            if actual_prefix:
                send_text = f"{actual_prefix}\n{content}"
            else:
                send_text = content
                
            logger.debug(f"向 {target} 发送文本: {send_text[:50]}...{send_text[-50:] if len(send_text) > 100 else ''}")
            
            try:
                self.robot.wcf.send_text(send_text, target_wxid)
                logger.info(f"成功向 {target} 转发文本消息")
                success = True
            except Exception as e:
                logger.error(f"向 {target} 转发文本消息失败: {e}")
                
        elif forward_type == "file":
            # 文件消息需要特殊处理
            logger.debug("处理文件类型消息")
            
            # 处理微信文件
            try:
                # 1. 找到原始文件
                if message_type == 49:  # 文件消息
                    logger.debug("处理XML类型的文件消息")
                    # 从XML中提取文件名
                    try:
                        # 尝试提取文件名
                        filename_match = re.search(r'<title>(.*?)</title>', content)
                        if filename_match:
                            filename = filename_match.group(1)
                            logger.debug(f"从XML提取的文件名: {filename}")
                        else:
                            # 如果找不到文件名，使用默认名
                            logger.debug("无法从XML提取文件名，使用默认名")
                            filename = f"文件_{int(time.time())}"
                            
                        # 提取消息ID
                        msg_id = None
                        if hasattr(message, 'id'):
                            msg_id = message.id
                        else:
                            msg_id = message.get('id')
                            
                        logger.debug(f"文件消息ID: {msg_id}")
                        
                        # 检查是否缓存了匹配的文件名
                        if hasattr(self, 'matched_filename') and self.matched_filename:
                            filename = self.matched_filename
                            logger.debug(f"使用缓存的匹配文件名: {filename}")
                            
                        # 查找并下载文件
                        if msg_id:
                            # 添加前缀
                            if actual_prefix:
                                prefix_msg = f"{actual_prefix}"
                                try:
                                    logger.debug(f"向 {target} 发送前缀消息: {prefix_msg}")
                                    self.robot.wcf.send_text(prefix_msg, target_wxid)
                                except Exception as e:
                                    logger.warning(f"向 {target} 发送前缀消息失败: {e}")
                                
                            # 尝试查找文件路径
                            file_path = self.find_file_in_wechat_dir(filename)
                            if file_path and os.path.exists(file_path):
                                logger.debug(f"找到文件: {file_path}")
                                # 发送文件
                                try:
                                    # 发送文件
                                    result = self.robot.wcf.send_file(file_path, target_wxid)
                                    if result == 0:
                                        logger.info(f"成功向 {target} 转发文件: {filename}")
                                        success = True
                                    else:
                                        logger.error(f"向 {target} 转发文件 {filename} 失败，尝试标准转发")
                                        # 尝试使用标准转发
                                        forward_result = self.robot.wcf.forward_msg(msg_id, target_wxid)
                                        if forward_result == 1:
                                            logger.info(f"成功使用标准转发向 {target} 发送文件")
                                            success = True
                                except Exception as e:
                                    logger.error(f"向 {target} 发送文件失败: {e}")
                                    # 尝试使用标准转发
                                    try:
                                        forward_result = self.robot.wcf.forward_msg(msg_id, target_wxid)
                                        if forward_result == 1:
                                            logger.info(f"成功使用标准转发向 {target} 发送文件")
                                            success = True
                                    except Exception as e2:
                                        logger.error(f"标准转发也失败: {e2}")
                            else:
                                logger.warning(f"找不到微信文件: {filename}")
                                # 尝试通过转发消息的方式发送
                                try:
                                    logger.debug(f"尝试使用转发消息方式发送文件")
                                    forward_result = self.robot.wcf.forward_msg(msg_id, target_wxid)
                                    if forward_result == 1:
                                        logger.info(f"成功使用转发方式向 {target} 发送文件: {filename}")
                                        success = True
                                    else:
                                        logger.error(f"使用转发方式向 {target} 发送文件 {filename} 失败")
                                except Exception as e:
                                    logger.error(f"尝试转发消息失败: {e}")
                        else:
                            logger.warning("无法获取消息ID，无法查找文件")
                            
                    except Exception as e:
                        logger.error(f"处理文件消息出错: {e}")
                else:
                    logger.warning(f"不支持的消息类型: {message_type}")
            except Exception as e:
                logger.error(f"处理文件转发失败: {e}")
                
        # 返回结果
        logger.info(f"任务 {task_name} 处理完成，转发{'成功' if success else '失败'}")
        return success 