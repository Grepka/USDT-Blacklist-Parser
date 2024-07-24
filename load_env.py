import os

def load_env_file(file_path='/root/BlackList_parser/.env'):
    """Загружает переменные окружения из файла .env."""
    if os.path.exists(file_path):
        with open(file_path) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

load_env_file()
