import html
from .util import get_database, get_g_list, get_search, adjust_list, adjust_img, delete_img


# 保存问答
async def set_que(bot, group_id: str, user_id: str, que_raw: str, ans_raw: str, gid: str) -> str:
    db = await get_database()
    # html转码
    que_raw = html.unescape(que_raw)
    ans_raw = html.unescape(ans_raw)
    # 新问题就调整并下载图片
    que_raw = await adjust_img(bot, que_raw, save=True)
    # 已有问答再次设置的话，就先删除旧图片
    gid = gid if group_id == 'all' else group_id
    ans_old = db.get(gid, {}).get(user_id, {}).get(que_raw, [])
    if ans_old: await delete_img(ans_old)
    # 保存新的回答
    ans_raw = await adjust_img(bot, ans_raw, save=True)
    ans = ans_raw.split('#')
    ans = await adjust_list(ans, '#')
    group_list = await get_g_list(bot)
    for group_id in group_list:
        group_dict = db.get(group_id, {'all': {}})
        group_dict['all'][que_raw] = ans
        db[group_id] = group_dict
    return '好的我记住了'


# 删除问答
async def del_que(bot, group_id: str, user_id: str, unque_str: str, is_singer_group: bool = True, is_self: bool = False) -> tuple:
    db = await get_database()
    unque_str = html.unescape(unque_str)
    group_dict = db.get(group_id, {'all': {}})
    user_dict = group_dict.get(user_id, {})
    # 删除我问
    if is_self:
        if (not user_dict.get(unque_str)) and (not group_dict['all'].get(unque_str)):
            return '没有这张图呢', ''
        elif (not user_dict.get(unque_str)) and (group_dict['all'].get(unque_str)):
            return '你没有权限删除呢', ''
        else:
            ans = user_dict.get(unque_str)
            user_dict.pop(unque_str)
            group_dict[user_id] = user_dict
    # 删除有人问和全群问
    else:
        if (not user_dict.get(unque_str)) and (not group_dict['all'].get(unque_str)):
            return '没有这张图呢' if is_singer_group else '', ''
        elif user_dict.get(unque_str):
            ans = user_dict.get(unque_str)
            user_dict.pop(unque_str)
            group_dict[user_id] = user_dict
        else:
            ans = group_dict['all'].get(unque_str)
            group_dict['all'].pop(unque_str)
    ans_str = '#'.join(ans)  # 调整图片
    ans_str = await adjust_img(bot, ans_str, is_ans=True)
    ans.append(unque_str)
    db[group_id] = group_dict
    return f'我忘了 “{ans_str}” 了', ans  # 返回输出文件以及需要删除的图片


# 显示问答
async def show_que(group_id: str, user_id: str, search_str: str, is_self: bool = True) -> str:
    db = await get_database()
    search_str = html.unescape(search_str)
    msg = f'查询 “{search_str}” 相关的结果如下：\n' if (search_str and is_self) else ''
    msg_head = '本群中' if is_self else f'\n群{group_id}中'
    subject = '管理员' if user_id == 'all' else '你'
    if user_id == 'all':
        group_dict = db.get(group_id, {'all': {}})
        que_list = await get_search(list(group_dict['all'].keys()), search_str)
    else:
        group_dict = db.get(group_id, {'all': {}})
        user_dict = group_dict.get(user_id, {})
        que_list = await get_search(list(user_dict.keys()), search_str)
    if not que_list:
        msg += f'{msg_head}没有找到有关{subject}的图' if is_self else ''
    else:
        msg += f'{msg_head}{subject}设置的问题有：\n' + ' | '.join(que_list)
    return msg
