# 高德地图 路径规划 API

> 来源：https://lbs.amap.com/api/webservice/guide/api/direction
> 依赖：使用前需先将地名转为坐标（地理编码 API）

## 产品介绍

路径规划 API 是一套以 HTTP/HTTPS 形式提供的步行、驾车、公交路径规划接口，返回起终点的距离、耗时和路线步骤。

**重要依赖**：路径规划 API 的 `origin` 和 `destination` 参数需要**经纬度坐标**（格式 `lng,lat`），而不是地名。因此调用前必须先通过 **地理编码 API** 将地名转换为坐标。

## 调用依赖链

```
用户输入地名（"天安门"、"故宫"）
    │
    ├─ 1. 地理编码 API
    │     https://restapi.amap.com/v3/geocode/geo
    │     address="天安门" → 116.397499,39.908722
    │
    ├─ 2. 地理编码 API
    │     https://restapi.amap.com/v3/geocode/geo
    │     address="故宫" → 116.403963,39.915119
    │
    └─ 3. 路径规划 API
          https://restapi.amap.com/v3/direction/{mode}
          origin=116.397499,39.908722
          destination=116.403963,39.915119
          → 距离、耗时、路线步骤
```

---

## 一、驾车路径规划

### API 服务地址

| 项目 | 内容 |
|------|------|
| **URL** | `https://restapi.amap.com/v3/direction/driving?parameters` |
| **请求方式** | GET |
| **编码** | UTF-8 |

### 请求参数

| 参数名 | 含义 | 规则说明 | 是否必须 | 缺省值 |
|--------|------|----------|----------|--------|
| `key` | 请求服务权限标识 | 高德 Web 服务 API KEY | **必填** | 无 |
| `origin` | 起点坐标 | 经度在前，纬度在后，格式：`lng,lat`。如：`116.397499,39.908722` | **必填** | 无 |
| `destination` | 终点坐标 | 格式同起点 | **必填** | 无 |
| `origin_id` | 起点POI ID | 如果起点是POI，可传此参数获得更优路径 | 可选 | 无 |
| `destination_id` | 终点POI ID | 同上 | 可选 | 无 |
| `strategy` | 路径规划策略 | 见下方策略表 | 可选 | 0 |
| `waypoints` | 途经点 | 经纬度，最多16个，经度在前。格式：`lng1,lat1;lng2,lat2` | 可选 | 无 |
| `avoidpolygons` | 避让区域 | 避开某些区域，格式：`lng1,lat1;lng2,lat2` | 可选 | 无 |
| `sig` | 签名 | 数字签名，付费用户必填 | 可选 | 无 |

### 驾车策略 (strategy)

| 值 | 说明 |
|----|------|
| 0 | 速度优先（不考虑实时路况） |
| 1 | 费用优先（不走收费路段，且忽略实时路况） |
| 2 | 距离优先（不考虑实时路况） |
| 3 | 速度优先（避开当前拥堵路段） |
| 4 | 速度优先（避开当前拥堵且考虑未来拥堵趋势） |
| 5 | 多路径（不进行躲避） |
| 6 | 速度优先（考虑当前路况，不走高速） |
| 7 | 速度优先（考虑当前路况，且不走高速并避免收费） |
| 8 | 速度优先（考虑当前路况，且躲避拥堵并避免收费） |
| 9 | 速度优先（考虑当前路况，且不走高速并躲避收费） |
| 10 | 速度优先（考虑当前路况，且躲避拥堵，速度优先，不走高速且避免收费） |

### 返回结果参数 (驾车)

| 字段 | 说明 |
|------|------|
| `status` | 0=失败；1=成功 |
| `infocode` | 状态码，10000=正确 |
| `count` | 返回路径方案数 |
| `route` | 路径规划方案 |
| `route.origin` | 起点坐标 |
| `route.destination` | 终点坐标 |
| `route.paths[]` | 路径方案列表 |
| `paths[].distance` | 距离（米） |
| `paths[].duration` | 预计耗时（秒） |
| `paths[].strategy` | 采用的策略 |
| `paths[].tolls` | 收费金额（元） |
| `paths[].toll_distance` | 收费路段距离（米） |
| `paths[].steps[]` | 导航步骤 |
| `steps[].instruction` | 驾驶导航指令 |
| `steps[].road` | 道路名称 |
| `steps[].distance` | 此段距离（米） |
| `steps[].duration` | 此段耗时（秒） |
| `steps[].polyline` | 路段坐标点串（用于画线） |

