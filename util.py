import os
import re
import beautiful
import json
import random
import urllib
from sqlitedict import SqliteDict
from hoshino import R, logger, util
from .textfilter.filter import DFAFilter

file_path = R.img("image_match").path

# 是否使用星乃自带的严格词库（可随时改动，重启生效）
# use_strict = True     # 使用星乃自带敏感词库
use_strict = False  # 使用XQA自带敏感词库


async def get_database() -> SqliteDict:
    # 创建目录
    img_path = os.path.join(file_path, 'img/')
    if not os.path.exists(img_path):
        os.makedirs(img_path)
    db_path = os.path.join(file_path, 'data.sqlite')
    # 替换默认的pickle为json的形式读写数据库
    db = SqliteDict(db_path, encode=json.dumps, decode=json.loads, autocommit=True)
    return db


async def get_g_list(bot) -> list:
    group_list = await bot.get_group_list()
    g_list = []
    for group in group_list:
        group_id = group['group_id']
        g_list.append(str(group_id))
    return g_list


# 匹配替换字符
async def replace_message(match_que: re.Match, match_dict: dict, que: str) -> str:
    ans_tmp = match_dict.get(que)
    # 随机选择
    ans = random.choice(ans_tmp)
    flow_num = re.search(r'\S*\$([0-9])\S*', ans)
    if not flow_num:
        return ans
    for i in range(int(flow_num.group(1))):
        ans = ans.replace(f'${i + 1}', match_que.group(i + 1))
    return ans


async def get_search(que_list: list, search_str: str) -> list:
    if not search_str:
        return que_list
    search_list = []
    for question in que_list:
        if re.search(rf'\S*{search_str}\S*', question):
            search_list.append(question)
    return search_list


# 进行图片处理
async def adjust_img(bot, str_raw: str, is_ans: bool = False, save: bool = False) -> str:
    flit_msg = beautiful(str_raw) # 整个消息匹配敏感词
    cq_list = re.findall(r'([CQ:(\S+?),(\S+?)=(\S+?)])', str_raw) # 找出其中所有的CQ码
    # 对每个CQ码元组进行操作
    for cqcode in cq_list:
        flit_cq = beautiful(cqcode[0])  # 对当前的CQ码匹配敏感词
        raw_body = cqcode[3].split(',')[0].split('.image')[0].split('/')[-1].split('\\')[-1] # 获取等号后面的东西，并排除目录
        print("       $$$")
        print(raw_body)
        print("       $$$")
        if cqcode[1] == 'image':
            # 对图片单独保存图片，并修改图片路径为真实路径
            raw_body = raw_body if '.' in raw_body else raw_body + '.image'
            raw_body = await doing_img(bot, raw_body, is_ans, save)
        if is_ans:
            # 如果是回答的时候，就将 匹配过的消息 中的 匹配过的CQ码 替换成未匹配的
            flit_msg = flit_msg.replace(flit_cq, f'[CQ:{cqcode[1]},{cqcode[2]}={raw_body}]')
        else:
            # 如果是保存问答的时候，就只替换图片的路径，其他CQ码的替换相当于没变
            str_raw = str_raw.replace(cqcode[0], f'[CQ:{cqcode[1]},{cqcode[2]}={raw_body}]')
    return str_raw if not is_ans else flit_msg


# 匹配消息
async def match_ans(info: dict, message: str, ans: str) -> str:
    list_tmp = list(info.keys())
    list_tmp.reverse()
    # 优先完全匹配
    if message in list_tmp:
        return random.choice(info[message])
    # 其次正则匹配
    for que in list_tmp:
        try:
            if re.match(que + '$', message):
                ans = await replace_message(re.match(que + '$', message), info, que)
                break
        except re.error:
            # 如果que不是re.pattern的形式就跳过
            continue
    return ans


# 下载以及分类图片
async def doing_img(bot, img: str, is_ans: bool = False, save: bool = False) -> str:
    img_path = os.path.join(file_path, 'img/')
    if save:
        try:
            img_url = await bot.get_image(file=img)
            file = os.path.join(img_path, img)
            if not os.path.isfile(img_path + img):
                urllib.request.urlretrieve(url=img_url['url'], filename=file)
                logger.critical(f'XQA: 已下载图片{img}')
        except:
            if not os.path.isfile(img_path + img):
                logger.critical(f'XQA: 图片{img}已经过期，请重新设置问答')
            pass
    if is_ans:  # 保证保存图片的完整性，方便迁移和后续做操作
        return 'file:///' + os.path.abspath(img_path + img)
    return img


# 调整转义分割字符 “#”
async def adjust_list(list_tmp: list, char: str) -> list:
    ans_list = []
    str_tmp = list_tmp[0]
    i = 0
    while i < len(list_tmp):
        if list_tmp[i].endswith('\\'):
            str_tmp += char + list_tmp[i + 1]
        else:
            ans_list.append(str_tmp)
            str_tmp = list_tmp[i + 1] if i + 1 < len(list_tmp) else list_tmp[i]
        i += 1
    return ans_list


# 删啊删
async def delete_img(list_raw: list) -> list:
    for str_raw in list_raw:
        img_list = re.findall(r'(\[CQ:image,file=(.+?\.image)\])', str_raw)
        for img in img_list:
            file = img[1]
            try:
                file = os.path.split(file)[-1]
            except:
                pass
            try:
                os.remove(os.path.abspath(file_path + '/img/' + img[1]))
                logger.info(f'XQA: 已删除图片{file}')
            except:
                logger.info(f'XQA: 图片{file}不存在，无需删除')


# 和谐模块
def beautifulworld(msg: str) -> str:
    w = ''
    infolist = msg.split('[')
    for i in infolist:
        if i:
            try:
                w = w + '[' + i.split(']')[0] + ']' + beautiful(i.split(']')[1])
            except:
                w = w + beautiful(i)
    return w


# 切换和谐词库
def beautiful(msg: str, strict: bool = use_strict) -> str:
    beautiful_message = DFAFilter()
    beautiful_message.parse(os.path.join(os.path.dirname(__file__), 'textfilter/sensitive_words.txt'))
    if strict:
        msg = util.filt_message(msg)
    else:
        msg = beautiful_message.filter(msg)
    return msg

