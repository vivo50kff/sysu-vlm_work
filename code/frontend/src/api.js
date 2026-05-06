/**
 * API服务模块
 */
import axios from 'axios'

const API_BASE_URL = '/api/v1'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

/**
 * 发送聊天消息
 * @param {string} message - 用户消息
 * @param {string|null} imageBase64 - base64编码的图片
 * @param {string|null} conversationId - 对话ID
 * @param {Array|null} history - 对话历史
 * @returns {Promise<Object>} - 响应结果
 */
export async function chat(message, imageBase64 = null, conversationId = null, history = null) {
  const response = await apiClient.post('/chat', {
    message,
    image_base64: imageBase64,
    conversation_id: conversationId,
    history
  })
  return response.data
}

/**
 * 上传图片并发送消息
 * @param {string} message - 用户消息
 * @param {File} imageFile - 图片文件
 * @param {string|null} conversationId - 对话ID
 * @returns {Promise<Object>} - 响应结果
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
 * @param {string} conversationId - 对话ID
 * @returns {Promise<Object>} - 对话历史
 */
export async function getConversation(conversationId) {
  const response = await apiClient.get(`/conversation/${conversationId}`)
  return response.data
}

/**
 * 删除对话
 * @param {string} conversationId - 对话ID
 * @returns {Promise<Object>} - 删除结果
 */
export async function deleteConversation(conversationId) {
  const response = await apiClient.delete(`/conversation/${conversationId}`)
  return response.data
}

/**
 * 清空对话历史
 * @param {string} conversationId - 对话ID
 * @returns {Promise<Object>} - 清空结果
 */
export async function clearConversation(conversationId) {
  const response = await apiClient.post(`/conversation/${conversationId}/clear`)
  return response.data
}

/**
 * 获取所有对话列表
 * @returns {Promise<Object>} - 对话列表
 */
export async function listConversations() {
  const response = await apiClient.get('/conversations')
  return response.data
}

/**
 * 健康检查
 * @returns {Promise<Object>} - 健康状态
 */
export async function healthCheck() {
  const response = await apiClient.get('/health')
  return response.data
}

export default {
  chat,
  chatWithImage,
  getConversation,
  deleteConversation,
  clearConversation,
  listConversations,
  healthCheck
}