# 高德地图 IP 定位 API

> 来源：https://lbs.amap.com/api/webservice/guide/api/ipconfig
> 最后更新：2026-02-02

## 产品介绍

IP 定位是一套简单的 HTTP 接口，根据用户输入的 IP 地址，快速定位 IP 的所在位置。

**限制**：仅支持 IPv4，不支持国外 IP 解析。

## API 服务地址

| 项目 | 内容 |
|------|------|
| **URL** | `https://restapi.amap.com/v3/ip?parameters` |
| **请求方式** | GET |
| **编码** | UTF-8 |

## 请求参数

| 参数名 | 含义 | 规则说明 | 是否必须 | 缺省值 |
|--------|------|----------|----------|--------|
| `key` | 请求服务权限标识 | 在高德开放平台申请 Web 服务 API 类型 KEY | **必填** | 无 |
| `ip` | IP 地址 | 需要搜索的 IP 地址（仅支持国内），若不填则取客户 HTTP 请求方 IP | 可选 | 无 |
| `sig` | 签名 | 数字签名，选择数字签名认证的付费用户必填 | 可选 | 无 |

## 返回结果参数

| 名称 | 含义 | 规则说明 |
|------|------|----------|
| `status` | 返回结果状态值 | 0 表示失败；1 表示成功 |
| `info` | 返回状态说明 | status=0 时返回错误原因，否则返回 "OK" |
| `infocode` | 状态码 | 10000 代表正确，详情参阅 info 状态表 |
| `province` | 省份名称 | 直辖市显示直辖市名称；局域网返回"局域网"；非法 IP 及国外 IP 返回空 |
| `city` | 城市名称 | 直辖市显示直辖市名称；局域网/非法/国外 IP 返回空 |
| `adcode` | 城市的 adcode 编码 | 可参考城市编码表获取 |
| `rectangle` | 所在城市矩形区域范围 | 所在城市范围的左下右上对标对 |

## 服务示例

```
https://restapi.amap.com/v3/ip?ip=114.247.50.2&output=xml&key=<用户的key>
```

### 请求示例

```bash
curl "https://restapi.amap.com/v3/ip?key=YOUR_KEY&ip=114.247.50.2"
```

### 返回示例 (JSON)

```json
{
  "status": "1",
  "info": "OK",
  "infocode": "10000",
  "province": "北京市",
  "city": "北京市",
  "adcode": "110000",
  "rectangle": "116.0119343,39.66127144;116.7829835,40.2164962"
}
```

## 项目配置

在 WeatherAgent 项目中，API Key 通过 `.env` 文件配置：

```env
AMAP_API_KEY=你的高德Key
AMAP_BASE_URL=https://restapi.amap.com
```

## 适用场景

希望能够将 IP 信息转换为地理位置信息的场景。
