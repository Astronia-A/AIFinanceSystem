<template>
  <div class="manager-container">
    <!-- 上部分：录入面板 -->
    <div class="card entry-panel">
      <div class="panel-header">
        <h3>📝 账务操作台</h3>
        <!-- 功能区：模板下载与批量导入 -->
        <div class="batch-actions">
          <button class="btn-outline" @click="downloadTemplate">
            下载 Excel 模板
          </button>
          <button class="btn-outline" @click="triggerFileInput">
            批量导入 Excel
          </button>
          <input 
            type="file" 
            ref="fileInput" 
            style="display: none" 
            accept=".xlsx, .xls"
            @change="handleBatchUpload"
          >
        </div>
      </div>

      <!-- 单条录入表单 -->
      <div class="form-grid">
        <div class="form-group">
          <label>日期</label>
          <input type="date" v-model="form.date" class="input-ctrl">
        </div>
        <div class="form-group">
          <label>项目名称</label>
          <input type="text" v-model="form.item" placeholder="例如：采购办公用品" class="input-ctrl">
        </div>
        <div class="form-group">
          <label>金额 (正收负支)</label>
          <input type="number" v-model.number="form.amount" placeholder="例如：-500" class="input-ctrl">
        </div>
        <div class="form-group btn-group">
          <button @click="submit" class="btn-primary" :disabled="loading">
            {{ loading ? '保存中...' : '保存记录' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 下部分：表格 -->
    <div class="card table-panel">
      <div class="panel-header-row">
        <div class="left-info">
          <h3>📋 账目明细表</h3>
          <span class="total-count">共 {{ displayRecords.length }} 条记录</span>
        </div>
        
        <!-- 时间筛选工具栏  -->
        <div class="filter-toolbar">
          <select v-model="currentPreset" @change="handlePresetChange" class="preset-select">
            <option v-for="p in presets" :key="p.days" :value="p.days">{{ p.label }}</option>
            <option v-if="currentPreset === 0" :value="0" disabled>自定义区间</option>
          </select>
          
          <div class="divider">|</div>

          <div class="date-range-picker">
            <input type="date" v-model="dateRange.start" @change="handleCustomDate" class="date-input">
            <span class="range-separator">至</span>
            <input type="date" v-model="dateRange.end" @change="handleCustomDate" class="date-input">
          </div>
        </div>
      </div>
      
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <!-- 可排序的表头：ID -->
              <th @click="handleSort('id')" class="sortable-th">
                ID 
                <span class="sort-icon">{{ getSortIcon('id') }}</span>
              </th>              
              <!-- 可排序的表头：日期 -->
              <th @click="handleSort('record_date')" class="sortable-th">
                日期
                <span class="sort-icon">{{ getSortIcon('record_date') }}</span>
              </th>              
              <th>项目</th>
              <th>收/支</th>              
              <!-- 可排序的表头：金额 -->
              <th @click="handleSort('amount')" class="sortable-th">
                金额
                <span class="sort-icon">{{ getSortIcon('amount') }}</span>
              </th>              
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="displayRecords.length === 0">
              <td colspan="6" class="empty-tip">暂无数据，请先录入或调整筛选条件</td>
            </tr>
            <tr v-for="row in displayRecords" :key="row.id">
              <td>#{{ row.id }}</td>
              <td>{{ row.record_date }}</td>
              <td>{{ row.item_name }}</td>
              <td>
                <span :class="['tag', row.amount >= 0 ? 'tag-in' : 'tag-out']">
                  {{ row.record_type }}
                </span>
              </td>
              <td :class="row.amount >= 0 ? 'text-green' : 'text-red'">
                {{ row.amount }}
              </td>
              <td>
                <button class="btn-text-danger" @click="handleDelete(row.id)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'

const API_URL = 'http://localhost:8000'
const records = ref<any[]>([]) // 原始全量数据
const loading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const form = ref({ date: new Date().toISOString().split('T')[0], item: '', amount: 0 })

// === 1. 排序状态 ===
const sortKey = ref('id') // 默认按 ID 排序
const sortOrder = ref<'asc' | 'desc'>('asc') // 默认升序

// === 2. 筛选状态 ===
const currentPreset = ref(9999) // 默认显示全部数据
const dateRange = reactive({ start: '', end: '' })
const presets = [
  { label: '所有数据', days: 9999 },
  { label: '最近 7 天', days: 7 },
  { label: '最近 1 个月', days: 30 },
  { label: '最近 3 个月', days: 90 },
  { label: '最近半年', days: 180 },
  { label: '最近一年', days: 365 },
]

// === 3.计算属性（过滤 + 排序） ===
const displayRecords = computed(() => {
  // 1. 过滤步骤
  let result = records.value.filter(item => {
    const d = item.record_date
    return d >= dateRange.start && d <= dateRange.end
  })

  // 2. 排序步骤
  result.sort((a, b) => {
    let valA = a[sortKey.value]
    let valB = b[sortKey.value]
    // 金额处理
    if (sortKey.value === 'amount' || sortKey.value === 'id') {
      valA = parseFloat(valA)
      valB = parseFloat(valB)
    }
    // 日期处理
    if (valA < valB) return sortOrder.value === 'asc' ? -1 : 1
    if (valA > valB) return sortOrder.value === 'asc' ? 1 : -1
    return 0
  })

  return result
})

// === 4. 排序逻辑 ===
function handleSort(key: string) {
  if (sortKey.value === key) {
    // 如果点击当前已排序的列，切换方向
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    // 如果点击新列，默认升序
    sortKey.value = key
    sortOrder.value = 'asc'
  }
}

function getSortIcon(key: string) {
  if (sortKey.value !== key) return '↕' // 未选中状态
  return sortOrder.value === 'asc' ? '↑' : '↓' // 选中状态
}

// === 5. 筛选逻辑 ===
function applyPreset(days: number) {
  currentPreset.value = days
  if (days === 9999) {
    // 设一个很大的范围覆盖所有数据
    dateRange.start = '1970-01-01' 
    dateRange.end = '2099-12-31'
  } else {
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - days + 1)
    dateRange.end = formatDate(end)
    dateRange.start = formatDate(start)
  }
}

function handlePresetChange() {
  applyPreset(currentPreset.value)
}

function handleCustomDate() {
  currentPreset.value = 0
}

function formatDate(date: Date) {
  return date.toISOString().split('T')[0]
}

// === 6. 数据操作 ===
async function loadList() {
  try {
    const res = await fetch(`${API_URL}/api/records`)
    if (res.ok) records.value = await res.json()
  } catch (e) {
    console.error("加载失败", e)
  }
}

async function submit() {
  if (!form.value.item || form.value.amount === 0) return alert('请填写完整')
  loading.value = true
  try {
    await fetch(`${API_URL}/api/records`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value)
    })
    form.value.item = ''
    form.value.amount = 0
    await loadList()
  } finally {
    loading.value = false
  }
}

