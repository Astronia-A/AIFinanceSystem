<!-- src/components/ConfigPanel.vue -->
<template>
  <div class="config-panel">
    
    <!-- 虚拟人配置 (保持不变) -->
    <section class="config-section">
      <h3 class="section-title">虚拟人 SDK 配置</h3>
      <div class="form-group">
        <label>应用 APP ID</label>
        <input v-model="appState.avatar.appId" type="text" placeholder="请输入 APP ID" />
      </div>
      <div class="form-group">
        <label>应用 APP Secret</label>
        <input v-model="appState.avatar.appSecret" type="text" placeholder="请输入 APP Secret" />
      </div>
    </section>

    <!-- ASR配置 (保持不变) -->
    <section class="config-section">
      <h3 class="section-title">语音识别配置</h3>
      <div class="form-group">
        <label>ASR 服务商</label>
        <select v-model="appState.asr.provider"><option value="tx">腾讯云</option></select>
      </div>
      <div class="form-group">
        <label>ASR App ID</label>
        <input v-model="appState.asr.appId" type="text" />
      </div>
      <div class="form-group">
        <label>ASR Secret ID</label>
        <input v-model="appState.asr.secretId" type="text" />
      </div>
      <div class="form-group">
        <label>ASR Secret Key</label>
        <input v-model="appState.asr.secretKey" type="text" />
      </div>
    </section>

    <!-- LLM配置 (核心修改区域) -->
    <section class="config-section">
      <h3 class="section-title">财务大脑配置 (Ollama)</h3>
      
      <div class="form-group">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <label>选择分析模型</label>
          <!-- 添加一个小刷新按钮，允许用户手动重新获取模型列表 -->
          <button @click="fetchModels" style="font-size: 12px; padding: 2px 6px;">↻ 刷新列表</button>
        </div>
        
        <select v-model="appState.llm.model">
          <!-- 这里的 options 改为动态生成的 availableModels -->
          <option 
            v-for="model in availableModels" 
            :key="model" 
            :value="model"
          >
            {{ model }}
          </option>
        </select>
      </div>
      
      <!-- API Key 输入框已被移除，因为本地运行不需要 Key -->
    </section>

    <!-- 控制按钮和消息交互 (保持不变) -->
    <section class="control-section">
      <!-- ... 原有代码 ... -->
       <div class="button-group">
        <button 
          @click="handleConnect" 
          :disabled="isConnecting || appState.avatar.connected"
          class="btn btn-primary"
        >
          {{ isConnecting ? '连接中...' : appState.avatar.connected ? '已连接' : '连接' }}
        </button>
        <button 
          @click="handleDisconnect" 
          :disabled="!appState.avatar.connected"
          class="btn btn-secondary"
        >
          断开
        </button>
      </div>
    </section>
    
    <section class="message-section">
       <!-- ... 原有代码保持不变 ... -->
       <div class="form-group">
        <label>输入消息</label>
        <textarea 
          v-model="appState.ui.text" 
          rows="4" 
          placeholder="请输入您的消息..."
        />
      </div>
      <div class="button-group">
        <button 
          @click="handleVoiceInput" 
          :disabled="!appState.avatar.connected || appState.asr.isListening"
          class="btn btn-voice"
        >
          {{ appState.asr.isListening ? '正在听...' : '语音输入' }}
        </button>
        <button 
          @click="handleSendMessage" 
          :disabled="!appState.avatar.connected || !appState.ui.text.trim() || isSending"
          class="btn btn-primary"
        >
          {{ isSending ? '发送中...' : '发送' }}
        </button>
      </div>
    </section>

  </div>
</template>

<script setup lang="ts">
import { inject, ref, computed, onMounted } from 'vue' // <--- 引入 onMounted
import { useAsr } from '../composables/useAsr'
// 移除: import { SUPPORTED_LLM_MODELS } from '../constants' 
import type { AppState, AppStore } from '../types'

const appState = inject<AppState>('appState')!
const appStore = inject<AppStore>('appStore')!

const isConnecting = ref(false)
const isSending = ref(false)

// 新增: 动态模型列表
const availableModels = ref<string[]>(['llama3.2']) // 默认值，防止空列表

