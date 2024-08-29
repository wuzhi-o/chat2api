import csv
import json
import os

from utils.Logger import logger

DATA_FOLDER = "data"
# TOKENS_FILE = os.path.join(DATA_FOLDER, "token.txt")
REFRESH_MAP_FILE = os.path.join(DATA_FOLDER, "refresh_map.json")
ERROR_TOKENS_FILE = os.path.join(DATA_FOLDER, "error_token.txt")
WSS_MAP_FILE = os.path.join(DATA_FOLDER, "wss_map.json")
AUTHORIZATION_FILE = os.path.join(DATA_FOLDER, "authorization.txt")

count = 0
authorization_list = []
token_list = []
error_token_list = []
refresh_map = {}
wss_map = {}


def get_all_tokens_from_csv(filepath):
    # 检查文件是否存在
    if not os.path.exists(filepath):
        return ''  # 文件不存在，返回空字符串

    tokens = []

    try:
        # 打开 CSV 文件
        with open(filepath, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            # 遍历每一行，获取 'Key' 列的值
            for row in reader:
                tokens.append(row['Token'])

        # 将所有的 Key 用英文逗号分隔并连成一个字符串
        return ','.join(tokens)

    except Exception as e:
        # 处理文件读取中的其他潜在错误，返回空字符串
        print(f"Error reading file: {e}")
        return ''


def update_token_list():
    global token_list
    tokens = get_all_tokens_from_csv('data/accounts.csv').replace(' ', '')
    token_list = tokens.split(',') if tokens else []
    logger.info(str(token_list))


update_token_list()

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

if os.path.exists(REFRESH_MAP_FILE):
    with open(REFRESH_MAP_FILE, "r") as file:
        refresh_map = json.load(file)
else:
    refresh_map = {}

if os.path.exists(WSS_MAP_FILE):
    with open(WSS_MAP_FILE, "r") as file:
        wss_map = json.load(file)
else:
    wss_map = {}

# if os.path.exists(TOKENS_FILE):
#    with open(TOKENS_FILE, "r", encoding="utf-8") as f:
#        for line in f:
#            if line.strip() and not line.startswith("#"):
#                token_list.append(line.strip())
# else:
#    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
#        pass

if os.path.exists(ERROR_TOKENS_FILE):
    with open(ERROR_TOKENS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                error_token_list.append(line.strip())
else:
    with open(ERROR_TOKENS_FILE, "w", encoding="utf-8") as f:
        pass

if token_list:
    logger.info(f"Token list count: {len(token_list)}, Error token list count: {len(error_token_list)}")
