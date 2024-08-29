import ast
import os
import csv

from dotenv import load_dotenv

from utils.Logger import logger

load_dotenv(encoding="ascii")


def is_true(x):
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        return x.lower() in ['true', '1', 't', 'y', 'yes']
    elif isinstance(x, int):
        return x == 1
    else:
        return False


def get_all_keys_from_csv(filepath):
    # 检查文件是否存在
    if not os.path.exists(filepath):
        return ''  # 文件不存在，返回空字符串

    keys = []

    try:
        # 打开 CSV 文件
        with open(filepath, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            # 遍历每一行，获取 'Key' 列的值
            for row in reader:
                keys.append(row['Key'])

        # 将所有的 Key 用英文逗号分隔并连成一个字符串
        return ','.join(keys)

    except Exception as e:
        # 处理文件读取中的其他潜在错误，返回空字符串
        print(f"Error reading file: {e}")
        return ''


def update_user_list():
    global authorization_list
    authorization1 = get_all_keys_from_csv('data/users.csv').replace(' ', '')
    authorization_list = authorization1.split(',') if authorization1 else []
    logger.info(str(authorization_list))


api_prefix = os.getenv('API_PREFIX', "None")

authorization = get_all_keys_from_csv('data/users.csv').replace(' ', '')
chatgpt_base_url = os.getenv('CHATGPT_BASE_URL', 'https://chatgpt.com').replace(' ', '')
auth_key = os.getenv('AUTH_KEY', None)
user_agents = os.getenv('USER_AGENTS', '[]')

ark0se_token_url = os.getenv('ARK' + 'OSE_TOKEN_URL', '').replace(' ', '')
if not ark0se_token_url:
    ark0se_token_url = os.getenv('ARK0SE_TOKEN_URL', None)
proxy_url = os.getenv('PROXY_URL', '').replace(' ', '')
export_proxy_url = os.getenv('EXPORT_PROXY_URL', None)
cf_file_url = os.getenv('CF_FILE_URL', None)

history_disabled = is_true(os.getenv('HISTORY_DISABLED', True))
pow_difficulty = os.getenv('POW_DIFFICULTY', '000032')
retry_times = int(os.getenv('RETRY_TIMES', 3))
enable_gateway = is_true(os.getenv('ENABLE_GATEWAY', True))
conversation_only = is_true(os.getenv('CONVERSATION_ONLY', False))
enable_limit = is_true(os.getenv('ENABLE_LIMIT', True))
upload_by_url = is_true(os.getenv('UPLOAD_BY_URL', False))
check_model = is_true(os.getenv('CHECK_MODEL', False))
scheduled_refresh = is_true(os.getenv('SCHEDULED_REFRESH', False))

authorization_list = authorization.split(',') if authorization else []
chatgpt_base_url_list = chatgpt_base_url.split(',') if chatgpt_base_url else []
ark0se_token_url_list = ark0se_token_url.split(',') if ark0se_token_url else []
proxy_url_list = proxy_url.split(',') if proxy_url else []
user_agents_list = ast.literal_eval(user_agents)

logger.info("-" * 60)
logger.info("Chat2Api v1.4.5 | https://github.com/lanqian528/chat2api")
logger.info("-" * 60)
logger.info("Environment variables:")
logger.info("API_PREFIX:        " + str(api_prefix))
logger.info("AUTHORIZATION:     " + str(authorization_list))
logger.info("CHATGPT_BASE_URL:  " + str(chatgpt_base_url_list))
logger.info("AUTH_KEY:          " + str(auth_key))
logger.info("ARK0SE_TOKEN_URL:  " + str(ark0se_token_url_list))
logger.info("PROXY_URL:         " + str(proxy_url_list))
logger.info("EXPORT_PROXY_URL:  " + str(export_proxy_url))
logger.info("HISTORY_DISABLED:  " + str(history_disabled))
logger.info("POW_DIFFICULTY:    " + str(pow_difficulty))
logger.info("RETRY_TIMES:       " + str(retry_times))
logger.info("ENABLE_GATEWAY:    " + str(enable_gateway))
logger.info("CONVERSATION_ONLY: " + str(conversation_only))
logger.info("ENABLE_LIMIT:      " + str(enable_limit))
logger.info("UPLOAD_BY_URL:     " + str(upload_by_url))
logger.info("CHECK_MODEL:       " + str(check_model))
logger.info("SCHEDULED_REFRESH: " + str(scheduled_refresh))
logger.info("USER_AGENTS:       " + str(user_agents_list))
logger.info("-" * 60)


def get_config():
    """返回当前配置的字典"""
    return {
        "chatgpt_base_url": chatgpt_base_url,
        "proxy_url": proxy_url,
        "retry_times": retry_times,
        "enable_limit": enable_limit,
        "scheduled_refresh": scheduled_refresh,
        "auth_key": auth_key,
        "user_agents": user_agents_list,
        "history_disabled": history_disabled,
    }


def edit_config(**kwargs):
    """根据传入的关键字参数更新配置"""
    global chatgpt_base_url, chatgpt_base_url_list, proxy_url, proxy_url_list
    global retry_times, enable_limit, scheduled_refresh, auth_key
    global user_agents, user_agents_list, history_disabled

    # 更新每个配置项，如果 kwargs 中存在相应的键
    if "chatgpt_base_url" in kwargs:
        chatgpt_base_url = kwargs["chatgpt_base_url"]
        chatgpt_base_url_list = chatgpt_base_url.split(',')

    if "proxy_url" in kwargs:
        proxy_url = kwargs["proxy_url"]
        proxy_url_list = proxy_url.split(',') if proxy_url else []

    if "retry_times" in kwargs:
        retry_times = int(kwargs["retry_times"])

    if "enable_limit" in kwargs:
        enable_limit = is_true(kwargs["enable_limit"])

    if "scheduled_refresh" in kwargs:
        scheduled_refresh = is_true(kwargs["scheduled_refresh"])

    if "auth_key" in kwargs:
        if kwargs["auth_key"] == 'None':
            auth_key = None
        else:
            auth_key = kwargs["auth_key"]

    if "user_agents" in kwargs:
        user_agents = kwargs["user_agents"]
        user_agents_list = ast.literal_eval(user_agents)

    if "history_disabled" in kwargs:
        history_disabled = is_true(kwargs["history_disabled"])
