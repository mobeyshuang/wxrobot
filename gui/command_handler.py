import re
from typing import Dict, List, Optional, Tuple
from .ai_settings import AISettings
import time

class CommandHandler:
    def __init__(self, robot, ai_settings: AISettings = None):
        self.robot = robot
        self.ai_settings = ai_settings or AISettings()
        
        # 确保robot有wxid属性
        if not hasattr(self.robot, 'wxid'):
            try:
                self.robot.wxid = self.robot.wcf.get_self_wxid()
                print(f"已设置robot.wxid = {self.robot.wxid}")
            except Exception as e:
                print(f"获取机器人wxid失败: {e}")
        
        # 用户状态存储
        self.user_states = {}  # 用于存储用户的交互状态
        
        # 命令处理映射
        self.command_map = {
            "^设置": self._handle_settings_command,
            "1": self._handle_enable_ai,
            "2": self._handle_disable_ai,
            "3": self._handle_add_user,
            "4": self._handle_remove_user,
            "5": self._handle_list_users,
            "6": self._handle_add_group,
            "7": self._handle_remove_group,
            "8": self._handle_list_groups,
            "9": self._handle_view_role,
            "10": self._handle_modify_role
        }
    
    def handle_message(self, msg) -> bool:
        """处理消息，如果是命令则处理并返回True，否则返回False"""
        try:
            print(f"CommandHandler收到消息: {type(msg)}")
            
            # 判断消息类型，接收到的消息可能是WxMsg对象，也可能是字典
            if hasattr(msg, 'sender'):  # 是WxMsg对象
                sender = msg.sender
                content = msg.content
                room_wxid = msg.roomid
                
                print(f"WxMsg消息: sender={sender}, content={content}, room_wxid={room_wxid}")
                
                # 将消息转换为字典格式，方便统一处理
                message = {
                    "sender": sender,
                    "content": content,
                    "room_wxid": room_wxid,
                    "id": getattr(msg, 'id', None),
                    "type": getattr(msg, 'type', 0),
                    "is_at": lambda wxid: msg.is_at(wxid) if hasattr(msg, 'is_at') else False
                }
            else:  # 是字典
                message = msg
                sender = message.get("sender", "")
                content = message.get("content", "")
                room_wxid = message.get("room_wxid", "")
                
                print(f"字典消息: sender={sender}, content={content}, room_wxid={room_wxid}")
            
            # 优先判断是否是"^设置"命令，立即处理
            if content.strip() == "^设置":
                print(f"检测到^设置命令，直接处理")
                self._handle_settings_command(sender, content, room_wxid)
                return True
            
            # 只处理私聊消息或群聊中的@我的消息
            is_private = not room_wxid
            is_at_me = False
            
            if room_wxid:
                print(f"检查是否@我: self.robot.wxid={self.robot.wxid}")
                if hasattr(msg, 'is_at'):
                    is_at_me = msg.is_at(self.robot.wxid)
                    print(f"使用WxMsg.is_at()方法检查: {is_at_me}")
                elif "is_at" in message and callable(message["is_at"]):
                    is_at_me = message["is_at"](self.robot.wxid)
                    print(f"使用message['is_at']函数检查: {is_at_me}")
                else:
                    bot_wxid = self.robot.wcf.get_self_wxid()
                    is_at_me = f"@{bot_wxid}" in content
                    print(f"使用文本匹配检查@{bot_wxid}: {is_at_me}")
            
            print(f"is_private={is_private}, is_at_me={is_at_me}")
            
            if not (is_private or is_at_me):
                # 检查自动回复功能
                if room_wxid and self.ai_settings.is_group_allowed(room_wxid):
                    return self._check_auto_reply(message)
                print("不是私聊也没有@我，不处理命令")
                return False
            
            # 清除@信息获取纯内容
            if is_at_me:
                content = re.sub(r'@[\w\-_]+\s+', '', content).strip()
                print(f"清除@后的内容: {content}")
            
            # 检查用户当前状态
            user_state = self.user_states.get(sender, {})
            waiting_for = user_state.get("waiting_for")
            
            if waiting_for:
                # 用户正在某个交互流程中
                print(f"用户在交互流程中: {waiting_for}")
                self._handle_state_response(sender, content, waiting_for, user_state)
                return True
            
            # 检查普通命令
            for cmd, handler in self.command_map.items():
                if content.startswith(cmd):
                    print(f"匹配到命令: {cmd}")
                    handler(sender, content, room_wxid)
                    return True
            
            print(f"没有匹配到任何命令")
            
            # 检查AI聊天功能
            if self.ai_settings.is_ai_enabled() and self.ai_settings.is_user_allowed(sender):
                # 调用AI处理聊天
                return self._handle_ai_chat(sender, content, room_wxid)
                
            return False
            
        except Exception as e:
            print(f"处理命令失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _handle_settings_command(self, sender: str, content: str, room_wxid: str):
        """处理设置命令，提供设置菜单"""
        if not self._is_sender_valid(sender):
            self.robot.wcf.send_text("您没有权限使用设置功能", sender)
            return
            
        # 当前AI功能状态
        ai_status = "✅ 开启" if self.ai_settings.is_ai_enabled() else "❌ 关闭"
        user_count = len(self.ai_settings.get_users())
        group_count = len(self.ai_settings.get_groups())
        
        menu = f"""【微信机器人设置】
当前AI状态: {ai_status}
授权用户数: {user_count}
授权群组数: {group_count}

请回复数字选择功能:
1. 启用用户AI权限
2. 禁用用户AI权限
3. 添加用户
4. 删除用户
5. 查看用户列表
6. 添加群组
7. 删除群组
8. 查看群组列表
9. 查看用户角色
10. 设置用户角色
11. 设置自动回复关键词
"""
        
        # 尝试各种方式发送菜单
        try:
            # 尝试通过文本发送
            if self.robot.wcf.send_text(menu, sender):
                self.user_states[sender] = {"waiting_for": "settings_option"}
                return
        except Exception as e:
            print(f"发送设置菜单失败: {e}")
        
        try:
            # 尝试通过图片发送
            if self.robot.wcf.send_image(self._generate_menu_image(menu), sender):
                self.user_states[sender] = {"waiting_for": "settings_option"}
                return
        except Exception as e:
            print(f"发送设置菜单图片失败: {e}")
            
        # 尝试分段发送
        try:
            parts = menu.split("\n\n")
            for part in parts:
                self.robot.wcf.send_text(part, sender)
                time.sleep(0.5)
            self.user_states[sender] = {"waiting_for": "settings_option"}
        except Exception as e:
            print(f"分段发送设置菜单失败: {e}")
            self.robot.wcf.send_text("发送设置菜单失败，请稍后再试", sender)
    
    def _handle_enable_ai(self, sender: str, content: str, room_wxid: str):
        """处理启用AI功能的命令"""
        # 当用户选择"1"选项时，提供用户列表以启用AI功能
        users = self.ai_settings.get_users()
        if not users:
            self.robot.wcf.send_text("当前没有允许使用AI的用户，请先添加用户", sender)
            return
            
        self.robot.wcf.send_text("请选择要启用AI功能的用户（回复序号）：", sender)
        
        user_list = ""
        for i, user in enumerate(users):
            enabled = "✅" if self.ai_settings.is_user_allowed(user["wxid"]) else "❌"
            user_list += f"{i+1}. {user['name']} ({user['wxid']}) {enabled}\n"
        
        self.robot.wcf.send_text(user_list, sender)
        self.user_states[sender] = {"waiting_for": "select_user_for_ai", "users": users, "action": "enable"}
    
    def _handle_disable_ai(self, sender: str, content: str, room_wxid: str):
        """处理禁用AI功能的命令"""
        # 当用户选择"2"选项时，提供用户列表以禁用AI功能
        users = self.ai_settings.get_users()
        if not users:
            self.robot.wcf.send_text("当前没有允许使用AI的用户", sender)
            return
            
        self.robot.wcf.send_text("请选择要禁用AI功能的用户（回复序号）：", sender)
        
        user_list = ""
        for i, user in enumerate(users):
            enabled = "✅" if self.ai_settings.is_user_allowed(user["wxid"]) else "❌"
            user_list += f"{i+1}. {user['name']} ({user['wxid']}) {enabled}\n"
        
        self.robot.wcf.send_text(user_list, sender)
        self.user_states[sender] = {"waiting_for": "select_user_for_ai", "users": users, "action": "disable"}
    
    def _handle_add_user(self, sender: str, content: str, room_wxid: str):
        """处理添加用户命令"""
        self.robot.wcf.send_text("请输入要添加的用户微信昵称或ID", sender)
        self.user_states[sender] = {"waiting_for": "add_user_input"}
        
    def _handle_remove_user(self, sender: str, content: str, room_wxid: str):
        """处理删除用户命令"""
        users = self.ai_settings.get_users()
        if not users:
            self.robot.wcf.send_text("当前没有允许使用AI的用户", sender)
            return
        
        self.robot.wcf.send_text("请输入要删除的用户微信昵称或直接回复序号：", sender)
        
        user_list = ""
        for i, user in enumerate(users):
            user_list += f"{i+1}. {user['name']} ({user['wxid']})\n"
        
        self.robot.wcf.send_text(user_list, sender)
        self.user_states[sender] = {"waiting_for": "remove_user_input", "users": users}
    
    def _handle_list_users(self, sender: str, content: str, room_wxid: str):
        """处理查看用户命令"""
        users = self.ai_settings.get_users()
        if not users:
            self.robot.wcf.send_text("当前没有允许使用AI的用户", sender)
            return
        
        user_list = "允许使用AI的用户列表：\n"
        for i, user in enumerate(users):
            user_list += f"{i+1}. {user['name']} ({user['wxid']})\n"
        
        self.robot.wcf.send_text(user_list, sender)
    
    def _handle_add_group(self, sender: str, content: str, room_wxid: str):
        """处理添加群组命令"""
        groups = self.robot.wcf.get_chatrooms()
        if not groups:
            self.robot.wcf.send_text("获取群聊列表失败", sender)
            return
        
        group_list = "请选择要添加的群组（回复序号）：\n"
        for i, group in enumerate(groups):
            group_list += f"{i+1}. {group['name']}\n"
            if i >= 19:  # 限制显示20个群组
                group_list += "...\n"
                break
        
        self.robot.wcf.send_text(group_list, sender)
        self.user_states[sender] = {"waiting_for": "add_group", "groups": groups[:20]}
    
    def _handle_remove_group(self, sender: str, content: str, room_wxid: str):
        """处理删除群组命令"""
        groups = self.ai_settings.get_groups()
        if not groups:
            self.robot.wcf.send_text("当前没有允许自动回复的群组", sender)
            return
        
        group_list = "请选择要删除的群组（回复序号）：\n"
        for i, group in enumerate(groups):
            group_list += f"{i+1}. {group['name']} ({group['wxid']})\n"
        
        self.robot.wcf.send_text(group_list, sender)
        self.user_states[sender] = {"waiting_for": "remove_group", "groups": groups}
    
    def _handle_list_groups(self, sender: str, content: str, room_wxid: str):
        """处理查看群组命令"""
        groups = self.ai_settings.get_groups()
        if not groups:
            self.robot.wcf.send_text("当前没有允许自动回复的群组", sender)
            return
        
        group_list = "允许自动回复的群组列表：\n"
        for i, group in enumerate(groups):
            group_list += f"{i+1}. {group['name']} ({group['wxid']})\n"
        
        self.robot.wcf.send_text(group_list, sender)
    
    def _handle_view_role(self, sender: str, content: str, room_wxid: str):
        """处理查看角色命令"""
        users = self.ai_settings.get_users()
        if not users:
            self.robot.wcf.send_text("当前没有允许使用AI的用户", sender)
            return
        
        user_list = "请选择要查看角色的用户（回复序号）：\n"
        for i, user in enumerate(users):
            user_list += f"{i+1}. {user['name']} ({user['wxid']})\n"
        
        self.robot.wcf.send_text(user_list, sender)
        self.user_states[sender] = {"waiting_for": "view_role", "users": users}
    
    def _handle_modify_role(self, sender: str, content: str, room_wxid: str):
        """处理修改角色命令"""
        users = self.ai_settings.get_users()
        if not users:
            self.robot.wcf.send_text("当前没有允许使用AI的用户", sender)
            return
        
        user_list = "请选择要修改角色的用户（回复序号）：\n"
        for i, user in enumerate(users):
            user_list += f"{i+1}. {user['name']} ({user['wxid']})\n"
        
        self.robot.wcf.send_text(user_list, sender)
        self.user_states[sender] = {"waiting_for": "select_user_for_role", "users": users}
    
    def _handle_state_response(self, sender: str, content: str, waiting_for: str, state: Dict):
        """处理用户在交互状态中的响应"""
        if waiting_for == "settings_option":
            # 处理设置菜单选项
            try:
                option = content.strip()
                handler = self.command_map.get(option)
                if handler:
                    handler(sender, content, "")
                else:
                    self.robot.wcf.send_text("无效的选项，请重新选择", sender)
            except Exception as e:
                self.robot.wcf.send_text(f"处理选项出错: {e}", sender)
                del self.user_states[sender]
                
        elif waiting_for == "add_user_input":
            # 处理添加用户的输入
            user_name = content.strip()
            
            # 检查是否是名片信息
            if content.startswith("BEGIN:VCARD"):
                wxid, name = self._parse_vcard(content)
                if wxid:
                    result = self.ai_settings.add_user(wxid, name)
                    response = f"已添加用户 {name}({wxid}) ✅" if result else "添加用户失败❌"
                    self.robot.wcf.send_text(response, sender)
                    del self.user_states[sender]
                    return
            
            # 尝试通过昵称查找微信ID
            friends = self.robot.wcf.get_friends()
            matching_friends = []
            
            # 精确匹配
            exact_match = None
            for friend in friends:
                if friend.get("name") == user_name:
                    exact_match = friend
                    break
                elif friend.get("wxid") == user_name:
                    exact_match = friend
                    break
                # 如果名字或ID包含用户输入的内容，加入匹配列表
                elif user_name in friend.get("name", "") or user_name in friend.get("wxid", ""):
                    matching_friends.append(friend)
            
            if exact_match:
                # 找到精确匹配，直接添加
                wxid = exact_match.get("wxid")
                name = exact_match.get("name", wxid)
                result = self.ai_settings.add_user(wxid, name)
                response = f"已添加用户 {name}({wxid}) ✅" if result else "添加用户失败❌"
                self.robot.wcf.send_text(response, sender)
                del self.user_states[sender]
            elif matching_friends:
                # 找到部分匹配，提供选择
                if len(matching_friends) == 1:
                    # 只有一个匹配项，直接确认
                    friend = matching_friends[0]
                    self.robot.wcf.send_text(
                        f"找到一个匹配的用户: {friend.get('name')}({friend.get('wxid')})\n请确认是否添加（回复 Y/N）",
                        sender
                    )
                    self.user_states[sender] = {
                        "waiting_for": "confirm_add_user",
                        "user": friend
                    }
                else:
                    # 多个匹配项，提供选择列表
                    response = "找到多个匹配的用户，请选择（回复序号）：\n"
                    for i, friend in enumerate(matching_friends[:10]):  # 限制最多显示10个
                        response += f"{i+1}. {friend.get('name')}({friend.get('wxid')})\n"
                    
                    self.robot.wcf.send_text(response, sender)
                    self.user_states[sender] = {
                        "waiting_for": "select_user_to_add",
                        "users": matching_friends[:10]
                    }
            else:
                # 没有找到匹配，提示用户直接输入微信ID
                self.robot.wcf.send_text(
                    f"未找到匹配的好友\"{user_name}\"，请直接输入微信ID",
                    sender
                )
                self.user_states[sender] = {"waiting_for": "add_user_wxid"}
                
        elif waiting_for == "remove_user_input":
            users = state.get("users", [])
            input_value = content.strip()
            
            # 检查是否是序号
            if input_value.isdigit():
                try:
                    idx = int(input_value) - 1
                    if 0 <= idx < len(users):
                        user = users[idx]
                        result = self.ai_settings.remove_user(user["wxid"])
                        response = f"已删除用户 {user['name']} ✅" if result else "删除用户失败❌"
                    else:
                        response = "选择无效，请输入正确的序号"
                except ValueError:
                    response = "请输入有效的序号"
            else:
                # 按昵称或ID查询
                matching_users = []
                for user in users:
                    if user["name"] == input_value or user["wxid"] == input_value:
                        # 精确匹配
                        result = self.ai_settings.remove_user(user["wxid"])
                        response = f"已删除用户 {user['name']} ✅" if result else "删除用户失败❌"
                        self.robot.wcf.send_text(response, sender)
                        del self.user_states[sender]
                        return
                    elif input_value in user["name"] or input_value in user["wxid"]:
                        matching_users.append(user)
                
                if matching_users:
                    if len(matching_users) == 1:
                        # 只有一个匹配项
                        user = matching_users[0]
                        result = self.ai_settings.remove_user(user["wxid"])
                        response = f"已删除用户 {user['name']} ✅" if result else "删除用户失败❌"
                    else:
                        # 多个匹配项，提供选择
                        response = "找到多个匹配的用户，请选择要删除的（回复序号）：\n"
                        for i, user in enumerate(matching_users):
                            response += f"{i+1}. {user['name']} ({user['wxid']})\n"
                        
                        self.robot.wcf.send_text(response, sender)
                        self.user_states[sender] = {
                            "waiting_for": "select_user_to_remove",
                            "users": matching_users
                        }
                        return
                else:
                    response = f"未找到匹配的用户 \"{input_value}\""
            
            self.robot.wcf.send_text(response, sender)
            del self.user_states[sender]
        
        elif waiting_for == "select_user_to_remove":
            try:
                users = state.get("users", [])
                idx = int(content.strip()) - 1
                if 0 <= idx < len(users):
                    user = users[idx]
                    result = self.ai_settings.remove_user(user["wxid"])
                    response = f"已删除用户 {user['name']} ✅" if result else "删除用户失败❌"
                else:
                    response = "选择无效，请输入正确的序号"
            except ValueError:
                response = "请输入有效的序号"
            
            self.robot.wcf.send_text(response, sender)
            del self.user_states[sender]
        
        elif waiting_for == "add_user_wxid":
            # 直接添加用户ID
            wxid = content.strip()
            name = self._get_friend_name(wxid) or wxid
            result = self.ai_settings.add_user(wxid, name)
            response = f"已添加用户 {name}({wxid}) ✅" if result else "添加用户失败❌"
            self.robot.wcf.send_text(response, sender)
            del self.user_states[sender]
            
        elif waiting_for == "confirm_add_user":
            # 确认添加用户
            if content.strip().upper() in ["Y", "YES", "是", "确认"]:
                user = state.get("user", {})
                wxid = user.get("wxid", "")
                name = user.get("name", wxid)
                result = self.ai_settings.add_user(wxid, name)
                response = f"已添加用户 {name}({wxid}) ✅" if result else "添加用户失败❌"
            else:
                response = "已取消添加用户"
            
            self.robot.wcf.send_text(response, sender)
            del self.user_states[sender]
            
        elif waiting_for == "select_user_to_add":
            # 选择要添加的用户
            try:
                users = state.get("users", [])
                idx = int(content.strip()) - 1
                if 0 <= idx < len(users):
                    user = users[idx]
                    wxid = user.get("wxid", "")
                    name = user.get("name", wxid)
                    result = self.ai_settings.add_user(wxid, name)
                    response = f"已添加用户 {name}({wxid}) ✅" if result else "添加用户失败❌"
                else:
                    response = "选择无效，请输入正确的序号"
            except ValueError:
                response = "请输入有效的序号"
            
            self.robot.wcf.send_text(response, sender)
            del self.user_states[sender]
        
        elif waiting_for == "select_user_for_ai":
            # 处理选择用户以启用/禁用AI
            try:
                users = state.get("users", [])
                action = state.get("action", "enable")
                idx = int(content.strip()) - 1
                
                if 0 <= idx < len(users):
                    user = users[idx]
                    wxid = user["wxid"]
                    name = user["name"]
                    
                    if action == "enable":
                        # 启用AI
                        if self.ai_settings.is_user_allowed(wxid):
                            response = f"{name} 已经启用了AI功能"
                        else:
                            self.ai_settings.add_user(wxid, name)
                            self.ai_settings.save_settings()
                            response = f"已为 {name} 启用AI功能 ✅"
                    else:
                        # 禁用AI
                        if not self.ai_settings.is_user_allowed(wxid):
                            response = f"{name} 已经禁用了AI功能"
                        else:
                            self.ai_settings.remove_user(wxid)
                            self.ai_settings.save_settings()
                            response = f"已为 {name} 禁用AI功能 ✅"
                else:
                    response = "选择无效，请输入正确的序号"
            except ValueError:
                response = "请输入有效的序号"
            except Exception as e:
                logger.error(f"处理AI功能切换出错: {e}")
                response = f"处理出错: {str(e)[:100]}"
                
            self.robot.wcf.send_text(response, sender)
            del self.user_states[sender]
    
    def _parse_vcard(self, vcard_content: str) -> Tuple[Optional[str], Optional[str]]:
        """解析名片内容，提取微信ID和名称"""
        wxid_match = re.search(r'WXID:([\w\-_]+)', vcard_content)
        name_match = re.search(r'FN:([\w\-_\u4e00-\u9fa5]+)', vcard_content)
        
        wxid = wxid_match.group(1) if wxid_match else None
        name = name_match.group(1) if name_match else (wxid or "未知用户")
        
        return wxid, name
    
    def _get_friend_name(self, wxid: str) -> Optional[str]:
        """尝试获取好友的名称"""
        try:
            friends = self.robot.wcf.get_friends()
            for friend in friends:
                if friend["wxid"] == wxid:
                    return friend["name"]
            return None
        except:
            return None
    
    def _check_auto_reply(self, message: Dict) -> bool:
        """检查是否需要自动回复"""
        try:
            # 判断消息类型，同样支持WxMsg对象和字典
            if hasattr(message, 'roomid'):  # 是WxMsg对象
                room_wxid = message.roomid
                content = message.content
            else:  # 是字典
                room_wxid = message.get("room_wxid")
                content = message.get("content", "")
            
            # 检查是否是允许自动回复的群
            if not self.ai_settings.is_group_allowed(room_wxid):
                return False
            
            # 检查是否是@我的消息或@所有人
            is_at_me = False
            is_at_all = "@所有人" in content
            
            if hasattr(message, 'is_at'):
                is_at_me = message.is_at(self.robot.wxid)
            elif hasattr(message, "is_at"):  # 字典中的函数
                is_at_me = message["is_at"](self.robot.wxid)
            else:
                is_at_me = f"@{self.robot.wcf.get_self_wxid()}" in content
            
            if not (is_at_me or is_at_all):
                return False
            
            # 检查是否包含自动回复关键词
            keywords = self.ai_settings.get_auto_reply_keywords()
            has_keyword = any(keyword in content for keyword in keywords)
            
            if has_keyword:
                # 发送自动回复
                self.robot.wcf.send_text("收到", room_wxid)
                return True
                
            return False
        except Exception as e:
            print(f"检查自动回复失败: {e}")
            return False
    
    def _handle_ai_chat(self, sender: str, content: str, room_wxid: str):
        """处理AI聊天"""
        try:
            # 检查AI是否配置
            if not hasattr(self.robot, "chat") or not self.robot.chat:
                self.robot.wcf.send_text("AI功能未配置，请先在设置中配置Deepseek", sender)
                return False
                
            # 从内容中移除@标记
            if content.startswith("@"):
                parts = content.split(" ", 1)
                if len(parts) > 1:
                    content = parts[1].strip()
                    
            # 获取AI回答
            try:
                response = self.robot.chat.get_answer(content, sender)
                if response:
                    self.robot.wcf.send_text(response, sender)
                    return True
                else:
                    self.robot.wcf.send_text("AI无法生成回答，请稍后再试", sender)
            except Exception as e:
                logger.error(f"获取AI回答出错: {e}")
                self.robot.wcf.send_text(f"获取AI回答失败: {str(e)[:100]}", sender)
                
            return False
        except Exception as e:
            logger.error(f"处理AI聊天出错: {e}")
            return False
    
    def _is_sender_valid(self, sender: str) -> bool:
        """检查发送者是否有效且有权限使用设置功能"""
        if not sender:
            return False
            
        # 检查是否是管理员（如果有管理员列表）
        if hasattr(self.ai_settings, "admin_users") and self.ai_settings.admin_users:
            return sender in self.ai_settings.admin_users
            
        # 如果没有指定管理员，则默认所有允许使用AI的用户都可以使用设置功能
        return self.ai_settings.is_user_allowed(sender)
        
    def _generate_menu_image(self, text: str) -> str:
        """将文本生成为图片并返回图片路径，用于发送菜单
        
        Args:
            text: 要转换为图片的文本
            
        Returns:
            图片文件路径
        """
        try:
            import os
            from PIL import Image, ImageDraw, ImageFont
            import tempfile
            
            # 计算图片尺寸
            font_size = 20
            try:
                font = ImageFont.truetype("simhei.ttf", font_size)
            except:
                font = ImageFont.load_default()
                
            lines = text.split('\n')
            line_height = font_size * 1.5
            width = 400
            height = int(len(lines) * line_height) + 40
            
            # 创建图片
            img = Image.new('RGB', (width, height), color=(255, 255, 255))
            d = ImageDraw.Draw(img)
            
            # 绘制文本
            y = 20
            for line in lines:
                d.text((20, y), line, font=font, fill=(0, 0, 0))
                y += line_height
                
            # 保存图片
            temp_dir = tempfile.gettempdir()
            path = os.path.join(temp_dir, f"menu_{int(time.time())}.png")
            img.save(path)
            return path
        except Exception as e:
            logger.error(f"生成菜单图片出错: {e}")
            return "" 