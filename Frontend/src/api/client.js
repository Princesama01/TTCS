import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for logging
apiClient.interceptors.request.use(
  config => {
    console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  error => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  response => {
    console.log(`API Response: ${response.status}`);
    return response;
  },
  error => {
    console.error('Response error:', error);
    return Promise.reject(error);
  }
);

// Chat API
export const chatAPI = {
  async sendMessage(question, conversationId = null, language = 'vi', returnSources = false) {
    try {
      const response = await apiClient.post('/chat', {
        question,
        conversation_id: conversationId,
        language,
        return_sources: returnSources,
      });
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },
};

// Document API
export const documentAPI = {
  async uploadDocuments(files, chunkSize = 512, chunkOverlap = 50) {
    try {
      const formData = new FormData();
      
      files.forEach(file => {
        formData.append('files', file);
      });
      
      formData.append('chunk_size', chunkSize.toString());
      formData.append('chunk_overlap', chunkOverlap.toString());

      const response = await apiClient.post('/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },

  async getDocuments() {
    try {
      const response = await apiClient.get('/documents');
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },

  async deleteDocument(documentId) {
    try {
      const response = await apiClient.delete(`/documents/${documentId}`);
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },

  async getSources(query) {
    try {
      const response = await apiClient.get('/sources', {
        params: { query },
      });
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },
};

// Statistics API
export const statisticsAPI = {
  async getStats() {
    try {
      const response = await apiClient.get('/statistics');
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },

  async getHealth() {
    try {
      const response = await apiClient.get('/health');
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },
};

export default apiClient;
