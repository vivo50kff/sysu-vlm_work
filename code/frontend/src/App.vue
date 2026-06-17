<template>
  <div class="app-layout">
    <!-- ========== 侧边栏 ========== -->
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <span class="sidebar-title" v-show="!sidebarCollapsed">📋 对话历史</span>
        <el-button
          :icon="sidebarCollapsed ? ArrowRight : ArrowLeft"
          circle size="small" class="toggle-btn"
          @click="sidebarCollapsed = !sidebarCollapsed"
        />
      </div>

      <div v-show="!sidebarCollapsed" class="sidebar-body">
        <el-button type="primary" class="sidebar-btn" @click="newConversation">
          <el-icon><Plus /></el-icon> 新建对话
        </el-button>

        <!-- 对话列表 -->
        <div class="conv-list" v-if="conversations.length > 0">
          <div
            v-for="conv in conversations" :key="conv.conversation_id"
            :class="['conv-item', { active: conv.conversation_id === conversationId }]"
            @click="switchConversation(conv.conversation_id)"
          >
            <div class="conv-preview">{{ conv.preview || '(新对话)' }}</div>
            <div class="conv-meta">
              <span class="conv-count">{{ conv.message_count }} 条消息</span>
              <el-button type="danger" size="small" circle :icon="Delete"
                @click.stop="deleteConv(conv.conversation_id)" />
            </div>
          </div>
        </div>
        <div v-else class="sidebar-empty">
          <el-icon :size="32"><ChatDotRound /></el-icon>
          <p>暂无对话记录</p>
          <p class="hint">发送第一条消息开始</p>
        </div>

        <!-- 底部功能区 -->
        <div class="sidebar-tools">
          <div class="tools-title">⚙️ 功能</div>
          <el-button class="sidebar-btn" @click="showEvalDialog = true">
            📊 批量评测
          </el-button>
          <el-button class="sidebar-btn" @click="showCaseReport">
            📋 案例分析报告
          </el-button>
          <el-button class="sidebar-btn" @click="exportCurrentConv">
            💾 导出当前对话
          </el-button>
          <el-button class="sidebar-btn" @click="showPromptsDialog = true">
            📝 提示词模板
          </el-button>
        </div>
      </div>
    </aside>

    <!-- ========== 主聊天区 ========== -->
    <main class="main-area">
      <!-- 头部 -->
      <header class="top-bar">
        <div class="top-bar-left">
          <span class="logo">🤖</span>
          <div>
            <h1 class="app-title">VLM 图文问答助手</h1>
            <p class="app-subtitle">基于视觉语言模型的智能问答系统</p>
          </div>
        </div>
        <div class="top-bar-right">
          <span class="mode-label">当前模式</span>
          <el-select v-model="currentImageType" size="small" class="mode-select" @change="onImageTypeChange">
            <el-option v-for="m in imageTypeOptions" :key="m.value" :label="m.label" :value="m.value" />
          </el-select>
          <el-tag :type="currentModeTagType" size="small" effect="plain">{{ currentImageTypeLabel }}</el-tag>
        </div>
      </header>

      <!-- 消息区 -->
      <div class="msg-area" ref="messagesContainer">
        <!-- 欢迎页 -->
        <div v-if="messages.length === 0" class="welcome">
          <div class="welcome-bot">🤖</div>
          <h2>欢迎使用 VLM 图文问答助手</h2>
          <p>上传图片并输入问题，AI 将为您解读图片内容</p>
          <div class="welcome-tags">
            <el-tag v-for="m in imageTypeOptions" :key="m.value" size="default" :type="m.tagType" effect="plain">
              {{ m.label }}
            </el-tag>
          </div>
        </div>

        <!-- 消息气泡 -->
        <div v-for="(msg, index) in messages" :key="index" :class="['msg-row', msg.role]">
          <div class="msg-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
          <div class="msg-bubble">
            <img v-if="msg.image" :src="msg.image" class="msg-img" @click="previewImage(msg.image)" />
            <div class="msg-text" v-html="renderMarkdown(msg.content)"></div>
            <div class="msg-tools">
              <el-button size="small" text @click="copyText(msg.content)">📋 复制</el-button>
              <el-button v-if="msg.role === 'assistant'" size="small" text
                @click="addToCases(msg, index)">📝 收录案例</el-button>
            </div>
          </div>
        </div>

        <!-- 加载动画 -->
        <div v-if="isLoading" class="loading">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="loading-text">AI 正在思考...</span>
        </div>
      </div>

      <!-- 输入区 -->
      <footer class="input-area">
        <!-- 图片预览 -->
        <div v-if="selectedImage" class="img-preview">
          <img :src="selectedImage" />
          <el-button :icon="Close" circle size="small" class="preview-close" @click="removeImage" />
        </div>

        <div class="input-row">
          <el-tooltip content="上传图片">
            <el-button :icon="Picture" circle class="input-btn upload-btn" @click="triggerImageUpload" />
          </el-tooltip>
          <input type="file" ref="imageInput" accept="image/*" hidden @change="handleImageSelect" />

          <el-input v-model="inputMessage" type="textarea" :rows="2"
            :placeholder="inputPlaceholder" resize="none"
            class="msg-input"
            @keydown.enter.exact.prevent="sendMessage" />

          <el-tooltip content="发送 (Enter)">
            <el-button type="primary" :icon="Promotion" circle
              class="input-btn send-btn"
              :loading="isLoading"
              :disabled="!inputMessage.trim() && !selectedImage"
              @click="sendMessage" />
          </el-tooltip>

          <el-tooltip content="清空对话">
            <el-button :icon="Delete" circle class="input-btn clear-btn" @click="clearChat" />
          </el-tooltip>
        </div>
      </footer>
    </main>

    <!-- ========== 对话框 ========== -->
    <el-dialog v-model="showImagePreview" title="图片预览" width="60%">
      <img :src="previewImageUrl" style="width:100%;border-radius:8px" />
    </el-dialog>

    <!-- 评测对话框 -->
    <el-dialog v-model="showEvalDialog" title="📊 批量评测" width="520px" @open="onEvalDialogOpen">
      <el-form label-width="90px" label-position="right">
        <el-form-item label="数据集">
          <el-select v-model="evalConfig.dataset_type" class="form-full" @change="onDatasetChange">
            <el-option v-for="ds in datasetOptions" :key="ds.value"
              :label="ds.label" :value="ds.value" :disabled="ds.disabled" />
          </el-select>
          <div v-if="selectedDatasetInfo" class="ds-info">
            <p>{{ selectedDatasetInfo.description }}</p>
            <el-tag v-if="selectedDatasetInfo.note"
              :type="selectedDatasetInfo.available ? 'warning' : 'danger'" size="small">
              {{ selectedDatasetInfo.note }}
            </el-tag>
            <div v-if="!selectedDatasetInfo.available && selectedDatasetInfo.download_url" class="ds-dl">
              📥 <a :href="selectedDatasetInfo.download_url" target="_blank">下载数据集</a>
              <span class="ds-size">({{ selectedDatasetInfo.download_size }})</span>
            </div>
          </div>
        </el-form-item>

        <el-form-item label="图像类型" v-if="evalConfig.dataset_type === 'builtin'">
          <el-select v-model="evalConfig.image_type" class="form-full">
            <el-option label="🌄 自然场景" value="natural_scene" />
            <el-option label="📄 文档" value="document" />
          </el-select>
        </el-form-item>

        <el-form-item label="样本数量">
          <el-input-number v-model="evalConfig.max_samples" :min="1" :max="100" class="form-full" />
        </el-form-item>

        <el-form-item label="数据集路径" v-if="needsPath">
          <el-input v-model="evalConfig.dataset_path" :placeholder="pathPlaceholder"
            :disabled="selectedDatasetInfo?.available" class="form-full" />
          <div v-if="selectedDatasetInfo?.available && selectedDatasetInfo?.path" class="ds-found">
            ✅ 已自动检测到: {{ selectedDatasetInfo.path }}
          </div>
        </el-form-item>
      </el-form>

      <!-- 评测结果 -->
      <div v-if="evalResult" class="eval-output">
        <el-divider />
        <h4>📈 评测结果</h4>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="数据集">{{ evalResult.dataset_name }}</el-descriptions-item>
          <el-descriptions-item label="样本总数">{{ evalResult.total_samples }}</el-descriptions-item>
          <el-descriptions-item label="正确数">{{ evalResult.correct_count }}</el-descriptions-item>
          <el-descriptions-item label="包含匹配率">
            {{ (evalResult.contains_match_rate * 100).toFixed(1) }}%
          </el-descriptions-item>
          <el-descriptions-item label="精确匹配率">
            {{ (evalResult.exact_match_rate * 100).toFixed(1) }}%
          </el-descriptions-item>
          <el-descriptions-item label="综合准确率">
            <el-tag :type="evalResult.accuracy > 0.6 ? 'success' : 'warning'" size="small">
              {{ (evalResult.accuracy * 100).toFixed(1) }}%
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="平均耗时">{{ evalResult.avg_response_time?.toFixed(2) }}s</el-descriptions-item>
        </el-descriptions>

        <div v-if="evalResult.error_analysis?.error_types" class="eval-errors">
          <strong>错误类型分布:</strong>
          <el-tag v-for="(count, type) in evalResult.error_analysis.error_types" :key="type"
            size="small" type="danger" class="error-tag">{{ type }}: {{ count }}</el-tag>
        </div>

        <div v-if="evalResult.success_cases?.length" class="case-block success">
          <strong>✅ 成功案例</strong>
          <div v-for="(c, i) in evalResult.success_cases.slice(0, 3)" :key="i" class="case-card">
            <div><b>Q:</b> {{ c.question }}</div>
            <div><b>A:</b> {{ c.prediction?.substring(0, 100) }}</div>
          </div>
        </div>

        <div v-if="evalResult.failure_cases?.length" class="case-block failure">
          <strong>❌ 失败案例</strong>
          <div v-for="(c, i) in evalResult.failure_cases.slice(0, 3)" :key="i" class="case-card">
            <div><b>Q:</b> {{ c.question }}</div>
            <div><b>GT:</b> {{ c.ground_truth }}</div>
            <div><b>Pred:</b> {{ c.prediction?.substring(0, 100) }}</div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="showEvalDialog = false">关闭</el-button>
        <el-button type="primary" :loading="evalRunning" :disabled="!canStartEval" @click="runBatchEval">
          {{ evalRunning ? '评测中...' : '开始评测' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 案例报告对话框 -->
    <el-dialog v-model="showCasesDialog" title="📋 案例分析报告" width="700px">
      <div v-if="caseReport">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="总案例">{{ caseReport.total_cases }}</el-descriptions-item>
          <el-descriptions-item label="成功">{{ caseReport.success_count }}</el-descriptions-item>
          <el-descriptions-item label="失败">{{ caseReport.failure_count }}</el-descriptions-item>
          <el-descriptions-item label="成功率" :span="3">
            <el-progress :percentage="Math.round(caseReport.success_rate * 100)"
              :color="caseReport.success_rate > 0.6 ? '#67c23a' : '#e6a23c'" />
          </el-descriptions-item>
        </el-descriptions>

        <el-divider />
        <h4>案例列表</h4>
        <div v-for="c in caseReport.cases" :key="c.id" :class="['case-row', c.is_success ? 'case-ok' : 'case-fail']">
          <div><b>[{{ c.is_success ? '✅ 成功' : '❌ 失败' }}]</b> {{ c.question }}</div>
          <div class="case-meta">GT: {{ c.ground_truth }}</div>
          <div class="case-pred">Pred: {{ c.prediction?.substring(0, 150) }}</div>
          <el-tag v-if="c.error_type" size="small" type="danger" style="margin-top:4px">{{ c.error_type }}</el-tag>
          <div v-if="c.analysis" class="case-analysis">分析: {{ c.analysis }}</div>
          <el-input v-if="!c.analysis" size="small" placeholder="添加分析..."
            @keydown.enter="updateCaseAnalysis(c.id, $event)" style="margin-top:6px" />
        </div>
      </div>
      <div v-else class="case-empty">
        <p>暂无案例数据。请先运行批量评测或手动添加案例。</p>
      </div>
    </el-dialog>

    <!-- 提示词对话框 -->
    <el-dialog v-model="showPromptsDialog" title="📝 系统提示词模板" width="640px">
      <el-tabs v-model="activePromptTab">
        <el-tab-pane v-for="p in systemPrompts" :key="p.type" :label="p.type" :name="p.type">
          <div class="prompt-block">{{ p.content }}</div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import {
  Picture, Promotion, Delete, ArrowRight, ArrowLeft,
  Plus, ChatDotRound, Close
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import {
  chat, healthCheck, getConversation, deleteConversation,
  listConversations, getDatasetStatus
} from './api.js'
import axios from 'axios'

const API_BASE = '/api/v1'

// ── 图像类型 ──
const imageTypeOptions = [
  { label: '🌄 自然场景', value: 'natural_scene', tagType: '' },
  { label: '📄 文档',     value: 'document',      tagType: 'success' },
  { label: '📊 幻灯片',   value: 'slide',          tagType: 'warning' },
  { label: '🛍️ 商品',     value: 'product',        tagType: 'danger' },
]

// ── 状态 ──
const messages = ref([])
const inputMessage = ref('')
const selectedImage = ref(null)
const selectedImageBase64 = ref(null)
const isLoading = ref(false)
const conversationId = ref(null)
const conversations = ref([])
const sidebarCollapsed = ref(false)
const currentImageType = ref('natural_scene')

const showImagePreview = ref(false)
const previewImageUrl = ref(null)
const showEvalDialog = ref(false)
const showCasesDialog = ref(false)
const showPromptsDialog = ref(false)
const activePromptTab = ref('natural_scene')

// 评测
const datasetStatus = ref(null)
const evalConfig = ref({
  dataset_type: 'builtin', image_type: 'natural_scene', max_samples: 10, dataset_path: ''
})
const evalResult = ref(null)
const evalRunning = ref(false)

// 案例
const caseReport = ref(null)
const systemPrompts = ref([])

// DOM refs
const messagesContainer = ref(null)
const imageInput = ref(null)

marked.setOptions({ breaks: true, gfm: true })

// ── 计算属性 ──
const inputPlaceholder = computed(() => ({
  natural_scene: '输入问题... 可上传自然场景图片',
  document:      '输入问题... 可上传文档/表格截图',
  slide:         '输入问题... 可上传幻灯片截图',
  product:       '输入问题... 可上传商品图片',
}[currentImageType.value] || '输入您的问题...'))

const currentImageTypeLabel = computed(() => {
  const opt = imageTypeOptions.find(o => o.value === currentImageType.value)
  return opt ? opt.label.replace(/[^一-龥]/g, '') : '自然场景'
})

const currentModeTagType = computed(() => {
  const opt = imageTypeOptions.find(o => o.value === currentImageType.value)
  return (opt && opt.tagType) ? opt.tagType : 'info'
})

const datasetOptions = computed(() => {
  if (!datasetStatus.value) return []
  return datasetStatus.value.datasets.map(ds => {
    let icon = ds.available ? '✅' : '❌'
    if (ds.key === 'builtin') icon = '📝'
    if (ds.key === 'custom')  icon = '📝'
    return { value: ds.key, label: `${icon} ${ds.name}`, disabled: !ds.available && ds.key !== 'builtin' && ds.key !== 'custom' }
  })
})

const selectedDatasetInfo = computed(() =>
  datasetStatus.value?.datasets?.find(ds => ds.key === evalConfig.value.dataset_type) || null
)

const needsPath = computed(() => evalConfig.value.dataset_type !== 'builtin')

const pathPlaceholder = computed(() => {
  const info = selectedDatasetInfo.value
  if (!info) return '数据集路径'
  if (info.available && info.path) return info.path
  if (info.key === 'custom') return 'JSON 文件路径，参考 data/datasets/sample_custom.json'
  return '留空使用标准路径 data/datasets/'
})

const canStartEval = computed(() => {
  const info = selectedDatasetInfo.value
  if (!info) return false
  if (info.key === 'builtin') return true
  if (info.key === 'custom') return !!evalConfig.value.dataset_path
  return info.available || !!evalConfig.value.dataset_path
})

// ── 工具 ──
function renderMarkdown(t) { return marked.parse(t) }
function triggerImageUpload() { imageInput.value.click() }
function scrollToBottom() { nextTick(() => { const el = messagesContainer.value; if (el) el.scrollTop = el.scrollHeight }) }
function copyText(t) { navigator.clipboard.writeText(t).then(() => ElMessage.success('已复制')) }
function onImageTypeChange() { ElMessage.success(`已切换: ${currentImageTypeLabel.value} 模式`) }
function previewImage(url) { previewImageUrl.value = url; showImagePreview.value = true }
function removeImage() { selectedImage.value = null; selectedImageBase64.value = null }
function newConversation() { messages.value = []; conversationId.value = null; removeImage() }

function handleImageSelect(e) {
  const f = e.target.files[0]
  if (!f) return
  if (!f.type.startsWith('image/')) return ElMessage.error('请选择图片文件')
  if (f.size > 5 * 1024 * 1024) return ElMessage.error('图片不能超过 5MB')
  const r = new FileReader()
  r.onload = ev => { selectedImage.value = ev.target.result; selectedImageBase64.value = ev.target.result.split(',')[1] }
  r.readAsDataURL(f)
  e.target.value = ''
}

// ── 对话 ──
async function sendMessage() {
  const msg = inputMessage.value.trim()
  if (!msg && !selectedImage.value) return ElMessage.warning('请输入消息或上传图片')

  messages.value.push({ role: 'user', content: msg || '请描述这张图片', image: selectedImage.value })
  inputMessage.value = ''
  const img = selectedImageBase64.value
  removeImage()
  scrollToBottom()
  isLoading.value = true

  try {
    const history = messages.value.slice(0, -1).map(m => ({ role: m.role, content: m.content }))
    const resp = await chat(msg || '请描述这张图片', img, conversationId.value,
      history.length > 0 ? history : null, currentImageType.value)
    conversationId.value = resp.conversation_id
    messages.value.push({ role: 'assistant', content: resp.response })
    scrollToBottom()
    loadConversations()
  } catch (e) {
    ElMessage.error('发送失败: ' + (e.response?.data?.detail || e.message))
    messages.value.pop()
  } finally { isLoading.value = false }
}

function clearChat() { messages.value = []; conversationId.value = null; removeImage() }

// ── 对话管理 ──
async function loadConversations() {
  try { const d = await listConversations(); conversations.value = d.conversations || [] } catch {}
}
async function switchConversation(id) {
  try {
    const d = await getConversation(id)
    messages.value = d.messages.map(m => ({ role: m.role, content: m.content, image: m.image_url ? `data:image/jpeg;base64,${m.image_url}` : null }))
    conversationId.value = id; scrollToBottom()
  } catch { ElMessage.error('加载失败') }
}
async function deleteConv(id) {
  try { await deleteConversation(id); if (id === conversationId.value) newConversation(); loadConversations() } catch { ElMessage.error('删除失败') }
}
async function exportCurrentConv() {
  if (!conversationId.value) return ElMessage.warning('请先开始对话')
  try {
    const r = await axios.get(`${API_BASE}/conversation/${conversationId.value}/export?format=markdown`)
    const b = new Blob([r.data], { type: 'text/markdown' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = `conversation_${conversationId.value}.md`; a.click()
    ElMessage.success('导出成功')
  } catch { ElMessage.error('导出失败') }
}

// ── 评测 ──
async function onEvalDialogOpen() {
  try { const d = await getDatasetStatus(); datasetStatus.value = d; onDatasetChange(evalConfig.value.dataset_type) } catch {}
}
function onDatasetChange(key) {
  const ds = datasetStatus.value?.datasets?.find(d => d.key === key)
  evalConfig.value.dataset_path = (ds?.available && ds?.path) ? ds.path : ''
}
async function runBatchEval() {
  evalRunning.value = true; evalResult.value = null
  try { const r = await axios.post(`${API_BASE}/evaluate/batch`, evalConfig.value); evalResult.value = r.data; ElMessage.success('评测完成') }
  catch (e) { ElMessage.error('评测失败: ' + (e.response?.data?.detail || e.message)) }
  finally { evalRunning.value = false }
}

// ── 案例 ──
async function showCaseReport() {
  try { const r = await axios.get(`${API_BASE}/cases/report`); caseReport.value = r.data; showCasesDialog.value = true }
  catch { ElMessage.error('获取案例报告失败') }
}
async function addToCases(msg, idx) {
  const u = messages.value[idx - 1]; if (!u || u.role !== 'user') return
  try { await axios.post(`${API_BASE}/cases`, { question: u.content, prediction: msg.content, image_type: currentImageType.value, is_success: true }); ElMessage.success('已收录') }
  catch { ElMessage.error('收录失败') }
}
async function updateCaseAnalysis(id, ev) {
  const v = ev.target.value; if (!v) return
  try { const f = new FormData(); f.append('analysis', v); await axios.put(`${API_BASE}/cases/${id}/analysis`, f); ev.target.value = ''; showCaseReport() }
  catch { ElMessage.error('更新失败') }
}

// ── 提示词 ──
async function loadPrompts() {
  try { const r = await axios.get(`${API_BASE}/prompts`); systemPrompts.value = r.data.prompts || [] } catch {}
}

// ── 启动 ──
onMounted(async () => {
  try { const h = await healthCheck(); ElMessage.success(`已连接 ${h.api_provider} (${h.model_name})`) }
  catch { ElMessage.warning('后端未连接，请先启动服务') }
  loadConversations(); loadPrompts()
})
</script>

<style scoped>
/* ===== 全局布局 ===== */
.app-layout {
  display: flex;
  height: 100vh;
  background: #f0f2f5;
}

/* ===== 侧边栏 ===== */
.sidebar {
  width: 260px;
  min-width: 52px;
  background: #fff;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  transition: width .2s;
  overflow: hidden;
}
.sidebar.collapsed { width: 52px; }

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 12px;
  border-bottom: 1px solid #ebeef5;
  min-height: 52px;
}
.sidebar-title { font-size: 14px; font-weight: 600; color: #303133; white-space: nowrap; }
.toggle-btn { flex-shrink: 0; }

.sidebar-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 12px;
  overflow-y: auto;
  gap: 8px;
}

.sidebar-btn {
  width: 100%;
  justify-content: flex-start !important;
  font-size: 13px;
  border-radius: 8px;
}

/* 对话列表 */
.conv-list { display: flex; flex-direction: column; gap: 4px; flex: 1; overflow-y: auto; min-height: 0; }
.conv-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all .15s;
}
.conv-item:hover { background: #f5f7fa; border-color: #dcdfe6; }
.conv-item.active { background: #ecf5ff; border-color: #a0cfff; }
.conv-preview {
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 6px;
}
.conv-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.conv-count { font-size: 11px; color: #909399; }

.sidebar-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
  gap: 6px;
}
.sidebar-empty p { margin: 0; font-size: 13px; }
.sidebar-empty .hint { font-size: 11px; color: #dcdfe6; }

/* 功能区 */
.sidebar-tools {
  border-top: 1px solid #ebeef5;
  padding-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.tools-title { font-size: 12px; font-weight: 600; color: #909399; margin-bottom: 2px; }

/* ===== 主区域 ===== */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #fff;
}

/* ===== 顶栏 ===== */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  flex-shrink: 0;
  gap: 16px;
}
.top-bar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.logo { font-size: 32px; line-height: 1; }
.app-title { margin: 0; font-size: 20px; font-weight: 700; }
.app-subtitle { margin: 2px 0 0; font-size: 12px; opacity: .85; }

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.mode-label { font-size: 12px; opacity: .8; }
.mode-select { width: 130px; }

/* ===== 消息区 ===== */
.msg-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: #fafbfc;
}

/* 欢迎 */
.welcome {
  margin: auto;
  text-align: center;
  padding: 48px 24px;
  color: #606266;
}
.welcome-bot { font-size: 72px; margin-bottom: 16px; }
.welcome h2 { margin: 0 0 8px; font-size: 22px; color: #303133; }
.welcome p { margin: 0 0 20px; font-size: 14px; }
.welcome-tags { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; }

/* 消息行 */
.msg-row {
  display: flex;
  gap: 12px;
  max-width: 80%;
}
.msg-row.user { align-self: flex-end; flex-direction: row-reverse; }
.msg-row.assistant { align-self: flex-start; }

.msg-avatar {
  width: 38px; height: 38px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; flex-shrink: 0;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,.08);
}

.msg-bubble {
  padding: 12px 16px;
  border-radius: 14px;
  line-height: 1.65;
  position: relative;
}
.msg-row.user .msg-bubble { background: #409eff; color: #fff; border-bottom-right-radius: 4px; }
.msg-row.assistant .msg-bubble { background: #fff; color: #303133; border-bottom-left-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }

/* 列表编号/符号保持在气泡内 */
.msg-text :deep(ol),
.msg-text :deep(ul) {
  padding-left: 1.4em; margin: 4px 0;
}
.msg-text :deep(li) {
  word-break: break-word;
}
.msg-text :deep(ol) { list-style-position: outside; }

.msg-img {
  max-width: 280px; max-height: 180px;
  border-radius: 8px; cursor: pointer;
  margin-bottom: 8px; display: block;
}

.msg-tools {
  display: flex; gap: 4px; margin-top: 6px;
  opacity: 0; transition: opacity .15s;
}
.msg-row:hover .msg-tools { opacity: 1; }
.msg-row.user .msg-tools .el-button { color: rgba(255,255,255,.75); }
.msg-row.user .msg-tools .el-button:hover { color: #fff; }

/* 加载 */
.loading {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 16px; color: #909399;
}
.loading .dot {
  width: 7px; height: 7px; border-radius: 50%; background: #c0c4cc;
  animation: bounce 1.4s infinite ease-in-out both;
}
.loading .dot:nth-child(1) { animation-delay: 0s; }
.loading .dot:nth-child(2) { animation-delay: .2s; }
.loading .dot:nth-child(3) { animation-delay: .4s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}
.loading-text { font-size: 13px; margin-left: 6px; }

/* ===== 输入区 ===== */
.input-area {
  padding: 16px 24px;
  border-top: 1px solid #ebeef5;
  background: #fff;
  flex-shrink: 0;
}

/* 图片预览 */
.img-preview {
  position: relative;
  display: inline-block;
  margin-bottom: 12px;
}
.img-preview img {
  max-height: 160px;
  max-width: 260px;
  border-radius: 10px;
  border: 1px solid #e4e7ed;
  display: block;
}
.preview-close {
  position: absolute;
  top: -10px;
  right: -10px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,.15);
}

.input-row {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}
.msg-input { flex: 1; }
.msg-input :deep(.el-textarea__inner) {
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
}
.input-btn { flex-shrink: 0; }
.send-btn { background: #67c23a; border-color: #67c23a; }
.send-btn:hover { background: #5daf34; border-color: #5daf34; }
.clear-btn { color: #909399; }

/* ===== 对话框通用 ===== */
.form-full { width: 100%; }
.ds-info { margin-top: 8px; font-size: 12px; color: #909399; line-height: 1.5; }
.ds-info p { margin: 0 0 4px; }
.ds-dl { margin-top: 4px; font-size: 12px; }
.ds-dl a { color: #409eff; }
.ds-size { color: #c0c4cc; }
.ds-found { font-size: 11px; color: #67c23a; margin-top: 4px; }

/* 评测结果 */
.eval-output { margin-top: 16px; }
.eval-output h4 { margin: 0 0 10px; font-size: 15px; }
.eval-errors { margin-top: 10px; }
.eval-errors strong { font-size: 13px; }
.error-tag { margin: 2px 4px 2px 0; }

.case-block { margin-top: 10px; }
.case-block strong { font-size: 13px; }
.case-card { margin: 6px 0; padding: 8px; border-radius: 6px; font-size: 12px; line-height: 1.5; }
.case-block.success .case-card { background: #f0f9eb; }
.case-block.failure .case-card { background: #fef0f0; }

/* 案例报告 */
.case-row { padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; font-size: 13px; line-height: 1.5; }
.case-ok { background: #f0f9eb; border-left: 4px solid #67c23a; }
.case-fail { background: #fef0f0; border-left: 4px solid #f56c6c; }
.case-meta, .case-pred { font-size: 12px; color: #909399; }
.case-analysis { font-size: 12px; color: #409eff; margin-top: 4px; }
.case-empty { text-align: center; padding: 40px; color: #909399; }

/* 提示词 */
.prompt-block {
  white-space: pre-wrap;
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.7;
  color: #303133;
}

/* 用户消息的 markdown 覆盖 */
.msg-row.user .msg-bubble :deep(a) { color: #fff; }
.msg-row.user .msg-bubble :deep(pre) { background: rgba(255,255,255,.15); }
.msg-row.user .msg-bubble :deep(code) { background: rgba(255,255,255,.2); color: #fff; }
.msg-row.user .msg-bubble :deep(blockquote) { border-left-color: rgba(255,255,255,.4); color: rgba(255,255,255,.85); }

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .sidebar { display: none; }
  .top-bar { padding: 10px 16px; }
  .top-bar-right { display: none; }
  .app-title { font-size: 16px; }
  .msg-row { max-width: 92%; }
  .msg-area { padding: 16px; }
  .input-area { padding: 12px 16px; }
}
</style>
