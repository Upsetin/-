import os
import io
import sys
import json
import base64
import random
import time
import shutil
import string
import logging
import requests
import platform
import numpy
import hashlib
from matplotlib import pyplot as plt 
from matplotlib import use as matplotuse
from urllib import parse
from PyQt6.QtGui import QAction, QIcon, QMouseEvent, QPixmap, QRegularExpressionValidator, QCursor, QFocusEvent
from PyQt6.QtCore import QObject, QRegularExpression, QThread, Qt, pyqtBoundSignal, pyqtSignal
from PyQt6.QtSql import QSqlDatabase, QSqlQuery
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher
from PyQt6.QtWidgets import QApplication, QCheckBox, QComboBox, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListView, QMenu, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget, QSystemTrayIcon, QDockWidget, QMainWindow
from tenacity import retry, wait_random, wait_fixed, retry_if_exception_type, stop_after_attempt
from bs4 import BeautifulSoup
os.chdir(os.path.split(os.path.realpath(__file__))[0])
# 将工作目录转移到脚本所在目录，保证下面的相对路径都能正确找到文件
if platform.system()=="Windows":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ChinaUniOnlineGUI")
    # 让Windows的任务栏图标可以正常显示
matplotuse("Agg")
# 让matplotlib使用Agg后端避免Tkinter在非主线程运行的问题
class ProcessorModule():
    def __init__(self,data:dict,id_:str):
        super().__init__()
        self.logger=logging.getLogger(__name__)
        self.data=data
        try:
            if "id" in self.data.keys():
                self.id_=self.data["id"]
            else:
                self.id_=id_.replace(".json","")
            self.name=self.data["name"]
            self.mod_type=self.data["type"]
            self.author=self.data["author"]
            self.enabled=self.data["enabled"]
            if self.mod_type=="notifier":
                self.api=self.data["api"]
                self.token=self.data["token"]
                self.method=self.data["method"]
                if "params" in self.data.keys():
                    self.params=self.data["params"]
                else:
                    self.params={}
                if "json" in self.data.keys():
                    self.json_=self.data["json"]
                else:
                    self.json_={}
                if "data" in self.data.keys():
                    self.data_=self.data["data"]
                else:
                    self.data_={}
            else:
                self.logger.debug("不支持的模块类型")
                raise ModuleLoadError("不支持的模块类型")
        except KeyError:
            self.logger.debug("模块 %s 格式有误" %self.name)
            raise ModuleLoadError("模块格式有误")
        except Exception as e:
            self.logger.debug("模块 %s 加载过程中出现错误：%s" %(self.name,e))
            raise ModuleLoadError("模块加载出错")
        else:
            if os.path.exists("modules/configs")==False:
                os.mkdir("modules/configs")
            if os.path.exists("modules/configs/%s.json" %self.id_)==True:
                self.logger.debug("已加载模块配置文件")
                with open(file="modules/configs/%s.json" %self.id_,mode="r",encoding="utf-8") as reader:
                    self.conf=json.loads(reader.read())
            else:
                self.conf={}
            self.logger.debug("模块 %s 加载成功" %self.name)
    def handle_string(self,data:str,msg:str):
        params=dict()
        if "{token}" in data:
            params["token"]=self.token
        if "{msg}" in data:
            params["msg"]=msg
        if self.conf!={}:
            for key in self.conf.keys():
                    if "{config}.%s" %key in data:
                        data=data.replace("{config}.%s" %key,self.conf[key])
                        self.logger.debug("成功应用模块配置 %s=%s 到模块 %s" %(key,self.conf[key],self.name))
        else:
            self.logger.debug("模块 %s 不需要配置文件" %self.name)
        self.logger.debug("格式化参数：%s" %params)
        if "{config}" in data:
            self.logger.warning("模块 %s 存在未解析的关键字，可能会影响执行" %self.name)
            data=data.replace("{config}","#config#")
        return data.format(**params).replace("#config#","{config}")
    def parse(self,smsg:str):
        if self.mod_type=="notifier":
            self.token=self.handle_string(data=self.token,msg=smsg)
            self.logger.debug("token=%s" %self.token)
            self.api=self.handle_string(data=self.api,msg=smsg)
            self.logger.debug("api=%s" %self.api)
            for key in self.params.keys():
                self.params[key]=self.handle_string(data=self.params[key],msg=smsg)
            self.logger.debug("params=%s" %self.params)
            for key in self.json_.keys():
                self.json_[key]=self.handle_string(data=self.json_[key],msg=smsg)
            self.logger.debug("json_=%s" %self.json_)
            for key in self.data_.keys():
                self.data_[key]=self.handle_string(data=self.data_[key],msg=smsg)
            self.logger.debug("data_=%s" %self.data_)
    def exec(self,data):
        self.parse(smsg=data)
        if self.enabled==True:
            self.logger.info("模块 %s 正在执行" %self.name)
            if self.mod_type=="notifier":
                json_resp=requests.request(method=self.method,url=self.api,data=self.data_,params=self.params,json=self.json_).json()
                self.logger.debug("服务器回复：%s" %json_resp)
        else:
            self.logger.debug("模块 %s 已禁用" %self.name)
class SQLException(Exception):
    def __init__(self,*args):
        super().__init__(*args)
class ModuleLoadError(Exception):
    def __init__(self,*args):
        super().__init__(*args)
class ModuleSecureWarning(Warning):
    def __init__(self,*args):
        super().__init__(*args)
class EnhancedLabel(QLabel):
    # 一个可以在被单击时发送信号的标签
    clicked=pyqtSignal()
    def __init__(self,parent:QWidget):
        super().__init__()
        self.setParent(parent)
    def close(self):
        super().close()
    def mousePressEvent(self,event:QMouseEvent):
        super().mousePressEvent(event)
        self.clicked.emit()
    def mouseReleaseEvent(self,event:QMouseEvent):
        super().mouseReleaseEvent(event)
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
    def mouseMoveEvent(self,event:QMouseEvent):
        super().mouseMoveEvent(event)