// ASR Hook (保持不变)
const asrConfig = computed(() => ({
  provider: 'tx' as const,
  appId: appState.asr.appId,
  secretId: appState.asr.secretId,
  secretKey: appState.asr.secretKey
}))
const { stop: stopAsr } = useAsr(asrConfig.value)

// 新增: 获取模型列表的函数
async function fetchModels() {
  try {
    const res = await fetch('http://localhost:8000/api/models');
    if(res.ok) {
      const data = await res.json();
      if (data.models && data.models.length > 0) {
        availableModels.value = data.models;
        // 如果当前选中的模型不在列表里，默认选第一个
        if (!availableModels.value.includes(appState.llm.model)) {
          appState.llm.model = availableModels.value[0];
        }
      }
    }
  } catch (e) {
    console.error("无法连接后端获取模型列表，请确保 python main.py 已启动", e);
  }
}

// 组件加载时自动获取一次模型
onMounted(() => {
  fetchModels();
});

// 事件处理函数 (保持不变)
async function handleConnect() {
  if (isConnecting.value) return
  isConnecting.value = true
  try {
    await appStore.connectAvatar()
  } catch (error) {
    console.error('连接失败:', error)
    alert('连接失败，请检查配置信息')
  } finally {
    isConnecting.value = false
  }
}

function handleDisconnect() {
  appStore.disconnectAvatar()
}

function handleVoiceInput() {
   // ... (原代码保持不变) ...
   // 篇幅原因省略，请直接使用你原来的逻辑，不需要改动
   if (appState.asr.isListening) {
    stopAsr()
    appStore.stopVoiceInput()
    return
  }
  
  const { appId, secretId, secretKey } = appState.asr
  if (!appId || !secretId || !secretKey) {
    alert('请先配置ASR信息')
    return
  }
  
  const { start: startAsrWithConfig, stop: stopAsrWithConfig } = useAsr({
    provider: 'tx',
    appId: appState.asr.appId,
    secretId: appState.asr.secretId,
    secretKey: appState.asr.secretKey
  })
  
  appStore.startVoiceInput({
    onFinished: (text: string) => {
      appState.ui.text = text
      stopAsrWithConfig()
      appStore.stopVoiceInput()
    },
    onError: (error: any) => {
      console.error('语音识别错误:', error)
      stopAsrWithConfig()
      appStore.stopVoiceInput()
    }
  })
  
  startAsrWithConfig({
    onFinished: (text: string) => {
      appState.ui.text = text
      appStore.stopVoiceInput()
    },
    onError: (error: any) => {
      console.error('语音识别错误:', error)
      appStore.stopVoiceInput()
    }
  })
}

async function handleSendMessage() {
  if (isSending.value || !appState.ui.text.trim()) return
  isSending.value = true
  try {
    await appStore.sendMessage()
  } catch (error) {
    console.error('发送消息失败:', error)
    alert('发送消息失败')
  } finally {
    isSending.value = false
  }
}
</script>

<style scoped>
/* 保持原来的样式 */
.config-panel { width: 420px; max-height: 100vh; overflow-y: auto; padding: 24px; background: #ffffff; border-left: 1px solid #e0e0e0; display: flex; flex-direction: column; gap: 24px; }
.config-section, .control-section, .message-section { border: 1px solid #e8e8e8; border-radius: 8px; padding: 16px; background: #fafafa; }
.section-title { margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: #333; border-bottom: 1px solid #e0e0e0; padding-bottom: 8px; }
.form-group { margin-bottom: 16px; }
label { display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: #555; }
input, select, textarea { width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; transition: border-color 0.2s; }
input:focus, select:focus, textarea:focus { outline: none; border-color: #007bff; box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.1); }
textarea { resize: vertical; min-height: 80px; }
.button-group { display: flex; gap: 12px; justify-content: flex-end; }
.btn { padding: 10px 20px; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s; min-width: 80px; }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-primary { background: #007bff; color: white; }
.btn-primary:hover:not(:disabled) { background: #0056b3; }
.btn-secondary { background: #6c757d; color: white; }
.btn-secondary:hover:not(:disabled) { background: #545b62; }
.btn-voice { background: #28a745; color: white; }
.btn-voice:hover:not(:disabled) { background: #1e7e34; }
</style>