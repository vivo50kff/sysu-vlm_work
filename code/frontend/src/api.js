/**
 * API服务模块
 */
import axios from 'axios'

const API_BASE_URL = '/api/v1'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,  // 2分钟超时（评测需要更长时间）
  headers: {
    'Content-Type': 'application/json'
  }
})

/**
 * 发送聊天消息
 */
export async function chat(message, imageBase64 = null, conversationId = null, history = null, imageType = 'natural_scene') {
  const response = await apiClient.post('/chat', {
    message,
    image_base64: imageBase64,
    conversation_id: conversationId,
    history,
    image_type: imageType
  })
  return response.data
}

/**
 * 上传图片并发送消息
 */
export async function chatWithImage(message, imageFile, conversationId = null) {
  const formData = new FormData()
  formData.append('message', message)
  formData.append('image', imageFile)
  if (conversationId) {
    formData.append('conversation_id', conversationId)
  }

  const response = await apiClient.post('/chat/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return response.data
}

/**
 * 获取对话历史
 */
export async function getConversation(conversationId) {
  const response = await apiClient.get(`/conversation/${conversationId}`)
  return response.data
}

/**
 * 删除对话
 */
export async function deleteConversation(conversationId) {
  const response = await apiClient.delete(`/conversation/${conversationId}`)
  return response.data
}

/**
 * 清空对话历史
 */
export async function clearConversation(conversationId) {
  const response = await apiClient.post(`/conversation/${conversationId}/clear`)
  return response.data
}

/**
 * 获取所有对话列表
 */
export async function listConversations() {
  const response = await apiClient.get('/conversations')
  return response.data
}

/**
 * 导出对话
 */
export async function exportConversation(conversationId, format = 'json') {
  const response = await apiClient.get(`/conversation/${conversationId}/export`, {
    params: { format }
  })
  return response.data
}

/**
 * 导入对话
 */
export async function importConversation(data) {
  const formData = new FormData()
  formData.append('data', data)
  const response = await apiClient.post('/conversation/import', formData)
  return response.data
}

/**
 * 搜索对话
 */
export async function searchConversations(keyword) {
  const response = await apiClient.get('/conversations/search', {
    params: { keyword }
  })
  return response.data
}

/**
 * 健康检查
 */
export async function healthCheck() {
  const response = await apiClient.get('/health')
  return response.data
}

/**
 * 单条评测
 */
export async function evaluate(imageBase64, question, groundTruth, imageType = 'natural_scene') {
  const response = await apiClient.post('/evaluate', {
    image_base64: imageBase64,
    question,
    ground_truth: groundTruth,
    image_type: imageType
  })
  return response.data
}

/**
 * 批量评测
 */
export async function batchEvaluate(config) {
  const response = await apiClient.post('/evaluate/batch', config)
  return response.data
}

/**
 * 获取评测报告
 */
export async function getEvalReport(datasetType = 'builtin', imageType = 'natural_scene', maxSamples = 10) {
  const response = await apiClient.get('/evaluate/report', {
    params: {
      dataset_type: datasetType,
      image_type: imageType,
      max_samples: maxSamples
    }
  })
  return response.data
}

/**
 * 添加案例
 */
export async function addCase(caseData) {
  const response = await apiClient.post('/cases', caseData)
  return response.data
}

/**
 * 获取案例列表
 */
export async function listCases() {
  const response = await apiClient.get('/cases')
  return response.data
}

/**
 * 获取案例报告
 */
export async function getCasesReport(format = 'json') {
  const response = await apiClient.get('/cases/report', {
    params: { format }
  })
  return response.data
}

/**
 * 获取单个案例
 */
export async function getCase(caseId) {
  const response = await apiClient.get(`/cases/${caseId}`)
  return response.data
}

/**
 * 更新案例分析
 */
export async function updateCaseAnalysis(caseId, analysis) {
  const formData = new FormData()
  formData.append('analysis', analysis)
  const response = await apiClient.put(`/cases/${caseId}/analysis`, formData)
  return response.data
}

/**
 * 清空案例
 */
export async function clearCases() {
  const response = await apiClient.delete('/cases')
  return response.data
}

/**
 * 获取提示词模板
 */
export async function getSystemPrompts() {
  const response = await apiClient.get('/prompts')
  return response.data
}

/**
 * 获取数据集可用状态
 */
export async function getDatasetStatus() {
  const response = await apiClient.get('/evaluate/datasets')
  return response.data
}

export default {
  chat,
  chatWithImage,
  getConversation,
  deleteConversation,
  clearConversation,
  listConversations,
  exportConversation,
  importConversation,
  searchConversations,
  healthCheck,
  evaluate,
  batchEvaluate,
  getEvalReport,
  addCase,
  listCases,
  getCasesReport,
  getCase,
  updateCaseAnalysis,
  clearCases,
  getSystemPrompts,
  getDatasetStatus
}