class UserAvatar(QWidget):
    # 用户信息
    def __init__(self,parent:QWidget,name:str,phone:str,score:int,times:int,t_score:int,t_times:int,school:str,province_name:str,avatar:bytes=None):
        super().__init__()
        self.parent_=parent
        layout_=QVBoxLayout()
        self.setLayout(layout_)
        self.avatar_label=EnhancedLabel(parent=self)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setToolTip("正确率分布的雷达图，单击可放大")
        self.avatar_label.clicked.connect(self.resize_avatar)
        if avatar!=None:
            self.pixmap=QPixmap()
            self.pixmap.loadFromData(avatar)
            pixmap=self.pixmap.scaled(200, 150, Qt.AspectRatioMode.KeepAspectRatio)
            self.avatar_label.setPixmap(pixmap)
        info=QVBoxLayout()
        info.setSpacing(0)
        self.name_label=QLabel("姓名：%s" %name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.province_label=QLabel("来自：%s" %province_name)
        self.province_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.phone_label=QLabel("电话：%s" %phone)
        self.phone_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label=QLabel("分数：%d\n团队得分：%d" %(score,t_score))
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.school_label=QLabel("学校：%s" %school)
        self.school_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.times_label=QLabel("答题次数：%d\n团队答题次数：%d" %(times,t_times))
        self.times_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.addWidget(self.name_label)
        info.addWidget(self.province_label)
        info.addWidget(self.phone_label)
        info.addWidget(self.score_label)
        info.addWidget(self.school_label)
        info.addWidget(self.times_label)
        layout_.addLayout(info,3)
        layout_.addWidget(self.avatar_label,7)
        self.setParent(self.parent_)
    def update_score(self,score:int,t_score:int):
        self.score_label.setText("分数：%d\n团队得分：%d" %(score,t_score))
    def update_times(self,times:int,t_times:int):
        self.times_label.setText("答题次数：%d\n团队答题次数：%d" %(times,t_times))
    def update_avatar(self,avatar:bytes):
        self.pixmap=QPixmap()
        self.pixmap.loadFromData(avatar)
        pixmap=self.pixmap.scaled(200, 150, Qt.AspectRatioMode.KeepAspectRatio)
        self.avatar_label.setPixmap(pixmap)
    def resize_avatar(self):
        large_avatar=EnhancedLabel(parent=self.parent_)
        large_avatar.setPixmap(self.pixmap)
        large_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        large_avatar.move(int((self.parent_.width()-large_avatar.width())/2),int((self.parent_.height()-large_avatar.width())/2))
        large_avatar.clicked.connect(large_avatar.close)
        large_avatar.setToolTip("单击这个放大的图像可以关闭")
        large_avatar.show()
        
class EnhancedEdit(QLineEdit):
    # 一个自定义QLineEdit，可以在失去焦点和获得焦点时时传递信号
    lostFocus=pyqtSignal()
    getFocus=pyqtSignal()
    def __init__(self,long:bool=False):
        super().__init__()
        self.long=long
        if self.long==True:
            self.getFocus.connect(self.show_clear_button)
            self.lostFocus.connect(self.disable_clear_button)
    def focusOutEvent(self, a0: QFocusEvent) -> None:
        self.lostFocus.emit()
        return super().focusOutEvent(a0)
    def focusInEvent(self, a0: QFocusEvent) -> None:
        self.getFocus.emit()
        return super().focusInEvent(a0)
    def mousePressEvent(self, a0: QMouseEvent) -> None:
        super().mousePressEvent(a0)
        if self.long==True and a0.button()==Qt.MouseButton.LeftButton:
            self.selectAll()
    def show_clear_button(self):
        if self.isClearButtonEnabled()==False:
            self.setClearButtonEnabled(True)
    def disable_clear_button(self):
        if self.isClearButtonEnabled()==True:
            self.setClearButtonEnabled(False)
class QLogger(logging.Handler):
    # 一个自定义logging handler，用于在GUI中显示日志内容
    def __init__(self,update_signal:pyqtBoundSignal):
        super().__init__()
        self.widget=QPlainTextEdit()
        self.widget.setReadOnly(True)
        self.update_signal=update_signal
    def emit(self,record):
        msg=self.format(record)
        self.update_signal.emit(msg)
    def scroll_widget_to_bottom(self):
        self.widget.verticalScrollBar().setSliderPosition(self.widget.verticalScrollBar().maximum())
class TestProcessor():
    def __init__(self,query:QSqlQuery,show_qr_signal:pyqtBoundSignal,close_qr_signal:pyqtBoundSignal,user_info_signal:pyqtBoundSignal,update_info_signal:pyqtBoundSignal,prefix:str="ssxx"):
        '''答题处理器
        进行自动化答题的处理器类
        参数:
            query(QSqlQuery):用于查询答案数据
            show_qr_signal(pyqtBoundSgnal):PyQt信号，传递二维码的Bytes用于OAuth登陆，现由于OAuth被服务器废弃，仅保留作为兼容
            close_qr_signal(pyqtBoundSgnal):PyQt信号，无传递数据，用于告诉UI主进程已完成登陆，关闭二维码的显示，现状同上
            user_info_signal(pyqtBoundSgnal):PyQt信号，传递用户数据的dict用于生成用户信息Widget
            update_info_signal(pyqtBoundSgnal):PyQt信号，传递用户数据的dict用于更新用户信息
            prefix(str):文本，用于标记比赛类型是传统的四史还是新的党史，默认为 ssxx 代表四史，dsjd 代表党史，同时也是区分相关URL的前缀
        '''
        self.logger=logging.getLogger(__name__)
        self.expire=0
        with open(file="config.json",mode="r",encoding="utf-8") as conf_reader:
            self.conf=json.loads(conf_reader.read())
        self.show_qr_signal=show_qr_signal
        self.close_qr_signal=close_qr_signal
        self.user_info_signal=user_info_signal
        self.update_info_signal=update_info_signal
        self.prefix=prefix
        self.query=query
        self.session=requests.sessions.session()
        # i呀我去提供的生成机制
        cookie = "_ga=GA1.2." + str(random.randrange(50000000,59999999)) + "." + str(int(time.time())-random.randrange(30000,120000)) + "; _gid=GA1.2." + str(random.randrange(500000000,599999999)) + "." + str(int(time.time())-random.randrange(30000,120000)) + "; tgw_l7_route=" + hashlib.md5(str(random.randrange(10000,99999)).encode('utf8')).hexdigest() + "; _gat=1"
        self.logger.debug("生成的Cookie：%s" %cookie)
        default_headers={
            "User-Agent":"Mozilla/5.0 (Linux; Android 10; BKL-AL20 Build/HUAWEIBKL-AL20; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.62 XWEB/2777 MMWEBSDK/201201 Mobile Safari/537.36 MMWEBID/1494 MicroMessenger/8.0.1.1841(0x28000151) Process/toolsmp WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64",
            "Referer":"https://ssxx.univs.cn/",
            "Accept":"application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin":"https://ssxx.univs.cn",
            "X-Requested-With":"com.tencent.mm",
            "Sec-Fetch-Site":"same-origin",
            "Sec-Fetch-Mode":"cors",
            "cookie":cookie
            }
        self.session.headers.update(default_headers)
        proxy=self.conf["proxy"]
        if proxy!="":
            self.session.proxies.update({"http":proxy,"https":proxy})
        if self.prefix=="ssxx":
            self.activity_id="5f71e934bcdbf3a8c3ba5061"
        elif self.prefix=="dsjd":
            self.activity_id="603dda8ce4c8f6da7d923897"
        else:
            self.logger.error("非法的比赛类型")
            raise ValueError("非法的比赛类型")
        self.modules=list()
        for root,dirs,files in os.walk("modules"):
            self.logger.debug("全部文件：%s" %files)
            for file in files:
                if file.endswith(".json")==True:
                        with open(os.path.join(root,file),mode="r",encoding="utf-8") as mod_reader:
                            self.logger.debug("正在读取文件 %s" %file)
                            try:
                                module=ProcessorModule(data=json.loads(mod_reader.read()),id_=file)
                            except ModuleLoadError:
                                self.logger.debug("文件 %s 无法当作模块加载" %file) 
                            else:
                                self.logger.debug("正在将文件 %s 当作模块加载" %file)
                                self.modules.append(module)
                else:
                    self.logger.debug("文件未以.json结尾，不被认为是模块")
            break
        self.logger.debug("已加载的模块列表：%s" %[mod.name for mod in self.modules])
        self.client="5f582dd3683c2e0ae3aaacee"
        self.login(type_="v0")
        params={"t":int(time.time()),"id":self.activity_id}
        json_response=self.session.get("https://%s.univs.cn/cgi-bin/portal/activity/" %self.prefix,params=params).json()
        self.activity_id=json_response["data"]["id"]
        params={"t":int(time.time()),"activity_id":self.activity_id}
        json_response=self.session.get("https://%s.univs.cn/cgi-bin/portal/race/mode/" %self.prefix,params=params).json()
        self.logger.debug("获取的模式数据：%s" %json_response)
        modes=json_response["data"]["modes"]
        self.ids={}
        for mode in modes:
            self.ids[mode["id"]]={"title":mode["title"],"enabled":self.is_enabled(title=mode["title"]),"times":self.times(title=mode["title"])}
        self.logger.debug("所有的模式设置：%s" %self.ids)
        if self.prefix=="ssxx":
            self.logger.info("已准备处理四史学习内容")
        elif self.prefix=="dsjd":
            self.logger.info("已准备处理党史活动内容")
    def login(self,keep_referer:bool=False,type_:str="v1"):
        if keep_referer==True:
            referer={"Referer":self.session.headers["Referer"]}
        else:
            referer={}
        orig_headers=self.session.headers
        if type_=="v1":
            # 旧版登陆，估计已经废了，仍然保留作为兼容
            self.logger.info("使用网页OAuth登陆")
            while True:
                random_="".join(random.sample(string.digits+string.ascii_letters,random.randrange(20,21))) # FAJ25n9gl2mXEkGgrljtq
                self.logger.debug("random=%s" %random_)
                self.logger.info("正在获取二维码")
                # fxxk腾讯！这参数的True和False得用文本，还区分大小写
                params={"random":random_,"useSelfWxapp":"true","enableFetchPhone":"false"}
                json_response=self.session.get("https://oauth.u.hep.com.cn/oauth/wxapp/qrcode/%s" %self.client,params=params).json()
                self.logger.debug("response=%s" %json_response)
                if json_response["data"]==None:
                    self.logger.error("登陆出错")
                    self.logger.debug(json_response["message"])
                    self.login(type_="v0")
                    return
                else:
                    if json_response["data"]["success"]==True:
                        self.logger.error("此二维码已被使用过")
                    else:
                        self.logger.debug("此二维码未被使用过")
                        break
                time.sleep(0.5)
            qr=json_response["data"]["qrcode"]
            self.logger.debug("qr=%s" %qr)
            self.session.headers.update({"Accept":"image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"})
            self.show_qr_signal.emit(self.session.get(qr).content)
            self.session.headers.update({"Accept":"application/json, text/plain, */*"})
            times=0
            while True:
                times=times+1
                post_data={"random":random_,"useSelfWxapp":"true"}
                try:
                    json_response=self.session.post("https://oauth.u.hep.com.cn/oauth/wxapp/confirm/qr",params=post_data).json()
                except requests.exceptions.RequestException:
                    self.logger.error("确认QR码扫描状态过程中传输数据出错，将继续")
                else:
                    if json_response["data"]["code"]==200:
                        self.logger.debug("第 %d 次轮询二维码验证结果成功" %times)
                        _id=json_response["data"]["data"]["_id"] # 5fc8400785e70a5d71bd2c44
                        username=json_response["data"]["data"]["username"] # zhanghua
                        self.token=json_response["data"]["data"]["token"]
                        params={"t":int(time.time()),"uid":_id}
                        json_response=self.session.get("https://%s.univs.cn/cgi-bin/authorize/token/" %self.prefix,params=params).json()
                        self.token=json_response["token"]
                        self.refresh_token=json_response["refresh_token"]
                        self.logger.info("用户 %s 登陆成功" %(username))
                        self.logger.debug("token=%s" %self.token)
                        self.close_qr_signal.emit()
                        break
                    elif json_response["data"]["code"]==500:
                        self.logger.debug("第 %d 次轮询二维码验证结果失败，继续等待" %times)
                    time.sleep(1.0)
                finally:
                    self.logger.debug("response=%s" %json_response)
        elif type_=="v2":
            # 处于未完成状态，不要使用这个模式
            self.logger.debug("使用模拟手机微信登陆")
            new_headers={
                "User-Agent":"Mozilla/5.0 (Linux; Android 10; BKL-AL20 Build/HUAWEIBKL-AL20; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.62 XWEB/2759 MMWEBSDK/201201 Mobile Safari/537.36 MMWEBID/1494 MicroMessenger/8.0.1.1841(0x28000151) Process/appbrand0 WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64 miniProgram",
                "Referer":"https://%s.univs.cn/client/detail/%s" %(self.prefix,self.activity_id),
                "X-Requested-With":"com.tencent.mm",
                "Accept-Encoding":"gzip, deflate"
            }
            self.session.headers.update(new_headers)
            json_response=self.session.get("https://%s.univs.cn/cgi-bin/authorize/token/" %self.prefix,params={"t":int(time.time())}).json()
            self.logger.debug("服务器返回数据：%s" %json_response)
            if json_response["code"]==1102:
                self.session.headers.update({"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/wxpic,image/tpg,image/apng,*/*;q=0.8,application/signed-exchange;v=b3"})
                resp=self.session.get("https://oauth.u.hep.com.cn/oauth/wechatmp/url/%s" %self.client,params={"redirectUrl":"%s" %self.session.headers["Referer"]})
                # 上面地址需要模拟微信浏览器环境打开，使用UA无效
                self.logger.debug("请求数据：%s,%s" %(self.session.headers,resp.url))
                if resp.status_code!=302:
                    self.logger.error("未触发重定向")
                    self.logger.debug(resp.text)
                    raise RuntimeError("服务器返回值：%d" %resp.status_code)
                else:
                    self.logger.debug("重定向地址：%s" %resp.url)
                query=parse.parse_qs(parse.urlparse(parse.unquote(resp.url)).query)
                wx_data=dict(
                    appid=query["appid"][0],redirect_uri=query["redirect_uri"][0],response_type=query["response_type"][0],
                    scope=query["scope"][0],state=query["state"][0],md=query["md"][0],uin=query["uin"][0],key=query["key"][0],
                    version=query["version"][0],pass_ticket=query["pass_ticket"][0])
                soup=BeautifulSoup(resp.text,"html.parser")
                elements=soup.select("input[type=\"hidden\"]")
                for element in elements:
                    wx_data[element.attrs["name"]]=element.attrs["value"]
                # wx_data具有以下key：uuid,uin,key,pass_ticket,version,appid,scope,state,md,response_type,redirect_uri
                self.session.headers.update({"Referer":resp.url})
                resp=self.session.get("https://open.weixin.qq.com/connect/oauth2/authorize_reply",params={"allow":1,"snap_userinfo":"on","uuid":wx_data["uuid"],"uin":wx_data["uin"],"key":wx_data["key"],"pass_ticket":wx_data["pass_ticket"],"version":wx_data["version"]})
                data=json.loads(parse.parse_qs(parse.urlparse(parse.unquote(resp.url)).query)["data"][0])
                self.session.headers.update({"Referer":resp.url})
                json_response=self.session.get("https://%s.univs.cn/cgi-bin/base/public/key/" %self.prefix,params={"t":int(time.time())}).json()
                self.logger.debug("OAuth内容：%s" %data["oauth"])
                json_response=self.session.get("https://%s.univs.cn/cgi-bin/authorize/token/" %self.prefix,params={"t":int(time.time()),"uid":wx_data["uid"],"activity_id":self.activity_id,"avatar":data["oauth"]["avatarUrl"]}).json()
            self.token=json_response["token"]
            self.refresh_token=json_response["refresh_token"]
        else:
            self.logger.info("使用存储的登陆信息完成登陆")
            self.token,self.refresh_token,self.uid,self.uc_token=self.get_token()
            if self.uc_token=="":
                self.logger.error("未设置uc_token")
                if self.token=="":
                    self.logger.error("Token未设置")
                    if self.uid=="":
                        self.logger.error("未设置UID")
                        raise RuntimeError("未设置登陆所需uc_token或者UID或者Token")
                    else:
                        login_type="uid"
                else:
                    login_type="token"
            else:
                uc_token_info=self.decode_token(self.uc_token)
                uc_token_detail=uc_token_info[self.uc_token.split(".")[1]]
                if time.time()>=uc_token_detail["exp"]:
                    self.logger.error("uc_token已过期")
                    login_type="token"
                else:
                    self.uid=uc_token_detail["data"]["id"]
                    login_type="uc_token"
            if self.prefix=="dsjd":
                login_type="uid"
            if login_type=="uid":
                params={"t":int(time.time()),"uid":self.uid}
                self.logger.info("使用存储的UID完成登陆")
                do_r=True
            elif login_type=="uc_token":
                params={"t":int(time.time()),"uc_token":self.uc_token}
                self.logger.info("使用存储的uc_token完成登陆")
                do_r=True
            elif login_type=="token":
                params={}
                do_r=False
            else:
                self.logger.warning("未找到正确的登陆信息")
                params={}
                do_r=False
            if do_r==True:
                json_response=self.session.get("https://%s.univs.cn/cgi-bin/authorize/token/" %self.prefix,params=params).json()
                self.logger.debug("服务器回复：%s" %json_response)
                if json_response["code"]==0:
                    self.token=json_response["token"]
                    self.logger.debug("获取Token:%s" %self.token)
                    self.refresh_token=json_response["refresh_token"]
                    self.logger.debug("获取Refresh Token：%s" %self.refresh_token)
                else:
                    self.error_handler(json_response)
        self.expire=self.decode_token()[self.token.split(".")[1]]["exp"]
        headers={
            "Referer":"https://%s.univs.cn/clientLogin?redirect=/client/detail/%s" %(self.prefix,self.activity_id),
            "Authorization":"Bearer %s" %self.token}
        self.session.headers.update(orig_headers)
        self.session.headers.update(headers)
        if keep_referer==True:
            self.session.headers.update(referer)
        if self.expire-time.time()<500:
            self.update_token()
        params={"t":int(time.time())}
        json_response=self.session.get("https://%s.univs.cn/cgi-bin/portal/user/" %self.prefix,params=params).json()
        if json_response["code"]==1002:
            self.logger.error("Token已过期")
            raise RuntimeError(self.error_handler(json_response=json_response))
        elif json_response["code"]!=0:
            msg=self.error_handler(json_response=json_response)
            self.logger.error("获取用户信息出现问题：%s" %msg)
            raise RuntimeError("获取用户信息出现问题")
        self.logger.debug("获取用户信息：%s" %json_response)
        name=json_response["data"]["name"]
        university_name=json_response["data"]["university_name"]
        zip_=json_response["data"]["zip"]
        mobile=json_response["data"]["mobile"]
        self.logger.info("用户 %s 来自 %s，手机号 %s" %(name,university_name,zip_+" "+mobile))
        self.user_info=self.get_user_info()
        self.user_info.update({"name":name,"phone":zip_+" "+mobile})
        self.session.headers.update({"Referer": "https://%s.univs.cn/client/detail/%s" %(self.prefix,self.activity_id)})
        self.user_info_signal.emit(self.user_info)
        self.logger.debug("已提交用户数据")
    def get_user_info(self):
        orig_headers=self.session.headers
        avatar=None
        self.session.headers.update({"Referer": "https://%s.univs.cn/client/detail/%s/score" %(self.prefix,self.activity_id)})
        json_response=self.session.get("https://%s.univs.cn/cgi-bin/race/grade/" %self.prefix,params={"t":int(time.time()),"activity_id":self.activity_id}).json()
        self.logger.debug("服务器返回用户信息：%s" %json_response)
        if json_response["code"]==1005:
            self.logger.error("用户在其他地方登陆，当前客户端被迫下线")
            raise RuntimeError("检测到此账号在其他客户端登陆")
        elif json_response["code"]!=0:
            msg=self.error_handler(json_response=json_response)
            self.logger.error("服务器返回错误代码：%d，错误信息：%s" %(json_response["code"],msg))
            raise RuntimeError("查询分数过程中服务器返回数据有误，查看日志获得更多信息")
        integral=json_response["data"]["integral"] # 分数
        join_times=json_response["data"]["join_times"] # 答题次数
        t_join_times=json_response["data"]["t_join_times"] #团队分数
        t_integral=json_response["data"]["t_integral"] # 团队答题次数
        university_name=json_response["data"]["university_name"] # 学校名称
        province_name=json_response["data"]["province_name"] # 地区
        json_response=self.session.get("https://%s.univs.cn/cgi-bin/user/race/fight/accuracy/" %self.prefix,params={"t":int(time.time()),"activity_id":self.activity_id}).json()
        self.logger.debug("获取用户答题准确率信息内容：%s" %json_response)
        if json_response["code"]==1005:
            self.logger.error("用户在其他地方登陆，当前客户端被迫下线")
            raise RuntimeError("检测到此账号在其他客户端登陆")
        elif json_response["code"]!=0:
            msg=self.error_handler(json_response=json_response)
            self.logger.error("服务器返回错误代码：%d，错误信息：%s" %(json_response["code"],msg))
            raise RuntimeError("查询分数过程中服务器返回数据有误，查看日志获得更多信息")
        avatar=json_response["data"]
        self.session.headers.update(orig_headers)
        return {"integral":integral,"join_times":join_times,"t_join_times":t_join_times,"t_integral":t_integral,"university_name":university_name,"avatar":avatar,"province_name":province_name}
    def is_enabled(self,title:str):
        for key in self.conf.keys():
            if type(self.conf[key])==dict and "title" in self.conf[key] and "enabled" in self.conf[key] and self.conf[key]["title"]==title:
                return bool(self.conf[key]["enabled"])
        return False
    def times(self,title:str):
        for key in self.conf.keys():
            if type(self.conf[key])==dict and "title" in self.conf[key] and "times" in self.conf[key] and self.conf[key]["title"]==title:
                self.logger.debug("设置的 %s 的次数为：%d" %(title,self.conf[key]["times"]))
                return int(self.conf[key]["times"])
        return 1
    def start(self,tray:QSystemTrayIcon,update_tray:pyqtBoundSignal,times:int=-1,bootstrap:bool=False):
        whitelist_mode=["5f71e934bcdbf3a8c3ba51d9","5f71e934bcdbf3a8c3ba51da"]
        # 不应该休眠的模式的白名单列表
        if bootstrap==True:
            # 初始化题目数据库，建议此时使用小号以避免污染答题记录
            self.logger.info("正在初始化题目数据库，强烈建议使用无关小号登陆")
            self.logger.info("每个挑战将刷 %d 次以获得足够的数据" %times)
        process_stat=list()
        randomrize=self.conf["randomrize"]
        self.logger.debug("随机化处理顺序设置：%s" %randomrize)
        for key in self.ids.keys():
            if times==-1:
                times=self.ids[key]["times"]
            if self.ids[key]["enabled"]==True:
                process_stat.append({"title":self.ids[key]["title"],"mode_id":key,"times":times,"status":0})
            else:
                self.logger.info("%s 已跳过" %self.ids[key]["title"])
        try:
            while True:
                if process_stat==[]:
                    self.logger.info("全部项目已完成处理")
                    break
                self.logger.debug("准备处理的项目列表：%s" %process_stat)
                if randomrize==True:
                    pos=random.randint(0,len(process_stat)-1)
                else:
                    pos=0
                self.logger.debug("选中的项目：%s" %process_stat[pos])
                if process_stat[pos]["mode_id"] in whitelist_mode:
                    sleepflag=False
                    self.logger.debug("项目 %s 关闭答题睡眠" %process_stat[pos]["title"])
                else:
                    sleepflag=True
                    self.logger.debug("项目 %s 启用答题睡眠" %process_stat[pos]["title"])
                msg="正在处理第 %d 次的 %s" %(process_stat[pos]["status"]+1,process_stat[pos]["title"])
                self.logger.info(msg)
                update_tray.emit(msg)
                try:
                    self.process(mode_id=process_stat[pos]["mode_id"],sleep=sleepflag)
                except requests.exceptions.ConnectionError as e:
                    self.logger.error("和服务器通信出错")
                    self.logger.debug("第 %d 次执行失败，错误详细内容：%s" %(process_stat[pos]["status"]+1,e))
                else:
                    self.logger.debug("第 %d 次执行成功" %(process_stat[pos]["status"]+1))
                    process_stat[pos]["status"]=process_stat[pos]["status"]+1
                    self.logger.debug("已更新处理列表")
                    if process_stat[pos]["status"]>=process_stat[pos]["times"]:
                        self.logger.debug("项目 %s 已完成，正在从列表中移除" %process_stat[pos]["title"])
                        process_stat.remove(process_stat[pos])
                    else:
                        self.logger.debug("项目 %s 有效，仍将加入处理过程" %process_stat[pos]["title"])
        except RuntimeError as e_r:
            self.logger.error("处理过程中出现错误")
            self.logger.debug("错误详细内容：%s" %e_r)
            tray.showMessage("ChineUniOnlineGUI：错误",str(e_r),QSystemTrayIcon.MessageIcon.Critical)
        finally:
            self.session.close()
            self.logger.debug("已关闭Session")
            with open(file="config.json",mode="r",encoding="utf-8") as reader:
                conf=json.loads(reader.read())
            conf["auth"]={"token":self.token,"refresh_token":self.refresh_token,"uid":self.uid,"uc_token":self.uc_token}
            with open(file="config.json",mode="w",encoding="utf-8") as writer:
                writer.write(json.dumps(conf,sort_keys=True,indent=4,ensure_ascii=False))
            self.logger.debug("已更新Token数据供下次使用")
    @retry(wait=wait_fixed(2)+wait_random(0,3),retry=retry_if_exception_type(requests.exceptions.ConnectionError),stop=stop_after_attempt(5),reraise=True)
    def process(self,mode_id:str,sleep:bool=True):
        self.logger.debug("当前prefix：%s"%self.prefix)
        headers={"Referer":"https://%s.univs.cn/client/exam/%s/1/1/%s" %(self.prefix,self.activity_id,mode_id)}
        self.session.headers.update(headers)
        params={"t":int(time.time()),"activity_id":self.activity_id,"mode_id":mode_id,"way":self.conf["way"]}
        self.logger.debug("获取题目信息的URL参数：%s" %params)
        json_response=self.session.get("https://%s.univs.cn/cgi-bin/race/beginning/" %self.prefix,params=params,data={}).json()
        self.logger.debug("获取题目数据：%s" %json_response)
        if json_response["code"]==1005:
            self.logger.error("用户在其他地方登陆，当前客户端被迫下线")
            raise RuntimeError("检测到此账号在其他客户端登陆")
        elif json_response["code"]==4832:
            self.logger.error("超过允许答题次数")
            if self.prefix=="dsjd":
                self.logger.info("你正在使用党史答题，党史答题每天只有一次机会")
            raise RuntimeError("超过最大允许答题次数")
        elif json_response["code"]!=0:
            msg=self.error_handler(json_response=json_response)
            self.logger.error("服务器返回错误代码：%d，错误信息：%s" %(json_response["code"],msg))
            raise RuntimeError("开始答题过程中服务器返回数据有误，查看日志获得更多信息")
        question_ids=json_response["question_ids"]
        num=0
        SuccessNum=0
        FailNum=0
        n="".join(random.choices(population=list(string.digits+string.ascii_letters),k=4))
        # 验证码生成逻辑在js的1713行
        self.logger.debug("生成验证码：%s" %n)
        if mode_id=="5f71e934bcdbf3a8c3ba51da":
            verify_pos=self.normal_choice_pos(lst=question_ids,max_=10)
        else:
            verify_pos=self.normal_choice_pos(lst=question_ids)
        for question_id in question_ids:
            if sleep==True:
                time.sleep(random.uniform(self.conf["advanced"]["sleep_on"]["min"],self.conf["advanced"]["sleep_on"]["max"]))
                # 随机休眠一段时间尝试规避速度过快导致的服务器警告
            else:
                time.sleep(random.uniform(self.conf["advanced"]["sleep_off"]["min"],self.conf["advanced"]["sleep_off"]["max"]))
                # 还是有几率在对决模式中出现答题过快的问题，因此加入一个更短时间的睡眠取得稳定性和获胜率的平衡
            i=question_ids.index(question_id)
            num=num+1
            if i==verify_pos:
                veryfy=True
            else:
                veryfy=False
            if self.get_option(activity_id=self.activity_id,question_id=question_id,mode_id=mode_id,veryfy=veryfy,n=n)==True:
                SuccessNum=SuccessNum+1
                self.logger.info("第 %d 道题目成功" %(i+1))
            else:
                FailNum=FailNum+1
                self.logger.info("第 %d 道题目失败" %(i+1))
            if SuccessNum>=10 and mode_id=="5f71e934bcdbf3a8c3ba51da":
                # 按照抢十赛规则，只要正确答题10道即可结束。。。
                self.logger.info("抢十赛数目已达到10，正在终止答题")
                break
        race_code=json_response["race_code"]
        self.finish(race_code=race_code,activity_id=self.activity_id,mode_id=mode_id)
        self.logger.info("此次成功查询 %d 个题，收录 %d 个题" %(SuccessNum,FailNum))
    def normal_choice_pos(self,lst:list,max_:int=-1):
        mu=(len(lst)-1)/2
        sigma=len(lst)/6
        if max_==-1:
            max_=len(lst)-1
        while True:
            index=int(random.normalvariate(mu=mu,sigma=sigma))
            if index in range(max_):
                self.logger.debug("选中需要模拟验证的位置：%d" %index)
                return index
    def check_verify(self,mode_id:str,n:str):
        # 这里的code和下面的code应该是利用self.encrypt_with_pubkey()加密的结果
        # n为验证码字符串
        time_=time.time()
        timestamp=int(time_)
        code=self.encrypt_with_pubkey(string=n,time_=timestamp)
        self.logger.debug("save_code=%s" %code)
        post_data={"activity_id":self.activity_id,"mode_id":mode_id,"way":self.conf["way"],"code":code}
        json_response=self.session.post("https://%s.univs.cn/cgi-bin/check/verification/code/" %self.prefix,json=post_data).json()
        return bool(json_response["status"])
    def submit_verify(self,mode_id:str,n:str):
        # n为验证码字符串
        time_=time.time()
        code=self.encrypt_with_pubkey(string=n,time_=int(time_))
        self.logger.debug("submit_code=%s" %code)
        post_data={"activity_id":self.activity_id,"mode_id":mode_id,"way":self.conf["way"],"code":code}
        json_response=self.session.post("https://%s.univs.cn/cgi-bin/save/verification/code/" %self.prefix,json=post_data).json()
        self.logger.debug("submit_response=%s" %json_response)
        if json_response["code"]==0:
            self.logger.info("提交验证码成功")
        elif json_response["code"]==1005:
            self.logger.error("用户在其他地方登陆，当前客户端被迫下线")
            raise RuntimeError("检测到此账号在其他客户端登陆")
        else:
            msg=self.error_handler(json_response=json_response)
            self.logger.error("提交验证码失败，错误代码：%d，服务器返回信息：%s" %(json_response["code"],msg))
    def get_option(self,activity_id,question_id,mode_id,n:str,veryfy:bool=False):
        if self.prefix not in ["ssxx"]:
            veryfy=False
        params={"t":int(time.time()),"activity_id":activity_id,"question_id":question_id,"mode_id":mode_id,"way":self.conf["way"]}
        json_response=self.session.get("https://%s.univs.cn/cgi-bin/race/question/" %self.prefix,params=params).json()
        if json_response["code"]==1005:
            self.logger.error("用户在其他地方登陆，当前客户端被迫下线")
            raise RuntimeError("检测到此账号在其他客户端登陆")
        elif json_response["code"]!=0:
            msg=self.error_handler(json_response=json_response)
            self.logger.error("服务器返回错误代码：%d，信息：%s" %(json_response["code"],msg))
            raise RuntimeError("获取题目过程中服务器返回数据有误，查看日志文件获得更多信息")
        self.logger.debug("获取选项信息：%s" %json_response)
        if veryfy==True:
            #根据抓包结果，先获取了问题，再进行的验证码处理
            if self.check_verify(mode_id=mode_id,n=n)==True:
                self.logger.info("验证码已通过或无验证码")
            else:
                self.submit_verify(mode_id=mode_id,n=n)
                self.logger.debug("当前验证码状态：%s" %self.check_verify(mode_id=mode_id,n=n))
        # 选项
        options_=json_response["data"]["options"]
        op_result={}
        title=str()
        answers=list()
        for option_ in options_:
            answers.append(option_["id"])
            op_title=self.clean_element(string_=option_["title"])
            op_result[option_['id']] = op_title
            # {id:title}
        self.logger.debug("获取选项信息：%s" %op_result)
        # 题目
        title=self.clean_element(string_=json_response['data']['title'])
        self.logger.info("题目：%s" %title)
        answer=self.search_ans(question=title)
        self.logger.debug("选择项目：%s" %op_result)
        if answer!=[]:
            self.logger.info("来自数据库的答案：%s" %answer)
            answer_ids=list()
            for answer_title in answer:
                for answer_id in answers:
                    if answer_title in op_result[answer_id].strip():
                        answer_ids.append(answer_id)
            self.logger.debug("正确答案的ID列表：%s" %answer_ids)
            return self.process_ans(question_id=question_id,answer_ids=answer_ids,mode_id=mode_id,activity_id=self.activity_id,catch=False)
        else:
            caught_answer=self.process_ans(question_id=question_id,activity_id=activity_id,mode_id=mode_id,answer_ids=answers,catch=True)
            if caught_answer!=None:
                self.logger.debug("已捕获的答案：%s" %caught_answer)
                answer_titles=list()
                for caught_answer_id in caught_answer:
                    for answer_id in op_result.keys():
                        if answer_id==caught_answer_id:
                            answer_titles.append(op_result[caught_answer_id].strip())
                self.logger.info("正确答案的可读名称列表：%s" %answer_titles)
                if len(answer_titles)==1:
                    answer_str=answer_titles[0]
                else:
                    answer_str="#".join(answer_titles)
                self.update_database(question=title,answer=answer_str)
                self.logger.info("捕获正确答案并更新数据库成功")
            else:
                raise RuntimeError("捕获答案出错，查看日志以获得更多信息")
    def update_database(self,question:str,answer:str):
        self.logger.debug("正在加入条目 QUESTION=%s,ANSWER=%s 到表ALL_ANSWERS中" %(question,answer))
        if self.query.exec("INSERT OR REPLACE INTO 'ALL_ANSWERS' (QUESTION,ANSWER) VALUES ('%s','%s')" %(question,answer))==False:
            self.logger.error("插入数据库失败，原因：%s，正在尝试创建表" %self.query.lastError().text())
            if self.query.exec("CREATE TABLE 'ALL_ANSWERS' (QUESTION TEXT NOT NULL UNIQUE,ANSWER TEXT NOT NULL)")==False:
                self.logger.error("创建表失败，原因：%s，数据库受损？" %self.query.lastError().text())
                raise RuntimeError("数据库已受损，需要手动修复")
            else:
                self.query.exec("INSERT INTO 'ALL_ANSWERS' (QUESTION,ANSWER) VALUES ('%s','%s')" %(question,answer))
                self.logger.debug("已创建表并加入数据库条目")
        else:
            self.logger.debug("已更新数据库条目")
    def process_ans(self,question_id:str,activity_id:str,mode_id:str,answer_ids:list,catch:bool=False):
        data={"activity_id":activity_id,"question_id":question_id,"answer":None,"mode_id":mode_id,"way":self.conf["way"]}
        if catch==True:
            data["answer"]=[random.choice(answer_ids)]
            prefix="catch"
        else:
            data["answer"]=answer_ids
            prefix="submit"
        self.logger.debug("data=%s" %data)
        json_response=self.session.post("https://%s.univs.cn/cgi-bin/race/answer/" %self.prefix,json=data).json()
        self.logger.debug("%s_response=%s" %(prefix,json_response))
        if json_response["code"]==0:
            if catch==True:
                return json_response["data"]["correct_ids"]
            else:
                return json_response["data"]["correct"]   
        elif json_response["code"]==1005:
            self.logger.error("用户在其他地方登陆，当前客户端被迫下线")
            raise RuntimeError("检测到此账号在其他客户端登陆")
        elif json_response["code"]!=0:
            msg=self.error_handler(json_response=json_response)
            self.logger.error("服务器返回错误代码：%d，信息：%s" %(json_response["code"],msg))
            raise RuntimeError("答题过程中服务器返回数据有误，查看日志获得更多信息")
    def clean_element(self,string_:str):
        # 清除元素中不显示（contains(@style,display:none)）的部分以获得正常的题目和选项
        # 使用 BeautifilSoup解析
        cleaned=0
        soup=BeautifulSoup(string_,"html.parser")
        selectors=["display:none;","display: none"]
        for each_selector in selectors:
            elements=soup.select("[style*=\"%s\"]" %each_selector)
            for element in elements:
                element.extract()
                cleaned=cleaned+1
        self.logger.debug("共清理 %d 个干扰元素" %cleaned)
        return soup.get_text().strip()
    def search_ans(self,question:str):
        # 数据要求：一个问题对应一个答案，整张表内应该不存在同名问题，
        # 多个答案用#组合为一个字符串，查询时将自动按#切割为列表，无答案返回空列表
        self.query.exec("SELECT COUNT(ANSWER) FROM 'ALL_ANSWERS' WHERE QUESTION='%s'" %(question))
        self.query.last()
        if int(self.query.value(0))!=0:
            self.logger.debug("找到 %d 个的答案" %int(self.query.value(0)))
            # 答案数应当永远为 1
            if self.query.exec("SELECT ANSWER from 'ALL_ANSWERS' WHERE QUESTION='%s'" %(question))==False:
                self.logger.error("查询SQL数据库出错，原因：%s" %self.query.lastError().text())
            else:
                self.query.last()
                value=self.query.value(0)
                self.logger.debug("查询得到的值：%s" %value)
                return str(value).split("#")
        else:
            self.logger.debug("未找到答案")
        return []
    def finish(self,activity_id:str,mode_id:str,race_code:str):
        payload={
            "race_code":race_code
        }
        json_response=self.session.post("https://%s.univs.cn/cgi-bin/race/finish/" %self.prefix,json=payload).json()
        self.logger.debug(json_response)
        if json_response["code"]==4823:
            n="".join(random.choices(string.ascii_letters+string.digits,k=4))
            self.check_verify(mode_id=mode_id,n=n)
            self.submit_verify(mode_id=mode_id,n=n)
            #self.finish(activity_id=activity_id,mode_id=mode_id,race_code=race_code)
            self.logger.warning("在结束过程中出现验证")
        elif json_response["code"]==0:
            owner=json_response["data"]["owner"]
            self.logger.info("执行完成，正确数：%d，答题用时：%d 秒" %(owner["correct_amount"],owner["consume_time"]))
            if json_response["data"]["opponent"]!=None and json_response["data"]["opponent"]!={}:
                opponent=json_response["data"]["opponent"]
                self.logger.info("处于对战模式，对方信息：来自 %s 的 %s，正确数 %d，用时 %d秒" %(opponent["univ_name"],opponent["name"],opponent["correct_amount"],opponent["consume_time"]))
        elif json_response["code"]==4831:
            self.logger.warning("答题用时过短")
        elif json_response["code"]==1005:
            self.logger.error("用户在其他地方登陆，当前客户端被迫下线")
            raise RuntimeError("检测到此账号在其他客户端登陆")
        else:
            self.logger.error("提交失败，请在调试模式下查看服务器返回数据以确定问题")
            raise RuntimeError("提交结果过程中服务器返回数据有误，查看日志获得更多信息")
        self.logger.debug("正在更新得分情况")
        self.update_info_signal.emit(self.get_user_info())
        if self.expire-time.time()<500:
            self.logger.warning("Token还有 %d 秒即将过期" %(self.expire-time.time()))
            self.update_token()
    def encrypt_with_pubkey(self,string:str,time_:int=int(time.time())):
        params={"t":time_}
        json_response=self.session.get("https://%s.univs.cn/cgi-bin/base/public/key/" %self.prefix,params=params).json()
        pubkey=RSA.import_key(json_response["data"]["public_key"])
        cipher=Cipher.new(pubkey)
        return base64.b64encode(cipher.encrypt(string.encode())).decode()
    def get_token(self):
        with open(file="config.json",mode="r",encoding="utf-8") as reader:
            conf=json.loads(reader.read())
            token=conf["auth"]["token"]
            refresh_token=conf["auth"]["refresh_token"]
            uid=conf["auth"]["uid"]
            uc_token=conf["auth"]["uc_token"]
        self.logger.debug("Token=%s,refresh_token=%s,uid=%s,uc_token=%s" %(token,refresh_token,uid,uc_token))
        return token,refresh_token,uid,uc_token
    def update_token(self):
        json_response=self.session.get("https://%s.univs.cn/cgi-bin/authorize/token/refresh/" %self.prefix).json()
        self.logger.debug("返回数据：%s" %json_response)
        if json_response["code"]==0:
            self.token=json_response["token"]
            self.session.headers.update({"Authorization":"Bearer %s" %self.token})
            self.logger.info("更新Token成功")
            self.expire=self.decode_token()[self.token.split(".")[1]]["exp"]
        elif json_response["code"]==1005:
            self.logger.error("用户在其他地方登陆，当前客户端被迫下线")
        else:
            self.logger.error("更新Token失败,服务器返回信息：%s" %self.error_handler(json_response=json_response))
    def decode_token(self,token:str=""):
        # 原理来自https://github.com/deximy/FxxkSsxx
        if token=="":
            token=self.token
        result=dict()
        for part in token.split("."):
            self.logger.debug("Token分片：%s" %part)
            try:
                result[part]=json.loads(base64.b64decode(part+"==").decode())
            except Exception:
                result[part]=None
                self.logger.debug("跳过分片解码")
            else:
                self.logger.debug("分片解码完成")
        return result
    def error_handler(self,json_response:dict):
        if "message" in json_response.keys():
            msg=json_response["message"]
        elif "msg" in json_response.keys():
            msg=json_response["msg"]
        else:
            msg="(无)"
        self.logger.error("服务器返回信息：%s" %msg)
        return msg
    def get_modules(self,**kwargs):
        '''通过信息寻找模块
        参数：
            name:str 模块名称
            type_:str 模块类型
            id_:str 模块id
        返回：
            同时满足上述三个要求的模块列表
        '''
        if kwargs=={}:
            self.logger.debug("方法调用参数有误，需要至少1个筛选器")
            return []
        mods_name=list()
        mods_id=list()
        mods_type=list()
        self.logger.debug("获得的参数：%s" %kwargs)
        if "name" in kwargs.keys():
            name=kwargs["name"]
        else:
            name=""
        if "id_" in kwargs.keys():
            id_=kwargs["id_"]
        else:
            id_=""
        if "type_" in kwargs.keys():
            type_=kwargs["type_"]
        else:
            type_=""
        for mod in self.modules:
            if name!="" and mod.name==name:
                mods_name.append(mod)
            if id_!="" and mod.id_==id_:
                mods_id.append(mod)
            if type_!="" and mod.mod_type==type_:
                mods_type.append(mod)
        if mods_name==[]:
            mods_name=self.modules
        if mods_id==[]:
            mods_id=self.modules
        if mods_type==[]:
            mods_type=self.modules
        self.logger.debug("选出的模块列表：mods_name=%s,mods_id=%s,mods_type=%s" %([mod_name.name for mod_name in mods_name],[mod_id.name for mod_id in mods_id],[mod_type.name for mod_type in mods_type]))
        return list(set(mods_name).intersection(mods_id,mods_type))

class Work(QObject):
    close_dock_signal=pyqtSignal()
    update_tray=pyqtSignal(str)
    def __init__(self,query:QSqlQuery,show_qr_signal:pyqtBoundSignal,finish_signal:pyqtBoundSignal,close_qr_signal:pyqtBoundSignal,tray:QSystemTrayIcon,user_info_signal:pyqtBoundSignal,update_info_signal:pyqtBoundSignal):
        super().__init__()
        self.finish_signal=finish_signal
        self.show_qr_signal=show_qr_signal
        self.close_qr_signal=close_qr_signal
        self.user_info_signal=user_info_signal
        self.tray=tray
        self.update_info_signal=update_info_signal
        self.query=query
        self.logger=logging.getLogger(__name__)
    def start(self):
        self.logger.debug("正在启动子线程")
        self.processor=TestProcessor(query=self.query,show_qr_signal=self.show_qr_signal,close_qr_signal=self.close_qr_signal,user_info_signal=self.user_info_signal,update_info_signal=self.update_info_signal,prefix="ssxx")
        self.logger.debug("已实例化四史处理类")
        self.processor.start(tray=self.tray,update_tray=self.update_tray)
        self.close_dock_signal.emit()
        self.processor=TestProcessor(query=self.query,show_qr_signal=self.show_qr_signal,close_qr_signal=self.close_qr_signal,user_info_signal=self.user_info_signal,update_info_signal=self.update_info_signal,prefix="dsjd")
        self.logger.debug("已实例化党史处理类")
        self.processor.start(tray=self.tray,update_tray=self.update_tray)
        self.finish_signal.emit()
        self.logger.debug("已提交终止信号")
        smsg="%s ChinaUniOnlineGUI：\n程序执行完成，具体执行结果请查看程序记录" %time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time()))
        modules=self.processor.get_modules(type_="notifier")
        self.logger.debug("获取模块：%s" %[mod.name for mod in modules])
        for mod in modules:
            mod.exec(smsg)
