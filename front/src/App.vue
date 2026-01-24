<!-- src/App.vue -->
<template>
  <div class="app-layout">
    <!-- 左侧：导航栏 -->
    <SideMenu 
      :active-tab="currentView" 
      @update:activeTab="currentView = $event"
      @trigger-ai="showAvatar = true"
    />

    <!-- 右侧：动态内容区域 -->
    <main class="main-content">
      <!-- 顶部标题栏 (可选) -->
      <header class="top-bar">
        <h2>{{ pageTitle }}</h2>
        <div class="date-display">{{ currentDate }}</div>
      </header>

      <!-- 核心：动态组件切换 -->
      <!-- component :is 会根据 currentView 的值自动加载对应组件 -->
      <div class="content-wrapper">
        <Transition name="fade" mode="out-in">
          <component :is="currentComponent" />
        </Transition>
      </div>
    </main>

    <!-- 浮层：数字人分析 (只有点击 AI 分析时才显示) -->
    <Transition name="slide-up">
      <AvatarAnalysis 
        v-if="showAvatar" 
        @close="showAvatar = false" 
      />
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, provide } from 'vue'
import dayjs from 'dayjs' // 如果没有装 dayjs，可以用 new Date().toLocaleDateString()

// 引入所有组件
import SideMenu from './components/SideMenu.vue'
import Dashboard from './components/Dashboard.vue'
import RecordManager from './components/RecordManager.vue'
import KnowledgeBase from './components/KnowledgeBase.vue'
import AvatarAnalysis from './components/AvatarAnalysis.vue'

// 引入状态管理 (保持你原有的逻辑)
import { appState, appStore } from './stores/app'
provide('appState', appState)
provide('appStore', appStore)

// 状态控制
const currentView = ref('dashboard') // 默认显示 dashboard
const showAvatar = ref(false)
const currentDate = ref(dayjs().format('YYYY年MM月DD日'))

// 计算属性：根据当前视图 ID 返回对应的组件对象
const currentComponent = computed(() => {
  switch (currentView.value) {
    case 'dashboard': return Dashboard
    case 'records': return RecordManager
    case 'knowledge': return KnowledgeBase
    default: return Dashboard
  }
})

// 计算属性：动态标题
const pageTitle = computed(() => {
  const map: Record<string, string> = {
    dashboard: '📊 收支总览',
    records: '📝 数据录入与管理',
    knowledge: '📚 财务知识库管理'
  }
  return map[currentView.value] || '系统'
})
</script>

<style>
/* 全局重置 */
body { margin: 0; padding: 0; font-family: 'PingFang SC', sans-serif; background: #f1f5f9; }

.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.main-content {
  flex: 1; /* 占满剩余空间 */
  display: flex;
  flex-direction: column;
  background-color: #f1f5f9;
}

.top-bar {
  background: white;
  padding: 0 30px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.top-bar h2 { font-size: 18px; color: #334155; margin: 0; }
.date-display { color: #64748b; font-size: 14px; }

.content-wrapper {
  flex: 1;
  padding: 24px;
  overflow-y: auto; /* 内容过多时只在右侧滚动 */
}

/* 页面切换动画 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* 数字人弹窗动画 */
.slide-up-enter-active, .slide-up-leave-active { transition: transform 0.3s ease; }
.slide-up-enter-from, .slide-up-leave-to { transform: translateY(100%); }
</style>