### 服务示例

```bash
curl "https://restapi.amap.com/v3/direction/driving?\
key=YOUR_KEY&\
origin=116.397499,39.908722&\
destination=116.403963,39.915119&\
strategy=0"
```

---

## 二、步行路径规划

### API 服务地址

| 项目 | 内容 |
|------|------|
| **URL** | `https://restapi.amap.com/v3/direction/walking?parameters` |
| **请求方式** | GET |

### 请求参数

| 参数名 | 含义 | 是否必须 | 说明 |
|--------|------|----------|------|
| `key` | API KEY | **必填** | — |
| `origin` | 起点坐标 | **必填** | `lng,lat` |
| `destination` | 终点坐标 | **必填** | `lng,lat` |
| `sig` | 签名 | 可选 | 付费用户 |

### 返回结果参数

| 字段 | 说明 |
|------|------|
| `route.paths[].distance` | 总距离（米） |
| `route.paths[].duration` | 步行预估耗时（秒） |
| `route.paths[].steps[]` | 步行导航步骤 |
| `steps[].instruction` | 步行指引 |
| `steps[].road` | 道路名称 |
| `steps[].distance` | 步骤距离（米） |

---

## 三、公交路径规划

### API 服务地址

| 项目 | 内容 |
|------|------|
| **URL** | `https://restapi.amap.com/v3/direction/transit/integrated?parameters` |
| **请求方式** | GET |

### 请求参数

| 参数名 | 含义 | 是否必须 | 说明 |
|--------|------|----------|------|
| `key` | API KEY | **必填** | — |
| `origin` | 起点坐标 | **必填** | `lng,lat` |
| `destination` | 终点坐标 | **必填** | `lng,lat` |
| `city` | 城市 | **必填** | 城市中文或citycode/adcode |
| `cityd` | 终点城市 | 可选 | 跨城时使用 |
| `strategy` | 换乘策略 | 可选 | 0:推荐；1:少换乘；2:少步行；3:舒适 |
| `sig` | 签名 | 可选 | — |

### 返回结果参数

| 字段 | 说明 |
|------|------|
| `route.transits[]` | 换乘方案列表 |
| `transits[].cost` | 费用（元） |
| `transits[].duration` | 耗时（秒） |
| `transits[].distance` | 总距离（米） |
| `transits[].walking_distance` | 步行距离（米） |
| `transits[].segments[]` | 换乘段（步行/公交/地铁） |
| `segments[].bus` | 公交/地铁线路信息 |
| `segments[].walking` | 步行信息 |
| `segments[].entrance` | 地铁入口 |
| `segments[].exit` | 地铁出口 |

---

## 四、项目中的路径规划工具现状

### RoutePlannerTool (`backend/app/tools/route_planner.py`)

**当前状态**：使用模拟数据（`_get_mock_route`），基于起终点名称的 MD5 hash 生成随机距离。

**待改造**：接入上述真实 API。改造时：
1. 先调用地理编码 API 将 `origin` 和 `destination` 转为坐标
2. 再调用路径规划 API（根据 `travel_mode` 选择 driving/walking/transit 端点）
3. 解析返回结果，构建统一格式

**输入依赖**：
- `origin: str` — 可以是地名（需先调用 geocoding 转坐标）或坐标
- `destination: str` — 同上
- `travel_mode: str` — driving / walking / transit

---

## 项目配置

```env
AMAP_API_KEY=你的高德Key
AMAP_BASE_URL=https://restapi.amap.com
```

URL 拼接示例：
```python
# 驾车
AMAP_DRIVING_URL = f"{AMAP_BASE_URL}/v3/direction/driving"
# 步行
AMAP_WALKING_URL = f"{AMAP_BASE_URL}/v3/direction/walking"
# 公交
AMAP_TRANSIT_URL = f"{AMAP_BASE_URL}/v3/direction/transit/integrated"
```
