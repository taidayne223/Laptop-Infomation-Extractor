# Laptop Information Extractor

Công cụ tự động thu thập thông tin cấu hình phần cứng của laptop (Windows & macOS) và xuất ra một file Prompt tối ưu để gửi cho AI (Gemini, ChatGPT, Claude) phục vụ Deep Research.

---

## ⚡ Hướng dẫn sử dụng nhanh

###  Trên macOS:
1. Nhấp đúp chuột (Double-click) vào file `make_prompt_macos.command` ở thư mục này.
2. Chương trình sẽ tự động thu thập cấu hình và tạo file Prompt.

### ❖ Trên Windows:
1. Nhấp đúp chuột (Double-click) hoặc chạy file `make_prompt.bat` trong Terminal.

---

## 📁 Kết quả lưu ở đâu?

* Sau khi chạy xong, file Prompt kết quả sẽ được lưu trong thư mục:
  👉 **`Noi luu File ket qua/`**
* Đồng thời, hệ thống sẽ **tự động mở file** prompt và **mở thư mục chứa file** này để bạn dễ dàng copy/upload lên AI.

---

## 🔒 Bảo mật & Riêng tư
* Chương trình tự động ẩn (Redact) các thông tin nhạy cảm như Serial Number, UUID, Service Tag trước khi lưu vào file kết quả để bảo vệ sự riêng tư của bạn.
