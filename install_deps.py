import subprocess
import sys

packages = ['aiosqlite', 'python-dotenv']

for package in packages:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
