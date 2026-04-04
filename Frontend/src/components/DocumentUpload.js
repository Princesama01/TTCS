import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { documentAPI } from '../api/client';
import './DocumentUpload.css';

function DocumentUpload({ onDocumentUploaded }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [chunkSize, setChunkSize] = useState(512);
  const [chunkOverlap, setChunkOverlap] = useState(50);
  const [uploadResult, setUploadResult] = useState(null);

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(prevFiles => [...prevFiles, ...selectedFiles]);
  };

  const handleRemoveFile = (index) => {
    setFiles(prevFiles => prevFiles.filter((_, i) => i !== index));
  };

  const handleClearFiles = () => {
    setFiles([]);
    setUploadResult(null);
  };

  const handleUpload = async (e) => {
    e.preventDefault();

    if (files.length === 0) {
      toast.error('Vui lòng chọn ít nhất một tệp');
      return;
    }

    setLoading(true);
    setProgress(0);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return prev;
          }
          return prev + Math.random() * 20;
        });
      }, 300);

      const result = await documentAPI.uploadDocuments(
        files,
        chunkSize,
        chunkOverlap
      );

      clearInterval(progressInterval);
      setProgress(100);

      setUploadResult(result);
      toast.success(`✅ Tải lên ${result.processed_files} tệp thành công!`);
      
      // Reset form after 2 seconds
      setTimeout(() => {
        setFiles([]);
        onDocumentUploaded?.();
      }, 2000);
    } catch (error) {
      console.error('Upload error:', error);
      
      const errorMessage = typeof error === 'string'
        ? error
        : error?.detail || 'Có lỗi xảy ra khi tải lên tệp';
      
      toast.error(`❌ Lỗi: ${errorMessage}`);
      setUploadResult(null);
    } finally {
      setLoading(false);
      setTimeout(() => setProgress(0), 1000);
    }
  };

  return (
    <div className="upload-container">
      <div className="upload-card">
        <h2>📤 Upload Tài Liệu</h2>
        <p className="upload-description">
          Tải lên các tệp PDF để hệ thống xử lí và lập chỉ mục. Bạn có thể tải lên nhiều tệp cùng một lúc.
        </p>

        <form onSubmit={handleUpload} className="upload-form">
          {/* File Selection Area */}
          <div className="file-selection-area">
            <label htmlFor="file-input" className="file-input-label">
              <div className="file-input-content">
                <div className="file-input-icon">📁</div>
                <div className="file-input-text">
                  <p className="file-input-main">Kéo thả tệp hoặc nhấp để chọn</p>
                  <p className="file-input-sub">Hỗ trợ: PDF, TXT, DOCX</p>
                </div>
              </div>
              <input
                id="file-input"
                type="file"
                multiple
                accept=".pdf,.txt,.docx"
                onChange={handleFileSelect}
                disabled={loading}
                className="file-input-hidden"
              />
            </label>
          </div>

          {/* Selected Files List */}
          {files.length > 0 && (
            <div className="selected-files">
              <div className="files-header">
                <h3>📋 Tệp được chọn ({files.length})</h3>
                <button
                  type="button"
                  onClick={handleClearFiles}
                  className="btn-clear"
                  disabled={loading}
                >
                  ✕ Xóa tất cả
                </button>
              </div>

              <div className="files-list">
                {files.map((file, index) => (
                  <div key={index} className="file-item">
                    <div className="file-info">
                      <span className="file-icon">📄</span>
                      <div className="file-details">
                        <p className="file-name">{file.name}</p>
                        <p className="file-size">
                          {(file.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveFile(index)}
                      disabled={loading}
                      className="btn-remove"
                      title="Xóa tệp"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Settings */}
          <div className="settings-section">
            <h3>⚙️ Cài đặt xử lí</h3>
            
            <div className="settings-grid">
              <div className="setting-group">
                <label htmlFor="chunk-size">Kích thước khối (tokens)</label>
                <input
                  id="chunk-size"
                  type="number"
                  min="100"
                  max="2000"
                  step="50"
                  value={chunkSize}
                  onChange={(e) => setChunkSize(parseInt(e.target.value))}
                  disabled={loading}
                  className="setting-input"
                />
                <p className="setting-help">Kích thước mỗi đoạn văn bản</p>
              </div>

              <div className="setting-group">
                <label htmlFor="chunk-overlap">Chồng lặp khối (tokens)</label>
                <input
                  id="chunk-overlap"
                  type="number"
                  min="0"
                  max="500"
                  step="10"
                  value={chunkOverlap}
                  onChange={(e) => setChunkOverlap(parseInt(e.target.value))}
                  disabled={loading}
                  className="setting-input"
                />
                <p className="setting-help">Độ chồng lặp giữa các khối</p>
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          {loading && progress > 0 && (
            <div className="progress-section">
              <div className="progress-info">
                <span>Đang xử lí...</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
          )}

          {/* Upload Result */}
          {uploadResult && (
            <div className="upload-result success">
              <h3>✅ Tải lên thành công!</h3>
              <div className="result-details">
                <p><strong>Tệp được xử lí:</strong> {uploadResult.processed_files}</p>
                <p><strong>Tổng khối:</strong> {uploadResult.total_chunks}</p>
                <p><strong>Thông báo:</strong> {uploadResult.message}</p>
              </div>
            </div>
          )}

          {/* Submit Button */}
          <div className="form-actions">
            <button
              type="submit"
              disabled={files.length === 0 || loading}
              className="btn btn-primary"
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  Đang tải lên...
                </>
              ) : (
                <>
                  📤 Tải lên {files.length > 0 ? files.length : ''} tệp
                </>
              )}
            </button>
          </div>
        </form>

        {/* Info Box */}
        <div className="info-box">
          <h4>💡 Mẹo</h4>
          <ul>
            <li>Tải lên tệp PDF để hệ thống phân tích nội dung</li>
            <li>Kích thước khối càng nhỏ, độ chính xác càng cao nhưng tốc độ chậm hơn</li>
            <li>Chồng lặp giúp giữ ngữ cảnh giữa các khối</li>
            <li>Mỗi tệp sẽ được lập chỉ mục tự động vào hệ thống VectorStore</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default DocumentUpload;
