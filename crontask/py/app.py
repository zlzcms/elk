from datetime import datetime, timedelta
import aiohttp
import json
from fastapi import FastAPI, Request
from loguru import logger


app = FastAPI()

# lark消息格式
# {
#     "msg_type": "post",
#     "content": {
#         "post": {
#             "zh_cn": {
#                     "title": "接口异常通知",
#                     "content": [
#                         [{
#                             "tag": "text",
#                             "text": "事件名: xasdad"
#                         }],
#                         [{
#                             "tag": "text",
#                             "text": "事件组: xasdad"
#                         }],
#                         [{
#                             "tag": "text",
#                             "text": "事件描述: xasdad"
#                         }],
#                         [{
#                             "tag": "a",
#                             "text": "点击查看任务详情",
#                             "href": "http://www.example.com/"
#                         }]
#                     ]
#                 }
#         }
#     }
# }


@app.post("/lark/msg", summary="发送 Lark msg")
async def sendlarkmsg(request: Request):
    bb = await request.json()
    #print(json.dumps(bb,indent=4))
    action = bb.get('action',None)
    if action == 'job_start':
        return 'OK'
    if action not in ['job_launch_failure','job_complete']:
        logger.warning(f"{action} is not support: {bb}")
        return 'OK'
    
    if 'code' in bb and bb.get('code') == 0:
        logger.info(f"{action} is success, {bb.get('event_title')}")
        return 'OK'
    
    data = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "接口异常通知",
                    "content": []
                }
            }
        }
    }

    key_zh =  {
        "event_title": "事件名称",
        "category_title": "事件组别",
        #"action": "事件状态",
        "code": "返回代码",
        "description": "结果描述",
        #"complete": "是否完成",
        #"job_details_url": "任务详情",
        #"edit_event_url": "事件详情",
        #"html": "原始返回",
        #"content":"原始内容",
        #"time_start": "开始时间",
        "elapsed": "总耗时(s)",
    }


    # 定义一个新的 tag 
    # 将新的 tag 添加到 content 列表中
    for key,name in key_zh.items():
        valume = bb.pop(key,None)
        if valume:
            new_tag = [{"tag": "text", "text": f"{name}:\t {valume}"}]
            data["content"]["post"]["zh_cn"]["content"].append(new_tag)  

            if key == 'description' and 'timeout' in str(valume).lower():
                logger.warning(f"任务超时警告: {bb.get('event_title')} , 不发送")   # 任务超时不发送 消息，误触太多
                return 'OK'
            
    html  = bb.pop('html',None)
    if html:
        str_to_show = html.pop('content',None).strip('<pre>').strip('</pre>').strip()
        try:
            dddd = json.loads(str_to_show)
            str_to_show = dddd['message']
        except Exception as e:
            print(f"发生错误: {e}")
        new_tag = [{"tag": "text", "text": f"原始返回:\t {str_to_show}"}]
        data["content"]["post"]["zh_cn"]["content"].append(new_tag)  


    job_details_url = bb.pop('job_details_url',None) 
    if job_details_url:
        new_tag = [{"tag": "a", "text": "点击查看任务详情","href": f"{job_details_url}"}]
        data["content"]["post"]["zh_cn"]["content"].append(new_tag)  
    else:
        edit_event_url =  bb.pop('edit_event_url',None)
        if edit_event_url:
            new_tag = [{"tag": "a", "text": "点击查看事件详情","href": f"{edit_event_url}"}]
            data["content"]["post"]["zh_cn"]["content"].append(new_tag)  

    #   "plugin": "shellplug",
    # "plugin": "urlplug",
    url = 'https://open.larksuite.com/open-apis/bot/v2/hook/d81e234c-7aaa-40ae-90e0-ba5c2431c0e0'
    pri_url = bb['params'].pop('lark_url',None)  
    if pri_url:
        url = pri_url

    async with aiohttp.ClientSession() as session:
        async with session.post(url,json= data) as response:
            response_json = await response.json()
            if response_json['code']==0:
                return 'ok'
            else:
                logger.warning("Lark 消息发送失败" + response_json)
    # obj=await sess.get(...)
    # do something
    return 'OK' 

#  {
#     "event_title": "122-TD-Login-\u6d4b\u8bd5",
#     "category_title": "General",
#     "complete": 1,
#     "code": 401,
#     "description": "HTTP 401 Unauthorized",
#     "html": {
#         "title": "Raw Response Content",
#         "content": "<pre>{\"code\":3,\"desc\":\"Authentication failure\",\"timing\":10253540}</pre>"
#     },
#     "action": "job_complete",
# }

# {
#     "username": "peter",
#     "action": "job_launch_failure",
#     "code": 1,
#     "description": "Maximum of 1 job already running for event: K\u7ebf\u670d\u52a1",
#     "event_title": "K\u7ebf\u670d\u52a1",
#     "edit_event_url": "http://localhost:3012/#Schedule?sub=edit_event&id=em66kig7f09",
# }


# {
#     "event_title": "K\u7ebf\u670d\u52a1",
#     "category_title": "GTC",
#     "complete": 1,
#     "code": 1,
#     "description": "Request Timeout (10000 ms)",
#     "action": "job_complete",
#     "job_details_url": "http://localhost:3012/#JobDetails?id=jm66m6ks00z",
# }