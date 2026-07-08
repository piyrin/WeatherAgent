# 高德地图 地理/逆地理编码 API

> 来源：https://lbs.amap.com/api/webservice/guide/api/georegeo
> 最后更新：2026-02-02

## 产品介绍

地理编码/逆地理编码 API 是通过 HTTP/HTTPS 协议访问远程服务的接口，提供结构化地址与经纬度之间的相互转化能力。

**结构化地址定义**：地址是一串字符，内含国家、省份、城市、区县、城镇、乡村、街道、门牌号码、屋邨、大厦等建筑物名称。按照由大区域名称到小区域名称组合在一起。注意：针对大陆、港、澳地区的地理编码转换时可以将国家信息选择性的忽略，但省、市、城镇等级别的地址构成是不能忽略的。暂时不支持返回台湾省的详细地址信息。

## 适用场景

- **地理编码**（地址 → 经纬度）：将详细的结构化地址转换为高德经纬度坐标。支持对地标性名胜景区、建筑物名称解析为高德经纬度坐标。
  - 结构化地址举例：北京市朝阳区阜通东大街6号 → `116.480881,39.989410`
  - 地标性建筑举例：天安门 → `116.397499,39.908722`

- **逆地理编码**（经纬度 → 地址）：将经纬度转换为详细结构化的地址，且返回附近周边的 POI、AOI 信息。
  - 例如：`116.480881,39.989410` → 北京市朝阳区阜通东大街6号

---

## 一、地理编码（地址 → 经纬度）

### API 服务地址

| 项目 | 内容 |
|------|------|
| **URL** | `https://restapi.amap.com/v3/geocode/geo?parameters` |
| **请求方式** | GET |
| **编码** | UTF-8 |

### 请求参数

| 参数名 | 含义 | 规则说明 | 是否必须 | 缺省值 |
|--------|------|----------|----------|--------|
| `key` | 请求服务权限标识 | 在高德开放平台申请 Web 服务 API 类型 KEY | **必填** | 无 |
| `address` | 结构化地址信息 | **规则遵循层级**：国家 → 省份 → 城市 → 区县 → 城镇 → 乡村 → 街道 → 门牌号码 → 屋邨 → 大厦。大陆/港/澳可省略国家，但省、市、区县级不能省略。如：北京市朝阳区阜通东大街6号。也支持地标名称（如天安门） | **必填** | 无 |
| `city` | 指定查询的城市 | 可选值：城市中文、中文全拼、citycode、adcode。如：北京/beijing/010/110000 | 可选 | 无 |
| `output` | 返回数据格式类型 | 可选值：JSON、XML | 可选 | JSON |
| `sig` | 签名 | 数字签名，付费用户必填 | 可选 | 无 |

### 返回结果参数

| 名称 | 含义 | 规则说明 |
|------|------|----------|
| `status` | 返回结果状态值 | 0 表示失败；1 表示成功 |
| `info` | 返回状态说明 | status=0 时返回错误原因 |
| `infocode` | 状态码 | 10000 代表正确 |
| `count` | 返回结果数目 | 解析出的经纬度数量 |
| `geocodes` | 地理编码信息列表 | 数组 |
| `geocodes[].formatted_address` | 结构化地址信息 | — |
| `geocodes[].country` | 国家 | — |
| `geocodes[].province` | 省份 | — |
| `geocodes[].city` | 城市 | — |
| `geocodes[].citycode` | 城市编码 | — |
| `geocodes[].district` | 区县 | — |
| `geocodes[].township` | 乡镇 | — |
| `geocodes[].street` | 街道 | — |
| `geocodes[].number` | 门牌号 | — |
| `geocodes[].adcode` | 行政区划代码 | — |
| `geocodes[].location` | 坐标点 | 经度,纬度 |
| `geocodes[].level` | 匹配级别 | 见匹配级别列表 |

### 服务示例

```
https://restapi.amap.com/v3/geocode/geo?address=北京市朝阳区阜通东大街6号&city=北京&key=<用户的key>
```

### 请求示例

```bash
curl "https://restapi.amap.com/v3/geocode/geo?key=YOUR_KEY&address=北京市朝阳区阜通东大街6号&city=北京"
```

### 返回示例 (JSON)

```json
{
  "status": "1",
  "info": "OK",
  "infocode": "10000",
  "count": "1",
  "geocodes": [
    {
      "formatted_address": "北京市朝阳区阜通东大街6号",
      "country": "中国",
      "province": "北京市",
      "citycode": "010",
      "city": "北京市",
      "district": "朝阳区",
      "township": [],
      "neighborhood": { "name": [], "type": [] },
      "building": { "name": [], "type": [] },
      "adcode": "110105",
      "street": "阜通东大街",
      "number": "6号",
      "location": "116.480881,39.989410",
      "level": "门牌号"
    }
  ]
}
```

---

## 二、逆地理编码（经纬度 → 地址）

### API 服务地址

| 项目 | 内容 |
|------|------|
| **URL** | `https://restapi.amap.com/v3/geocode/regeo?parameters` |
| **请求方式** | GET |
| **编码** | UTF-8 |

### 请求参数

