<template>
  <div class="dashboard-container">
    <!-- 顶部卡片栏 -->
    <div class="stats-grid">
      <div class="stat-card blue">
        <div class="label">总收入</div>
        <div class="value clickable" @click="toggleMode('totalIn')" title="点击切换显示格式">
          ¥ {{ formatSmartNumber(summary.totalIn, 'totalIn') }}
        </div>
      </div>
      <div class="stat-card red">
        <div class="label">总支出</div>
        <div class="value clickable" @click="toggleMode('totalOut')" title="点击切换显示格式">
          ¥ {{ formatSmartNumber(Math.abs(summary.totalOut), 'totalOut') }}
        </div>
      </div>
      <div class="stat-card green">
        <div class="label">💰 净利润</div>
        <div class="value clickable" @click="toggleMode('profit')" title="点击切换显示格式">
          ¥ {{ formatSmartNumber(summary.profit, 'profit') }}
        </div>
        <div class="sub" :class="summary.profit >= 0 ? 'pos' : 'neg'">
          {{ summary.profit >= 0 ? '盈利状态' : '亏损状态' }}
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="chart-section">
      <div class="chart-header">
        <h3>📅 收支趋势分析</h3>        
        <!-- 筛选工具栏 -->
        <div class="filter-toolbar">          
          <!-- 使用 Select 下拉框 -->
          <div class="select-wrapper">
            <select 
              v-model="currentPreset" 
              @change="handlePresetChange"
              class="preset-select"
            >
              <option v-for="p in presets" :key="p.days" :value="p.days">
                {{ p.label }}
              </option>
              <!-- 这是一个隐藏选项，只有当用户手动修改日期时才会选中它 -->
              <option v-if="currentPreset === 0" :value="0" disabled>
                自定义区间
              </option>
            </select>
          </div>
          
          <div class="divider">|</div>

          <!-- 自定义日期范围 -->
          <div class="date-range-picker">
            <input type="date" v-model="dateRange.start" @change="handleCustomDate" class="date-input">
            <span class="range-separator">至</span>
            <input type="date" v-model="dateRange.end" @change="handleCustomDate" class="date-input">
          </div>
        </div>
      </div>

      <!-- 图表组件 -->
      <v-chart class="echart" :option="chartOption" autoresize />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent, DataZoomComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent, DataZoomComponent])

const API_URL = 'http://localhost:8000'

// === 状态定义 ===
const summary = ref({ totalIn: 0, totalOut: 0, profit: 0 })
const rawData = ref<any[]>([]) 
const chartOption = ref({})

const preciseModes = reactive<Record<string, boolean>>({
  totalIn: false, totalOut: false, profit: false
})

// === 时间筛选状态 ===
const currentPreset = ref(7) // 默认选中 7天
const dateRange = reactive({ start: '', end: '' })

const presets = [
  { label: '最近 7 天', days: 7 },
  { label: '最近 14 天', days: 14 },
  { label: '最近 1 个月', days: 30 },
  { label: '最近 3 个月', days: 90 },
  { label: '最近半年', days: 180 },
  { label: '最近一年', days: 365 },
  { label: '所有数据', days: 9999 }
]

// === 初始化 ===
onMounted(async () => {
  await fetchData()
  applyPreset(7)
})

// === 获取数据 ===
async function fetchData() {
  try {
    const res = await fetch(`${API_URL}/api/records`)
    const data = await res.json()
    rawData.value = data
    calculateSummary(data)
  } catch (e) {
    console.error("获取数据失败", e)
  }
}

function handlePresetChange() {
  applyPreset(currentPreset.value)
}

// === 应用时间预设 ===
function applyPreset(days: number) {
  currentPreset.value = days // 确保下拉框选中对应值
  
  if (days === 9999) {
    if (rawData.value.length > 0) {
      const dates = rawData.value.map(d => d.record_date).sort()
      dateRange.start = dates[0]
      dateRange.end = dates[dates.length - 1]
    } else {
      const today = new Date().toISOString().split('T')[0]
      dateRange.start = today
      dateRange.end = today
    }
  } else {
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - days + 1)
    
    dateRange.end = formatDate(end)
    dateRange.start = formatDate(start)
  }
  
  updateChart()
}

