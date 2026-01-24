<template>
  <div class="kb-container">
    <div class="card upload-card">
      
      <!-- 新增：状态提示条 -->
      <div v-if="kbExists" class="status-banner success">
        <span class="status-icon">✅</span>
        <div class="status-text">
          <strong>系统已存在知识库</strong>
          <small>您可以直接进行 AI 分析，也可以上传新文件覆盖旧知识库。</small>
        </div>
      </div>
      <div v-else class="status-banner warning">
        <span class="status-icon">⚠️</span>
        <div class="status-text">
          <strong>暂无知识库数据</strong>
          <small>建议上传财务准则或审计报告，以增强 AI 分析能力。</small>
        </div>
      </div>

      <div class="icon-header">📚</div>
      <h2>上传财务知识库</h2>
      <p class="desc">
        请上传 PDF 或 TXT 文件（如企业审计准则、内部财务规定等）。<br>
        AI 将会阅读这些文件，并建立本地向量索引。
      </p>

      <!-- 上传区域 -->
      <div 
        class="drop-zone" 
        @dragover.prevent 
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <input 
          type="file" 
          ref="fileInput" 
          style="display: none" 
          accept=".pdf,.txt"
          @change="handleFileSelect"
        >
        <div v-if="!isUploading">
          <span class="upload-icon">☁️</span>
          <p>点击或拖拽文件到此处上传</p>
        </div>
        <div v-else class="uploading-state">
          <div class="spinner"></div>
          <p>正在解析并建立向量索引，请稍候...</p>
        </div>
      </div>

      <!-- 操作反馈消息 -->
      <div v-if="message" :class="['msg-box', msgType]">
        {{ message }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const API_URL = 'http://localhost:8000'

const fileInput = ref<HTMLInputElement | null>(null)
const isUploading = ref(false)
const message = ref('')
const msgType = ref('info')

// 新增：知识库存在状态
const kbExists = ref(false)

// === 1. 检查状态 ===
async function checkStatus() {
  try {
    const res = await fetch(`${API_URL}/api/knowledge/status`)
    if (res.ok) {
      const data = await res.json()
      kbExists.value = data.exists
    }
  } catch (e) {
    console.error("无法获取知识库状态")
  }
}

// === 2. 上传逻辑 ===
async function uploadFile(file: File) {
  if (!file.name.endsWith('.pdf') && !file.name.endsWith('.txt')) {
    showMessage('只支持 PDF 或 TXT 格式', 'error')
    return
  }

  isUploading.value = true
  message.value = ''
  
  const formData = new FormData()
  formData.append('file', file)

  try {
    const res = await fetch(`${API_URL}/api/upload_knowledge`, {
      method: 'POST',
      body: formData
    })
    
    if (res.ok) {
      showMessage(`✅ "${file.name}" 上传并索引成功！`, 'success')
      // 上传成功后，刷新状态，变成“已存在”
      kbExists.value = true
    } else {
      showMessage('❌ 上传失败，请检查后端日志', 'error')
    }
  } catch (e) {
    showMessage('❌ 网络错误，无法连接服务器', 'error')
  } finally {
    isUploading.value = false
    if(fileInput.value) fileInput.value.value = ''
  }
}

function triggerFileInput() { fileInput.value?.click() }
function handleFileSelect(event: any) { const file = event.target.files[0]; if(file) uploadFile(file); }
function handleDrop(event: any) { const file = event.dataTransfer.files[0]; if(file) uploadFile(file); }
function showMessage(text: string, type: 'success'|'error'|'info') { message.value = text; msgType.value = type; }

onMounted(() => {
  checkStatus()
})
</script>

<style scoped>
.kb-container {
  display: flex; justify-content: center; align-items: center;
  height: 100%; min-height: 500px; padding: 20px;
}

.upload-card {
  background: white; width: 100%; max-width: 600px;
  border-radius: 16px; padding: 40px; text-align: center;
  box-shadow: 0 10px 30px rgba(0,0,0,0.05);
  position: relative; overflow: hidden;
}

/* === 新增：状态横幅样式 === */
.status-banner {
  margin: -40px -40px 30px -40px; /* 抵消父容器 padding */
  padding: 15px 20px;
  display: flex; align-items: center; gap: 15px; text-align: left;
}
.status-banner.success { background: #f0fdf4; border-bottom: 1px solid #bbf7d0; color: #166534; }
.status-banner.warning { background: #fffbeb; border-bottom: 1px solid #fde68a; color: #92400e; }

.status-icon { font-size: 24px; }
.status-text { display: flex; flex-direction: column; }
.status-text strong { font-size: 15px; margin-bottom: 2px; }
.status-text small { opacity: 0.8; font-size: 12px; }

/* 其他样式保持不变 */
.icon-header { font-size: 48px; margin-bottom: 20px; }
h2 { color: #1e293b; margin-bottom: 10px; }
.desc { color: #64748b; line-height: 1.6; margin-bottom: 30px; font-size: 14px; }
.drop-zone {
  border: 2px dashed #cbd5e1; border-radius: 12px;
  padding: 40px; cursor: pointer; transition: all 0.3s;
  background: #f8fafc;
}
.drop-zone:hover { border-color: #3b82f6; background: #eff6ff; }
.upload-icon { font-size: 40px; display: block; margin-bottom: 10px; }
.msg-box { margin-top: 20px; padding: 12px; border-radius: 6px; font-size: 14px; }
.msg-box.success { background: #dcfce7; color: #166534; }
.msg-box.error { background: #fee2e2; color: #991b1b; }
.spinner {
  width: 30px; height: 30px; border: 3px solid #e2e8f0;
  border-top-color: #3b82f6; border-radius: 50%;
  margin: 0 auto 10px;
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>