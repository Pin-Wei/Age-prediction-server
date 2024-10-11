import os
import sys

# 獲取當前腳本的目錄
current_dir = os.path.dirname(os.path.abspath(__file__))
# 將當前目錄添加到 Python 路徑
sys.path.append(current_dir)

from textreading_processor import TextReadingProcessor

processor = TextReadingProcessor('data', 'output')
result = processor.process_subject('A555555555')
print(result)