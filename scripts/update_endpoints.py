import os
import re
from core.config import Config

config = Config()
api_base = config.get_api_base()

def update_endpoints(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    # แทนที่ทั้ง URL พื้นฐาน
    new_content = re.sub(r'https://api\.anthropic\.com/v1', api_base.rstrip('/'), content)
    
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"Updated: {file_path}")

# ไฟล์ที่จะอัปเดต (ตัด core/config.py ออก)
files_to_update = [
    "api/claude_models.py",
    "api/claude_structured.py",
    "api/claude_files.py",
    "api/claude_cache.py",
    "api/claude_citations.py",
    "core/coder.py",
    "core/claude_code_exec.py",
    "core/claude_tools.py",
    "core/claude_code.py",
    "utils/claude_tokens.py",
    "agents/claude_router.py",
    "agents/claude_advisor.py",
    "agents/cowork.py",
    "agents/claude_fable5.py",
    "agents/claude_agents_sdk.py"
]

for file in files_to_update:
    if os.path.exists(file):
        update_endpoints(file)