class BootStrap(QObject):
    close_dock_signal=pyqtSignal()
    update_tray=pyqtSignal(str)
    def __init__(self,query:QSqlQuery,show_qr_signal:pyqtBoundSignal,finish_signal:pyqtBoundSignal,close_qr_signal:pyqtBoundSignal,tray:QSystemTrayIcon,user_info_signal:pyqtBoundSignal,update_info_signal:pyqtBoundSignal,times:int=30):
        super().__init__()
        self.logger=logging.getLogger(__name__)
        self.show_qr_signal=show_qr_signal
        self.finish_signal=finish_signal
        self.close_qr_signal=close_qr_signal
        self.user_info_signal=user_info_signal
        self.update_info_signal=update_info_signal
        self.times=times
        self.tray=tray
        self.query=query
    def start(self):
        self.logger.debug("正在启动子线程")
        self.processor=TestProcessor(query=self.query,show_qr_signal=self.show_qr_signal,close_qr_signal=self.close_qr_signal,user_info_signal=self.user_info_signal,update_info_signal=self.update_info_signal,prefix="ssxx")
        self.logger.debug("已实例化四史处理类")
        self.processor.start(times=self.times,tray=self.tray,update_tray=self.update_tray,bootstrap=True)
        self.close_dock_signal.emit()
        self.processor=TestProcessor(query=self.query,show_qr_signal=self.show_qr_signal,close_qr_signal=self.close_qr_signal,user_info_signal=self.user_info_signal,update_info_signal=self.update_info_signal,prefix="dsjd")
        self.logger.debug("已实例化党史处理类")
        self.processor.start(times=self.times,tray=self.tray,update_tray=self.update_tray,bootstrap=True)
        self.finish_signal.emit()
        self.logger.debug("已提交终止信号")
        smsg="%s ChinaUniOnlineGUI：\n程序执行完成，具体执行结果请查看程序记录" %time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time()))
        modules=self.processor.get_modules(type_="notifier")
        for mod in modules:
            mod.exec(smsg)
