<template>
  <div class="finance-dashboard">
    <!-- 顶部操作栏 -->
    <div class="header">
      <h2>💰 财务管理系统</h2>
      <div class="actions">
        <!-- 核心入口：点击这个按钮才召唤数字人 -->
        <button class="btn-ai" @click="$emit('start-analysis')">
          🤖 召唤 AI 数字人分析
        </button>
      </div>
    </div>

    <!-- 数据录入区 -->
    <div class="panel input-panel">
      <h3>📝 记账录入</h3>
      <div class="form-row">
        <input v-model="newItem.date" type="date" placeholder="日期">
        <input v-model="newItem.item" type="text" placeholder="项目名称 (如: 销售收入)">
        <input v-model.number="newItem.amount" type="number" placeholder="金额 (+收入 -支出)">
        <button @click="addRecord" class="btn-save">保存</button>
      </div>
      <!-- 简单的批量导入模拟 -->
      <div style="margin-top: 10px; font-size: 12px; color: #666;">
        * 批量导入功能可在此处扩展 (Excel Upload)
      </div>
    </div>

    <!-- 知识库管理区 -->
    <div class="panel kb-panel">
      <h3>🧠 知识库设置</h3>
      <input type="file" @change="uploadKnowledge" accept=".pdf,.txt">
      <span v-if="uploadStatus">{{ uploadStatus }}</span>
    </div>

    <!-- 数据列表区 -->
    <div class="panel list-panel">
      <h3>📊 账目明细</h3>
      <table>
        <thead>
          <tr>
            <th>日期</th>
            <th>项目</th>
            <th>金额</th>
            <th>类型</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in records" :key="row.id">
            <td>{{ row.record_date }}</td>
            <td>{{ row.item_name }}</td>
            <td :class="row.amount >= 0 ? 'income' : 'expense'">
              {{ row.amount }}
            </td>
            <td>{{ row.record_type }}</td>
            <td>
              <button @click="deleteRecord(row.id)" class="btn-del">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

// 定义向父组件发送的事件
defineEmits(['start-analysis'])

const records = ref<any[]>([])
const newItem = ref({ date: '', item: '', amount: 0 })
const uploadStatus = ref('')
const API_URL = 'http://localhost:8000'

// 加载数据
async function loadRecords() {
  const res = await fetch(`${API_URL}/api/records`)
  records.value = await res.json()
}

// 添加数据
async function addRecord() {
  if (!newItem.value.date || !newItem.value.item) return alert("请填写完整")
  
  await fetch(`${API_URL}/api/records`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(newItem.value)
  })
  
  // 清空并刷新
  newItem.value = { date: '', item: '', amount: 0 }
  await loadRecords()
}

// 删除数据
async function deleteRecord(id: number) {
  // 简单模拟删除，实际后端可以加个 DELETE 接口，或者这里只是演示前端逻辑
  // 假设后端还没写 DELETE 接口，这里先不报错
  console.log("请求删除 ID:", id)
  alert("删除功能需后端配合添加 DELETE /api/records/{id} 接口")
}

// 上传知识库
async function uploadKnowledge(event: any) {
  const file = event.target.files[0]
  if (!file) return
  
  const formData = new FormData()
  formData.append('file', file)
  
  uploadStatus.value = "上传并索引中..."
  try {
    const res = await fetch(`${API_URL}/api/upload_knowledge`, {
      method: 'POST',
      body: formData
    })
    if (res.ok) uploadStatus.value = "✅ 知识库更新成功！"
    else uploadStatus.value = "❌ 上传失败"
  } catch (e) {
    uploadStatus.value = "❌ 网络错误"
  }
}

onMounted(() => {
  loadRecords()
})
</script>

<style scoped>
/* 简单的 CRUD 样式 */
.finance-dashboard { padding: 20px; max-width: 1200px; margin: 0 auto; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.btn-ai { background: linear-gradient(45deg, #6a11cb, #2575fc); color: white; border: none; padding: 12px 24px; border-radius: 25px; font-size: 16px; cursor: pointer; transition: transform 0.2s; box-shadow: 0 4px 15px rgba(37, 117, 252, 0.3); }
.btn-ai:hover { transform: scale(1.05); }

.panel { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.05); margin-bottom: 20px; }
h3 { margin-top: 0; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px; margin-bottom: 15px; }

.form-row { display: flex; gap: 10px; }
input { padding: 8px; border: 1px solid #ddd; border-radius: 4px; flex: 1; }
.btn-save { background: #28a745; color: white; border: none; padding: 8px 20px; border-radius: 4px; cursor: pointer; }

table { width: 100%; border-collapse: collapse; }
th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
.income { color: #28a745; font-weight: bold; }
.expense { color: #dc3545; font-weight: bold; }
.btn-del { background: #ff4d4f; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 12px; }
</style>