import re
import html
from hoshino import Service, priv
from .util import get_database, match_ans, adjust_img, get_g_list, delete_img
from .operate_msg import set_que, del_que, show_que


sv_help = '''
发送查表情来获取表情
发送上传**#[图片]来上传图片
示例：上传手机里有原神#[图片]
'''.strip()


sv = Service('image_match', enable_on_default=True, help_=sv_help)


@sv.on_fullmatch('表情帮助')
async def help(bot, ev):
    await bot.send(ev, sv_help)


# 设置问答，支持正则表达式和回流
@sv.on_message('group')
async def set_question(bot, ev):
    results = re.match(r'^上传([\s\S]*)~([\s\S]*)$', str(ev.message))
    if not results: return
    tag_raw, img_raw = results.group(1), results.group(2)
    if (not tag_raw) or (not img_raw):
        await bot.finish(ev, f'上传我才记得住~')
    group_id, user_id = 'all', str(ev.user_id)
    print("       $$$111")
    print(img_raw)
    print("       $$$1111")
    msg = await set_que(bot, group_id, user_id, tag_raw, img_raw, str(ev.group_id))
    await bot.send(ev, msg)


@sv.on_prefix('查表情')
async def search(bot, ev):
    search_str = ev['match'].group(1)
    group_id, user_id = str(ev.group_id), str(ev.user_id)
    msg = f'可能是在找'
    msg += await show_que(group_id, user_id, search_str)
    await bot.send(ev, msg)


@sv.on_message('group')
async def image_match(bot, ev):
    group_id, user_id, message = str(ev.group_id), str(ev.user_id), str(ev.message)
    db = await get_database()
    group_dict = db.get(group_id, {'all': {}})
    message = html.unescape(message)
    # 仅调整问题中的图片
    message = await adjust_img(bot, message)
    # 优先回复自己的问答
    ans = await match_ans(group_dict.get(user_id, {}), message, '')
    # 没有自己的问答才回复有人问
    ans = await match_ans(group_dict['all'], message, ans) if not ans else ans
    if ans:
        ans = await adjust_img(bot, ans, is_ans=True, save=True)
        await bot.send(ev, ans)






