# WeChatRobot3 函数索引文档

本文档列出了项目中的主要类和函数，供开发参考。

## 目录
- [WxMsg 类](#wxmsg-类)
- [Robot 类](#robot-类)
- [MessageTransfer 类](#messagetransfer-类)
- [AI对话类](#ai对话类)
- [Wcf 类](#wcf-类)

## WxMsg 类
微信消息的基础类，用于处理接收到的消息。

### 属性
- `type` (int): 消息类型
- `id` (str): 消息id
- `xml` (str): 消息xml部分
- `sender` (str): 消息发送人
- `roomid` (str): 群id(仅群消息有)
- `content` (str): 消息内容
- `thumb` (str): 视频或图片消息的缩略图路径
- `extra` (str): 视频或图片消息的路径

### 方法
```python
def from_self() -> bool
```
判断是否自己发送的消息

```python
def from_group() -> bool
```
判断是否群聊消息

```python
def is_at(wxid) -> bool
```
判断是否被@：群消息，在@名单里，并且不是@所有人

## Robot 类
机器人的主类，处理消息和实现各种功能。

### 主要方法
```python
def processMsg(msg: WxMsg) -> None
```
处理接收到的消息的主函数

```python
def sendTextMsg(msg: str, receiver: str, at_list: str = "") -> None
```
发送文本消息
- `msg`: 消息内容
- `receiver`: 接收人wxid或群id
- `at_list`: 要@的wxid，@所有人为"notify@all"

```python
def getAllGroups() -> dict
```
获取所有群组信息，返回格式: {"wxid": "NickName"}

```python
def toChitchat(msg: WxMsg) -> bool
```
处理AI闲聊功能

```python
def toAt(msg: WxMsg) -> bool
```
处理被@消息

```python
def autoAcceptFriendRequest(msg: WxMsg) -> None
```
自动接受好友请求

```python
def sayHiToNewFriend(msg: WxMsg) -> None
```
向新好友打招呼

```python
def update_group_members(group_id=None) -> bool
```
更新群成员信息
- `group_id`: 指定群ID，如果为None则更新所有群
- 返回: 是否更新成功

## MessageTransfer 类
消息转发处理类。

### 主要方法
```python
def forward_message(message: dict, target: str) -> bool
```
转发消息到指定目标
- `message`: 消息内容
- `target`: 目标接收者

```python
def process_task(message: Dict, task_config: Dict)
```
处理转发任务
- `message`: 消息内容
- `task_config`: 任务配置

```python
def find_file_in_wechat_dir(filename: str, max_retries: int = 3, retry_interval: float = 1.0) -> Optional[str]
```
在微信文件目录中查找指定文件，支持重试机制
- `filename`: 文件名
- `max_retries`: 最大重试次数，默认3次
- `retry_interval`: 重试间隔时间(秒)，默认1秒
- 返回: 找到的文件完整路径，未找到返回None

```python
def wait_for_file(filename: str, timeout: float = 5.0) -> bool
```
等待文件出现在微信目录中
- `filename`: 文件名
- `timeout`: 最大等待时间(秒)，默认5秒
- 返回: 文件是否出现

```python
def get_current_month_dir() -> str
```
获取当前月份目录名
- 返回: 格式为"YYYY-MM"的目录名

### 属性
- `wechat_files_dir`: 微信文件保存目录
- `file_size_threshold`: 文件大小阈值，超过此值使用下载-重发模式（默认3MB）

## AI对话类

### ChatGPT
```python
def get_answer(question: str, wxid: str) -> str
```
获取ChatGPT回答
- `question`: 问题内容
- `wxid`: 用户id或群id

### ZhiPu (智谱AI)
```python
def get_answer(msg: str, wxid: str, **args) -> str
```
获取智谱AI回答
- `msg`: 问题内容
- `wxid`: 用户id或群id

### ChatGLM
```python
def get_answer(question: str, wxid: str) -> str
```
获取ChatGLM回答
- `question`: 问题内容
- `wxid`: 用户id或群id

## Wcf 类
微信操作的核心类，提供与微信交互的基本功能。

### 初始化
```python
def __init__(host=None, debug=False, block=True)
```
初始化Wcf实例
- `host`: 主机地址，默认None
- `debug`: 是否开启调试模式
- `block`: 是否阻塞等待

### 消息相关方法
```python
def enable_recv_msg(callback)
```
启用消息接收，设置回调函数

```python
def enable_receiving_msg()
```
启用消息接收模式

```python
def disable_recv_msg()
```
禁用消息接收

```python
def get_msg()
```
获取消息

```python
def send_text(msg: str, receiver: str, at_list: str = "")
```
发送文本消息
- `msg`: 消息内容
- `receiver`: 接收者wxid
- `at_list`: @的用户列表

```python
def send_image(path: str, receiver: str)
```
发送图片
- `path`: 图片路径
- `receiver`: 接收者wxid

```python
def forward_msg(msg_id: str, receiver: str)
```
转发消息
- `msg_id`: 消息ID
- `receiver`: 接收者wxid

### 群组相关方法
```python
def get_chatroom_members(room_id: str)
```
获取群成员列表

```python
def get_chatroom_name(room_id: str)
```
获取群名称

```python
def get_chatroom_list()
```
获取群聊列表

```python
def get_alias_in_chatroom(wxid: str, room_id: str)
```
获取群成员昵称

### 好友相关方法
```python
def get_friends()
```
获取好友列表

```python
def accept_new_friend(v3: str, v4: str, scene: int)
```
接受好友请求

### 系统相关方法
```python
def is_login() -> bool
```
检查是否已登录

```python
def get_self_wxid() -> str
```
获取自己的wxid

```python
def cleanup()
```
清理资源

```python
def query_sql(db: str, sql: str)
```
执行SQL查询
- `db`: 数据库名
- `sql`: SQL语句

## 注意事项
1. 获取群组信息时应使用`robot.allGroups`字典
2. 获取联系人信息时应使用`robot.contacts`
3. 群聊消息处理时，应使用wxid进行匹配而不是群名称
4. 发送消息时有频率限制，需要注意控制发送速度
5. 文件相关操作建议使用`MessageTransfer`类提供的方法
6. 使用Wcf类的方法时需要确保微信已登录
7. 处理文件转发时，建议使用wait_for_file方法等待文件就绪 