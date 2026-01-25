<template>
  <div class="avatar-overlay">
    <!-- 关闭按钮 -->
    <button class="close-btn" @click="handleClose">✖ 结束咨询</button>
    <div class="content-container">
      <!-- 左侧：交互控制台 -->
      <div class="control-panel">
        <div class="panel-header">
          <div class="header-title">
            <h3>🤖 AI 审计师</h3>
            <span class="status-dot" :class="{ online: appState.avatar.connected }"></span>
          </div>
          
          <!-- 连接/断开控制按钮 -->
          <button 
            class="conn-btn" 
            :class="appState.avatar.connected ? 'btn-disconnect' : 'btn-connect'"
            @click="toggleConnection"
            :disabled="isConnecting"
          >
            {{ btnText }}
          </button>
        </div>

        <!-- 上下文设置区 -->
        <div class="context-settings">
          <div class="setting-row">
            <label>模型</label>
            <select v-model="selectedModel" class="dark-select">
              <option v-for="m in models" :key="m" :value="m">{{ m }}</option>
            </select>
          </div>
          <div class="setting-row">
            <label> 时间</label>
            <div class="date-inputs">
              <input type="date" v-model="dateRange.start" class="dark-input">
              <span>至</span>
              <input type="date" v-model="dateRange.end" class="dark-input">
            </div>
          </div>
          <div class="quick-dates">
            <span @click="setPreset(30)">近30天</span>
            <span @click="setPreset(90)">近3月</span>
            <span @click="setPreset(365)">近1年</span>
          </div>
        </div>

        <!-- 聊天记录区 -->
        <div class="chat-history" ref="chatBox">
          <div v-if="chatMessages.length === 0" class="empty-chat">
            <div class="welcome-icon"></div>
            <p>👋您好，我是您的专属数字财务顾问。</p>
            <p>请点击上方按钮连接我，并设定分析时间段。</p>
          </div>          
          <div 
            v-for="(msg, index) in chatMessages" 
            :key="index" 
            class="message-item"
            :class="msg.role"
          >
            <div class="avatar-icon">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
            <div class="message-bubble">
              <div class="bubble-content">{{ msg.content }}</div>
            </div>
          </div>          
          <!-- Loading 状态 -->
          <div v-if="isLoading" class="message-item ai">
            <div class="avatar-icon">🤖</div>
            <div class="message-bubble typing">
              <span>正在阅读账本并思考...</span>
            </div>
          </div>
        </div>
        <!-- 输入区 -->
        <div class="input-area">
          <div class="quick-prompts">
            <button @click="sendQuery('请分析这段时间的整体收支状况')">📊 整体分析</button>
            <button @click="sendQuery('最大的几笔支出是什么？合理吗？')">💸 查大额支出</button>
            <button @click="sendQuery('目前的利润率如何？有什么建议？')">📈 利润分析</button>
          </div>
          <div class="input-row">
            <textarea 
              v-model="userInput" 
              placeholder="输入您的问题 (Enter 发送)..." 
              @keydown.enter.prevent="handleSend"
              :disabled="!appState.avatar.connected" 
            ></textarea>
            <button 
              @click="handleSend" 
              :disabled="isLoading || !userInput.trim() || !appState.avatar.connected"
            >
              发送
            </button>
          </div>
          <button v-if="isSpeaking" @click="stopSpeaking" class="stop-btn">
            🛑 停止播报
          </button>
        </div>
      </div>

      <!-- 右侧：数字人舞台 -->
      <div class="avatar-stage">
        <!-- 未连接时的遮罩层提示 -->
        <div v-if="!appState.avatar.connected" class="offline-mask">
          <div class="offline-content">
            <span style="font-size: 40px">😴</span>
            <p>AI 顾问离线中</p>
            <p>请点击左侧 "连接 AI 顾问" 唤醒</p>
          </div>
        </div>
        <AvatarRender /> 
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick, computed, onUnmounted } from 'vue'
import AvatarRender from './AvatarRender.vue'
import { appState, appStore } from '../stores/app'
import { generateSSML } from '../utils'

const emit = defineEmits(['close'])
const API_URL = 'http://localhost:8000'

// 状态定义
const selectedModel = ref('Qwen2.5:7b')
const models = ref<string[]>([])
const dateRange = reactive({ start: '', end: '' })
const userInput = ref('')
const isLoading = ref(false)
const isSpeaking = ref(false)
const isConnecting = ref(false) 