// === 手动选择日期 ===
function handleCustomDate() {
  // 当用户手动修改日期时，将下拉框置为 0（显示“自定义区间”）
  currentPreset.value = 0 
  updateChart()
}

function formatDate(date: Date) {
  return date.toISOString().split('T')[0]
}

// === 图表更新逻辑 ===
function updateChart() {
  const filtered = rawData.value.filter(item => {
    const d = item.record_date
    return d >= dateRange.start && d <= dateRange.end
  })

  const sorted = [...filtered].sort((a,b) => new Date(a.record_date).getTime() - new Date(b.record_date).getTime())
  const dates = sorted.map(i => i.record_date)
  const values = sorted.map(i => parseFloat(i.amount))

  chartOption.value = {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '8%', containLabel: true },
    xAxis: { 
      type: 'category', 
      data: dates,
      axisTick: { alignWithLabel: true }
    },
    yAxis: { type: 'value' },
    dataZoom: [{ type: 'inside' }],
    series: [
      {
        name: '金额',
        type: 'bar',
        data: values,
        barMaxWidth: '50px', 
        itemStyle: {
          color: (params: any) => params.value >= 0 ? '#3b82f6' : '#ef4444',
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  }
}

// === 辅助功能 ===
function toggleMode(key: string) { preciseModes[key] = !preciseModes[key] }
function calculateSummary(data: any[]) {
  let tin = 0, tout = 0
  data.forEach(item => {
    const val = parseFloat(item.amount)
    if (val > 0) tin += val
    else tout += val
  })
  summary.value = { totalIn: tin, totalOut: tout, profit: tin + tout }
}
function formatSmartNumber(num: number, key: string) {
  const absVal = Math.abs(num)
  const isPrecise = preciseModes[key]
  if (absVal >= 100000 && !isPrecise) {
    return (num / 10000).toFixed(2) + ' 万'
  } else {
    return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
}
</script>

<style scoped>
/* 卡片样式 */
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 24px; }
.stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-left: 5px solid #ccc; transition: transform 0.2s; }
.stat-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.stat-card.blue { border-left-color: #3b82f6; }
.stat-card.red { border-left-color: #ef4444; }
.stat-card.green { border-left-color: #22c55e; }
.label { color: #64748b; font-size: 14px; margin-bottom: 8px; }
.value { font-size: 24px; font-weight: bold; color: #1e293b; white-space: nowrap; }
.clickable { cursor: pointer; user-select: none; border-bottom: 1px dashed transparent; display: inline-block; }
.clickable:hover { color: #3b82f6; border-bottom-color: #cbd5e1; }
.sub { margin-top: 5px; font-size: 12px; }
.sub.pos { color: #22c55e; } .sub.neg { color: #ef4444; }

/* 图表区样式 */
.chart-section { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); min-height: 500px; }
.chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #f1f5f9; padding-bottom: 15px; }
.chart-header h3 { margin: 0; color: #334155; }

.filter-toolbar { display: flex; align-items: center; gap: 15px; }
.divider { color: #e2e8f0; font-size: 14px; }

/* 下拉框样式 */
.preset-select {
  padding: 6px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background-color: white;
  color: #475569;
  font-size: 14px;
  outline: none;
  cursor: pointer;
  transition: all 0.2s;
}
.preset-select:hover { border-color: #3b82f6; }
.preset-select:focus { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1); }

/* 日期选择器样式 */
.date-range-picker { display: flex; align-items: center; gap: 8px; }
.date-input { border: 1px solid #cbd5e1; border-radius: 6px; padding: 5px 8px; font-family: inherit; color: #475569; outline: none; }
.date-input:focus { border-color: #3b82f6; }
.range-separator { color: #94a3b8; font-size: 12px; }

.echart { height: 400px; width: 100%; }
</style>