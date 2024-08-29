import asyncio
import csv
import os
import types
import warnings

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from starlette.responses import RedirectResponse

from chatgpt.ChatService import ChatService
from chatgpt.authorization import refresh_all_tokens
import chatgpt.globals as globals
from chatgpt.reverseProxy import chatgpt_reverse_proxy
from utils import config
from utils.Logger import logger
from utils.config import api_prefix, scheduled_refresh
from utils.retry import async_retry

warnings.filterwarnings("ignore")

app = FastAPI()


# 挂载静态文件目录
app.mount("/statics", StaticFiles(directory="statics"), name="statics")
scheduler = AsyncIOScheduler()
templates = Jinja2Templates(directory="templates")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def app_start():
    if scheduled_refresh:
        scheduler.add_job(id='refresh', func=refresh_all_tokens, trigger='cron', hour=3, minute=0, day='*/4',
                          kwargs={'force_refresh': True})
        scheduler.start()
        asyncio.get_event_loop().call_later(0, lambda: asyncio.create_task(refresh_all_tokens(force_refresh=False)))


async def to_send_conversation(request_data, req_token):
    chat_service = ChatService(req_token)
    try:
        await chat_service.set_dynamic_data(request_data)
        await chat_service.get_chat_requirements()
        return chat_service
    except HTTPException as e:
        await chat_service.close_client()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        await chat_service.close_client()
        logger.error(f"Server error, {str(e)}")
        raise HTTPException(status_code=500, detail="Server error")


async def process(request_data, req_token):
    chat_service = await to_send_conversation(request_data, req_token)
    await chat_service.prepare_send_conversation()
    res = await chat_service.send_conversation()
    return chat_service, res


@app.post("/v1/chat/completions")
async def send_conversation(request: Request, req_token: str = Depends(oauth2_scheme)):
    try:
        request_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "Invalid JSON body"})
    chat_service, res = await async_retry(process, request_data, req_token)
    try:
        if isinstance(res, types.AsyncGeneratorType):
            background = BackgroundTask(chat_service.close_client)
            return StreamingResponse(res, media_type="text/event-stream", background=background)
        else:
            background = BackgroundTask(chat_service.close_client)
            return JSONResponse(res, media_type="application/json", background=background)
    except HTTPException as e:
        await chat_service.close_client()
        if e.status_code == 500:
            logger.error(f"Server error, {str(e)}")
            raise HTTPException(status_code=500, detail="Server error")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        await chat_service.close_client()
        logger.error(f"Server error, {str(e)}")
        raise HTTPException(status_code=500, detail="Server error")


@app.get(f"/{api_prefix}/admin", response_class=HTMLResponse)
async def admin_html(request: Request):
    tokens_count = len(set(globals.token_list) - set(globals.error_token_list))
    error_tokens_list = list(set(globals.error_token_list))
    #logger.info(str(error_tokens_list))
    # 读取 accounts.csv 文件内容
    accounts = []
    accounts_csv = "data/accounts.csv"
    if os.path.isfile(accounts_csv):
        with open(accounts_csv, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            accounts = list(reader)
    #logger.info(str(accounts))
    # 读取 users.csv 文件内容
    users = []
    users_csv = "data/users.csv"
    if os.path.isfile(users_csv):
        with open(users_csv, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            users = list(reader)

    # 读取 config.py 中的配置信息
    configs=config.get_config()
    # 将数据传递给模板
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "accounts": accounts,
        "users": users,
        "configs": configs,
        "api_prefix": api_prefix,
        "tokens_count": tokens_count,
        "error_tokens": error_tokens_list,
    })


@app.post(f"/{api_prefix}/admin/upload-account")
async def upload_account(request: Request, text: str = Form(...)):
    # 将输入的文本按行分割
    lines = text.strip().split("\n")

   # print(lines)

    # 检查 CSV 文件是否存在，以决定是否需要写入表头
    csv_file = "data/accounts.csv"
    file_exists = os.path.isfile(csv_file)

    # 打开 CSV 文件并写入数据
    with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # 如果文件不存在，则写入表头
        if not file_exists:
            writer.writerow(['Account', 'Password', 'Token'])
        for line in lines:
            # 假设每行数据是用逗号分隔的：账号,密码,Token
            parts = [part.strip() for part in line.split(',')]
            if len(parts) == 3:  # 确保有三个部分
                writer.writerow(parts)
            else:
                # 如果行格式不正确，可以选择忽略或记录错误
                continue
    globals.update_token_list()
    # 重定向到 /admin 页面
    return RedirectResponse(url=f"/{api_prefix}/admin#tab-1", status_code=303)