class SettingWindow(QDialog):
    def __init__(self,parent:QWidget,theme:dict):
        super().__init__()
        self.logger=logging.getLogger(__name__)
        with open(file="config.json",mode="r",encoding="utf-8") as conf_reader:
            self.conf=json.loads(conf_reader.read())
        self.logger.debug("初始化设置界面。设置内容：%s" %self.conf)
        self.shape=3 # GroupBox布局
        layout=QGridLayout()
        self.setLayout(layout)
        self.setModal(True)
        self.setParent(parent)
        self.resize(int(parent.size().width()*(600/1024)),int(parent.size().height()*(600/1024)))
        self.move(int(0.5*(parent.width()-self.width())),int(0.5*(parent.height()-self.height())))
        title=QLabel("设置")
        title.setStyleSheet(theme["title"])
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title,0,1,Qt.AlignmentFlag.AlignCenter)
        control_close=QPushButton()
        control_close.setStyleSheet(theme["control_close"])
        control_close.setToolTip("关闭")
        control_close.setFixedHeight(20)
        control_close.clicked.connect(self.close_callback)
        layout.addWidget(control_close,0,0)
        debug_check=QCheckBox("调试模式")
        debug_check.setChecked(self.conf["debug"])
        debug_check.setToolTip("单击切换开关状态")
        debug_check.setStyleSheet(theme["check_box"])
        debug_check.setObjectName("debug")
        self.content=QGridLayout()
        (x,y)=self.show_setting(conf=self.conf,layout=self.content,theme=theme)# 返回content的最后一个元素的x,y
        proxy=QGroupBox()
        proxy.setObjectName("proxy")
        proxy_layout=QVBoxLayout()
        proxy_label=QLabel("代理地址：")
        proxy_label.setStyleSheet(theme["label"])
        proxy_input=EnhancedEdit()
        proxy_input.setPlaceholderText("(无)")
        proxy_input.setText(self.conf["proxy"])
        proxy_input.setValidator(QRegularExpressionValidator(QRegularExpression("^(http[s]{0,1}|socks5)://(.*:.*@)?([^/:]+)(:[1-6][0-9]{0,4})?$")))
        proxy_input.setToolTip("格式为协议://[用户名:密码@]IP:端口，留空保持直连")
        proxy_input.setStyleSheet(theme["line_edit"])
        proxy_layout.addWidget(proxy_label)
        proxy_layout.addWidget(proxy_input)
        proxy.setLayout(proxy_layout)
        proxy.setStyleSheet(theme["group_box"])
        proxy.setToolTip("代理设置")
        theme_group=QGroupBox()
        theme_group.setObjectName("theme")
        theme_group.setToolTip("设置界面样式")
        theme_group.setStyleSheet(theme["group_box"])
        theme_label=QLabel("样式设置：")
        theme_label.setStyleSheet(theme["label"])
        theme_choose=QComboBox()
        choose_listview=QListView()
        theme_choose.setToolTip("选择想要的样式")
        theme_dic=self.get_themes()
        for key in theme_dic.keys():
            theme_choose.addItem(key,theme_dic[key])
        theme_choose.setCurrentIndex(theme_choose.findData(self.conf["theme"]))
        theme_choose.setView(choose_listview)
        choose_listview.parentWidget().setWindowFlag(Qt.WindowType.NoDropShadowWindowHint)
        theme_choose.setStyleSheet(theme["combo_box"])
        theme_layout=QVBoxLayout()
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(theme_choose)
        theme_group.setLayout(theme_layout)
        auth=QGroupBox()
        auth.setObjectName("auth")
        auth.setToolTip("登陆认证信息（需要抓包）：")
        auth.setStyleSheet(theme["group_box"])
        auth_layout=QGridLayout()
        token_label=QLabel("Token：")
        token_label.setStyleSheet(theme["label"])
        token_input=EnhancedEdit(long=True)
        token_input.setStyleSheet(theme["line_edit"])
        token_input.setToolTip("登陆所需Token")
        token_input.setText(self.conf["auth"]["token"])
        token_input.setObjectName("token")
        token_input.home(False)
        refresh_label=QLabel("刷新Token：")
        refresh_label.setStyleSheet(theme["label"])
        refresh_input=EnhancedEdit(long=True)
        refresh_input.setStyleSheet(theme["line_edit"])
        refresh_input.setToolTip("刷新Token所需的Token")
        refresh_input.setText(self.conf["auth"]["refresh_token"])
        refresh_input.setObjectName("refresh_token")
        refresh_input.home(False)
        uid_label=QLabel("UID：")
        uid_label.setStyleSheet(theme["label"])
        uid_input=EnhancedEdit(long=True)
        uid_input.setStyleSheet(theme["line_edit"])
        uid_input.setToolTip("UID（优先使用作为登陆认证信息）")
        uid_input.setText(self.conf["auth"]["uid"])
        uid_input.setObjectName("uid")
        uid_input.home(False)
        uc_token_label=QLabel("uc_token：")
        uc_token_label.setStyleSheet(theme["label"])
        uc_token_input=EnhancedEdit(long=True)
        uc_token_input.setStyleSheet(theme["line_edit"])
        uc_token_input.setToolTip("服务器API更新后新的认证信息")
        uc_token_input.setText(self.conf["auth"]["uc_token"])
        uc_token_input.setObjectName("uc_token")
        uc_token_input.home(False)
        auth_layout.addWidget(token_label,0,0,Qt.AlignmentFlag.AlignRight)
        auth_layout.addWidget(token_input,0,1,Qt.AlignmentFlag.AlignLeft)
        auth_layout.addWidget(refresh_label,1,0,Qt.AlignmentFlag.AlignRight)
        auth_layout.addWidget(refresh_input,1,1,Qt.AlignmentFlag.AlignLeft)
        auth_layout.addWidget(uid_label,2,0,Qt.AlignmentFlag.AlignRight)
        auth_layout.addWidget(uid_input,2,1,Qt.AlignmentFlag.AlignLeft)
        auth_layout.addWidget(uc_token_label,3,0,Qt.AlignmentFlag.AlignRight)
        auth_layout.addWidget(uc_token_input,3,1,Qt.AlignmentFlag.AlignLeft)
        auth.setLayout(auth_layout)
        way=QCheckBox("团队模式")
        way.setChecked(bool(self.conf["way"]-1))
        way.setToolTip("是否开启团队模式")
        way.setStyleSheet(theme["check_box"])
        way.setObjectName("way")
        hide=QCheckBox("最小化到托盘菜单")
        hide.setChecked(self.conf["hide"])
        hide.setToolTip("最小化窗口到托盘")
        hide.setStyleSheet(theme["check_box"])
        hide.setObjectName("hide")
        show_user_info=QCheckBox("显示用户信息")
        show_user_info.setChecked(self.conf["show_user_info"])
        show_user_info.setToolTip("是否在获取用户信息后显示到程序界面上")
        show_user_info.setStyleSheet(theme["check_box"])
        show_user_info.setObjectName("show_user_info")
        randomrize=QCheckBox("随机化处理顺序")
        randomrize.setChecked(self.conf["randomrize"])
        randomrize.setToolTip("是否随机化不同项目的处理顺序")
        randomrize.setStyleSheet(theme["check_box"])
        randomrize.setObjectName("randomrize")
        for widget in [proxy,theme_group,debug_check,way,hide,show_user_info,randomrize,auth]:
            self.content.addWidget(widget,x,y)
            self.logger.debug("已添加额外部件 %s 于(%d,%d)" %(widget.objectName(),x,y))
            if y+1>=self.shape:
                x=x+1
                y=0
            else:
                y=y+1
        layout.addLayout(self.content,1,1)
    def close_callback(self):
        self.save_settings()
        self.logger.debug("已保存设置")
        self.close()
    def save_settings(self):
        settings=dict()
        enabled=True
        times=1
        for i in range(self.content.count()):
            layoutitem=self.content.itemAt(i)
            if type(layoutitem.widget())==QCheckBox and layoutitem.widget().objectName()=="way":
                settings[layoutitem.widget().objectName()]=int(layoutitem.widget().isChecked())+1
            elif type(layoutitem.widget())==QCheckBox:
                settings[layoutitem.widget().objectName()]=layoutitem.widget().isChecked()
            elif type(layoutitem.widget())==QGroupBox:
                group=layoutitem.widget()
                auth=dict()
                for j in group.children():
                    if group.objectName()=="auth":
                        if type(j)==EnhancedEdit:
                            auth.update({j.objectName():j.text().strip()})
                        data=auth
                    elif group.objectName()=="proxy" and type(j)==EnhancedEdit:
                        data=str(j.text())
                    elif group.objectName()=="theme" and type(j)==QComboBox:
                        data=j.currentData()
                    
                    else:
                        if type(j)==QCheckBox:
                            enabled=j.isChecked()
                        elif type(j)==EnhancedEdit:
                            times=int(j.text())
                        data={"title":group.title(),"enabled":enabled,"times":times}
                    settings[group.objectName()]=data
        settings.update({"font_prop":self.conf["font_prop"],"advanced":self.conf["advanced"],"pos":self.conf["pos"]})
        self.logger.debug("设置数据：%s" %settings)
        with open(file="config.json",mode="w",encoding="utf-8") as conf_writer:
            conf_writer.write(json.dumps(settings,ensure_ascii=False,sort_keys=True,indent=4))
    def show_setting(self,conf:dict,layout:QGridLayout,theme:dict):
        groups=list()
        x=0
        y=0
        for key in conf.keys():
            if type(conf[key])!=dict or key=="auth" or key=="advanced" or key=="font_prop":
                continue
            conf_title=conf[key]["title"]
            conf_enabled=conf[key]["enabled"]
            conf_times=conf[key]["times"]
            group=QGroupBox(conf_title)
            group.setStyleSheet(theme["group_box"])
            group.setToolTip(conf_title+"  的设置")
            enabled=QCheckBox("启用")
            enabled.setObjectName(key)
            enabled.setToolTip("单击切换开关状态")
            enabled.setChecked(conf_enabled)
            enabled.setStyleSheet(theme["check_box"])
            times=QHBoxLayout()
            times_label=QLabel("次数：")
            times_label.setStyleSheet(theme["label"])
            times_input=EnhancedEdit()
            times_input.setObjectName(key)
            if times_input.objectName()=="party_history":
                times_input.setText("1")
                times_input.setEnabled(False)
                times_input.setToolTip("党史每天只能做一次")
            else:
                times_input.setText(str(conf_times))
                times_input.setToolTip("仅限正整数，过多的次数（>50次/项）可能导致掉登陆")
            times_input.setValidator(QRegularExpressionValidator(QRegularExpression("^[1-9][0-9]{1,8}$")))
            times_input.setStyleSheet(theme["line_edit"])
            times.addWidget(times_label)
            times.addWidget(times_input)
            group_layout=QVBoxLayout()
            group_layout.addWidget(enabled)
            group_layout.addLayout(times)
            group.setLayout(group_layout)
            group.setObjectName(key)
            groups.append(group)
        for group in groups:
            if y>=self.shape:
                x=x+1
                y=0
            layout.addWidget(group,x,y)
            self.logger.debug("已放置部件 %s 于(%d,%d)" %(group.objectName(),x,y))
            y=y+1
        self.logger.debug("最后的元素位置：(%d,%d)" %(x,y))
        return (x,y)
    def get_themes(self):
        data=dict()# {"默认":"default"}
        for home,dirs,files in os.walk("themes"):
            for dir_ in dirs:
                try:
                    with open(file=os.path.join(home,dir_,dir_+".json"),mode="r",encoding="utf-8") as reader:
                        data[json.loads(reader.read())["name"]]=dir_
                except:
                    continue

            break
        return data
