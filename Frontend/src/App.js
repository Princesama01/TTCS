import React, { useState } from 'react';
import { Toaster } from 'react-hot-toast';
import './App.css';
import DocumentUpload from './components/DocumentUpload';
import ChatInterface from './components/ChatInterface';
import DocumentList from './components/DocumentList';

function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [refreshDocuments, setRefreshDocuments] = useState(false);

  const handleDocumentUploaded = () => {
    setRefreshDocuments(prev => !prev);
  };

  return (
    <div className="app">
      <Toaster position="top-right" />
      
      <header className="app-header">
        <div className="header-content">
          <h1>📚 RAG Document Q&A System</h1>
          <p>Tìm kiếm và hỏi đáp trên tài liệu của bạn</p>
        </div>
      </header>

      <div className="app-container">
        <nav className="tab-navigation">
          <button
            className={`tab-button ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            💬 Chat
          </button>
          <button
            className={`tab-button ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => setActiveTab('upload')}
          >
            📤 Upload Tài Liệu
          </button>
          <button
            className={`tab-button ${activeTab === 'documents' ? 'active' : ''}`}
            onClick={() => setActiveTab('documents')}
          >
            📋 Quản Lý Tài Liệu
          </button>
        </nav>

        <main className="app-content">
          {activeTab === 'chat' && <ChatInterface />}
          {activeTab === 'upload' && (
            <DocumentUpload onDocumentUploaded={handleDocumentUploaded} />
          )}
          {activeTab === 'documents' && (
            <DocumentList key={refreshDocuments} />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
