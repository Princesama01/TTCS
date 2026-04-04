# 🚀 HƯỚNG DẪN NHANH - FRONTEND RAG

## 📋 Yêu cầu
- Node.js 14 trở lên (tải từ https://nodejs.org/)
- npm (kèm theo Node.js)

## ⚡ Bước 1: Cài đặt (5 phút)

```bash
# 1. Mở Terminal/PowerShell
# 2. Chuyển đến thư mục Frontend
cd d:\TTCS\Code\Frontend

# 3. Cài đặt thư viện
npm install
```

## 🎯 Bước 2: Cấu hình Backend

Sửa file `.env.local`:
```
REACT_APP_API_URL=http://localhost:8000/api/v1
```

(Nếu backend chạy ở port khác, thay đổi URL tương ứng)

## ▶️ Bước 3: Chạy ứng dụng

```bash
npm start
```

Trình duyệt sẽ tự mở tại `http://localhost:3000`

## 📚 Sử dụng

### Tab 1: 💬 Chat
- Nhập câu hỏi về tài liệu
- Chọn ngôn ngữ: Tiếng Việt hoặc English
- Bật "Hiển thị tài liệu nguồn" để xem nguồn
- Click "Gửi" hoặc Enter

### Tab 2: 📤 Upload Tài Liệu
- Kéo thả tệp hoặc nhấp "Chọn tệp"
- Hỗ trợ: PDF, TXT, DOCX
- Điều chỉnh "Kích thước khối" (512 là tốt)
- Nhấp "Tải lên" để xử lý

### Tab 3: 📋 Quản Lý Tài
- Xem tất cả tài liệu đã upload
- Tìm kiếm theo tên
- Sắp xếp: theo tên, kích thước, hoặc ngày
- Nhấp 🗑️ để xóa

## ⚙️ Cài đặt Advanced

### Chạy trên port khác
```bash
PORT=3001 npm start
```

### Build cho production
```bash
npm run build
```

### Chạy build version
```bash
npx serve -s build
```

## 🆘 Lỗi Thường Gặp

| Lỗi | Giải pháp |
|-----|----------|
| `npm: command not found` | Cài Node.js lại |
| `Port 3000 in use` | Thay đổi port hoặc đóng process cũ |
| `Cannot connect to API` | Kiểm tra backend chạy ở port 8000 |
| `CORS error` | Bật CORS trong backend config.py |

## 📁 Cấu trúc Thư Mục

```
Frontend/
├── src/
│   ├── components/      # Chat, Upload, DocumentList
│   ├── api/            # Kết nối API
│   └── App.js          # Component chính
├── package.json
├── .env.local          # Config
└── README.md
```

## 💡 Tips

✅ Giữ Terminal mở để nhất log  
✅ Kiểm tra console browser (F12) để debug  
✅ Reload trang nếu gặp vấn đề  
✅ Đảm bảo Backend chạy ở port 8000  

---

**Cần giúp?** Xem chi tiết README.md