// 消息列表
interface ChatMsg { role: 'user' | 'ai'; content: string }
const chatMessages = ref<ChatMsg[]>([])
const chatBox = ref<HTMLElement | null>(null)

// 计算按钮文字
const btnText = computed(() => {
  if (isConnecting.value) return '连接中...'
  return appState.avatar.connected ? '🔌 断开连接' : '🔗 连接 AI 顾问'
})

// === 初始化 ===
onMounted(() => {
  fetchModels()
  setPreset(30)
  // 移除自动连接逻辑
})

// === 连接/断开切换逻辑 ===
async function toggleConnection() {
  if (isConnecting.value) return
  isConnecting.value = true

  try {
    if (appState.avatar.connected) {
      // 执行断开
      appStore.disconnectAvatar()
      addSystemMessage("🔌 已断开与顾问的连接。")
    } else {
      // 执行连接
      await appStore.connectAvatar()
      addSystemMessage("🟢 顾问连接成功！请开始提问。")
    }
  } catch (e) {
    addSystemMessage(`❌ 操作失败: ${e}`)
  } finally {
    isConnecting.value = false
  }
}

async function handleSend() {
  if (!userInput.value.trim() || isLoading.value) return
  if (!appState.avatar.connected) {
    alert("请先点击左上角连接 AI 分析师")
    return
  }
  const text = userInput.value
  userInput.value = ''
  await sendQuery(text)
}

async function sendQuery(text: string) {
  if (!appState.avatar.connected) {
    alert("请先连接 AI 分析师")
    return
  }

  chatMessages.value.push({ role: 'user', content: text })
  scrollToBottom()
  isLoading.value = true
  
  try {
    const res = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model_name: selectedModel.value,
        user_query: text,
        start_date: dateRange.start,
        end_date: dateRange.end
      })
    })

    const data = await res.json()
    const reply = data.reply

    chatMessages.value.push({ role: 'ai', content: reply })
    scrollToBottom()
    speakText(reply)

  } catch (e) {
    chatMessages.value.push({ role: 'ai', content: "⚠️ 分析出错，请检查后端服务。" })
  } finally {
    isLoading.value = false
  }
}

function speakText(text: string) {
  if (!appState.avatar.instance) return
  isSpeaking.value = true
  const ssml = generateSSML(text)
  appState.avatar.instance.speak(ssml, true, true) 
}

function stopSpeaking() {
  if (appState.avatar.instance) {
    const emptySSML = generateSSML(" ")
    appState.avatar.instance.speak(emptySSML, true, true)
    isSpeaking.value = false
  }
}

async function fetchModels() {
  try {
    const res = await fetch(`${API_URL}/api/models`)
    const data = await res.json()
    if (data.models) models.value = data.models
    const targetModel = 'Qwen2.5:7b'    
    // 默认使用Qwen2.5:7b
    if (models.value.includes(targetModel)) {
      selectedModel.value = targetModel
    } 
    else if (models.value.length > 0) {
       // 当Qweb2.5不存在时，选择其他模型
       selectedModel.value = models.value[0]
    }
  } catch(e) { console.error(e) }
}

function setPreset(days: number) {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - days)
  dateRange.end = end.toISOString().split('T')[0]
  dateRange.start = start.toISOString().split('T')[0]
}

function addSystemMessage(text: string) {
  chatMessages.value.push({ role: 'ai', content: text })
  scrollToBottom()
}

function scrollToBottom() {
  nextTick(() => {
    if (chatBox.value) {
      chatBox.value.scrollTop = chatBox.value.scrollHeight
    }
  })
}

function handleClose() {
  stopSpeaking()
  emit('close')
}

onUnmounted(() => stopSpeaking())
</script>

<style scoped>
/* 整体布局 */
.avatar-overlay {
  position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
  background: #000; z-index: 2000; display: flex; flex-direction: column;
}

.close-btn {
  position: absolute; top: 20px; right: 20px; z-index: 2001;
  background: rgba(255, 59, 48, 0.8); color: white; border: none;
  padding: 8px 16px; border-radius: 4px; cursor: pointer;
}

.content-container { display: flex; width: 100%; height: 100%; }

/* 左侧控制面板 */
.control-panel {
  width: 420px;
  background: #1a1a1a;
  border-right: 1px solid #333;
  display: flex; flex-direction: column;
  color: #eee;
  box-shadow: 5px 0 15px rgba(0,0,0,0.5);
  z-index: 10;
}

