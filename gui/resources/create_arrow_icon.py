import base64
import os

# 简单的下拉箭头图标，Base64编码
arrow_icon_base64 = b"""
iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMCAYAAABWdVznAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAOxAAADsQBlSsOGwAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAABDSURBVCiRY2CgEPz////o////v1EsidWU/4Q0kG0LI5IpjHhdwkA5YATZxIjNBVRzA12aGHEFLdnhjM3JZCUDijQAAKMsGI9vOMPKAAAAAElFTkSuQmCC
"""

# 确保目录存在
os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)

# 将Base64解码并写入文件
with open('gui/resources/down_arrow.png', 'wb') as f:
    f.write(base64.b64decode(arrow_icon_base64))

print("下拉箭头图标已创建") 