@app.post(f"/{api_prefix}/admin/edit-account"+"/{account_id}")
async def update_account(request: Request, account_id: int, account: str = Form(...), password: str = Form(...),
                         token: str = Form(...)):
    # 加载现有的账户信息
    with open("data/accounts.csv", mode='r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        accounts = list(reader)
    # 更新特定的账户信息
    accounts[account_id] = [account, password, token]
    # 保存更新后的账户信息
    with open("data/accounts.csv", mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(accounts)
    globals.update_token_list()
    return RedirectResponse(url=f"/{api_prefix}/admin#tab-1", status_code=302)


@app.post(f"/{api_prefix}/admin/delete-account/"+"{account_id}")
async def delete_account(account_id: int):
    # 加载现有的账户信息
    with open("data/accounts.csv", mode='r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        accounts = list(reader)
    # 删除指定账户
    accounts.pop(account_id)
    # 保存更新后的账户信息
    with open("data/accounts.csv", mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(accounts)
    globals.update_token_list()
    return RedirectResponse(url=f"/{api_prefix}/admin#tab-1", status_code=302)


@app.post(f"/{api_prefix}/admin/delete-all-accounts")
async def delete_all_accounts():
    file_path = "data/accounts.csv"
    if os.path.exists(file_path):
        os.remove(file_path)
    globals.update_token_list()
    return RedirectResponse(url=f"/{api_prefix}/admin#tab-1", status_code=302)


@app.post(f"/{api_prefix}/admin/upload-user")
async def upload_user(request: Request, text: str = Form(...)):
    # 将输入的文本按行分割
    lines = text.strip().split("\n")
    # 检查CSV文件是否存在，以决定是否需要写入表头
    csv_file = "data/users.csv"
    file_exists = os.path.isfile(csv_file)
    # 打开CSV文件并写入数据
    with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # 如果文件不存在，则写入表头
        if not file_exists:
            writer.writerow(['User', 'Key', 'Note'])
        for line in lines:
            parts = [part.strip() for part in line.split(',')]
            if len(parts) == 3:  # 确保有三个部分
                writer.writerow(parts)
            else:
                # 如果行格式不正确，可以选择忽略或记录错误
                continue
    config.update_user_list()
    return RedirectResponse(url=f"/{api_prefix}/admin#tab-2", status_code=302)


@app.post(f"/{api_prefix}/admin/edit-user/"+"{user_id}")
async def update_user(request: Request, user_id: int, user: str = Form(...), key: str = Form(...),
                         note: str = Form(...)):
    # 加载现有的账户信息
    with open("data/users.csv", mode='r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        users = list(reader)
    # 更新特定的账户信息
    users[user_id] = [user, key, note]
    # 保存更新后的账户信息
    with open("data/users.csv", mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(users)
    config.update_user_list()
    return RedirectResponse(url=f"/{api_prefix}/admin#tab-2", status_code=302)


@app.post(f"/{api_prefix}/admin/delete-user/"+"{user_id}")
async def delete_user(user_id: int):
    # 加载现有的账户信息
    with open("data/users.csv", mode='r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        users = list(reader)
    # 删除指定账户
    users.pop(user_id)
    # 保存更新后的账户信息
    with open("data/users.csv", mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(users)
    config.update_user_list()
    return RedirectResponse(url=f"/{api_prefix}/admin#tab-2", status_code=302)


@app.post(f"/{api_prefix}/admin/delete-all-users")
async def delete_all_users():
    file_path = "data/users.csv"
    if os.path.exists(file_path):
        os.remove(file_path)
    config.update_user_list()
    return RedirectResponse(url=f"/{api_prefix}/admin#tab-2", status_code=302)


@app.post(f"/{api_prefix}/admin/update-config")
async def update_config(
        request: Request,
        chatgpt_base_url: str = Form(...),
        proxy_url: str = Form(""),
        retry_times: int = Form(...),
        enable_limit: bool = Form(...),
        scheduled_refresh: bool = Form(...),
        auth_key: str = Form(None),  # 允许为空
        user_agents: str = Form(None),  # 允许为空，默认值为 ""
        history_disabled: bool = Form(...)
):
    # 更新配置
    kwargs = {
        "chatgpt_base_url": chatgpt_base_url,
        "proxy_url": proxy_url,
        "retry_times": retry_times,
        "enable_limit": enable_limit,
        "scheduled_refresh": scheduled_refresh,
        "auth_key": auth_key,
        "user_agents": user_agents,
        "history_disabled": history_disabled,
    }
    # 调用 edit_config 更新配置
    config.edit_config(**kwargs)
    # 重定向回管理页面
    return RedirectResponse(url=f"/{api_prefix}/admin#tab-3", status_code=302)