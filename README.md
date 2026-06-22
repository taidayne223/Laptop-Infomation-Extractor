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
* Prompt bao gồm bảng thông số dễ đọc và phụ lục JSON đã khử riêng tư, giúp AI cloud có thêm bằng chứng local để xác minh đúng model/variant khi làm Deep Research.

---

## 🔒 Bảo mật & Riêng tư
* Chương trình tự động ẩn (Redact) các thông tin nhạy cảm như Serial Number, UUID, Service Tag trước khi lưu vào file kết quả để bảo vệ sự riêng tư của bạn.
* File prompt được sinh ra trong `Noi luu File ket qua/` là dữ liệu máy thật, chỉ nên dùng local hoặc upload trực tiếp cho AI bạn chọn. Thư mục này đã được ignore để không vô tình push lên GitHub.
* Các thông tin dễ lộ danh tính như đường dẫn user, hostname/tên máy, email, registry/device path, nhãn ổ đĩa, địa chỉ IP/MAC và tên mạng Wi-Fi cũng được khử hoặc ẩn trong dữ liệu xuất ra.
