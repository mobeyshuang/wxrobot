import os
import wcferry
import ctypes
import sys
import win32api
import win32process
import win32con

def check_sdk():
    try:
        # 获取 wcferry 库的路径
        wcferry_path = os.path.dirname(wcferry.__file__)
        sdk_path = os.path.join(wcferry_path, "sdk.dll")
        
        print(f"wcferry 版本: {wcferry.__version__}")
        print(f"wcferry 路径: {wcferry_path}")
        print(f"sdk.dll 路径: {sdk_path}")
        print(f"sdk.dll 是否存在: {os.path.exists(sdk_path)}")
        
        # 检查是否以管理员权限运行
        try:
            is_admin = os.getuid() == 0
        except AttributeError:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        print(f"是否以管理员权限运行: {is_admin}")
        
        # 检查微信进程
        def is_wechat_running():
            try:
                import psutil
                for proc in psutil.process_iter(['name']):
                    if 'WeChat.exe' in proc.info['name']:
                        return True
                return False
            except:
                return False
        
        print(f"微信是否运行: {is_wechat_running()}")
        
        if os.path.exists(sdk_path):
            # 获取文件大小
            file_size = os.path.getsize(sdk_path)
            print(f"sdk.dll 文件大小: {file_size} 字节")
            
            # 尝试加载 DLL
            try:
                sdk = ctypes.cdll.LoadLibrary(sdk_path)
                print("sdk.dll 加载成功")
                
                # 尝试调用初始化函数
                print("正在尝试初始化 SDK...")
                result = sdk.WxInitSDK(True, 10086)
                print(f"WxInitSDK 返回值: {result}")
                
                if result == -1:
                    print("\n初始化失败的可能原因：")
                    print("1. 微信未登录")
                    print("2. 微信版本与 wcferry 不兼容")
                    print("3. 需要管理员权限")
                    print("4. 微信进程异常")
                    
                    print("\n建议操作：")
                    print("1. 确保微信已登录")
                    print("2. 检查微信版本是否与 wcferry 兼容")
                    print("3. 尝试以管理员权限运行程序")
                    print("4. 重启微信")
                
            except Exception as e:
                print(f"sdk.dll 加载失败: {str(e)}")
        else:
            print("sdk.dll 文件不存在！")
            
    except Exception as e:
        print(f"检查过程中出错: {str(e)}")

if __name__ == "__main__":
    check_sdk() 