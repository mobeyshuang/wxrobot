from typing import Dict, Optional
from datetime import datetime, timedelta
import schedule
import time
import threading
from wcferry import Wcf
import os
import re

class MessageScheduler:
    def __init__(self, task_executor):
        self.task_executor = task_executor
        self.wcf = task_executor.wcf
        self.robot = task_executor.robot
        self.scheduled_tasks = {}
        self.running = True
        
    def setup_task(self, task_config: Dict) -> bool:
        """设置定时任务"""
        try:
            task_name = task_config["name"]
            print(f"\n开始设置定时任务: {task_name}")
            print(f"任务配置: {task_config}")
            
            # 如果任务已存在，先清理旧任务
            if task_name in self.scheduled_tasks:
                print(f"发现同名任务，先清理旧任务: {task_name}")
                schedule.clear(task_name)  # 清除调度
                del self.scheduled_tasks[task_name]  # 删除任务记录
                print(f"已清理旧任务: {task_name}")
                
            # 获取任务配置
            send_time = task_config.get("time", "")
            repeat_type = task_config.get("repeat_type", "一次")
            target_type = task_config.get("target_type", "群聊").strip()  # 去除可能的空格
            target = task_config.get("target", "").strip()  # 去除可能的空格
            message = task_config.get("message", "")
            attachment = task_config.get("attachment", "")
            
            print(f"解析的任务参数:")
            print(f"- 发送时间: {send_time}")
            print(f"- 重复类型: {repeat_type}")
            print(f"- 目标类型: {target_type}")
            print(f"- 目标: {target}")
            print(f"- 消息: {message}")
            print(f"- 附件: {attachment}")
            
            # 检查状态并更新 last_state
            status = task_config.get("status", "stopped")
            is_running = status == "running"
            task_config["last_state"] = is_running
            print(f"任务状态: {status} (is_running: {is_running})")
            
            if not send_time or not target:
                print(f"定时任务配置不完整: {task_name}")
                print(f"- 发送时间: {send_time}")
                print(f"- 目标: {target}")
                return False
                
            # 获取目标wxid
            target_wxid = None
            
            # 根据目标类型获取wxid
            if target_type == "群聊":
                print(f"正在查找群聊: {target}")
                # 优先从robot.allGroups中获取群聊wxid
                if hasattr(self.robot, 'allGroups') and isinstance(self.robot.allGroups, dict):
                    for gid, gname in self.robot.allGroups.items():
                        if gname == target:
                            target_wxid = gid
                            print(f"从robot.allGroups中找到群聊wxid: {target_wxid}")
                            break
                
                # 如果从allGroups中没找到，再尝试其他方法
                if not target_wxid:
                    print(f"在robot.allGroups中未找到群聊: {target}，尝试其他方法")
                    # 使用get_wxid_by_name函数获取群聊wxid
                    from robot import get_wxid_by_name
                    target_wxid = get_wxid_by_name(self.robot, target, "group")
                    
                if not target_wxid:
                    print(f"未找到群聊: {target}")
                    print(f"当前群组列表: {self.robot.allGroups}")
                    return False
                    
                print(f"找到群聊wxid: {target_wxid}")
            elif target_type == "好友":  # 确保类型完全匹配
                print(f"正在查找好友: {target}")
                
                # 优先在robot.contacts中查找
                if hasattr(self.robot, 'contacts') and self.robot.contacts:
                    for contact in self.robot.contacts:
                        if isinstance(contact, dict):
                            # 检查各种可能的名称字段
                            if (contact.get("name") == target or 
                                contact.get("remark") == target or 
                                contact.get("nickname") == target):
                                target_wxid = contact.get("wxid")
                                print(f"从robot.contacts中找到好友wxid: {target_wxid}")
                                break
                            
                            # 如果包含表情符号，可能需要更复杂的匹配
                            contact_name = contact.get("name", "")
                            contact_remark = contact.get("remark", "")
                            
                            if target and (target in contact_name or target in contact_remark):
                                target_wxid = contact.get("wxid")
                                print(f"从robot.contacts中通过部分匹配找到好友wxid: {target_wxid}")
                                break
                
                # 如果还没找到，再尝试使用find_user_by_name
                if not target_wxid:
                    print(f"在robot.contacts直接匹配中未找到好友，尝试使用find_user_by_name")
                    target_wxid = self.find_user_by_name(target)
                
                if not target_wxid:
                    print(f"警告: 未能找到好友 {target} 的wxid，任务设置失败")
                    return False
                    
                print(f"找到好友wxid: {target_wxid}")
            else:
                print(f"不支持的目标类型: {target_type}")
                return False
            
            if not target_wxid:
                print(f"未找到定时消息目标: {target}")
                return False
                
            def send_message():
                try:
                    print(f"开始执行定时任务: {task_name}")
                    print(f"发送目标: {target} (wxid: {target_wxid})")
                    
                    success = False
                    
                    # 获取任务配置中的特殊消息类型标志
                    send_weather = task_config.get("send_weather", False)
                    send_news = task_config.get("send_news", False)
                    print(f"特殊消息类型: 天气={send_weather}, 新闻={send_news}")
                    
                    # 获取任务配置中的城市代码
                    city_code = task_config.get("city_code", "")
                    
                    # 处理天气消息
                    if send_weather:
                        print(f"准备发送天气消息")
                        try:
                            # 判断目标类型，如果是群聊，使用群ID，否则使用好友名称
                            if target_type == "群聊":
                                # 如果配置了城市代码，则使用自定义城市代码
                                if city_code:
                                    print(f"使用自定义城市代码: {city_code}")
                                    # 使用自定义城市代码发送天气
                                    from base.func_weather import Weather
                                    weather_text = Weather(city_code).get_weather()
                                    
                                    # 使用DeepSeek生成祝福语
                                    if weather_text and hasattr(self.robot, 'chat') and self.robot.chat:
                                        try:
                                            from base.func_deepseek import Deepseek
                                            if isinstance(self.robot.chat, Deepseek):
                                                prompt = f"""请根据以上天气信息输出一句与天气有关的祝福语,并加一个emoji。"

天气信息：
{weather_text}"""
                                                # 使用自定义系统提示词
                                                system_prompt = "你是对话助手，正常回答对话，不需要进行多余的解释。"
                                                blessing = self.robot.chat.chat(prompt, system_prompt=system_prompt)
                                                if blessing:
                                                    weather_text += f"\n\n{blessing}"
                                                    print("已添加DeepSeek生成的祝福语")
                                        except Exception as blessing_err:
                                            print(f"生成祝福语时出错: {blessing_err}")
                                    
                                    if weather_text:
                                        self.wcf.send_text(weather_text, target_wxid)
                                        print(f"使用城市代码 {city_code} 发送天气消息成功")
                                        success = True
                                    else:
                                        print(f"获取城市 {city_code} 的天气信息失败")
                                else:
                                    # 使用默认城市代码
                                    self.robot.weatherReport([target_wxid])
                                    print(f"使用默认城市代码发送天气消息成功")
                                    success = True
                            else:
                                # 如果配置了城市代码，则使用自定义城市代码
                                if city_code:
                                    print(f"使用自定义城市代码: {city_code}")
                                    # 使用自定义城市代码发送天气
                                    from base.func_weather import Weather
                                    weather_text = Weather(city_code).get_weather()
                                    
                                    # 使用DeepSeek生成祝福语
                                    if weather_text and hasattr(self.robot, 'chat') and self.robot.chat:
                                        try:
                                            from base.func_deepseek import Deepseek
                                            if isinstance(self.robot.chat, Deepseek):
                                                prompt = f"""请根据以上天气信息输出一句与天气有关的祝福语,并加一个emoji。"

天气信息：
{weather_text}"""
                                                # 使用自定义系统提示词
                                                system_prompt = "你是对话助手，正常回答对话，不需要进行多余的解释。"
                                                blessing = self.robot.chat.chat(prompt, system_prompt=system_prompt)
                                                if blessing:
                                                    weather_text += f"\n\n{blessing}"
                                                    print("已添加DeepSeek生成的祝福语")
                                        except Exception as blessing_err:
                                            print(f"生成祝福语时出错: {blessing_err}")
                                    
                                    if weather_text:
                                        self.wcf.send_text(weather_text, target_wxid)
                                        print(f"使用城市代码 {city_code} 发送天气消息成功")
                                        success = True
                                    else:
                                        print(f"获取城市 {city_code} 的天气信息失败")
                                else:
                                    # 使用默认城市代码
                                    self.robot.weatherReport([target])
                                    print(f"使用默认城市代码发送天气消息成功")
                                    success = True
                            print(f"天气消息处理完成")
                        except Exception as weather_err:
                            print(f"发送天气消息时发生异常: {str(weather_err)}")
                            import traceback
                            traceback.print_exc()
                    
                    # 处理新闻消息
                    if send_news:
                        print(f"准备发送新闻消息")
                        try:
                            # 根据目标类型构建接收者列表
                            if target_type == "群聊":
                                # 从群聊名称获取wxid
                                group_wxid = None
                                for wxid, name in self.robot.allGroups.items():
                                    if name == target:
                                        group_wxid = wxid
                                        break
                                if group_wxid:
                                    self.robot.newsReport([group_wxid])
                                    print(f"新闻消息发送到群聊 {target} 成功")
                                    success = True
                                else:
                                    print(f"未找到群聊 {target} 的wxid")
                            else:
                                # 直接使用好友wxid发送
                                self.robot.newsReport([target_wxid])
                                print(f"新闻消息发送到好友 {target} 成功")
                                success = True
                        except Exception as news_err:
                            print(f"发送新闻消息时发生异常: {str(news_err)}")
                            import traceback
                            traceback.print_exc()
                    
                    # 处理附件
                    if attachment:
                        print(f"准备发送附件: {attachment}")
                        try:
                            # 检查文件是否存在
                            if not os.path.exists(attachment):
                                print(f"文件不存在: {attachment}")
                            else:
                                # 获取文件大小
                                file_size = os.path.getsize(attachment)
                                if file_size > 10 * 1024 * 1024:  # 10MB
                                    print(f"文件过大: {file_size} bytes")
                                else:
                                    # 规范化路径
                                    normalized_path = os.path.normpath(attachment)
                                    print(f"发送文件: {normalized_path}")
                                    try:
                                        result = self.wcf.send_file(normalized_path, target_wxid)
                                        if result == 0:  # 微信接口成功返回0
                                            print(f"文件发送成功")
                                            success = True
                                        else:
                                            print(f"文件发送失败，返回值: {result}")
                                    except Exception as file_err:
                                        print(f"发送文件时发生异常: {str(file_err)}")
                                        import traceback
                                        traceback.print_exc()
                        except Exception as e:
                            print(f"处理附件时发生异常: {str(e)}")
                            import traceback
                            traceback.print_exc()
                    
                    # 然后发送文本消息
                    if message:
                        print(f"发送文本消息: {message}")
                        try:
                            result = self.wcf.send_text(message, target_wxid)
                            if result == 0:  # 微信接口成功返回0
                                print(f"文本消息发送成功")
                                success = True
                            else:
                                print(f"文本消息发送失败，返回值: {result}")
                        except Exception as txt_err:
                            print(f"发送文本消息时发生异常: {str(txt_err)}")
                            import traceback
                            traceback.print_exc()
                    
                    # 如果至少有一项发送成功，则更新任务状态
                    if success:
                        print(f"任务 {task_name} 至少一项内容发送成功，更新统计")
                        # 更新任务状态
                        if task_name in self.scheduled_tasks:
                            self.scheduled_tasks[task_name]["last_run"] = datetime.now()
                            self.scheduled_tasks[task_name]["success_count"] += 1
                            
                            # 更新配置中的状态记录
                            config = self.scheduled_tasks[task_name]["config"]
                            config["last_state"] = config.get("status", "stopped") == "running"
                        
                            # 更新任务执行器中的统计信息
                            if hasattr(self.robot, 'task_executor'):
                                stats = self.robot.task_executor.get_task_stats(task_name)
                                if stats:
                                    stats["succeeded"] += 1
                                    stats["processed"] += 1
                                    self.robot.task_executor.stats_updated.emit(task_name, stats)
                                    print(f"已更新任务统计: 成功次数+1")
                    else:
                        print(f"任务 {task_name} 所有内容发送失败")
                        # 记录失败
                        if task_name in self.scheduled_tasks:
                            self.scheduled_tasks[task_name]["error_count"] += 1
                            # 更新任务执行器中的统计信息
                            if hasattr(self.robot, 'task_executor'):
                                stats = self.robot.task_executor.get_task_stats(task_name)
                                if stats:
                                    stats["failed"] += 1
                                    stats["processed"] += 1
                                    self.robot.task_executor.stats_updated.emit(task_name, stats)
                                    print(f"已更新任务统计: 失败次数+1")
                    
                    # 如果是一次性任务，执行后立即取消调度
                    if repeat_type == "一次":
                        print(f"一次性任务 {task_name} 已执行，取消调度")
                        schedule.clear(task_name)
                        # 更新任务状态为已停止
                        if task_name in self.scheduled_tasks:
                            self.scheduled_tasks[task_name]["config"]["status"] = "stopped"
                            self.scheduled_tasks[task_name]["config"]["last_state"] = False
                            # 通知任务执行器更新状态
                            if hasattr(self.robot, 'task_executor'):
                                self.robot.task_executor.status_changed.emit(task_name, False)
                    elif repeat_type == "每小时":
                        print(f"每小时任务 {task_name} 执行完成，下次执行将在 {interval_hours} 小时后")
                        # 更新下次执行时间
                        if task_name in self.scheduled_tasks:
                            next_run = datetime.now() + timedelta(hours=interval_hours)
                            self.scheduled_tasks[task_name]["next_run"] = next_run
                            print(f"下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                    # 返回 CancelJob 确保任务只执行一次
                    return schedule.CancelJob
                
                except Exception as e:
                    print(f"发送定时消息失败: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    if task_name in self.scheduled_tasks:
                        self.scheduled_tasks[task_name]["error_count"] += 1
                        
                        # 更新任务执行器中的统计信息
                        if hasattr(self.robot, 'task_executor'):
                            stats = self.robot.task_executor.get_task_stats(task_name)
                            if stats:
                                stats["failed"] += 1
                                stats["processed"] += 1
                                self.robot.task_executor.stats_updated.emit(task_name, stats)
                
            # 设置定时任务
            time_parts = send_time.split(":")
            if len(time_parts) != 2:
                print(f"时间格式不正确: {send_time}")
                return False
                
            hour, minute = time_parts
            hour = hour.zfill(2)
            minute = minute.zfill(2)
            
            # 记录任务信息
            self.scheduled_tasks[task_name] = {
                "config": task_config,
                "last_run": None,
                "success_count": 0,
                "error_count": 0,
                "next_run": None
            }
            
            # 根据重复类型设置任务
            if repeat_type == "每天":
                schedule.every().day.at(f"{hour}:{minute}").do(send_message).tag(task_name)
                print(f"设置每天{hour}:{minute}执行的定时任务: {task_name}")
            elif repeat_type == "每小时":
                # 获取间隔小时数，默认为1小时
                try:
                    interval_hours = int(task_config.get("interval_hours", 1))
                    print(f"每小时任务间隔设置为: {interval_hours}小时")
                    
                    # 确保interval_hours至少为1，否则使用默认值1
                    if interval_hours < 1:
                        print(f"间隔小时数 {interval_hours} 无效，使用默认值1")
                        interval_hours = 1
                except Exception as e:
                    print(f"解析interval_hours失败: {e}，使用默认值1")
                    interval_hours = 1
                
                # 处理首次执行的时间
                first_run_minute = int(minute)  # 默认从当前分钟开始
                first_run_hour = None  # 默认不指定小时
                
                # 检查是否指定了首次执行的小时
                start_time = task_config.get("start_time", "")
                print(f"设置首次执行时间: {start_time}")
                if start_time:
                    try:
                        # 解析首次执行时间
                        start_parts = start_time.split(":")
                        if len(start_parts) == 2:
                            first_run_hour = int(start_parts[0])
                            first_run_minute = int(start_parts[1])
                            print(f"解析到首次执行时间: {first_run_hour}:{first_run_minute}")
                            
                            # 验证时间值是否有效
                            if not (0 <= first_run_hour < 24 and 0 <= first_run_minute < 60):
                                print(f"首次执行时间 {first_run_hour}:{first_run_minute} 超出有效范围，使用当前时间")
                                first_run_hour = datetime.now().hour
                                first_run_minute = datetime.now().minute
                    except Exception as e:
                        print(f"解析首次执行时间失败: {e}，将使用当前时间")
                        first_run_hour = datetime.now().hour
                        first_run_minute = datetime.now().minute
                else:
                    print("未指定首次执行时间，将使用当前时间")
                    first_run_hour = datetime.now().hour
                    first_run_minute = datetime.now().minute
                
                # 如果指定了首次执行的小时，则需要等待到该时间点才开始第一次执行
                if first_run_hour is not None:
                    try:
                        # 计算首次执行的延迟时间
                        now = datetime.now()
                        print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # 创建首次执行的时间对象
                        first_run_time = now.replace(
                            hour=first_run_hour, 
                            minute=first_run_minute, 
                            second=0, 
                            microsecond=0
                        )
                        print(f"计算的首次执行时间: {first_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # 如果首次执行时间已过，则调整到下一个符合条件的时间点
                        if first_run_time < now:
                            print("首次执行时间已过，调整到下一个符合条件的时间点")
                            # 计算下一个执行时间
                            hours_to_add = interval_hours
                            # 如果间隔大于24小时，需要特殊处理
                            while first_run_time < now:
                                if interval_hours >= 24:
                                    days_to_add = interval_hours // 24
                                    hours_remainder = interval_hours % 24
                                    first_run_time = first_run_time + timedelta(days=days_to_add, hours=hours_remainder)
                                else:
                                    # 正常情况下，只需要添加interval_hours小时
                                    first_run_time = first_run_time + timedelta(hours=interval_hours)
                            
                            print(f"调整后的首次执行时间: {first_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            
                            # 更新下次执行时间
                            self.scheduled_tasks[task_name]["next_run"] = first_run_time
                        
                        # 计算延迟秒数
                        delay_seconds = max(0, (first_run_time - now).total_seconds())
                        print(f"首次执行延迟秒数: {delay_seconds}")
                        
                    except Exception as e:
                        print(f"设置首次执行时间出错: {e}")
                        import traceback
                        traceback.print_exc()
                        # 出错时使用默认设置
                        print("使用默认的每小时执行设置")
                        first_run_hour = None
                
                # 设置每x小时执行一次的任务
                try:
                    job = schedule.every(interval_hours).hours.do(send_message).tag(task_name)
                    print(f"已创建每{interval_hours}小时执行一次的任务")
                    
                    # 如果有首次执行时间，设置任务的下一次执行时间
                    if first_run_hour is not None and first_run_time > now:
                        try:
                            # 设置下一次执行时间
                            job.next_run = first_run_time
                            print(f"已设置下一次执行时间: {first_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            self.scheduled_tasks[task_name]["next_run"] = first_run_time
                        except Exception as e:
                            print(f"设置下一次执行时间出错: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    print(f"设置每{interval_hours}小时执行一次的定时任务: {task_name}")
                except Exception as e:
                    print(f"创建每小时任务失败: {e}")
                    return False
            elif repeat_type == "每周":
                week_days = task_config.get("week_days", [])
                print(f"设置每周{week_days}的{hour}:{minute}执行的定时任务: {task_name}")
                
                # 创建一个检查函数，只在指定的星期几执行任务
                def weekly_task():
                    # 获取当前是星期几（0是星期一，6是星期日）
                    current_weekday = datetime.now().weekday() + 1  # 转换为1-7的格式
                    
                    # 检查今天是否是指定的执行日期
                    if current_weekday in week_days:
                        print(f"今天是星期{current_weekday}，符合任务执行条件")
                        return send_message()
                    else:
                        print(f"今天是星期{current_weekday}，不在任务执行日期{week_days}中，跳过")
                        return None
                
                # 每天都检查，但只在指定的星期几执行
                schedule.every().day.at(f"{hour}:{minute}").do(weekly_task).tag(task_name)
            else:  # 一次性任务
                date_str = task_config.get("date", "")
                if not date_str:
                    # 如果没有指定日期，默认今天
                    target_date = datetime.now().date()
                else:
                    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                # 当前日期
                current_date = datetime.now().date()
                
                # 目标时间
                target_time = datetime.now().replace(
                    year=target_date.year,
                    month=target_date.month,
                    day=target_date.day,
                    hour=int(hour),
                    minute=int(minute),
                    second=0,
                    microsecond=0
                )
                
                # 检查是否已过时
                if target_time < datetime.now():
                    print(f"任务时间已过期: {target_time}, 当前时间: {datetime.now()}")
                    # 可以选择不添加任务，或者设置为明天同一时间
                    if current_date == target_date:  # 同一天，设置为明天
                        target_time = target_time.replace(day=target_time.day + 1)
                    else:
                        # 已过期且日期不同，不添加任务
                        del self.scheduled_tasks[task_name]
                        return False
                
                # 计算距离执行时间的秒数
                delay_seconds = (target_time - datetime.now()).total_seconds()
                if delay_seconds <= 0:
                    print(f"任务时间已过期，不添加: {target_time}")
                    del self.scheduled_tasks[task_name]
                    return False
                
                # 使用 at 方法精确设置一次性任务的执行时间
                target_time_str = target_time.strftime("%H:%M:%S")
                
                # 添加执行标志到任务配置中
                self.scheduled_tasks[task_name]["executed"] = False
                
                # 定义执行函数
                def run_once():
                    # 首先检查任务是否已经执行过
                    if task_name in self.scheduled_tasks and self.scheduled_tasks[task_name].get("executed", False):
                        print(f"任务 {task_name} 已经执行过，跳过")
                        return schedule.CancelJob
                    
                    print(f"执行一次性任务: {task_name}")
                    
                    # 先标记任务为已执行，避免重复执行
                    self.scheduled_tasks[task_name]["executed"] = True
                    
                    # 执行任务
                    send_message()
                    
                    # 更新任务状态
                    self.scheduled_tasks[task_name]["config"]["status"] = "stopped"
                    self.scheduled_tasks[task_name]["config"]["last_state"] = False
                    
                    # 通知任务执行器更新状态
                    if hasattr(self.robot, 'task_executor'):
                        self.robot.task_executor.status_changed.emit(task_name, False)
                    
                    print(f"一次性任务 {task_name} 执行完成，返回取消标记")
                    return schedule.CancelJob
                
                # 设置一次性任务 - 使用精确的日期和时间
                if target_date == current_date:
                    # 如果是今天，使用 at 精确设置时间
                    job = schedule.every().day.at(target_time_str).do(run_once)
                else:
                    # 如果是未来日期，计算延迟并设置
                    job = schedule.every(delay_seconds).seconds.do(run_once)
                
                # 设置任务标签
                job.tag(task_name)
                
                print(f"设置{target_time.strftime('%Y-%m-%d %H:%M:%S')}执行的一次性定时任务: {task_name}")
            
            return True
            
        except Exception as e:
            print(f"设置定时任务失败: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def remove_task(self, task_name: str) -> bool:
        """移除定时任务"""
        try:
            if task_name not in self.scheduled_tasks:
                return False
                
            schedule.clear(task_name)
            del self.scheduled_tasks[task_name]
            print(f"成功移除定时任务: {task_name}")
            return True
            
        except Exception as e:
            print(f"移除定时任务失败: {e}")
            return False
            
    def get_task_status(self, task_name: str) -> Optional[Dict]:
        """获取任务状态"""
        return self.scheduled_tasks.get(task_name)
        
    def get_all_tasks(self) -> Dict:
        """获取所有任务"""
        return self.scheduled_tasks
        
    def find_user_by_name(self, name: str) -> Optional[str]:
        """根据名称查找用户的wxid"""
        print(f"正在查找好友: {name}")
        
        # 首先在robot.contacts中查找
        if hasattr(self.robot, 'contacts') and self.robot.contacts:
            print(f"在缓存的联系人列表中查找: {len(self.robot.contacts)}个联系人")
            for contact in self.robot.contacts:
                if isinstance(contact, dict):
                    # 检查各种可能的名称字段 - 精确匹配
                    if (contact.get("name") == name or 
                        contact.get("remark") == name or 
                        contact.get("nickname") == name):
                        print(f"通过精确匹配找到联系人: {name} -> {contact.get('wxid')}")
                        return contact.get("wxid")
                    
                    # 如果包含特殊字符，尝试模糊匹配
                    if any(ord(c) > 127 for c in name):  # 包含非ASCII字符
                        contact_name = contact.get("name", "")
                        contact_remark = contact.get("remark", "")
                        contact_nickname = contact.get("nickname", "")
                        
                        # 移除表情符号后比较 - 精确匹配
                        clean_name = ''.join(c for c in name if ord(c) < 10000)
                        clean_contact_name = ''.join(c for c in contact_name if ord(c) < 10000)
                        clean_contact_remark = ''.join(c for c in contact_remark if ord(c) < 10000)
                        clean_contact_nickname = ''.join(c for c in contact_nickname if ord(c) < 10000)
                        
                        if (clean_name and (clean_name == clean_contact_name or 
                                          clean_name == clean_contact_remark or 
                                          clean_name == clean_contact_nickname)):
                            print(f"通过清理特殊字符后精确匹配找到联系人: {name} -> {contact.get('wxid')}")
                            return contact.get("wxid")
                        
                        # 尝试完全模糊匹配（完全忽略表情等符号）
                        # 仅比较字母和数字部分 - 精确匹配
                        alpha_name = re.sub(r'[^\w\s]', '', name).strip()
                        alpha_contact_name = re.sub(r'[^\w\s]', '', contact_name).strip()
                        alpha_contact_remark = re.sub(r'[^\w\s]', '', contact_remark).strip()
                        alpha_contact_nickname = re.sub(r'[^\w\s]', '', contact_nickname).strip()
                        
                        if alpha_name and (
                            (alpha_name == alpha_contact_name and alpha_contact_name) or
                            (alpha_name == alpha_contact_remark and alpha_contact_remark) or
                            (alpha_name == alpha_contact_nickname and alpha_contact_nickname)
                        ):
                            print(f"通过字母数字匹配找到联系人: {name} -> {contact.get('wxid')}")
                            return contact.get("wxid")
                        
                        # 仅检查名称是否在联系人名称中 - 单向包含匹配
                        if name and (name in contact_name or name in contact_remark or name in contact_nickname):
                            print(f"通过名称在联系人名称中匹配找到联系人: {name} -> {contact.get('wxid')}")
                            return contact.get("wxid")
        else:
            print("警告: robot.contacts不存在或为空")
        
        # 如果在缓存的联系人中没有找到，才通过API尝试获取
        print("在缓存中未找到联系人，尝试通过API获取")
        try:
            friends = self.wcf.get_friends()
            print(f"通过API获取到 {len(friends)} 个联系人")
            for friend in friends:
                # 检查各种可能的名称字段 - 精确匹配
                if (friend.get("name") == name or 
                    friend.get("remark") == name or 
                    friend.get("nickname") == name):
                    print(f"通过API精确匹配找到好友: {name} -> {friend.get('wxid')}")
                    return friend.get("wxid")
                
                # 简单的模糊匹配
                friend_name = friend.get("name", "")
                friend_remark = friend.get("remark", "")
                friend_nickname = friend.get("nickname", "")
                
                if name and (name in friend_name or name in friend_remark or name in friend_nickname):
                    print(f"通过API名称包含匹配找到好友: {name} -> {friend.get('wxid')}")
                    return friend.get("wxid")
        except Exception as e:
            print(f"通过API获取联系人出错: {e}")
                
        # 未找到
        print(f"未找到用户: {name}")
        print(f"可用联系人列表前10个:")
        for contact in self.robot.contacts[:10]:  # 只显示前10个以避免输出太多
            if isinstance(contact, dict):
                print(f"  - {contact.get('wxid')}: {contact.get('name')} / {contact.get('remark')} / {contact.get('nickname')}")
        return None
        
    def run(self):
        """运行定时任务检查"""
        print("启动定时任务检查线程")
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                print(f"运行定时任务失败: {e}")
                time.sleep(5)  # 出错后等待更长时间
                
    def stop(self):
        """停止所有任务"""
        print("正在快速停止消息调度器...")
        self.running = False
        
        try:
            # 只取消所有任务的调度，但不删除任务记录
            schedule.clear()
            print("已清除所有任务调度")
        except Exception as e:
            print(f"清除任务调度时出错: {e}")
        
        # 不再尝试逐个删除任务，避免卡住
        # for task_name in list(self.scheduled_tasks.keys()):
        #     self.remove_task(task_name) 

    def run_pending_jobs(self):
        """执行所有待处理的任务"""
        try:
            # 获取当前时间
            now = datetime.now()
            
            # 遍历所有任务
            for task in self.scheduled_tasks.values():
                try:
                    # 检查任务是否启用
                    if not task.get("enabled", True):
                        continue
                        
                    # 获取任务配置
                    config = task.get("config", {})
                    if not config:
                        continue
                        
                    # 获取任务名称
                    task_name = config.get("name", "未命名任务")
                    
                    # 获取任务状态
                    task_status = config.get("status", "stopped")
                    if task_status != "running":
                        continue
                        
                    # 获取任务类型
                    task_type = config.get("type")
                    if not task_type:
                        continue
                        
                    # 获取任务时间配置
                    time_str = config.get("time", "00:00")
                    try:
                        task_time = datetime.strptime(time_str, "%H:%M").time()
                    except ValueError:
                        print(f"任务 {task_name} 的时间格式错误: {time_str}")
                        continue
                        
                    # 获取重复类型
                    repeat_type = config.get("repeat_type", "一次")
                    
                    # 检查是否应该执行任务
                    should_run = False
                    
                    if repeat_type == "一次":
                        # 一次性任务
                        date_str = config.get("date", "")
                        if date_str:
                            try:
                                task_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                                if now.date() == task_date and now.time() >= task_time:
                                    should_run = True
                            except ValueError:
                                print(f"任务 {task_name} 的日期格式错误: {date_str}")
                    elif repeat_type == "每天":
                        # 每天执行
                        if now.time() >= task_time:
                            should_run = True
                    elif repeat_type == "每周":
                        # 每周执行
                        week_days = config.get("week_days", [])
                        if now.weekday() + 1 in week_days and now.time() >= task_time:
                            should_run = True
                    elif repeat_type == "每小时":
                        # 每小时执行
                        interval_hours = config.get("interval_hours", 1)
                        if interval_hours <= 0:
                            interval_hours = 1
                            
                        # 获取上次执行时间
                        last_run = task.get("last_run")
                        if not last_run:
                            # 首次执行，使用配置的起始时间
                            start_time = config.get("start_time", time_str)
                            try:
                                last_run = datetime.strptime(start_time, "%H:%M").time()
                                last_run = datetime.combine(now.date(), last_run)
                            except ValueError:
                                print(f"任务 {task_name} 的起始时间格式错误: {start_time}")
                                continue
                        else:
                            try:
                                last_run = datetime.strptime(last_run, "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                print(f"任务 {task_name} 的上次执行时间格式错误: {last_run}")
                                continue
                                
                        # 计算下次执行时间
                        next_run = last_run + timedelta(hours=interval_hours)
                        
                        # 如果当前时间已经超过下次执行时间，则执行任务
                        if now >= next_run:
                            should_run = True
                    
                    if should_run:
                        # 执行任务
                        if task_type == "schedule":
                            self._execute_schedule_task(task)
                        elif task_type == "news":
                            self._execute_news_task(task)
                        elif task_type == "weather":
                            self._execute_weather_task(task)
                            
                        # 更新上次执行时间
                        task["last_run"] = now.strftime("%Y-%m-%d %H:%M:%S")
                        
                        # 获取任务统计信息
                        stats = task.get("stats", {})
                        processed = stats.get("processed", 0)
                        succeeded = stats.get("succeeded", 0)
                        failed = stats.get("failed", 0)
                        
                        # 获取上次的统计信息
                        last_stats = task.get("last_stats", {})
                        last_processed = last_stats.get("processed", 0)
                        last_succeeded = last_stats.get("succeeded", 0)
                        last_failed = last_stats.get("failed", 0)
                        
                        # 只在统计信息发生变化时输出
                        if (processed != last_processed or 
                            succeeded != last_succeeded or 
                            failed != last_failed):
                            print(f"任务 {task_name} 统计信息: {{'processed': {processed}, 'succeeded': {succeeded}, 'failed': {failed}}}")
                            # 更新上次的统计信息
                            task["last_stats"] = {
                                "processed": processed,
                                "succeeded": succeeded,
                                "failed": failed
                            }
                            
                except Exception as e:
                    print(f"执行任务时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    
        except Exception as e:
            print(f"运行待处理任务时出错: {str(e)}")
            import traceback
            traceback.print_exc() 