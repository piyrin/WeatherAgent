/**
 * =============================================
 * 高德地图 JSAPI 异步加载器
 * =============================================
 * 职责：
 *   1. 动态加载高德 JSAPI 2.0 脚本（只加载一次）
 *   2. 配置安全密钥（securityJsCode）
 *   3. 提供 createMap 工厂函数与 polyline 解析工具
 *
 * 设计原则：
 *   - 懒加载：首次调用时才插入 <script>，不影响首屏性能
 *   - 单例：全局只加载一次 JSAPI，后续调用复用 Promise
 *   - 配置统一：Key 和安全密钥从 config 读取（源于 .env）
 *
 * 对应配置：
 *   .env.development / .env.production 中的
 *   VITE_AMAP_JSAPI_KEY 和 VITE_AMAP_SECURITY_CODE
 */

import config from '@/config/index.js'

let amapLoadPromise = null  // 全局加载 Promise，确保 JSAPI 只加载一次

/**
 * 异步加载高德 JSAPI 2.0
 * 全局只加载一次，重复调用返回同一个 Promise
 *
 * @returns {Promise<typeof AMap>} AMap 全局对象
 */
export function loadAMap() {
  if (amapLoadPromise) return amapLoadPromise

  amapLoadPromise = new Promise((resolve, reject) => {
    // Key 未配置时直接报错（提示用户去 .env 填写）
    if (!config.amapJsapiKey || config.amapJsapiKey.includes('请填入')) {
      reject(new Error(
        '高德 JSAPI Key 未配置，请在 frontend/.env.development 中填写 VITE_AMAP_JSAPI_KEY'
      ))
      return
    }

    // 配置安全密钥（JSAPI 2.0 必需，在加载脚本前设置）
    if (config.amapSecurityCode && !config.amapSecurityCode.includes('请填入')) {
      window._AMapSecurityConfig = {
        securityJsCode: config.amapSecurityCode
      }
    }

    // 动态插入 script 标签
    const script = document.createElement('script')
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${config.amapJsapiKey}`
    script.async = true
    script.onerror = () => {
      amapLoadPromise = null  // 加载失败允许重试
      reject(new Error('高德 JSAPI 脚本加载失败，请检查网络或 Key 配置'))
    }
    script.onload = () => {
      if (window.AMap) {
        resolve(window.AMap)
      } else {
        amapLoadPromise = null
        reject(new Error('高德 JSAPI 加载完成但未找到 AMap 全局对象'))
      }
    }
    document.head.appendChild(script)
  })

  return amapLoadPromise
}

/**
 * 在指定容器创建地图实例并绘制路线
 *
 * @param {string|HTMLElement} container - 容器 DOM 元素或其 id
 * @param {Object} routeData - 路线数据
 * @param {string} routeData.polyline - 路线坐标串 "lng,lat;lng,lat;..."
 * @param {string} routeData.origin_coord - 起点坐标 "lng,lat"
 * @param {string} routeData.destination_coord - 终点坐标 "lng,lat"
 * @param {string} routeData.travel_mode - 出行方式
 * @param {Object} [mapOptions] - 额外地图配置
 * @returns {Promise<{map: Object, AMap: Object}>} 地图实例与 AMap 全局对象
 */
export async function createRouteMap(container, routeData, mapOptions = {}) {
  const AMap = await loadAMap()

  // 解析路线坐标
  const path = parsePolyline(AMap, routeData.polyline)
  const origin = routeData.origin_coord ? parseCoord(AMap, routeData.origin_coord) : null
  const destination = routeData.destination_coord ? parseCoord(AMap, routeData.destination_coord) : null

  // 自动计算中心点和缩放级别
  const center = origin || (path.length > 0 ? path[0] : null)
  const map = new AMap.Map(container, {
    zoom: mapOptions.zoom || 13,
    center: center || undefined,
    viewMode: '2D',
    ...mapOptions
  })

  // 绘制路线 Polyline
  if (path.length > 1) {
    const polyline = new AMap.Polyline({
      path,
      strokeColor: '#1677ff',
      strokeWeight: 6,
      strokeOpacity: 0.9,
      lineJoin: 'round',
      lineCap: 'round',
      showDir: true  // 显示行车方向箭头
    })
    map.add(polyline)

    // 自动调整视野以包含整条路线
    map.setFitView([polyline], false, [60, 60, 60, 60])
  }

  // 起点标记（绿色）
  if (origin) {
    const startMarker = new AMap.Marker({
      position: origin,
      content: '<div style="background:#52c41a;color:#fff;width:24px;height:24px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:bold;box-shadow:0 2px 6px rgba(0,0,0,0.3)">起</div>',
      offset: new AMap.Pixel(-12, -24)
    })
    map.add(startMarker)
  }

  // 终点标记（红色）
  if (destination) {
    const endMarker = new AMap.Marker({
      position: destination,
      content: '<div style="background:#ff4d4f;color:#fff;width:24px;height:24px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:bold;box-shadow:0 2px 6px rgba(0,0,0,0.3)">终</div>',
      offset: new AMap.Pixel(-12, -24)
    })
    map.add(endMarker)
  }

  return { map, AMap }
}

/**
 * 将路线 polyline 坐标串解析为 AMap.LngLat 数组
 *
 * @param {typeof AMap} AMap - AMap 全局对象
 * @param {string} polylineStr - 坐标串 "lng,lat;lng,lat;..."
 * @returns {AMap.LngLat[]} 坐标数组
 */
export function parsePolyline(AMap, polylineStr) {
  if (!polylineStr) return []
  return polylineStr
    .split(';')
    .filter(Boolean)
    .map((point) => parseCoord(AMap, point))
}

/**
 * 将单个 "lng,lat" 字符串解析为 AMap.LngLat
 *
 * @param {typeof AMap} AMap - AMap 全局对象
 * @param {string} coordStr - 坐标串 "lng,lat"
 * @returns {AMap.LngLat|null}
 */
export function parseCoord(AMap, coordStr) {
  if (!coordStr) return null
  const [lng, lat] = coordStr.split(',').map(Number)
  if (isNaN(lng) || isNaN(lat)) return null
  return new AMap.LngLat(lng, lat)
}
