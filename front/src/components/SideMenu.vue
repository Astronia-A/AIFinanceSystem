<!-- src/components/SideMenu.vue -->
<template>
  <div class="side-menu">
    <!-- 1. 欢迎组件区域 -->
    <div class="user-profile">
      <div class="avatar-circle">👤</div>
      <div class="user-info">
        <h3>管理员</h3>
        <span class="status-dot"></span> 在线
      </div>
    </div>

    <!-- 2. 导航菜单 -->
    <nav class="nav-list">
      <div 
        v-for="item in menuItems" 
        :key="item.id"
        class="nav-item"
        :class="{ active: activeTab === item.id }"
        @click="handleClick(item.id)"
      >
        <span class="icon">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </div>
    </nav>
    
    <div class="footer">
      <p>© 2024 智财云</p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  activeTab: string
}>()

const emit = defineEmits(['update:activeTab', 'trigger-ai'])

const menuItems = [
  { id: 'dashboard', label: '收支总览', icon: '' },
  { id: 'records', label: '数据录入', icon: '' },
  { id: 'knowledge', label: '知识库录入', icon: '' },
  { id: 'ai-analysis', label: 'AI 深度分析', icon: '' } 
]

function handleClick(id: string) {
  if (id === 'ai-analysis') {
    // 如果点击的是 AI，不切换页面，而是触发特殊事件
    emit('trigger-ai')
  } else {
    // 否则切换主区域视图
    emit('update:activeTab', id)
  }
}
</script>

<style scoped>
.side-menu {
  width: 240px;
  height: 100vh;
  background: #1e293b; 
  color: white;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 10px rgba(0,0,0,0.1);
}

.user-profile {
  padding: 30px 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  border-bottom: 1px solid #334155;
  background: #868686;
}

.avatar-circle {
  width: 50px; height: 50px;
  background: #3b82f6;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 24px;
}

.user-info h3 { margin: 0; font-size: 16px; }
.status-dot {
  display: inline-block; width: 8px; height: 8px;
  background: #22c55e; border-radius: 50%; margin-right: 5px;
}

.nav-list { flex: 1; padding: 20px 0; }

.nav-item {
  padding: 15px 25px;
  cursor: pointer;
  display: flex; align-items: center; gap: 12px;
  transition: all 0.3s;
  font-size: 15px;
  color: #94a3b8;
}

.nav-item:hover { background: #334155; color: white; }
.nav-item.active {
  background: #2563eb;
  color: white;
  border-right: 4px solid #60a5fa;
}

.footer { padding: 20px; font-size: 12px; color: #64748b; text-align: center; }
</style>