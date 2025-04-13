import requests, json
import logging

class Weather:
    def __init__(self, city_code: str) -> None:
        self.city_code = city_code
        self.LOG = logging.getLogger("Weather")

    def get_weather(self) -> str:
        """获取天气信息"""
        try:
            # 获取天气信息
            url = f"http://t.weather.sojson.com/api/weather/city/{self.city_code}"
            self.LOG.info(f"获取天气: {url}")
            response = requests.get(url)
            self.LOG.info(f"获取天气成功: {str(response.text)}")
            d = response.json()
            
            # 当返回状态码为200，输出天气状况
            if(d['status'] == 200):
                return f"""城市：{d['cityInfo']['parent']}/{d['cityInfo']['city']}
时间：{d['time']} {d['data']['forecast'][0]['week']}
温度：{d['data']['forecast'][0]['high']} {d['data']['forecast'][0]['low']}
天气：{d['data']['forecast'][0]['type']}
湿度：{d['data']['shidu']}
空气质量：{d['data']['quality']} (PM2.5: {d['data']['pm25']}, PM10: {d['data']['pm10']})
风向：{d['data']['forecast'][0]['fx']} {d['data']['forecast'][0]['fl']}
日出：{d['data']['forecast'][0]['sunrise']} 日落：{d['data']['forecast'][0]['sunset']}
感冒提醒：{d['data']['ganmao']}"""
            else:
                return "获取天气失败"
        except Exception as e:
            self.LOG.error(f"获取天气失败: {str(e)}")
            return "获取天气失败"

if __name__ == "__main__":
    w = Weather("101010100")  # 北京
    print(w.get_weather())  # 北京