async function handleDelete(id: number) {
  if (!confirm('⚠️ 确定要永久删除这条记录吗？')) return
  try {
    const res = await fetch(`${API_URL}/api/records/${id}`, { method: 'DELETE' })
    if (res.ok) {
      records.value = records.value.filter(r => r.id !== id)
    } else {
      alert("删除失败")
    }
  } catch (e) {
    alert("网络请求失败")
  }
}

// === 7. 导入导出 ===
function downloadTemplate() { window.open(`${API_URL}/api/template`, '_blank') }
function triggerFileInput() { fileInput.value?.click() }

async function handleBatchUpload(event: any) {
  const file = event.target.files[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  loading.value = true
  try {
    const res = await fetch(`${API_URL}/api/records/batch_upload`, { method: 'POST', body: formData })
    if (res.ok) {
      const data = await res.json()
      alert(`✅ 成功导入 ${data.count} 条数据！`)
      await loadList()
    } else {
      const err = await res.json()
      alert(`❌ 导入失败: ${err.detail}`)
    }
  } catch(e) { alert("网络错误") }
  finally { 
    loading.value = false
    if(fileInput.value) fileInput.value.value = ''
  }
}

onMounted(() => {
  loadList()
  applyPreset(9999) // 默认加载后显示全部
})
</script>

<style scoped>
.manager-container { display: flex; flex-direction: column; gap: 20px; }
.card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }

