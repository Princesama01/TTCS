import React, { useState, useRef, useEffect } from 'react';
import toast from 'react-hot-toast';
import { chatAPI } from '../api/client';
import './ChatInterface.css';

function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: 'Xin chào! 👋 Tôi là AI assistant, sẵn sàng giúp bạn tìm kiếm thông tin từ các tài liệu. Hỏi tôi bất cứ điều gì!',
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [language, setLanguage] = useState('vi');
  const [showSources, setShowSources] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();

    if (!inputValue.trim()) {
      toast.error('Vui lòng nhập câu hỏi');
      return;
    }

    if (loading) {
      return;
    }

    // Add user message
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setLoading(true);

    try {
      const response = await chatAPI.sendMessage(
        inputValue,
        conversationId,
        language,
        showSources
      );

      // Update conversation ID for future messages
      if (!conversationId && response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: response.answer,
        sources: response.source_documents || [],
        metadata: {
          retrievalTime: response.retrieval_time,
          generationTime: response.generation_time,
          totalTime: response.total_time,
        },
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, botMessage]);
      toast.success('Câu trả lời được tạo thành công!');
    } catch (error) {
      console.error('Error sending message:', error);
      
      const errorMessage = typeof error === 'string' 
        ? error 
        : error?.detail || 'Có lỗi xảy ra khi gửi câu hỏi';
      
      toast.error(errorMessage);

      const errorBotMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: `❌ Lỗi: ${errorMessage}`,
        isError: true,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorBotMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleNewConversation = () => {
    setMessages([
      {
        id: 1,
        type: 'bot',
        content: 'Xin chào! 👋 Tôi là AI assistant, sẵn sàng giúp bạn tìm kiếm thông tin từ các tài liệu. Hỏi tôi bất cứ điều gì!',
        timestamp: new Date(),
      },
    ]);
    setConversationId(null);
    toast.success('Đã bắt đầu cuộc trò chuyện mới');
  };

  return (
    <div className="chat-container">
      <div className="chat-sidebar">
        <div className="sidebar-section">
          <h3>⚙️ Tùy chọn</h3>
          
          <div className="option-group">
            <label>Ngôn ngữ:</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="option-select"
            >
              <option value="vi">Tiếng Việt</option>
              <option value="en">English</option>
            </select>
          </div>

          <div className="option-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={showSources}
                onChange={(e) => setShowSources(e.target.checked)}
              />
              {' '}Hiển thị tài liệu nguồn
            </label>
          </div>

          <button
            className="btn btn-secondary"
            onClick={handleNewConversation}
          >
            🔄 Cuộc trò chuyện mới
          </button>
        </div>

        {conversationId && (
          <div className="sidebar-section">
            <h3>📊 Thông tin</h3>
            <div className="info-item">
              <span>Conversation ID:</span>
              <code>{conversationId.substring(0, 8)}...</code>
            </div>
          </div>
        )}
      </div>

      <div className="chat-main">
        <div className="messages-container">
          {messages.map(message => (
            <div
              key={message.id}
              className={`message message-${message.type} ${message.isError ? 'error' : ''}`}
            >
              <div className="message-header">
                <span className="message-role">
                  {message.type === 'user' ? '👤 Bạn' : '🤖 AI'}
                </span>
                <span className="message-time">
                  {message.timestamp.toLocaleTimeString('vi-VN')}
                </span>
              </div>
              
              <div className="message-content">
                {message.content}
              </div>

              {message.sources && message.sources.length > 0 && (
                <div className="sources-section">
                  <h4>📚 Tài liệu nguồn:</h4>
                  <div className="sources-list">
                    {message.sources.map((source, idx) => (
                      <div key={idx} className="source-item">
                        <div className="source-header">
                          <strong>📄 {source.filename}</strong>
                          {source.page && <span className="source-page">Trang: {source.page}</span>}
                          {source.score && <span className="source-score">Điểm: {(source.score * 100).toFixed(1)}%</span>}
                        </div>
                        <p className="source-content">{source.content}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {message.metadata && (
                <div className="metadata">
                  <span>🔍 Tìm kiếm: {(message.metadata.retrievalTime * 1000).toFixed(0)}ms</span>
                  <span>⚡ Tạo: {(message.metadata.generationTime * 1000).toFixed(0)}ms</span>
                  <span>⏱️ Tổng: {(message.metadata.totalTime * 1000).toFixed(0)}ms</span>
                </div>
              )}
            </div>
          ))}
          
          {loading && (
            <div className="message message-bot loading">
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSendMessage} className="message-input-form">
          <div className="input-wrapper">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Nhập câu hỏi của bạn..."
              disabled={loading}
              className="message-input"
            />
            <button
              type="submit"
              disabled={loading || !inputValue.trim()}
              className="btn btn-send"
            >
              {loading ? '📤' : '📤'} Gửi
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ChatInterface;
