# 高德地图 天气查询 API

> 来源：https://lbs.amap.com/api/webservice/guide/api/weatherinfo
> 项目 WeatherTool 对应的外部 API

## 产品介绍

天气查询是一套简单的 HTTP 接口，根据行政区划代码（adcode）查询指定地区的实时天气和未来预报。

## API 服务地址

| 项目 | 内容 |
|------|------|
| **URL** | `https://restapi.amap.com/v3/weather/weatherInfo?parameters` |
| **请求方式** | GET |
| **编码** | UTF-8 |

## 请求参数

| 参数名 | 含义 | 规则说明 | 是否必须 | 缺省值 |
|--------|------|----------|----------|--------|
| `key` | 请求服务权限标识 | 高德开放平台 Web 服务 API KEY | **必填** | 无 |
| `city` | 城市编码 | 行政区划代码 adcode（6位数字），如：420981 | **必填** | 无 |
| `extensions` | 气象类型 | `base`：实况天气；`all`：预报天气（未来4天） | 可选 | base |
| `output` | 返回格式 | JSON / XML | 可选 | JSON |

## 返回结果参数

### base 模式（实况天气）

| 字段 | 说明 |
|------|------|
| `status` | 0=失败；1=成功 |
| `count` | 返回结果数目 |
| `info` | 状态说明 |
| `infocode` | 状态码，10000=正确 |
| `lives[]` | 实况天气数组 |
| `lives[].province` | 省份 |
| `lives[].city` | 城市名 |
| `lives[].adcode` | 行政区划代码 |
| `lives[].weather` | 天气现象（如：晴、多云、中雨） |
| `lives[].temperature` | 实时温度（°C） |
| `lives[].winddirection` | 风向 |
| `lives[].windpower` | 风力级别 |
| `lives[].humidity` | 湿度（%） |
| `lives[].reporttime` | 数据发布时间 |

### all 模式（预报天气，未来4天）

| 字段 | 说明 |
|------|------|
| `forecasts[]` | 预报天气数组 |
| `forecasts[].city` | 城市名 |
| `forecasts[].adcode` | 行政区划代码 |
| `forecasts[].province` | 省份 |
| `forecasts[].reporttime` | 发布时间 |
| `forecasts[].casts[]` | 未来4天预报 |
| `casts[].date` | 日期 (YYYY-MM-DD) |
| `casts[].week` | 星期几 |
| `casts[].dayweather` | 白天天气 |
| `casts[].nightweather` | 夜间天气 |
| `casts[].daytemp` | 白天温度 |
| `casts[].nighttemp` | 夜间温度 |
| `casts[].daywind` | 白天风向 |
| `casts[].nightwind` | 夜间风向 |
| `casts[].daypower` | 白天风力 |
| `casts[].nightpower` | 夜间风力 |

## 服务示例

### 实况天气

```bash
curl "https://restapi.amap.com/v3/weather/weatherInfo?key=YOUR_KEY&city=110000&extensions=base"
```

### 预报天气

```bash
curl "https://restapi.amap.com/v3/weather/weatherInfo?key=YOUR_KEY&city=110000&extensions=all"
```

### 实况返回示例 (JSON)

```json
{
  "status": "1",
  "count": "1",
  "info": "OK",
  "infocode": "10000",
  "lives": [
    {
      "province": "北京",
      "city": "北京市",
      "adcode": "110000",
      "weather": "晴",
      "temperature": "25",
      "winddirection": "北",
      "windpower": "≤3",
      "humidity": "40",
      "reporttime": "2026-07-08 14:00:00"
    }
  ]
}
```

### 预报返回示例 (JSON)

```json
{
  "status": "1",
  "count": "1",
  "info": "OK",
  "infocode": "10000",
  "forecasts": [
    {
      "city": "北京市",
      "adcode": "110000",
      "province": "北京",
      "reporttime": "2026-07-08 11:00:00",
      "casts": [
        {
          "date": "2026-07-08",
          "week": "1",
          "dayweather": "晴",
          "nightweather": "多云",
          "daytemp": "33",
          "nighttemp": "22",
          "daywind": "南",
          "nightwind": "南",
          "daypower": "1-3",
          "nightpower": "1-3"
        }
      ]
    }
  ]
}
```

## 项目中的使用

### WeatherTool (`backend/app/tools/weather.py`)

```python
# 配置（.env）
AMAP_API_KEY=9f015d2f0477dc68ce244d833ccab9c6
AMAP_BASE_URL=https://restapi.amap.com

# WeatherTool 调用
tool = WeatherTool()
result = await tool.run(adcode="420981", date="2026-07-08", days=3)
```

### 重要说明

1. **city 参数必须是 adcode**（6位数字），不能直接传城市中文名
2. **项目使用 extensions=all**（预报模式），可获取未来 4 天数据
3. WeatherTool 内置自动回退：如果 adcode 不合法，自动调用 CityResolver 将城市名转换为 adcode
4. 高德 Weather API 不支持指定历史日期查询，仅返回实况和未来预报
