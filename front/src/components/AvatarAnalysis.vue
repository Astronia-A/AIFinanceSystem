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

          <button
            class="conn-btn"
            :class="appState.avatar.connected ? 'btn-disconnect' : 'btn-connect'"
            @click="toggleConnection"
            :disabled="isConnecting"
          >
            {{ btnText }}
          </button>
        </div>

        <!-- === 新增：数字人凭证配置区 (可折叠) === -->
        <div class="auth-settings">
          <div class="setting-toggle" @click="showAuth = !showAuth">
            <span class="toggle-title">🔑 数字人 SDK 配置 (AppID/Secret)</span>
            <span class="toggle-icon">{{ showAuth ? '▼' : '▶' }}</span>
          </div>
          <!-- 展开后的输入框 -->
          <div class="setting-content" v-show="showAuth">
            <input
              type="text"
              v-model="appState.avatar.appId"
              placeholder="请输入 App ID"
              class="dark-input config-input"
              :disabled="appState.avatar.connected"
            >
            <input
              type="password"
              v-model="appState.avatar.appSecret"
              placeholder="请输入 App Secret"
              class="dark-input config-input"
              :disabled="appState.avatar.connected"
            >
            <div v-if="!appState.avatar.connected" class="config-tip">
              * 连接前请务必填写魔珐星云授权信息
            </div>
          </div>
        </div>

        <!-- 上下文设置区 (模型 & 时间) -->
        <div class="context-settings">
          <div class="setting-row">
            <label>🧠 模型</label>
            <select v-model="selectedModel" class="dark-select">
              <option v-for="m in models" :key="m" :value="m">{{ m }}</option>
            </select>
          </div>
          <div class="setting-row">
            <label>📅 时间</label>
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
            <div class="welcome-icon">👋</div>
            <p>您好，我是您的专属数字财务顾问。</p>
            <p>请配置 SDK 密钥并点击上方按钮连接我。</p>
          </div>

          <div
            v-for="(msg, index) in chatMessages"
            :key="index"
            class="message-item"
            :class="msg.role"
          >
            <template v-if="msg.role !== 'system_notice'">
              <div class="avatar-icon">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
              <div class="message-bubble">
                <div class="bubble-content">{{ msg.content }}</div>
              </div>
            </template>
            <div v-else class="system-notice-bubble">
              {{ msg.content }}
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
        <div v-if="!appState.avatar.connected" class="offline-mask">
          <div class="offline-content">
            <span style="font-size: 40px">😴</span>
            <p>AI 分析师正在休息</p>
            <p>请输入 AppID 并点击连接唤醒</p>
          </div>
        </div>
        <AvatarRender />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick, computed, onUnmounted, watch } from 'vue'
import AvatarRender from './AvatarRender.vue'
import { appState, appStore } from '../stores/app'
import { generateSSML } from '../utils'

const emit = defineEmits(['close'])
const API_URL = 'http://localhost:8000'

// 状态定义
const selectedModel = ref('qwen2.5:7b')
const models = ref<string[]>([])
const dateRange = reactive({ start: '', end: '' })
const userInput = ref('')
const isLoading = ref(false)
const isSpeaking = ref(false)
const isConnecting = ref(false)

// 新增：控制配置区域的展开和折叠，如果没有连上默认展开
const showAuth = ref(!appState.avatar.connected)

interface ChatMsg { role: 'user' | 'ai' | 'system_notice'; content: string }
const chatMessages = ref<ChatMsg[]>([])
const chatBox = ref<HTMLElement | null>(null)

const btnText = computed(() => {
  if (isConnecting.value) return '连接中...'
  return appState.avatar.connected ? '🔌 断开连接' : '🔗 连接 AI 分析师'
})

onMounted(() => {
  fetchModels()
  setPreset(30)
})

