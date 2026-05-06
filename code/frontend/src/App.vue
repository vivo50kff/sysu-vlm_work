<template>
  <div class="chat-container">
    <!-- 头部 -->
    <div class="chat-header">
      <h1>🤖 VLM图文问答助手</h1>
      <p>基于视觉语言模型的智能问答系统 - 支持图片理解与多轮对话</p>
    </div>

    <!-- 消息列表 -->
    <div class="chat-messages" ref="messagesContainer">
      <!-- 消息 -->
      <div 
        v-for="(msg, index) in messages" 
        :key="index" 
        :class="['message', msg.role]"
      >
        <div class="message-avatar">
          <span v-if="msg.role === 'user'">👤</span>
          <span v-else>🤖</span>
        </div>
        <div class="message-content">
          <!-- 图片 -->
          <img 
            v-if="msg.image" 
            :src="msg.image" 
            class="message-image"
            @click="previewImage(msg.image)"
          />
          <!-- 文本内容 -->
          <div v-html="renderMarkdown(msg.content)"></div>
        </div>
      </div>

      <!-- 加载指示器 -->
      <div v-if="isLoading" class="loading-indicator">
        <div class="typing-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <span>正在思考中...</span>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="chat-input-area">
      <!-- 图片预览 -->
      <div v-if="selectedImage" class="image-preview">
        <img :src="selectedImage" alt="预览图片" />
        <button class="remove-image" @click="removeImage">✕</button>
      </div>

      <!-- 输入行 -->
      <div class="input-row">
        <!-- 图片上传按钮 -->
        <el-button 
          type="primary" 
          :icon="Picture" 
          circle
          @click="triggerImageUpload"
          title="上传图片"
        />
        <input 
          type="file" 
          ref="imageInput" 
          accept="image/*" 
          style="display: none"
          @change="handleImageSelect"
        />

        <!-- 文本输入 -->
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="2"
          placeholder="输入您的问题... (支持上传图片进行图文问答)"
          resize="none"
          @keydown.enter.exact.prevent="sendMessage"
        />

        <!-- 发送按钮 -->
        <el-button 
          type="success" 
          :icon="Promotion" 
          circle
          @click="sendMessage"
          :loading="isLoading"
          :disabled="!inputMessage.trim() && !selectedImage"
          title="发送消息"
        />

        <!-- 清空按钮 -->
        <el-button 
          type="danger" 
          :icon="Delete" 
          circle
          @click="clearChat"
          title="清空对话"
        />
      </div>
    </div>

    <!-- 图片预览对话框 -->
    <el-dialog 
      v-model="showImagePreview" 
      title="图片预览"
      width="60%"
    >
      <img :src="previewImageUrl" style="width: 100%;" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { Picture, Promotion, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { chat, healthCheck } from './api.js'

// 状态
const messages = ref([])
const inputMessage = ref('')
const selectedImage = ref(null)
const selectedImageBase64 = ref(null)
const isLoading = ref(false)
const conversationId = ref(null)

// DOM引用
const messagesContainer = ref(null)
const imageInput = ref(null)

// 图片预览
const showImagePreview = ref(false)
const previewImageUrl = ref(null)

// 配置marked
marked.setOptions({
  breaks: true,
  gfm: true
})

/**
 * 渲染Markdown
 */
function renderMarkdown(text) {
  return marked.parse(text)
}

/**
 * 触发图片上传
 */
function triggerImageUpload() {
  imageInput.value.click()
}

/**
 * 处理图片选择
 */
function handleImageSelect(event) {
  const file = event.target.files[0]
  if (!file) return

  // 检查文件类型
  if (!file.type.startsWith('image/')) {
    ElMessage.error('请选择图片文件')
    return
  }

  // 检查文件大小 (最大5MB)
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过5MB')
    return
  }

  // 读取图片
  const reader = new FileReader()
  reader.onload = (e) => {
    selectedImage.value = e.target.result
    selectedImageBase64.value = e.target.result.split(',')[1]
  }
  reader.readAsDataURL(file)

  // 清空input
  event.target.value = ''
}

/**
 * 移除图片
 */
function removeImage() {
  selectedImage.value = null
  selectedImageBase64.value = null
}

/**
 * 发送消息
 */
async function sendMessage() {
  const message = inputMessage.value.trim()
  
  if (!message && !selectedImage.value) {
    ElMessage.warning('请输入消息或上传图片')
    return
  }

  // 添加用户消息到列表
  messages.value.push({
    role: 'user',
    content: message,
    image: selectedImage.value
  })

  // 清空输入
  inputMessage.value = ''
  const imageToSend = selectedImageBase64.value
  removeImage()

  // 滚动到底部
  scrollToBottom()

  // 设置加载状态
  isLoading.value = true

  try {
    // 构建历史消息
    const history = messages.value.slice(0, -1).map(msg => ({
      role: msg.role,
      content: msg.content
    }))

    // 调用API
    const response = await chat(
      message || '请描述这张图片',
      imageToSend,
      conversationId.value,
      history.length > 0 ? history : null
    )

    // 保存对话ID
    conversationId.value = response.conversation_id

    // 添加助手回复
    messages.value.push({
      role: 'assistant',
      content: response.response
    })

    scrollToBottom()
  } catch (error) {
    console.error('发送消息失败:', error)
    ElMessage.error('发送消息失败: ' + (error.response?.data?.detail || error.message))
    
    // 移除用户消息
    messages.value.pop()
  } finally {
    isLoading.value = false
  }
}

/**
 * 清空对话
 */
function clearChat() {
  messages.value = []
  conversationId.value = null
  removeImage()
  ElMessage.success('对话已清空')
}

/**
 * 滚动到底部
 */
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

/**
 * 预览图片
 */
function previewImage(imageUrl) {
  previewImageUrl.value = imageUrl
  showImagePreview.value = true
}

/**
 * 初始化
 */
onMounted(async () => {
  try {
    const health = await healthCheck()
    console.log('API健康检查:', health)
    ElMessage.success(`已连接到 ${health.api_provider} (${health.model_name})`)
  } catch (error) {
    console.error('API连接失败:', error)
    ElMessage.warning('后端API未连接，请确保后端服务已启动')
  }
})
</script>

<style scoped>
/* 组件特定样式已在style.css中定义 */
</style>