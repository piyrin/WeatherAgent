<template>
  <div class="map-card">
    <!-- 路线信息条 -->
    <div class="route-info">
      <span class="mode-tag" :class="routeData.travel_mode">{{ modeName }}</span>
      <span class="info-item">距离 {{ routeData.distance_km }} 公里</span>
      <span class="info-item">耗时 {{ routeData.duration_min }} 分钟</span>
      <span v-if="routeData.taxi_cost" class="info-item">打车约 {{ routeData.taxi_cost }} 元</span>
      <span v-if="routeData.walking_distance_km" class="info-item">步行 {{ routeData.walking_distance_km }} 公里</span>
      <span v-if="routeData.bus_count" class="info-item">换乘 {{ routeData.bus_count }} 段</span>
    </div>

    <!-- 缩略地图 -->
    <div class="map-thumb" @click="openFullMap">
      <div v-if="mapError" class="map-error">
        <el-icon :size="24"><MapLocation /></el-icon>
        <span>{{ mapError }}</span>
      </div>
      <div v-else ref="thumbMapRef" class="map-container"></div>
      <div v-if="!mapError" class="map-overlay">
        <el-icon><FullScreen /></el-icon>
        <span>点击查看大图</span>
      </div>
    </div>

    <!-- 全屏地图对话框 -->
    <el-dialog
      v-model="showFullMap"
      title="路线详情"
      width="90%"
      top="3vh"
      destroy-on-close
      @opened="initFullMap"
      @closed="fullMap = null"
    >
      <div class="route-detail">
        <div class="route-info-bar">
          <span class="mode-tag" :class="routeData.travel_mode">{{ modeName }}</span>
          <span>距离 {{ routeData.distance_km }} 公里</span>
          <span>耗时 {{ routeData.duration_min }} 分钟</span>
          <span v-if="routeData.taxi_cost">打车约 {{ routeData.taxi_cost }} 元</span>
          <span v-if="routeData.bus_count">换乘 {{ routeData.bus_count }} 段</span>
          <span v-if="routeData.walking_distance_km">步行 {{ routeData.walking_distance_km }} 公里</span>
        </div>
        <div ref="fullMapRef" class="full-map-container"></div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { FullScreen, MapLocation } from '@element-plus/icons-vue'
import { createRouteMap } from '@/utils/amap.js'

const props = defineProps({
  routeData: {
    type: Object,
    required: true
  }
})

const thumbMapRef = ref(null)
const fullMapRef = ref(null)
const showFullMap = ref(false)
const mapError = ref('')

let thumbMap = null
let fullMap = null

const modeName = computed(() => {
  const map = { driving: '驾车', walking: '步行', transit: '公交/地铁' }
  return map[props.routeData.travel_mode] || '路线'
})

onMounted(async () => {
  await nextTick()
  await initThumbMap()
})

onBeforeUnmount(() => {
  if (thumbMap) {
    thumbMap.destroy()
    thumbMap = null
  }
  if (fullMap) {
    fullMap.destroy()
    fullMap = null
  }
})

async function initThumbMap() {
  if (!thumbMapRef.value) return
  try {
    const result = await createRouteMap(thumbMapRef.value, props.routeData, {
      zoom: 12,
      dragEnable: false,
      zoomEnable: false,
      keyboardEnable: false,
      doubleClickZoom: false
    })
    thumbMap = result.map
  } catch (err) {
    mapError.value = err.message || '地图加载失败'
  }
}

function openFullMap() {
  showFullMap.value = true
}

async function initFullMap() {
  await nextTick()
  if (!fullMapRef.value) return
  try {
    const result = await createRouteMap(fullMapRef.value, props.routeData, {
      zoom: 13
    })
    fullMap = result.map
  } catch (err) {
    console.error('全屏地图加载失败:', err)
  }
}
</script>

<style scoped>
.map-card {
  margin-top: 10px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border-color);
  background: #fff;
}

/* 路线信息条 */
.route-info {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  font-size: 13px;
  color: var(--text-secondary);
}

.mode-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  background: #1677ff;
}

.mode-tag.driving {
  background: #1677ff;
}

.mode-tag.transit {
  background: #52c41a;
}

.mode-tag.walking {
  background: #faad14;
}

.info-item {
  white-space: nowrap;
}

/* 缩略地图 */
.map-thumb {
  position: relative;
  height: 180px;
  cursor: pointer;
  background: #f0f2f5;
}

.map-container {
  width: 100%;
  height: 100%;
}

.map-overlay {
  position: absolute;
  bottom: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 12px;
  border-radius: 4px;
  pointer-events: none;
}

.map-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  padding: 16px;
  text-align: center;
}

/* 全屏对话框内容 */
.route-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.route-info-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  background: #f5f7fa;
  border-radius: 6px;
  font-size: 14px;
  color: var(--text-primary);
}

.full-map-container {
  width: 100%;
  height: 70vh;
  min-height: 400px;
  border-radius: 6px;
  overflow: hidden;
}
</style>
