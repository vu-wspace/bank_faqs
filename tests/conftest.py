import os

# Các module khởi tạo client Groq/Tavily ngay khi import -> cần key (giá trị giả là đủ, test không gọi API thật)
os.environ.setdefault('GROQ_API_KEY', 'test-key')
os.environ.setdefault('TAVILY_API_KEY', 'test-key')
