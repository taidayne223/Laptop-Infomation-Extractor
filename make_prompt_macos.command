#!/usr/bin/env bash
# macOS launcher for Laptop Information Extractor

# Change directory to the folder containing this script
cd "$(dirname "$0")"

echo "=========================================="
echo "LAPTOP INFORMATION EXTRACTOR FOR MACOS"
echo "=========================================="
echo "Đang kiểm tra và thu thập thông tin cấu hình..."
echo ""

# Run the python script
if command -v python3 >/dev/null 2>&1; then
  python3 -m infomation_extractor "$@"
elif command -v python >/dev/null 2>&1; then
  python -m infomation_extractor "$@"
else
  echo "LỖI: Không tìm thấy Python 3 trên máy của bạn." >&2
  echo "Vui lòng cài đặt Python 3 từ https://www.python.org/downloads/ hoặc qua Homebrew." >&2
  echo ""
  echo "Nhấn Enter để thoát..."
  read -r
  exit 1
fi

echo ""
echo "=========================================="
echo "Hoàn thành! File prompt đã được tạo trong thư mục outputs/."
echo "Nhấn Enter để thoát..."
read -r