// === 模型与时间监听 (保留你之前的优秀逻辑) ===
watch(selectedModel, (newVal, oldVal) => {
  if (newVal !== oldVal && oldVal !== '') {
    chatMessages.value.push({
      role: 'system_notice',
      content: `🔄 已切换大脑为 ${newVal}，我们可以继续刚才的话题。`
    })
    scrollToBottom()
  }
})

watch(dateRange, () => {
  if (chatMessages.value.length === 0) return
  chatMessages.value =[]
}, { deep: true })

// === 连接/断开逻辑 (增加校验和自动折叠) ===
async function toggleConnection() {
  if (isConnecting.value) return

  // 校验：如果准备连接，但没有输入 ID 或 Secret
  if (!appState.avatar.connected) {
    if (!appState.avatar.appId.trim() || !appState.avatar.appSecret.trim()) {
      addSystemMessage("⚠️ 请先在上方配置数字人的 App ID 和 App Secret。")
      showAuth.value = true // 强制展开输入框提示用户
      return
    }
  }

  isConnecting.value = true

  try {
    if (appState.avatar.connected) {
      appStore.disconnectAvatar()
      addSystemMessage("🔌 已断开与数字人的连接。")
    } else {
      await appStore.connectAvatar()
      addSystemMessage("🟢 数字人连接成功！请开始提问。")
      showAuth.value = false // 连接成功后，自动折叠配置区，节省空间
    }
  } catch (e) {
    addSystemMessage(`❌ 连接失败，请检查密钥是否正确: ${e}`)
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
  if (!appState.avatar.connected) return

  chatMessages.value.push({ role: 'user', content: text })
  scrollToBottom()
  isLoading.value = true

  try {
    const historyPayload = chatMessages.value.slice(0, -1).map(msg => ({
      role: msg.role === 'system_notice' ? 'ai' : msg.role, // 过滤掉系统通知给后端
      content: msg.content
    }))

    const res = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model_name: selectedModel.value,
        user_query: text,
        start_date: dateRange.start,
        end_date: dateRange.end,
        history: historyPayload
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

    const targetModel = 'qwen2.5:7b'
    if (models.value.includes(targetModel)) {
      selectedModel.value = targetModel
    } else if (models.value.length > 0) {
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
  chatMessages.value.push({ role: 'system_notice', content: text })
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
/* 整体布局保持不变 */
.avatar-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: #000; z-index: 2000; display: flex; flex-direction: column; }
.close-btn { position: absolute; top: 20px; right: 20px; z-index: 2001; background: rgba(255, 59, 48, 0.8); color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
.content-container { display: flex; width: 100%; height: 100%; }

/* 左侧控制面板 */
.control-panel { width: 420px; background: #1a1a1a; border-right: 1px solid #333; display: flex; flex-direction: column; color: #eee; box-shadow: 5px 0 15px rgba(0,0,0,0.5); z-index: 10; }
.panel-header { padding: 15px 20px; border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center; background: #222; }
.header-title { display: flex; align-items: center; gap: 8px; }
.panel-header h3 { margin: 0; color: #fff; font-size: 18px; font-weight: 600; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #666; }
.status-dot.online { background: #67c23a; box-shadow: 0 0 5px #67c23a; }

.conn-btn { border: none; padding: 6px 15px; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: bold; transition: all 0.2s; }
.btn-connect { background: #409eff; color: white; }
.btn-connect:hover { background: #66b1ff; }
.btn-disconnect { background: #333; border: 1px solid #555; color: #bbb; }
.btn-disconnect:hover { border-color: #f56c6c; color: #f56c6c; }
.conn-btn:disabled { opacity: 0.6; cursor: wait; }

/* === 新增：SDK 授权配置区样式 === */
.auth-settings {
  background: #1f1f1f;
  border-bottom: 1px solid #333;
}
.setting-toggle {
  padding: 10px 20px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #252525;
  user-select: none;
}
.setting-toggle:hover { background: #2a2a2a; }
.toggle-title { font-size: 13px; color: #aaa; font-weight: bold; }
.toggle-icon { font-size: 10px; color: #888; }
.setting-content { padding: 15px 20px; display: flex; flex-direction: column; gap: 10px; }
.config-input { width: 100%; box-sizing: border-box; }
.config-input:disabled { opacity: 0.5; cursor: not-allowed; }
.config-tip { font-size: 12px; color: #f56c6c; }

/* 上下文设置 */
.context-settings { padding: 15px 20px; border-bottom: 1px solid #333; background: #1f1f1f; }
.setting-row { display: flex; align-items: center; margin-bottom: 10px; }
.setting-row label { width: 50px; color: #888; font-size: 13px; }

.dark-select, .dark-input { background: #333; border: 1px solid #444; color: white; padding: 5px 10px; border-radius: 4px; outline: none; flex: 1; }
.date-inputs { display: flex; align-items: center; gap: 5px; flex: 1; }
.quick-dates { display: flex; gap: 10px; padding-left: 50px; }
.quick-dates span { font-size: 12px; color: #409eff; cursor: pointer; text-decoration: underline; }

/* 聊天记录区 */
.chat-history { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; background: #1a1a1a; }
.empty-chat { text-align: center; color: #fff; margin-top: 60px; font-size: 15px; opacity: 0.9; }
.welcome-icon { font-size: 40px; margin-bottom: 15px; }

.message-item { display: flex; gap: 10px; max-width: 90%; }
.message-item.user { align-self: flex-end; flex-direction: row-reverse; }
.message-item.ai { align-self: flex-start; }
.avatar-icon { font-size: 24px; margin-top: 5px; }

.message-bubble { padding: 10px 15px; border-radius: 12px; font-size: 14px; line-height: 1.5; white-space: pre-wrap; word-break: break-all; }
.user .message-bubble { background: #409eff; color: white; border-top-right-radius: 2px; }
.ai .message-bubble { background: #333; color: #ddd; border-top-left-radius: 2px; border: 1px solid #444; }
.typing { color: #888; font-style: italic; }

.system-notice-bubble { width: 100%; text-align: center; font-size: 12px; color: #888; margin: 10px 0; background: rgba(255, 255, 255, 0.05); padding: 4px; border-radius: 4px; }

/* 输入区 */
.input-area { padding: 15px 20px; background: #222; border-top: 1px solid #333; }
.quick-prompts { display: flex; gap: 8px; margin-bottom: 10px; overflow-x: auto; padding-bottom: 5px; }
.quick-prompts button { background: #333; border: 1px solid #444; color: #ccc; padding: 4px 10px; border-radius: 15px; cursor: pointer; font-size: 12px; white-space: nowrap; }
.quick-prompts button:hover { border-color: #409eff; color: #409eff; }

.input-row { display: flex; gap: 10px; }
textarea { flex: 1; height: 50px; background: #333; border: 1px solid #444; color: white; padding: 10px; border-radius: 6px; resize: none; outline: none; }
textarea:focus { border-color: #409eff; }
textarea:disabled { opacity: 0.5; cursor: not-allowed; }

.input-row button { width: 70px; background: #409eff; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
.input-row button:disabled { background: #555; cursor: not-allowed; }

.stop-btn { width: 100%; margin-top: 10px; background: #f56c6c; color: white; border: none; padding: 5px; border-radius: 4px; cursor: pointer; }

/* 右侧舞台 */
.avatar-stage { flex: 1; height: 100%; background: #000; position: relative; display: flex; flex-direction: column; }
.avatar-stage :deep(.avatar-render), .avatar-stage :deep(.sdk-container) { width: 100% !important; height: 100% !important; flex: 1; }

.offline-mask { position: absolute; inset: 0; background: rgba(0,0,0,0.7); z-index: 100; display: flex; justify-content: center; align-items: center; color: white; text-align: center; }
.offline-content p { margin: 10px 0; color: #aaa; }
</style>