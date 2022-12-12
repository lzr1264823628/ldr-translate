import re
from api.server import baidu, tencent, youdao, google
import time
from utils import tools, config
from api import server_config
from utils.locales import t_ui, t

last_s_from = None
last_s_from_all = None
last_s_to_all = None
last_time = 0

no_translate_this = False

path_next_s = "s_next"
config_section = "setting"

# 整合一下，方便接入其他api接口


def text2(param):
    s_from, add_old = param
    return text(s_from, add_old)


def text(s_from, add_old=True):
    global last_s_from_all, last_s_from, last_s_to_all, last_time, no_translate_this

    to_lang_code, changeLang = tools.get_current_to_lang()
    server, changeServer = tools.get_current_translate_server()

    translate_span = config.get_config_setting("translate_span")

    if (s_from is None):
        if (last_s_from_all is None):
            return t_ui("notice_from"), t_ui("notice_to")
        elif (not add_old):
            s_from = last_s_from_all

    s_from = re.sub(r"-[\n|\r]+", "", s_from)
    #s_from = re.sub(r"(?<!\.|-|。)[\n|\r]+", " ", s_from)

    # 文字和上次一样，并且被翻译的语言没有修改，就不翻译了
    if (last_s_from == s_from and not changeLang and not changeServer):
        return last_s_from_all, last_s_to_all

    span = translate_span * 1.2 - (time.time() - last_time)
    if (span > 0):
        time.sleep(span)

    if (add_old):
        s_from_all = "%s %s" % (last_s_from_all, s_from)
    else:
        s_from_all = s_from

    try:
        last_s_to_all = translate(s_from_all, server, to_lang_code)
    except Exception as e:
        return s_from_all, "%s\n\n%s" % (t("error.request"), str(e))

    last_s_from = s_from
    last_s_from_all = s_from_all
    last_time = time.time()

    return last_s_from_all, last_s_to_all


def translate(s, server, to_lang_code, fromLang="auto"):

    if (server == server_config.server_tencent):
        s = tencent.translate_text(s, fromLang, to_lang_code)
    elif (server == server_config.server_baidu):
        s = baidu.translate_text(s, fromLang, to_lang_code)
    elif (server == server_config.server_youdao):
        s = youdao.translate_text(s, fromLang, to_lang_code)
    else:
        s = google.translate_text(s, fromLang, to_lang_code)

    return s


def ocr2(param):
    img_path, latex = param
    return ocr(img_path, latex)


def ocr(img_path, latex=False):
    ok = False
    s = ""
    try:
        if config.is_ocr_local():
            import easyocr
            reader = easyocr.Reader(['ch_sim', 'en'])
            list = reader.readtext(img_path, detail=0)
            s = ""
            for s_ in list:
                s += s_ + " "
            return True, s.strip()
        server, changeServer = tools.get_current_translate_server()
        if (server == server_config.server_tencent):
            # 这个有问题，暂时用百度的
            # ok, s = tencent.ocr(img_path, latex=latex)
            ok, s = baidu.ocr(img_path, latex=latex)
        else:
            ok, s = baidu.ocr(img_path, latex=latex)
    except Exception as e:
        s = "识别错误：" + str(e)
        if (config.is_ocr_local()):
            s += "。离线识别请安装依赖，终端输入： pip3 install easyocr"
        else:
            s += "。也可以使用离线文本识别，请在设置中启用。离线识别精度 < 在线api，但无次数限制"
        print(e)
    return ok, s


def check_server_api(param):
    is_ocr, server, a, b = param
    if is_ocr:
        return check_server_ocr(server, a, b)
    return check_server_translate(server, a, b)


def check_server_translate(server, a, b):
    ok = False
    a = a.strip().replace("\n", " ")
    b = b.strip().replace("\n", " ")
    try:
        if (server == server_config.server_tencent):
            ok = tencent.check(a, b)
        else:
            ok = baidu.check_translate(a, b)
    except Exception as e:
        print(e)

    return ok, a, b


def check_server_ocr(server, a, b):
    ok = False
    a = a.strip().replace("\n", " ")
    b = b.strip().replace("\n", " ")

    try:
        if (server == server_config.server_tencent):
            ok = tencent.check(a, b)
        else:
            ok = baidu.check_ocr(a, b)
    except Exception as e:
        print(e)

    return ok, a, b


def set_no_translate_this(ntt=True):
    global no_translate_this
    no_translate_this = ntt