| 参数名 | 含义 | 规则说明 | 是否必须 | 缺省值 |
|--------|------|----------|----------|--------|
| `key` | 请求服务权限标识 | 在高德开放平台申请 Web 服务 API 类型 KEY | **必填** | 无 |
| `location` | 经纬度坐标 | 经度在前，纬度在后，逗号分隔。最多支持 20 对坐标（批量查询） | **必填** | 无 |
| `extensions` | 返回结果控制 | `base`（默认，基本地址信息）；`all`（返回地址信息+附近 POI/AOI/道路信息） | 可选 | base |
| `poitype` | 返回附近 POI 类型 | extensions=all 时生效。指定 POI 类型，如：商务写字楼、餐饮服务 | 可选 | 无 |
| `radius` | 搜索半径 | extensions=all 时生效。周边 POI 搜索半径，范围 0-3000，单位：米 | 可选 | 1000 |
| `roadlevel` | 道路等级 | extensions=all 时生效。`0`：显示所有道路；`1`：过滤非主干道路，仅输出主干道路 | 可选 | 0 |
| `output` | 返回数据格式类型 | 可选值：JSON、XML | 可选 | JSON |
| `sig` | 签名 | 数字签名，付费用户必填 | 可选 | 无 |
| `batch` | 批量查询 | `true` 表示批量查询模式（location 可传多对坐标），`false` 为单点查询 | 可选 | false |
| `homeorcorp` | 是否优化 POI 返回顺序 | `0`：不对召回的 POI 策略排序；`1`：综合居家、公司、交通场景优化 POI 召回（半径限制可能变化） | 可选 | 1 |

### 返回结果参数

| 名称 | 含义 | 规则说明 |
|------|------|----------|
| `status` | 返回结果状态值 | 0=失败；1=成功 |
| `info` | 返回状态说明 | — |
| `infocode` | 状态码 | 10000 代表正确 |
| `regeocode` | 逆地理编码列表 | — |
| `regeocode.formatted_address` | 结构化地址信息 | 结构化地址信息，包括省+市+区+街道+门牌号 |
| `regeocode.addressComponent` | 地址元素列表 | 结构化地址拆解后的元素 |
| `regeocode.addressComponent.country` | 国家 | — |
| `regeocode.addressComponent.province` | 省份 | — |
| `regeocode.addressComponent.city` | 城市 | 当为直辖市时此字段为空 |
| `regeocode.addressComponent.citycode` | 城市编码 | — |
| `regeocode.addressComponent.district` | 区县 | — |
| `regeocode.addressComponent.adcode` | 行政区划代码 | — |
| `regeocode.addressComponent.township` | 乡镇 | — |
| `regeocode.addressComponent.towncode` | 乡镇编码 | — |
| `regeocode.addressComponent.streetNumber` | 街道+门牌号信息 | — |
| `regeocode.aois[]` | AOI 信息 (extensions=all) | 兴趣面信息 |
| `regeocode.roads[]` | 道路信息 (extensions=all) | 附近道路信息 |
| `regeocode.roadinters[]` | 道路交叉口 (extensions=all) | 附近交叉路口信息 |
| `regeocode.pois[]` | POI 信息 (extensions=all) | 周边兴趣点列表 |

### 服务示例

```
https://restapi.amap.com/v3/geocode/regeo?location=116.480881,39.989410&key=<用户的key>&extensions=all
```

### 请求示例

```bash
curl "https://restapi.amap.com/v3/geocode/regeo?key=YOUR_KEY&location=116.480881,39.989410&extensions=all&radius=1000"
```

### 返回示例 (JSON)

```json
{
  "status": "1",
  "info": "OK",
  "infocode": "10000",
  "regeocode": {
    "formatted_address": "北京市朝阳区望京街道阜通东大街6号",
    "addressComponent": {
      "country": "中国",
      "province": "北京市",
      "city": "",
      "citycode": "010",
      "district": "朝阳区",
      "adcode": "110105",
      "township": "望京街道",
      "towncode": "110105026000",
      "streetNumber": { "street": "阜通东大街", "number": "6号" }
    },
    "pois": [],
    "roads": [],
    "roadinters": [],
    "aois": []
  }
}
```

---

## 三、地理编码匹配级别列表

| 级别 | 说明 |
|------|------|
| 国家 | 匹配到国家级别 |
| 省 | 匹配到省份 |
| 城市 | 匹配到城市 |
| 区县 | 匹配到区县 |
| 乡镇 | 匹配到乡镇 |
| 村庄 | 匹配到村庄 |
| 街道 | 匹配到街道级别 |
| 门牌号 | 匹配到门牌号码 |
| 兴趣点 | 匹配到 POI 点 |
| 楼栋号 | 匹配到楼栋 |
| 道路 | 匹配到道路 |
| 道路交叉口 | 匹配到交叉路口 |
| 公交站点 | 匹配到公交站/地铁站 |
| 未知 | 未匹配到具体级别 |

---

## 项目配置

在 WeatherAgent 项目中，API Key 通过 `.env` 文件配置：

```env
AMAP_API_KEY=你的高德Key
AMAP_BASE_URL=https://restapi.amap.com
```

地理编码与逆地理编码 API 的高德基础 URL 为 `https://restapi.amap.com`。