/* 头部布局 */
.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #f1f5f9; padding-bottom: 15px; }
.panel-header h3 { margin: 0; color: #334155; }

/* 表格头部布局  */
.panel-header-row { 
  display: flex; justify-content: space-between; align-items: center; 
  margin-bottom: 20px; border-bottom: 1px solid #f1f5f9; padding-bottom: 15px; 
}
.left-info h3 { margin: 0; margin-bottom: 4px; color: #334155; }
.total-count { font-size: 12px; color: #94a3b8; }

/* 筛选工具栏样式*/
.filter-toolbar { display: flex; align-items: center; gap: 15px; }
.preset-select { padding: 6px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; outline: none; cursor: pointer; }
.divider { color: #e2e8f0; font-size: 14px; }
.date-range-picker { display: flex; align-items: center; gap: 8px; }
.date-input { border: 1px solid #cbd5e1; border-radius: 6px; padding: 5px 8px; font-family: inherit; color: #475569; outline: none; }
.range-separator { color: #94a3b8; font-size: 12px; }

/* 按钮区 */
.batch-actions { display: flex; gap: 10px; }
.btn-outline {
  background: white; border: 1px solid #cbd5e1; color: #475569;
  padding: 6px 16px; border-radius: 6px; cursor: pointer; transition: all 0.2s; font-size: 13px;
  display: flex; align-items: center; gap: 6px;
}
.btn-outline:hover { border-color: #3b82f6; color: #3b82f6; background: #eff6ff; }

/* 表单样式 */
.form-grid { display: grid; grid-template-columns: 1fr 2fr 1fr auto; gap: 15px; align-items: end; }
.form-group label { display: block; font-size: 13px; color: #64748b; margin-bottom: 6px; }
.input-ctrl { width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; outline: none; transition: border 0.2s; box-sizing: border-box; }
.input-ctrl:focus { border-color: #3b82f6; }
.btn-primary { background: #3b82f6; color: white; border: none; padding: 10px 24px; border-radius: 6px; cursor: pointer; height: 38px; font-weight: 500; }
.btn-primary:hover { background: #2563eb; }
.btn-primary:disabled { background: #94a3b8; cursor: not-allowed; }

/* 表格样式 */
.table-wrapper { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { text-align: left; padding: 12px; background: #f8fafc; color: #64748b; font-weight: 600; font-size: 14px; }
.data-table td { padding: 12px; border-bottom: 1px solid #f1f5f9; color: #334155; font-size: 14px; }
.empty-tip { text-align: center; color: #94a3b8; padding: 40px 0; }

/* 排序表头样式 */
.sortable-th { cursor: pointer; user-select: none; transition: background 0.2s; }
.sortable-th:hover { background: #e2e8f0; color: #3b82f6; }
.sort-icon { display: inline-block; margin-left: 5px; font-weight: normal; width: 15px; text-align: center; }

.tag { padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
.tag-in { background: #dcfce7; color: #166534; }
.tag-out { background: #fee2e2; color: #991b1b; }
.text-green { color: #166534; font-weight: bold; }
.text-red { color: #dc2626; font-weight: bold; }
.btn-text-danger { background: none; border: none; color: #ef4444; cursor: pointer; font-size: 13px; }
.btn-text-danger:hover { text-decoration: underline; background: #fef2f2; padding: 4px 8px; border-radius: 4px; }
</style>