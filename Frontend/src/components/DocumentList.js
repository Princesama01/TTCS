import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { documentAPI } from '../api/client';
import './DocumentList.css';

function DocumentList() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('name');

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const result = await documentAPI.getDocuments();
      setDocuments(result.documents || []);
      toast.success('Tải danh sách tài liệu thành công');
    } catch (error) {
      console.error('Error fetching documents:', error);
      const errorMessage = typeof error === 'string'
        ? error
        : error?.detail || 'Không thể tải danh sách tài liệu';
      
      toast.error(errorMessage);
      // Set empty list if error (API endpoint might not be implemented)
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteDocument = async (documentId) => {
    if (window.confirm('Bạn có chắc chắn muốn xóa tài liệu này?')) {
      try {
        await documentAPI.deleteDocument(documentId);
        setDocuments(prev => prev.filter(doc => doc.id !== documentId));
        toast.success('Tài liệu đã được xóa');
      } catch (error) {
        console.error('Error deleting document:', error);
        const errorMessage = typeof error === 'string'
          ? error
          : error?.detail || 'Không thể xóa tài liệu';
        
        toast.error(errorMessage);
      }
    }
  };

  const handleSearchSources = async (query) => {
    try {
      const result = await documentAPI.getSources(query);
      console.log('Search results:', result);
      toast.success('Tìm kiếm nguồn thành công');
    } catch (error) {
      console.error('Error searching sources:', error);
      const errorMessage = typeof error === 'string'
        ? error
        : error?.detail || 'Không thể tìm kiếm';
      
      toast.error(errorMessage);
    }
  };

  const filteredDocuments = documents
    .filter(doc =>
      doc.name.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      if (sortBy === 'name') {
        return a.name.localeCompare(b.name);
      } else if (sortBy === 'size') {
        return (b.size || 0) - (a.size || 0);
      } else if (sortBy === 'date') {
        return new Date(b.uploadedAt) - new Date(a.uploadedAt);
      }
      return 0;
    });

  return (
    <div className="documents-container">
      <div className="documents-header">
        <h2>📋 Quản Lý Tài Liệu</h2>
        <button
          onClick={fetchDocuments}
          disabled={loading}
          className="btn btn-refresh"
        >
          🔄 Làm mới
        </button>
      </div>

      {/* Search and Filter */}
      <div className="documents-controls">
        <div className="search-box">
          <input
            type="text"
            placeholder="🔍 Tìm kiếm tài liệu..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="sort-box">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="sort-select"
          >
            <option value="name">Sắp xếp theo tên</option>
            <option value="size">Sắp xếp theo kích thước</option>
            <option value="date">Sắp xếp theo ngày</option>
          </select>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="loading-state">
          <div className="spinner-large"></div>
          <p>Đang tải tài liệu...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && filteredDocuments.length === 0 && documents.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">📁</div>
          <h3>Không có tài liệu nào</h3>
          <p>Bắt đầu bằng cách tải lên tài liệu đầu tiên</p>
        </div>
      )}

      {/* No Results State */}
      {!loading && filteredDocuments.length === 0 && documents.length > 0 && (
        <div className="empty-state">
          <div className="empty-icon">🔍</div>
          <h3>Không tìm thấy kết quả</h3>
          <p>Thử thay đổi từ khóa tìm kiếm</p>
        </div>
      )}

      {/* Documents Grid */}
      {!loading && filteredDocuments.length > 0 && (
        <div className="documents-grid">
          {filteredDocuments.map(doc => (
            <div key={doc.id} className="document-card">
              <div className="document-icon">📄</div>
              
              <div className="document-content">
                <h3 className="document-name">{doc.name}</h3>
                
                <div className="document-meta">
                  {doc.size && (
                    <span className="meta-item">
                      💾 {(doc.size / 1024 / 1024).toFixed(2)} MB
                    </span>
                  )}
                  {doc.uploadedAt && (
                    <span className="meta-item">
                      📅 {new Date(doc.uploadedAt).toLocaleDateString('vi-VN')}
                    </span>
                  )}
                  {doc.chunks && (
                    <span className="meta-item">
                      🧩 {doc.chunks} khối
                    </span>
                  )}
                </div>

                {doc.description && (
                  <p className="document-description">{doc.description}</p>
                )}
              </div>

              <div className="document-actions">
                <button
                  onClick={() => handleSearchSources(doc.name)}
                  className="btn btn-action btn-search"
                  title="Tìm kiếm"
                >
                  🔍
                </button>
                <button
                  onClick={() => handleDeleteDocument(doc.id)}
                  className="btn btn-action btn-delete"
                  title="Xóa"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Stats */}
      {!loading && documents.length > 0 && (
        <div className="documents-stats">
          <div className="stat-item">
            <span className="stat-label">Tổng tài liệu:</span>
            <span className="stat-value">{documents.length}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Dung lượng:</span>
            <span className="stat-value">
              {(documents.reduce((sum, doc) => sum + (doc.size || 0), 0) / 1024 / 1024).toFixed(2)} MB
            </span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Tổng khối:</span>
            <span className="stat-value">
              {documents.reduce((sum, doc) => sum + (doc.chunks || 0), 0)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default DocumentList;