/* 头部样式优化 */
.panel-header {
  padding: 15px 20px; border-bottom: 1px solid #333;
  display: flex; justify-content: space-between; align-items: center;
  background: #222;
}
.header-title { display: flex; align-items: center; gap: 8px; }
.panel-header h3 { margin: 0; color: #fff; font-size: 18px; font-weight: 600; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #666; }
.status-dot.online { background: #67c23a; box-shadow: 0 0 5px #67c23a; }

/* 连接按钮样式 */
.conn-btn {
  border: none; padding: 6px 15px; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: bold; transition: all 0.2s;
}
.btn-connect { background: #409eff; color: white; }
.btn-connect:hover { background: #66b1ff; }
.btn-disconnect { background: #333; border: 1px solid #555; color: #bbb; }
.btn-disconnect:hover { border-color: #f56c6c; color: #f56c6c; }
.conn-btn:disabled { opacity: 0.6; cursor: wait; }

/* 上下文设置 */
.context-settings { padding: 15px 20px; border-bottom: 1px solid #333; background: #1f1f1f; }
.setting-row { display: flex; align-items: center; margin-bottom: 10px; }
.setting-row label { width: 50px; color: #888; font-size: 13px; }

.dark-select, .dark-input {
  background: #333; border: 1px solid #444; color: white;
  padding: 5px 10px; border-radius: 4px; outline: none; flex: 1;
}
.date-inputs { display: flex; align-items: center; gap: 5px; flex: 1; }
.quick-dates { display: flex; gap: 10px; padding-left: 50px; }
.quick-dates span { font-size: 12px; color: #409eff; cursor: pointer; text-decoration: underline; }

/* 聊天记录区 */
.chat-history {
  flex: 1; overflow-y: auto; padding: 20px;
  display: flex; flex-direction: column; gap: 15px;
  background: #1a1a1a;
}
.empty-chat { 
  text-align: center; 
  color: #fff; 
  margin-top: 60px; 
  font-size: 15px; 
  opacity: 0.9;
}
.welcome-icon { font-size: 40px; margin-bottom: 15px; }

.message-item { display: flex; gap: 10px; max-width: 90%; }
.message-item.user { align-self: flex-end; flex-direction: row-reverse; }
.message-item.ai { align-self: flex-start; }
.avatar-icon { font-size: 24px; margin-top: 5px; }

.message-bubble {
  padding: 10px 15px; border-radius: 12px; font-size: 14px; line-height: 1.5;
  white-space: pre-wrap; word-break: break-all;
}
.user .message-bubble { background: #409eff; color: white; border-top-right-radius: 2px; }
.ai .message-bubble { background: #333; color: #ddd; border-top-left-radius: 2px; border: 1px solid #444; }
.typing { color: #888; font-style: italic; }

/* 输入区 */
.input-area { padding: 15px 20px; background: #222; border-top: 1px solid #333; }
.quick-prompts { display: flex; gap: 8px; margin-bottom: 10px; overflow-x: auto; padding-bottom: 5px; }
.quick-prompts button {
  background: #333; border: 1px solid #444; color: #ccc;
  padding: 4px 10px; border-radius: 15px; cursor: pointer; font-size: 12px; white-space: nowrap;
}
.quick-prompts button:hover { border-color: #409eff; color: #409eff; }

.input-row { display: flex; gap: 10px; }
textarea {
  flex: 1; height: 50px; background: #333; border: 1px solid #444;
  color: white; padding: 10px; border-radius: 6px; resize: none; outline: none;
}
textarea:focus { border-color: #409eff; }
textarea:disabled { opacity: 0.5; cursor: not-allowed; }

.input-row button {
  width: 70px; background: #409eff; color: white; border: none;
  border-radius: 6px; cursor: pointer; font-weight: bold;
}
.input-row button:disabled { background: #555; cursor: not-allowed; }

.stop-btn { width: 100%; margin-top: 10px; background: #f56c6c; color: white; border: none; padding: 5px; border-radius: 4px; cursor: pointer; }

/* 右侧舞台 */
.avatar-stage { flex: 1; height: 100%; background: #000; position: relative; display: flex; flex-direction: column; }
.avatar-stage :deep(.avatar-render), .avatar-stage :deep(.sdk-container) { width: 100% !important; height: 100% !important; flex: 1; }

/* 离线遮罩提示 */
.offline-mask {
  position: absolute; inset: 0; background: rgba(0,0,0,0.7); z-index: 100;
  display: flex; justify-content: center; align-items: center; color: white;
  text-align: center;
}
.offline-content p { margin: 10px 0; color: #aaa; }
</style>