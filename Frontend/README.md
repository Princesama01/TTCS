# RAG Document Q&A Frontend

Frontend React cho hệ thống RAG Document Q&A

## 📋 Tính năng

- ✅ **Chat Interface**: Giao diện chat trực quan để hỏi đáp về tài liệu
- ✅ **Document Upload**: Tải lên và xử lý tài liệu PDF/TXT/DOCX
- ✅ **Document Management**: Quản lý các tài liệu đã upload
- ✅ **Source Display**: Hiển thị tài liệu nguồn khi trả lời
- ✅ **Performance Metrics**: Hiển thị thời gian xử lý
- ✅ **Language Support**: Hỗ trợ Tiếng Việt và English

## 🚀 Cài đặt

### Yêu cầu
- Node.js 14+ 
- npm hoặc yarn

### Bước 1: Cài đặt dependencies

```bash
cd d:\TTCS\Code\Frontend
npm install
```

### Bước 2: Cấu hình API

Tạo file `.env.local` (hoặc chỉnh sửa file `.env` hiện có):

```env
REACT_APP_API_URL=http://localhost:8000/api/v1
```

Thay đổi URL theo địa chỉ backend của bạn.

### Bước 3: Chạy development server

```bash
npm start
```

Ứng dụng sẽ mở tại: `http://localhost:3000`

## 📁 Cấu trúc Project

```
Frontend/
├── public/
│   └── index.html              # HTML template
├── src/
│   ├── api/
│   │   └── client.js           # API client và các function gọi API
│   ├── components/
│   │   ├── ChatInterface.js    # Component chat
│   │   ├── ChatInterface.css   # Styling chat
│   │   ├── DocumentUpload.js   # Component upload tài liệu
│   │   ├── DocumentUpload.css  # Styling upload
│   │   ├── DocumentList.js     # Component quản lý tài liệu
│   │   └── DocumentList.css    # Styling list
│   ├── App.js                  # Component chính
│   ├── App.css                 # Styling chính
│   ├── index.js                # Entry point
│   └── index.css               # Global styling
├── .env                        # Environment variables (mặc định)
├── .env.local                  # Environment variables (cục bộ - ghi đè .env)
├── package.json                # Dependencies
└── README.md                   # File này
```

## 🎯 Sử dụng

### 💬 Chat Interface
1. Nhập câu hỏi về tài liệu của bạn
2. Chọn ngôn ngữ (Tiếng Việt/English)
3. Bật tùy chọn "Hiển thị tài liệu nguồn" để xem nguồn
4. Nhận câu trả lời từ AI

### 📤 Upload Tài Liệu
1. Chọn tab "Upload Tài Liệu"
2. Kéo thả hoặc nhấp để chọn file
3. Điều chỉnh "Kích thước khối" và "Chồng lặp khối" nếu cần
4. Nhấp "Tải lên" để xử lý tài liệu

### 📋 Quản Lý Tài Liệu
1. Xem danh sách tất cả tài liệu đã upload
2. Tìm kiếm tài liệu theo tên
3. Sắp xếp theo tên, kích thước, hoặc ngày upload
4. Xóa tài liệu không cần thiết

## 🔌 API Endpoints

Các endpoint API backend được sử dụng:

```
POST   /api/v1/chat                    # Gửi câu hỏi
POST   /api/v1/documents/upload        # Upload tài liệu
GET    /api/v1/documents               # Lấy danh sách tài liệu
DELETE /api/v1/documents/{id}          # Xóa tài liệu
GET    /api/v1/sources                 # Tìm kiếm nguồn
GET    /api/v1/health                  # Kiểm tra trạng thái
GET    /api/v1/statistics              # Lấy thống kê
```

## ⚙️ Cài đặt Advanced

### Thay đổi cổng
Mặc định React chạy trên cổng 3000. Để chạy trên cổng khác:

```bash
PORT=3001 npm start
```

### Build cho production

```bash
npm run build
```

Các file build sẽ nằm trong thư mục `build/`.

Để serve:
```bash
npx serve -s build
```

### Environment Variables

| Biến | Giá trị mặc định | Mô tả |
|------|-----------------|-------|
| `REACT_APP_API_URL` | `http://localhost:8000/api/v1` | URL backend API |

## 🐛 Troubleshooting

### Lỗi CORS
**Vấn đề**: `Access to XMLHttpRequest blocked by CORS policy`

**Giải pháp**: Đảm bảo backend đã kích hoạt CORS. Kiểm tra trong `config.py`:
```python
ENABLE_CORS = True
```

### Không thể kết nối tới API
**Vấn đề**: `Failed to fetch`

**Giải pháp**: 
1. Kiểm tra backend có đang chạy không
2. Kiểm tra URL API trong `.env.local` có đúng không
3. Kiểm tra firewall không chặn port 8000

### Upload file thất bại
**Vấn đề**: `Failed to upload documents`

**Giải pháp**:
1. Kiểm tra kích thước file (có thể có giới hạn)
2. Kiểm tra định dạng file (hỗ trợ PDF, TXT, DOCX)
3. Kiểm tra backend có đủ bộ nhớ không

## 📦 Dependencies

- **react**: UI framework
- **axios**: HTTP client
- **react-hot-toast**: Notification system
- **react-icons**: Icon library

## 📝 Ghi chú

- Ứng dụng sử dụng localStorage để lưu trữ cục bộ (nếu cần)
- API client có interceptor tự động handle lỗi
- Mỗi câu hỏi có ID cuộc trò chuyện riêng để theo dõi

## 📞 Hỗ trợ

Nếu gặp vấn đề, kiểm tra console browser (F12) để xem chi tiết lỗi.

## 📄 Giấy phép

Xem LICENSE file trong Backend folder