class UI(QMainWindow):
    update_signal=pyqtSignal(str)
    show_qr_signal=pyqtSignal(bytes)
    finish_signal=pyqtSignal()
    finish_bootstrap_signal=pyqtSignal()
    close_qr_signal=pyqtSignal()
    user_info_signal=pyqtSignal(dict)
    update_info_signal=pyqtSignal(dict)
    class Theme():
        def __init__(self,name:str="default"):
            if os.path.exists("themes")==False:
                os.mkdir("themes")
            else:
                self.unpack_theme()
            try:
                with open(file="themes/%s/%s.json" %(name,name),mode="r",encoding="utf-8") as theme_reader:
                    theme=json.loads(theme_reader.read())
            except:
                theme={
                    "name":"默认",
                    "logging_fmt":"%(asctime)s-%(levelname)s-%(message)s",
                    "logging_datefmt":"%Y-%m-%d %H:%M:%S",
                    "main":"",
                    "dock":"QDockWidget{background:#9BE3DE;border:none;border-radius:5px;}",
                    "avatar":"QWidget{background:#9BE3DE;border:none;border-radius:5px;}",
                    "opacity":0.9,
                    "size":[1024,768],
                    "title":"QLabel{border:none;border-radius:5px;background:transparent;color:#9AD3BC;font-size:60px;}",
                    "logger":"QPlainTextEdit{font-family:Microsoft YaHei;background:#F3EAC2;border:none;border-radius:5px;}QScrollBar:vertical,QScrollBar::handle:vertical{background:#F3EAC2;border:none;border-radius:8px;width:16px;}QScrollBar::handle:vertical:hover{background:#F5B461;}QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{background:#FFFDF9;border:none;border-radius:8px;width:16px;}QScrollBar::down-arrow:vertical,QScrollBar::up-arrow:vertical{background:#F5B461;border:none;border-radius:8px;width:16px;height:16px;}QScrollBar::sub-line:vertical,QScrollBar::add-line:vertical{background:transparent;border:none;}",
                    "control_close":"QPushButton{background:#FFE3ED;border-radius:5px;border:none;}QPushButton:hover{background:#EC524B;}",
                    "control_max":"QPushButton{background:#FFFDF9;border-radius:5px;border:none;}QPushButton:hover{background:#F5B461;}",
                    "control_min":"QPushButton{background:#BEEBE9;border-radius:5px;border:none;}QPushButton:hover{background:#F3EAC2;}",
                    "start_button":"QPushButton{background:#9BE3DE;border:none;border-radius:5px;font-size:20px;font-family:DengXian;}QPushButton:hover{background:#9AD3BC;}",
                    "setting_button":"QPushButton{background:#9BE3DE;border:none;border-radius:5px;font-size:20px;font-family:DengXian;}QPushButton:hover{background:#9AD3BC;}",
                    "bootstrap":"QPushButton{background:#9BE3DE;border:none;border-radius:5px;font-size:10px;font-family:DengXian;}QPushButton:hover{background:#9AD3BC;}",
                    "qr_title":"QLabel{color:#ffe3ed;border:none;background-color:transparent;border-radius:5px;font-size:25px;}",
                    "qr":"QLabel{color:#ffe3ed;border:none;background-color:transparent;border-radius:5px;}",
                    "setting_window":"QDialog{border:none;border-radius:5px;background:#F3EAC2;}",
                    "setting":{
                        "title":"QLabel{border:none;border-radius:5px;background:transparent;color:#9AD3BC;font-size:20px;}",
                        "control_close":"QPushButton{background:#FFE3ED;border-radius:5px;border:none;}QPushButton:hover{background:#EC524B;}",
                        "check_box":"QCheckBox::indicator{width:10px;height:10px;border:none;border-radius:5px;background:#9BE3DE;}QCheckBox::indicator:unchecked{background:#BEEBE9;}QCheckBox::indicator:unchecked:hover{background:#9AD3BC;}QCheckBox::indicator:checked{background:#95E1D3;}QCheckBox::indicator:checked:hover{background:#98DED9;}",
                        "label":"QLabel{background:transparent;border:none;}",
                        "line_edit":"QLineEdit{border:1px solid #F3EAC2;border-radius:5px;background:transparent;}QLineEdit:hover{border:1px solid #F5B461;}",
                        "group_box":"QGroupBox{border-radius:5px;border:none;background:transparent;}",
                        "combo_box":"QComboBox{border-radius:5px;border:none;background:transparent;}QComboBox:hover{border:1px solid #F5B461;}QComboBox::drop-down:hover{background:#F5B461;}QComboBox::down-arrow{image:url(./themes/default/down.png);width:10px;height:10px;}QComboBox::down-arrow:on{image:url(./themes/default/up.png);}QComboBox QAbstractItemView{outline:none;border:none;border-radius:5px;}QComboBox QAbstractItemView:hover{border:1px solid #F5B461;}QComboBox QAbstractItemView::item{background:#F3EAC2;}QComboBox QAbstractItemView::item:selected{background:#F5B461;color:#F3EAC2;}"
                    },
                    "tray":"./themes/default/tray.png",
                    "tray_exit_icon":"./themes/default/tray_exit.png",
                    "tray_menu":"QMenu{background:white;border:none;}QMenu::item{background-color:transparent;padding:8px 32px;margin:0px 8px;border-bottom:1px solid #DBDBDB;}QMenu::item:selected{background:#2DABF9;}",
                    "tray_show_icon":"./themes/default/tray_show.png",
                    "icon":"./themes/default/icon.png",
                    "extra_data":{
                        "down.png":"iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAAACXBIWXMAAAsTAAALEwEAmpwYAAAFFmlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgNi4wLWMwMDIgNzkuMTY0NDg4LCAyMDIwLzA3LzEwLTIyOjA2OjUzICAgICAgICAiPiA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPiA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtbG5zOmRjPSJodHRwOi8vcHVybC5vcmcvZGMvZWxlbWVudHMvMS4xLyIgeG1sbnM6cGhvdG9zaG9wPSJodHRwOi8vbnMuYWRvYmUuY29tL3Bob3Rvc2hvcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RFdnQ9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZUV2ZW50IyIgeG1wOkNyZWF0b3JUb29sPSJBZG9iZSBQaG90b3Nob3AgMjIuMCAoV2luZG93cykiIHhtcDpDcmVhdGVEYXRlPSIyMDIxLTAzLTAyVDExOjE1OjU3KzA4OjAwIiB4bXA6TW9kaWZ5RGF0ZT0iMjAyMS0wMy0wMlQxMzoyNzoyMiswODowMCIgeG1wOk1ldGFkYXRhRGF0ZT0iMjAyMS0wMy0wMlQxMzoyNzoyMiswODowMCIgZGM6Zm9ybWF0PSJpbWFnZS9wbmciIHBob3Rvc2hvcDpDb2xvck1vZGU9IjMiIHBob3Rvc2hvcDpJQ0NQcm9maWxlPSJzUkdCIElFQzYxOTY2LTIuMSIgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDpiY2M4ZTYyMy1iYmFkLWEy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",
                        "up.png":"iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAAACXBIWXMAAAsTAAALEwEAmpwYAAAGvmlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgNi4wLWMwMDIgNzkuMTY0NDg4LCAyMDIwLzA3LzEwLTIyOjA2OjUzICAgICAgICAiPiA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPiA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtbG5zOmRjPSJodHRwOi8vcHVybC5vcmcvZGMvZWxlbWVudHMvMS4xLyIgeG1sbnM6cGhvdG9zaG9wPSJodHRwOi8vbnMuYWRvYmUuY29tL3Bob3Rvc2hvcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RFdnQ9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZUV2ZW50IyIgeG1wOkNyZWF0b3JUb29sPSJBZG9iZSBQaG90b3Nob3AgMjIuMCAoV2luZG93cykiIHhtcDpDcmVhdGVEYXRlPSIyMDIxLTAzLTAyVDExOjE1OjU3KzA4OjAwIiB4bXA6TW9kaWZ5RGF0ZT0iMjAyMS0wMy0wMlQxMzoyNzozOSswODowMCIgeG1wOk1ldGFkYXRhRGF0ZT0iMjAyMS0wMy0wMlQxMzoyNzozOSswODowMCIgZGM6Zm9ybWF0PSJpbWFnZS9wbmciIHBob3Rvc2hvcDpDb2xvck1vZGU9IjMiIHBob3Rvc2hvcDpJQ0NQcm9maWxlPSJzUkdCIElFQzYxOTY2LTIuMSIgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDphNTYzZTBhMi0wNmVjLTBjNDUtYjU1Ni0zZThiZWVjYjg3ZGMiIHhtcE1NOkRvY3VtZW50SUQ9ImFkb2JlOmRvY2lkOnBob3Rvc2hvcDpiYmYzZWRmNi04OTYyLTA2NGMtYTJlNC0zOWRhNTVjMjgyYjEiIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDpiY2M4ZTYyMy1iYmFkLWEyNGMtOTUxMi1lNTJmZWZlMTdmZmIiPiA8eG1wTU06SGlzdG9yeT4gPHJkZjpTZXE+IDxyZGY6bGkgc3RFdnQ6YWN0aW9uPSJjcmVhdGVkIiBzdEV2dDppbnN0YW5jZUlEPSJ4bXAuaWlkOmJjYzhlNjIzLWJiYWQtYTI0Yy05NTEyLWU1MmZlZmUxN2ZmYiIgc3RFdnQ6d2hlbj0iMjAyMS0wMy0wMlQxMToxNTo1NyswODowMCIgc3RFdnQ6c29mdHdhcmVBZ2VudD0iQWRvYmUgUGhvdG9zaG9wIDIyLjAgKFdpbmRvd3MpIi8+IDxyZGY6bGkgc3RFdnQ6YWN0aW9uPSJzYXZlZCIgc3RFdnQ6aW5zdGFuY2VJRD0ieG1wLmlpZDo1ZDkyNmVjNy02OTUzLTg4NDUtYWU4OC03NTFiNzQyNGI3OTMiIHN0RXZ0OndoZW49IjIwMjEtMDMtMDJUMTM6Mjc6MzkrMDg6MDAiIHN0RXZ0OnNvZnR3YXJlQWdlbnQ9IkFkb2JlIFBob3Rvc2hvcCAyMi4wIChXaW5kb3dzKSIgc3RFdnQ6Y2hhbmdlZD0iLyIvPiA8cmRmOmxpIHN0RXZ0OmFjdGlvbj0ic2F2ZWQiIHN0RXZ0Omluc3RhbmNlSUQ9InhtcC5paWQ6YTU2M2UwYTItMDZlYy0wYzQ1LWI1NTYtM2U4YmVlY2I4N2RjIiBzdEV2dDp3aGVuPSIyMDIxLTAzLTAyVDEzOjI3OjM5KzA4OjAwIiBzdEV2dDpzb2Z0d2FyZUFnZW50PSJBZG9iZSBQaG90b3Nob3AgMjIuMCAoV2luZG93cykiIHN0RXZ0OmNoYW5nZWQ9Ii8iLz4gPC9yZGY6U2VxPiA8L3htcE1NOkhpc3Rvcnk+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+8csxcwAABTVJREFUeNrtndtOE1EUhoc7D1Fj4iN44FBfRY0a773SSilF4+tJD6gxmph447UvIAU0Am0Z9zZry3I7BUpn2tl7PpIvmDGGZP5/1l7/WlNJ0jRNoLpwEzAANwEDAAYADAAYADAAYADAAIABAAMABgAMABgAMABgAMAAgAEAAwAGAAwAGAAwAGAAwACAAQADAAYADAAhGaAiXwuGS4ZFQ9PwzvDDcCTsGLYMrwx3DZfl3/CFAfiKQXwr6IphXYTeM6SKkaGPCeIVv2Z4aejJ037kGcAyNGyLCV6KYS5hgvDFvytP9ZY85aMM8f1K0JNqYY+Mi5gg7Cffib8tT3l6CiOpEtYEa4Y7mCDMhm9Flf2ziu84kj5hS5rGJY6DcMS/KKV7XcTvTyi+xpmgJYaiMQxA/DtSureklI/OKX6qImJPqgnpoORlf0lKtot6R1OIn9UYEhFLnvNbY3J+HibYVpWgRk9Qvqinc/4oZwPoOUFPjLZEOihXzj9Ptz/NcdAkIs7/zK95UW9QoPi6MdyVn9nABPPr9m0J3pix+H5E7DEnmF/Ua6qcP2vx/UrAnGDG4jfkxu8W1PBNYoK+lw4wQYFn/rJ68vPK+XlFxC4mKLbbr0mpdU9+GcTPMsGGGJWeoKCc3y846uVhAlbJOT/5s45605hgR0XE25hgujN/xYt6hyUr/WedE3AcnKPb1yvdUMTX7Mpx0JSegMZwwqi3lhzP9geBia9XyV3mBJOV/UUlvsv5oYk/Lh0QEU9p+JZV2XdRL1Txx5mAt41P6PY3kn9XuqGLn2UCexywSj4h6vUDPfPPukruyhFnI+IFzvz/c/5hhOJnNYYvqjwn0CvdltyQ2MX35wRdmRMsVq0n8Fe6XSmNVRC/8nMCJ74tfauq4RtWTHy9Su5UZU6gX912OX8vkqg3bTroqIgYpQn8j2h3I8r5eZqglUS4SvZzvjvzh4ifaYJmcrxKji7n625/hPCZc4KO9Ee3ZE6wELL4eqXrxD9A/FMjojVBPeQ5gb/SRfzJI2In1DmBjnoNL+cj/mQTw05ocwI95FlV3f4Q8c9lgu2Q5gR+ztdRD/HziYilXSX7H9HuJscrXcSf3gTfxQTrSQlXyeNy/gDxC6kEjTKtkvWTv+Hl/CHCFdYY1sswJ9Af12p5UQ/xi50TtJM5v0/gv72L+LOfE7TlOJj5R9P9la5r+AaIP/NVclvmBDOLiPrVbZ3zR4g/t8awLemg8IioX91uejkf8ecbEZ0JClslZ+V8t9JF/PJUAv1/Gxea84l65Vwlu3RwM685gV7p+lFvwI0v5ZzAmuCZMsHCNOLrlW4H8YOKiPVkyo+mXxiz0kX88rOjeoKJ5wQ659flyXc5H/HDnBOc+X0CnfMbIr6Leogf9pzg1Ijo53z35JPz45gTNE9aJfs5v6NWujz58VSC1axVsv/2bkfl/ENuYFQ9wabhuR8R3UrXRb3vEvUQP845wabMCW65ieGiOvNdzj/ghkUdETflOLDa/yn77hcsUfarUwnsh3NfWwN8NvyUZoGGrzomsL88+0uinng+qFk9rPbciIrzN+u75u+XlIc9ORr2uRbVtX317qat+skHwyf5/l6aA9slvpFk8JZrUV17Z/ho+Gr4Zg3wwPDY8Eh4aLhvuCd/x7W4rlmeGJ5KFEyuGK4K19SfuRbvNfv9uuFGkqYpVBhuAgbgJmAAwACAAQADAAYADAAYADAAYADAAIABAAMABgAMABgAMABgAMAAgAEAAwAGAAwAGAAwAGAAwAAQFr8BILiPqcgo6iEAAAAASUVORK5CYII=",
                        "icon.png":"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",
                        "tray.png":"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",
                        "tray_exit.png":"iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAQAAABpN6lAAAACg0lEQVR4Ae3dv0utdRwH8JfI4ZQgmTS4FFlQQxFKRlvQEApX4eImd1G5d7jcO9TS1hbUGgaWQYREa0VBNVRjQVIuQkGGJLQZEUYgyInGs3zBAwd6+rzff8ILznme5/v9/JgAsGrdoif0dCmnDn1jx7kRMwFmvWlDd3Ni29ejA8w69KBuZ2DT/qgAH9jQ/fzpSaejAKz6xP8jn1obBeBdW4BLr/nQ77qTngWvewRwYdrF1QF+sAB41Su6l0cd6QOecXB1gAs9wNO+18UcmfeLY8f2HV4dYABg3oku5ivPA257qyLA55bLAQQgAAEIQAACEIAABCAAAQhAAJZ9rF8ZgBUf6VcBaBAUAWgQvFgZgBVz3qsMwKTL2gAoBhCAAATgAc/5zN9VAW56w5Q/vOydmgA/eQwM3LFbD2DKmXsYIigFwJ5bDBEUA7jPF54dJqgC0CCoAtAgqALQIKgC0CCoA9AgKADQJigB0CYoAdAmKAHQJigB0CYoAdAmqAXQJmgDFCBoAxQgaAMUIGgDFCBoA1QgaALUIGgAVCFoAFQhaABUIWgAVCEYF8DDNs3476XvurlhgnEAbNszqQP5l2AcAN9Z0pUMxgHwo8drA9zwPpV/AixaN13qTzCPwfEnL0J5Fc7HUD6HcyCSI7EciuZYPBcjuRrL5Wiux1MgkRKZFEmlTC6FkimVTbF0yuXTMJGWmR13KzdN3es3M5Xb5np+9lDlxkm2vK3nLy9VbZ3lfi/40lna51sJQAACkDE6GaSUUVoZppZxehmomJGaAQhAAAIQgAAEIAABCEAAAhCArNvLwsWs3MzS1azdzeLlrN7O8nXgmjVLntLTpfzqwLd2nRsx/wDPfiltubwGqAAAAABJRU5ErkJggg==",
                        "tray_show.png":"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"
                    }
                }
                self.write_theme(name="default",theme=theme)
            self.name=theme["name"]
            self.opacity=theme["opacity"]
            self.size=theme["size"]
            self.title=theme["title"]
            self.logger=theme["logger"]
            self.control_close=theme["control_close"]
            self.control_max=theme["control_max"]
            self.control_min=theme["control_min"]
            self.start_button=theme["start_button"]
            self.setting_button=theme["setting_button"]
            self.bootstrap=theme["bootstrap"]
            self.qr_title=theme["qr_title"]
            self.qr=theme["qr"]
            self.setting_window=theme["setting_window"]
            self.setting=theme["setting"]
            self.logging_fmt=theme["logging_fmt"]
            self.logging_datefmt=theme["logging_datefmt"]
            self.tray=theme["tray"]
            self.icon=theme["icon"]
            self.tray_show=theme["tray_show_icon"]
            self.tray_exit=theme["tray_exit_icon"]
            self.tray_menu=theme["tray_menu"]
            self.main=theme["main"]
            self.avatar=theme["avatar"]
            self.dock=theme["dock"]
        def write_theme(self,name:str,theme:dict):
            if os.path.exists("themes/%s" %name)==False:
                os.mkdir("themes/%s" %name)
            with open(file="themes/%s/%s.json" %(name,name),mode="w",encoding="utf-8") as theme_writer:
                theme_writer.write(json.dumps(theme,indent=4,sort_keys=True,ensure_ascii=False))
            if "extra_data" in theme.keys() and type(theme["extra_data"])==dict:
                for key in theme["extra_data"].keys():
                    with open(file="themes/%s/%s" %(name,key),mode="wb") as writer:
                        writer.write(base64.b64decode(theme["extra_data"][key]))
        def unpack_theme(self):
            for home,dirs,files in os.walk("themes"):
                for file in files:
                    if file.endswith(".json")==True:
                        try:
                            with open(file=os.path.join(home,file),mode="r",encoding="utf-8") as reader:
                                theme=json.loads(reader.read())
                        except:
                            continue
                        else:
                            self.write_theme(name=file,theme=theme)
                            os.remove(os.path.join(home,file))
                break
    def __init__(self):
        super().__init__()
        self.m_flag=False
        self.need_message=True
        central_widget=QWidget()
        self.setCentralWidget(central_widget)
        self.logger=logging.getLogger(__name__)
        filehandler=logging.FileHandler(filename="logs.log",mode="w",encoding="utf-8")
        self.handler=QLogger(update_signal=self.update_signal)
        self.handler.setLevel(logging.INFO)
        filehandler.setLevel(logging.INFO)
        self.logger.setLevel(logging.INFO)
        self.default_conf={
            "pos":[0,0],
            "debug":False,
            "proxy":"",
            "theme":"default",
            "way":1,
            "hide":False,
            "show_user_info":True,
            "font_prop":{
                "family":"SimSun"
                },
            "randomrize":True,
            "advanced":{
                "sleep_off":{
                    "min":0.1,
                    "max":0.3
                },
                "sleep_on":{
                    "min":0.1,
                    "max":1.5
                }
            },
            "auth":{
                "token":"",
                "refresh_token":"",
                "uid":"",
                "uc_token":""
            },
            "hero":{
                "title":"英雄篇",
                "enabled":True,
                "times":1
                },
            "revival":{
                "title":"复兴篇",
                "enabled":True,
                "times":1
            },
            "creation":{
                "title":"创新篇",
                "enabled":True,
                "times":1
            },
            "belief":{
                "title":"信念篇",
                "enabled":True,
                "times":1
            },
            "limit_time":{
                "title":"限时赛",
                "enabled":True,
                "times":1
            },
            "rob":{
                "title":"抢十赛",
                "enabled":True,
                "times":1
            },
            "party_history":{
                "title":"党史活动",
                "enabled":True,
                "times":1
            }
        }
        if os.path.exists("config.json")==False:
            self.gen_conf()
        with open(file="config.json",mode="r",encoding="utf-8") as conf_reader:
            conf=json.loads(conf_reader.read())
        debug=bool(conf["debug"])
        if debug==True:
            self.handler.setLevel(logging.DEBUG)
            filehandler.setLevel(logging.DEBUG)
            self.logger.setLevel(logging.DEBUG)
        try:
            self.theme=self.Theme(name=conf["theme"])
        except:
            self.theme=self.Theme()
        self.setStyleSheet(self.theme.main)
        formatter=logging.Formatter(fmt=self.theme.logging_fmt,datefmt=self.theme.logging_datefmt)
        self.handler.setFormatter(formatter)
        filehandler.setFormatter(formatter)
        self.logger.addHandler(self.handler)
        self.logger.addHandler(filehandler)
        if os.path.exists("modules")==False:
            os.mkdir("modules")
        self.resize(self.theme.size[0],self.theme.size[1])
        self.setWindowOpacity(self.theme.opacity)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAutoFillBackground(True)
        self.setWindowIcon(QIcon(self.theme.icon))
        self.setWindowTitle("ChinaUniOnlineGUI")
        self.tray=QSystemTrayIcon()
        self.tray.setIcon(QIcon(self.theme.tray))
        self.tray.activated.connect(self.tray_func)
        self.main_layout=QGridLayout()
        central_widget.setLayout(self.main_layout)
        self.title=QLabel(self.windowTitle())
        self.title.setStyleSheet(self.theme.title)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.handler.widget.setStyleSheet(self.theme.logger)
        self.control=QVBoxLayout()
        self.control_close=QPushButton()
        self.control_close.setToolTip("关闭")
        self.control_close.setStyleSheet(self.theme.control_close)
        self.contron_max=QPushButton()
        if self.isMaximized()==False:
            self.contron_max.setToolTip("最大化")
        else:
            self.contron_max.setToolTip("还原")
        self.contron_max.setStyleSheet(self.theme.control_max)
        self.control_min=QPushButton()
        self.control_min.setToolTip("最小化")
        self.control_min.setStyleSheet(self.theme.control_min)
        self.start_button=QPushButton("开始(&S)")
        self.start_button.setStyleSheet(self.theme.start_button)
        self.start_button.setToolTip("开始")
        self.start_button.setFixedSize(120,60)
        self.start_button.setDefault(True)
        setting_button=QPushButton("设置")
        setting_button.setToolTip("设置")
        setting_button.setFixedSize(60,30)
        setting_button.setStyleSheet(self.theme.setting_button)
        setting_button.clicked.connect(self.setting_callback)
        self.bootstrap_=QPushButton("生成题库")
        self.bootstrap_.setToolTip("通过答题生成题目数据库")
        self.bootstrap_.setFixedSize(60,30)
        self.bootstrap_.setStyleSheet(self.theme.bootstrap)
        self.bootstrap_.clicked.connect(self.bootstrap_callback)
        self.bootstrap_.setEnabled(not os.path.exists("answers.db"))
        config_layout=QVBoxLayout()
        config_layout.setSpacing(0)
        config_layout.addWidget(setting_button)
        config_layout.addWidget(self.bootstrap_)
        start=QHBoxLayout()
        start.addWidget(self.start_button,2)
        start.addLayout(config_layout,1)
        self.control_close.clicked.connect(self.close)
        self.control_min.clicked.connect(self.min_callback)
        self.contron_max.clicked.connect(self.max_callback)
        self.start_button.clicked.connect(self.start_callback)
        self.finish_signal.connect(self.finish_callback)
        self.finish_bootstrap_signal.connect(self.finish_bootstrap)
        self.close_qr_signal.connect(self.close_qr)
        self.control.addWidget(self.control_min)
        self.control.addWidget(self.contron_max)
        self.control.addWidget(self.control_close)
        for i in range(self.control.count()):
            self.control.itemAt(i).widget().setFixedWidth(30)
        self.main_layout.addLayout(self.control,0,0)
        self.main_layout.addWidget(self.title,0,1)
        self.main_layout.addLayout(start,0,2)
        self.main_layout.addWidget(self.handler.widget,1,1,1,2)
        self.update_signal.connect(self.handler.widget.appendPlainText)
        self.handler.widget.textChanged.connect(self.handler.scroll_widget_to_bottom)
        self.show_qr_signal.connect(self.show_qr)
        self.user_info_signal.connect(self.user_info_callback)
        self.update_info_signal.connect(self.update_info_callback)
        self.logger.debug("当前调试状态：%s，使用样式：%s，完成UI初始化" %(debug,self.theme.name))
        self.logger.debug("正在尝试更新旧版配置")
        self.update_conf(conf=conf)
        self.hide_to_menu=conf["hide"]
        self.show_user_info=conf["show_user_info"]
        self.font_prop=conf["font_prop"]
        tray_menu=QMenu(parent=self)
        action_show=QAction(icon=QIcon(self.theme.tray_show),text="显示(&S)",parent=self)
        action_show.triggered.connect(self.show)
        action_exit=QAction(icon=QIcon(self.theme.tray_exit),text="退出(&X)",parent=self)
        action_exit.triggered.connect(self.close)
        tray_menu.addAction(action_show)
        tray_menu.addAction(action_exit)
        tray_menu.setStyleSheet(self.theme.tray_menu)
        self.tray.setContextMenu(tray_menu)
        self.move(conf["pos"][0],conf["pos"][1])
        self.update_status("未开始")
    def update_status(self,s:str):
        self.tray.setToolTip(self.windowTitle()+"\n当前状态："+s)
        self.handler.widget.setToolTip("当前状态："+s)
    def update_info_callback(self,info:dict):
        if self.show_user_info==True:
            self.avatar.update_score(score=info["integral"],t_score=info["t_integral"])
            self.avatar.update_times(times=info["join_times"],t_times=info["t_join_times"])
            self.avatar.update_avatar(self.draw_pic(info["avatar"]))
    def user_info_callback(self,info:dict):
        # info:{"integral":integral,"join_times":join_times,"t_join_times":t_join_times,"t_integral":t_integral,"university_name":university_name,"phone":zip_+" "+mobile,"avatar":avatar}
        self.logger.debug("获取数据：%s" %info)
        if self.show_user_info==True:
            self.avatar=UserAvatar(parent=self,name=info["name"],phone=info["phone"],score=info["integral"],times=info["join_times"],t_score=info["t_integral"],t_times=info["t_join_times"],school=info["university_name"],avatar=self.draw_pic(data=info["avatar"]),province_name=info["province_name"])
            self.avatar.resize(int(self.width()*(200/1024)),int(self.height()*(200/1024)))
            self.avatar.setStyleSheet(self.theme.avatar)
            self.dock=QDockWidget("当前登陆用户信息：",self)
            self.dock.setWidget(self.avatar)
            self.dock.setStyleSheet(self.theme.dock)
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,self.dock)
            self.resize(self.width()+self.dock.width(),self.height())
    def draw_pic(self,data:list):
        self.logger.debug("获取图片信息：%s" %data)
        titles=list()
        values_1=list()
        values_2=list()
        for item in data:
            titles.append(item["title"])
            if item["mode"]==1:
                values_1.append(item["accuracy"])
            elif item["mode"]==2:
                values_2.append(item["accuracy"])
        angles=numpy.linspace(0,2*numpy.pi,len(titles),endpoint=False)
        angles=numpy.concatenate((angles,[angles[0]]))
        titles=numpy.concatenate((titles,[titles[0]]))
        fig = plt.figure(dpi=100)
        ax = plt.subplot(111, polar=True)
        ax.set_thetagrids(angles*180/numpy.pi, titles,fontproperties=self.font_prop)
        ax.set_theta_zero_location('N')
        ax.set_rlim(0, 100)
        ax.set_rlabel_position(315)
        buffer=io.BytesIO()
        if values_1!=[]:
            values_1=numpy.concatenate((values_1,[values_1[0]]))
            ax.plot(angles,values_1,label="个人模式分布")
        if values_2!=[]:
            values_2=numpy.concatenate((values_2,[values_2[0]]))
            ax.plot(angles,values_2,label="团队模式分布")
        plt.legend(loc="best",prop=self.font_prop)
        plt.title("用户正确率分布",fontproperties=self.font_prop)
        fig.savefig(buffer)
        data_bytes=buffer.getvalue()
        plt.close(fig)
        buffer.close()
        return data_bytes
    def tray_func(self,reason:QSystemTrayIcon.ActivationReason):
        if reason==QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isHidden()==True:
                self.tray.setVisible(False)
                self.handler.scroll_widget_to_bottom()
                self.setVisible(True)
                self.setFocus()
            else:
                self.setVisible(False)
                self.tray.setVisible(True)
    def bootstrap_callback(self):
        if QSqlDatabase.contains("ANSWER_SEARCH"):
            self.db=QSqlDatabase.database("ANSWER_SEARCH")
        else:
            self.db=QSqlDatabase.addDatabase("QSQLITE","ANSWER_SEARCH")
        self.db.setDatabaseName("answers.db")
        if self.db.open()==False:
            self.logger.error("数据库受损，无法打开")
            self.logger.debug("详细错误：%s" %self.db.lastError().text())
            raise RuntimeError("数据库受损")
        elif self.db.transaction()==False:
            self.logger.error("启动数据库事务失败")
            self.logger.debug("详细错误：%s" %self.db.lastError().text())
            raise RuntimeError("数据库事务启动失败")
        self.logger.debug("已启动数据库连接")
        self.query=QSqlQuery(db=self.db)
        self.query.exec("CREATE TABLE 'ALL_ANSWERS' (QUESTION TEXT NOT NULL UNIQUE,ANSWER TEXT NOT NULL)")
        self.bootstrap_thread=QThread()
        self.bootstrap=BootStrap(query=self.query,show_qr_signal=self.show_qr_signal,finish_signal=self.finish_bootstrap_signal,close_qr_signal=self.close_qr_signal,tray=self.tray,user_info_signal=self.user_info_signal,update_info_signal=self.update_info_signal)
        self.bootstrap.close_dock_signal.connect(self.close_dock)
        self.bootstrap.update_tray.connect(self.update_status)
        self.bootstrap.moveToThread(self.bootstrap_thread)
        self.bootstrap_thread.started.connect(self.bootstrap.start)
        self.logger.debug("准备执行数据库初始化")
        self.bootstrap_.setEnabled(False)
        self.bootstrap_.setText("执行中...")
        self.start_button.setEnabled(False)
        self.bootstrap_thread.start()
    def finish_bootstrap(self):
        self.bootstrap_thread.quit()
        self.bootstrap_thread.wait()
        self.logger.debug("初始化数据库完成")
        self.query.finish()
        self.query.clear()
        self.db.commit()
        self.db.close()
        self.bootstrap_.setEnabled(True)
        self.bootstrap_.setText("生成题库")
        self.start_button.setEnabled(True)
    def min_callback(self):
        if self.isMinimized()==False:
            if self.hide_to_menu==False:
                self.showMinimized()
            else:
                self.setVisible(False)
                self.tray.setVisible(True)
                if self.need_message==True:
                    self.tray.showMessage("ChinaUniOnlineGUI","已最小化至托盘菜单，双击图标切换显示",QSystemTrayIcon.MessageIcon.Information)
                    self.need_message=False
    def max_callback(self):
        if self.isMaximized()==False:
            self.showMaximized()
            self.contron_max.setToolTip("还原")
        else:
            self.showNormal()
            self.contron_max.setToolTip("最大化")
    def start_callback(self):
        if QSqlDatabase.contains("ANSWER_SEARCH"):
            self.db=QSqlDatabase.database("ANSWER_SEARCH")
        else:
            self.db=QSqlDatabase.addDatabase("QSQLITE","ANSWER_SEARCH")
        self.db.setDatabaseName("answers.db")
        if self.db.open()==False:
            self.logger.error("数据库受损，无法打开")
            self.logger.debug("详细错误：%s" %self.db.lastError().text())
            raise RuntimeError("数据库受损")
        elif self.db.transaction()==False:
            self.logger.error("启动数据库事务失败")
            self.logger.debug("详细错误：%s" %self.db.lastError().text())
            raise RuntimeError("数据库事务启动失败")
        self.logger.debug("已启动数据库连接")
        self.query=QSqlQuery(db=self.db)
        tables=self.db.tables()
        if "ALL_ANSWERS" not in tables or len(tables)>1:
            self.logger.info("正在更新数据库到新版文件")
            shutil.copy("answers.db","answers.db.bak")
            self.logger.info("旧版数据库备份为answers.db.bak")
            self.logger.debug("全部旧数据表：%s" %tables)
            self.query.exec("CREATE TABLE 'ALL_ANSWERS' (QUESTION TEXT NOT NULL UNIQUE,ANSWER TEXT NOT NULL)")
            for table in tables:
                if table=="ALL_ANSWERS":
                    continue
                self.logger.debug("正在插入 %s 的旧数据到新表中" %table)
                self.query.exec("INSERT OR IGNORE INTO 'ALL_ANSWERS' SELECT * FROM '%s'" %table)
                self.logger.debug("正在删除旧数据表")
                self.query.exec("DROP TABLE '%s'" %table)
            self.db.commit()
        self.start_time=time.time()
        self.work=Work(show_qr_signal=self.show_qr_signal,finish_signal=self.finish_signal,close_qr_signal=self.close_qr_signal,tray=self.tray,user_info_signal=self.user_info_signal,update_info_signal=self.update_info_signal,query=self.query)
        self.work.close_dock_signal.connect(self.close_dock)
        self.work.update_tray.connect(self.update_status)
        self.work_thread=QThread()
        self.work.moveToThread(self.work_thread)
        self.work_thread.started.connect(self.work.start)
        self.work_thread.start()
        self.start_button.setEnabled(False)
        if self.bootstrap_.isEnabled()==True:
            self.bootstrap_.setEnabled(False)
        self.start_button.setText("执行中...")
    def finish_callback(self):
        self.start_button.setEnabled(True)
        self.bootstrap_.setEnabled(False)
        self.start_button.setText("开始(&S)")
        self.work_thread.quit()
        self.work_thread.wait()
        if self.show_user_info==True:
            self.close_dock()
        self.query.finish()
        self.query.clear()
        if self.db.commit()==True:
            self.logger.debug("提交数据库更改成功")
        else:
            self.logger.error("提交数据库更改失败，正在回滚更改")
            self.db.rollback()
        self.db.close()
        self.logger.info("已关闭数据库连接")
        passed_time=time.time()-self.start_time
        mins,secs=divmod(passed_time,60)
        hours,mins=divmod(mins,60)
        self.logger.info("执行完成，共计用时 {:0>2d}:{:0>2d}:{:0>2d}".format(int(hours),int(mins),int(secs)))
        if self.isVisible()==False:
            self.tray.showMessage("ChinaUniOnline:任务执行完成","共计用时 {:0>2d}:{:0>2d}:{:0>2d}".format(int(hours),int(mins),int(secs)),QSystemTrayIcon.MessageIcon.Information)
        self.update_status("已完成")
    def show_qr(self,qr:bytes):
        title_label=QLabel("请使用微信扫描小程序码完成登陆")
        title_label.setStyleSheet(self.theme.qr_title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFixedHeight(20)
        qr_label=QLabel()
        pixmap=QPixmap()
        pixmap.loadFromData(qr)
        qr_label.setPixmap(pixmap)
        qr_label.setStyleSheet(self.theme.qr)
        layout_=QVBoxLayout()
        layout_.addWidget(title_label,1)
        layout_.addWidget(qr_label,9)
        self.qr_dialog=QWidget(self)
        self.qr_dialog.setLayout(layout_)
        self.main_layout.addWidget(self.qr_dialog,1,1,Qt.AlignmentFlag.AlignCenter)
        self.qr_dialog.show()
    def close_qr(self):
        self.qr_dialog.close()    
    def setting_callback(self):
        setting=SettingWindow(parent=self,theme=self.theme.setting)
        setting.setStyleSheet(self.theme.setting_window)
        setting.show()
    def update_conf(self,conf:dict,new_conf:dict=None,write:bool=True):
        need_update=False
        skip=["auth"]
        if new_conf==None:
            new_conf=self.default_conf
        for key in new_conf.keys():
            self.logger.debug("正在比较键值 %s" %key)
            if key in conf:
                self.logger.debug("键值 %s 的数据已存在" %key)
                if type(new_conf[key])==dict and type(conf[key])==dict:
                    self.logger.debug("正在进行递归调用检查深层配置文件")
                    need_update=self.update_conf(conf=conf[key],new_conf=new_conf[key],write=False)
            else:
                need_update=True
                self.logger.debug("正在将 %s 的默认值应用到旧版数据上" %key)
                conf[key]=new_conf[key]                  
        if write==True and need_update==True:
            self.logger.info("旧版配置已备份为 config.json.bak")
            shutil.copy("config.json","config.json.bak")
            self.logger.debug("正在更新配置文件")
            with open(file="config.json",mode="w",encoding="utf-8") as writer:
                writer.write(json.dumps(conf,ensure_ascii=False,sort_keys=True,indent=4))
        return need_update
    def gen_conf(self):
        with open(file="config.json",mode="w",encoding="utf-8") as conf_writer:
            conf_writer.write(json.dumps(self.default_conf,indent=4,sort_keys=True,ensure_ascii=False))
        self.logger.info("已生成默认配置文件")
    def close_dock(self):
        if self.show_user_info==True:
            self.removeDockWidget(self.dock)
            self.resize(self.theme.size[0],self.theme.size[1])
    def close(self) -> bool:
        if QSqlDatabase.contains("ANSWER_SEARCH")==True:
            db=QSqlDatabase.database("ANSWER_SEARCH")
            if db.commit()==True:
                self.logger.debug("提交数据库更改成功")
            elif db.rollback()==True:
                self.logger.debug("已回滚数据库更改")
            else:
                self.logger.warning("未成功保存数据库，答案信息可能有损失")
            db.close()
            self.logger.debug("已关闭未关闭的数据库连接")
        else:
            self.logger.debug("无未关闭的数据库连接")
        with open(file="config.json",mode="r",encoding="utf-8") as reader:
            conf=json.loads(reader.read())
        conf["pos"]=[self.pos().x(),self.pos().y()]
        with open(file="config.json",mode="w",encoding="utf-8") as writer:
            writer.write(json.dumps(conf,ensure_ascii=False,indent=4,sort_keys=True))
        return super().close()
    def mousePressEvent(self, event:QMouseEvent):
        self.logger.debug("触发鼠标按压事件")
        super().mousePressEvent(event)
        self.setFocus()
        self.m_flag=True
        if event.button()==Qt.MouseButton.LeftButton and self.isMaximized()==False and self.hasFocus()==True:
            self.old_pos=event.globalPosition() #获取鼠标相对窗口的位置
            self.logger.debug("已获取鼠标位置")
    def mouseMoveEvent(self, event:QMouseEvent):
        self.logger.debug("触发鼠标移动事件")
        super().mouseMoveEvent(event)
        if self.m_flag==True:
            delta_x=int(event.globalPosition().x()-self.old_pos.x())
            delta_y=int(event.globalPosition().y()-self.old_pos.y())
            self.move(self.x()+delta_x,self.y()+delta_y)#更改窗口位置
            self.logger.debug("已更改窗口位置")
            self.old_pos=event.globalPosition()
            self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))  #更改鼠标图标
    def mouseReleaseEvent(self, event:QMouseEvent):
        self.logger.debug("触发鼠标释放事件")
        super().mouseReleaseEvent(event)
        self.m_flag=False
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
if __name__=="__main__":
    app=QApplication(sys.argv)
    ui=UI()
    ui.show()
    sys.exit(app.exec())
    