'''
Function:
    大学生在线 "四史"自动答题刷分
Author:
    XWhite
GitHub项目地址:
    https://github.com/Upsetin/ChinaUniOnline
更新日期:
    2021-03-18
'''

import requests,csv,re,json,random,time, hashlib
cookie = "_ga=GA1.2." + str(random.randrange(50000000,59999999)) + "." + str(int(time.time())-random.randrange(30000,120000)) + "; _gid=GA1.2." + str(random.randrange(500000000,599999999)) + "." + str(int(time.time())-random.randrange(30000,120000)) + "; tgw_l7_route=" + hashlib.md5(str(random.randrange(10000,99999)).encode('utf8')).hexdigest() + "; _gat=1"

#获取个人信息
def GetInfo():
    import requests

    url = "https://ssxx.univs.cn/cgi-bin/race/grade/?t="+str(int(time.time()))+"&activity_id=5f71e934bcdbf3a8c3ba5061"

    payload = {}
    headers = {
        'authority': 'ssxx.univs.cn',
        'sec-ch-ua': '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
        'accept': 'application/json, text/plain, */*',
        'authorization': 'Bearer %s' % (token),
        'sec-ch-ua-mobile': '?0',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; BKL-AL20 Build/HUAWEIBKL-AL20; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.62 XWEB/2777 MMWEBSDK/201201 Mobile Safari/537.36 MMWEBID/1494 MicroMessenger/8.0.1.1841(0x28000151) Process/toolsmp WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://ssxx.univs.cn/client/exam/5f71e934bcdbf3a8c3ba5061/1/1/5f71e934bcdbf3a8c3ba51d5',
        'accept-language': 'zh,en;q=0.9,zh-CN;q=0.8',
        'cookie': cookie
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    return response.json()


#获取登录二维码 -已失效
def ViewQR(url=''):
    html = requests.get(url)
    with open('QR.png', 'wb') as file:
        file.write(html.content)

    import platform
    userPlatform=platform.system()						# 获取操作系统
    fileDir='QR.png'

    if userPlatform == 'Darwin':								# Mac
        import subprocess
        subprocess.call(['open', fileDir])
    elif userPlatform == 'Linux':								# Linux
        import subprocess
        subprocess.call(['xdg-open', fileDir])
    else:																# Windows
        import os
        os.startfile(fileDir)


#读取题库
def ReadFile():
    with open("题库.csv", "r",encoding='UTF-8') as f:
        reader = csv.reader(f)
        db = []
        for row in list(reader):
            db.append(row)
    return db


#写入题库
def IntoFile(FileNmae = '题库.csv',Data=[]):
    file = open(FileNmae, 'a', encoding='utf-8')
    f = csv.writer(file)
    f.writerow(
        Data
    )
    print('已写入%s文件:'%(FileNmae),Data)
    file.close()


#获取题目
def GetQuestions(activity_id='5f71e934bcdbf3a8c3ba5061',mode_id='5f71e934bcdbf3a8c3ba51d5'):

    url = "https://ssxx.univs.cn/cgi-bin/race/beginning/?t="+str(int(time.time()))+"&activity_id=%s&mode_id=%s&way=1"%(activity_id,mode_id)

    payload = {}
    headers = {
        'authority': 'ssxx.univs.cn',
        'sec-ch-ua': '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
        'accept': 'application/json, text/plain, */*',
        'authorization': 'Bearer %s'%(token),
        'sec-ch-ua-mobile': '?0',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; BKL-AL20 Build/HUAWEIBKL-AL20; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.62 XWEB/2777 MMWEBSDK/201201 Mobile Safari/537.36 MMWEBID/1494 MicroMessenger/8.0.1.1841(0x28000151) Process/toolsmp WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://ssxx.univs.cn/client/exam/5f71e934bcdbf3a8c3ba5061/1/1/5f71e934bcdbf3a8c3ba51d5',
        'accept-language': 'zh,en;q=0.9,zh-CN;q=0.8',
        'cookie': cookie
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    # print('获取题目:',response.json())
    question_ids = response.json()['question_ids']
    num = 0
    SucessNum = 0
    FailNum = 0
    for i in range(len(question_ids)):
        num += 1
        if i == 10:
            if CheckVerification():
                print("验证码已通过")
            else:
                SubmitVerification()
                print("验证码状态：", CheckVerification())
        if GetOption(activity_id=activity_id,question_id=question_ids[i],mode_id=mode_id):
            SucessNum += 1
        else:
            FailNum += 1
    race_code = response.json()['race_code']
    Finsh(race_code)
    print('此次成功查询%s个题，收录%s个题'%(SucessNum,FailNum))


#获取选项
def GetOption(activity_id='5f71e934bcdbf3a8c3ba5061',question_id='5f17ef305d6fe02504ba5e17',mode_id='5f71e934bcdbf3a8c3ba51d5'):

    url = "https://ssxx.univs.cn/cgi-bin/race/question/?t="+str(int(time.time()))+"&activity_id=%s&question_id=%s&mode_id=%s&way=1"%(activity_id,question_id,mode_id)

    payload = {}
    headers = {
        'authority': 'ssxx.univs.cn',
        'sec-ch-ua': '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
        'accept': 'application/json, text/plain, */*',
        'authorization': 'Bearer %s'%(token),
        'sec-ch-ua-mobile': '?0',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; BKL-AL20 Build/HUAWEIBKL-AL20; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.62 XWEB/2777 MMWEBSDK/201201 Mobile Safari/537.36 MMWEBID/1494 MicroMessenger/8.0.1.1841(0x28000151) Process/toolsmp WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://ssxx.univs.cn/client/exam/5f71e934bcdbf3a8c3ba5061/1/1/5f71e934bcdbf3a8c3ba51d5',
        'accept-language': 'zh,en;q=0.9,zh-CN;q=0.8',
        'cookie': cookie
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    # print('获取选项:',response.json())

    options = response.json()['data']['options']
    #选项
    result = {}
    for i in options:
        title = i['title']
        replace1 = re.findall('<.*?>', title)
        for j in range(len(replace1)):
            if 'display:none;' in replace1[j] or 'display: none;' in replace1[j]:
                replace2 = re.findall('%s.*?%s' % (replace1[j], replace1[j + 1]), title)
                title = str(title).replace(replace2[0], '')
        for j in replace1:
            title = str(title).replace(j, '')
        result[title] = i['id']
    # print(result)

    #题目
    title = response.json()['data']['title']
    replace1 = re.findall('<.*?>',title)
    for i in range(len(replace1)):
        if 'display:none;' in replace1[i] or 'display: none;' in replace1[i]:
            replace2 = re.findall('%s.*?%s'%(replace1[i],replace1[i+1]),title)
            title = str(title).replace(replace2[0],'')
    for i in replace1:
        title = str(title).replace(i,'')
    # print(title)

    '''判断题目是否已在题库中'''
    db = ReadFile()
    for i in db:
        if not i:
            continue
        #在题库中
        if title in i[0]:
            print('在题库中已搜索到答案: %s - %s'%(i[0],i[1]))
            answer = []
            for j,k in result.items():
                if j in i[1]:
                    answer.append(k)
            #提交答案
            Confire(question_id=question_id,answer=answer)
            return 'Sucess'
    #题库中没有
    print('未在题库中搜索到答案，执行捕获题目模式...')
    results = SreachResult(question_id=question_id, answer=response.json()['data']['options'][0]['id'])
    TrueResult = []
    for i in results:
        for j,k in result.items():
            if i == k:
                TrueResult.append(j)
    num = 0
    for i in db:
        if title in i:
            num += 1
            break
    if not num:
        IntoFile(FileNmae = '题库.csv',Data=[title,TrueResult])
    else:
        print('已存在题库中: ',title[0],TrueResult)


#从题库中搜素答案
def SreachResult(question_id='5f17ef305d6fe02504ba5e17',answer='5f75fe348e6c9f85d1b6072a',activity_id='5f71e934bcdbf3a8c3ba5061',mode_id='5f71e934bcdbf3a8c3ba51d5'):

    url = "https://ssxx.univs.cn/cgi-bin/race/answer/"

    payload = "{\"activity_id\":\"%s\",\"question_id\":\"%s\",\"answer\":[\"%s\"],\"mode_id\":\"%s\",\"way\":\"1\"}"%(activity_id,question_id,answer,mode_id)
    headers = {
        'authority': 'ssxx.univs.cn',
        'sec-ch-ua': '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
        'accept': 'application/json, text/plain, */*',
        'authorization': 'Bearer %s'%(token),
        'sec-ch-ua-mobile': '?0',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; BKL-AL20 Build/HUAWEIBKL-AL20; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.62 XWEB/2777 MMWEBSDK/201201 Mobile Safari/537.36 MMWEBID/1494 MicroMessenger/8.0.1.1841(0x28000151) Process/toolsmp WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64',
        'content-type': 'application/json;charset=UTF-8',
        'origin': 'https://ssxx.univs.cn',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://ssxx.univs.cn/client/exam/5f71e934bcdbf3a8c3ba5061/1/1/5f71e934bcdbf3a8c3ba51d5',
        'accept-language': 'zh,en;q=0.9,zh-CN;q=0.8',
        'cookie': cookie
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    data = response.json()
    # print('提交选项:',data)
    return response.json()['data']['correct_ids']


#提交题目选项
def Confire(question_id='5f17ef305d6fe02504ba5e17',answer=['5f75fe348e6c9f85d1b6072a'],activity_id='5f71e934bcdbf3a8c3ba5061',mode_id='5f71e934bcdbf3a8c3ba51d5'):

    url = "https://ssxx.univs.cn/cgi-bin/race/answer/"

    payload = '{"activity_id":"%s","question_id":"%s","answer":%s,"mode_id":"%s","way":"1"}'%(activity_id,question_id,json.dumps(answer),mode_id)


    headers = {
        'authority': 'ssxx.univs.cn',
        'sec-ch-ua': '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
        'accept': 'application/json, text/plain, */*',
        'authorization': 'Bearer %s'%(token),
        'sec-ch-ua-mobile': '?0',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; BKL-AL20 Build/HUAWEIBKL-AL20; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.62 XWEB/2777 MMWEBSDK/201201 Mobile Safari/537.36 MMWEBID/1494 MicroMessenger/8.0.1.1841(0x28000151) Process/toolsmp WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64',
        'content-type': 'application/json;charset=UTF-8',
        'origin': 'https://ssxx.univs.cn',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://ssxx.univs.cn/client/exam/5f71e934bcdbf3a8c3ba5061/1/1/5f71e934bcdbf3a8c3ba51d5',
        'accept-language': 'zh,en;q=0.9,zh-CN;q=0.8',
        'cookie': cookie
    }

    time.sleep(random.uniform(0.5,1.5))
    response = requests.request("POST", url, headers=headers, data=payload)

    data = response.json()
    # print('提交选项:', data)
    # print(data)
    return response.json()['data']['correct_ids']


#提交整个试题
def Finsh(race_code='6018f697224c6a1526204144'):

    url = "https://ssxx.univs.cn/cgi-bin/race/finish/"

    payload = "{\"race_code\":\"%s\"}"%(race_code)
    headers = {
        'authority': 'ssxx.univs.cn',
        'sec-ch-ua': '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
        'accept': 'application/json, text/plain, */*',
        'authorization': 'Bearer %s'%(token),
        'sec-ch-ua-mobile': '?0',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; BKL-AL20 Build/HUAWEIBKL-AL20; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.62 XWEB/2777 MMWEBSDK/201201 Mobile Safari/537.36 MMWEBID/1494 MicroMessenger/8.0.1.1841(0x28000151) Process/toolsmp WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64',
        'content-type': 'application/json;charset=UTF-8',
        'origin': 'https://ssxx.univs.cn',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://ssxx.univs.cn/client/exam/5f71e934bcdbf3a8c3ba5061/1/1/5f71e934bcdbf3a8c3ba51d5',
        'accept-language': 'zh,en;q=0.9,zh-CN;q=0.8',
        'cookie': cookie
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    # print('提交:',response.json())

    if response.json()['code'] == 4823:
        SubmitVerification()
        Finsh(race_code)
    # print(response.json())
    try:
        print('已提交,正确数:%s 用时:%ss'%(response.json()['data']['owner']['correct_amount'],response.json()['data']['owner']['consume_time']))
    except:
        print(response.json())


#PK10 -已废弃，暂不更新
def PK10(activity_id='5f71e934bcdbf3a8c3ba5061',mode_id='5f71e934bcdbf3a8c3ba51da'):
    import requests

    url = "https://ssxx.univs.cn/cgi-bin/race/beginning/?t="+str(int(time.time()))+"&activity_id=%s&mode_id=%s&way=1"%(activity_id,mode_id)

    payload = {}
    headers = {
        'authority': 'ssxx.univs.cn',
        'sec-ch-ua': '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
        'accept': 'application/json, text/plain, */*',
        'authorization': 'Bearer %s'%(token),
        'sec-ch-ua-mobile': '?0',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; BKL-AL20 Build/HUAWEIBKL-AL20; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.62 XWEB/2777 MMWEBSDK/201201 Mobile Safari/537.36 MMWEBID/1494 MicroMessenger/8.0.1.1841(0x28000151) Process/toolsmp WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://ssxx.univs.cn/client/exam/5f71e934bcdbf3a8c3ba5061/3/1/5f71e934bcdbf3a8c3ba51da',
        'accept-language': 'zh,en;q=0.9,zh-CN;q=0.8',
        'cookie': cookie
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    # print(response.json())

    question_ids = response.json()['question_ids']
    num = 0
    SucessNum = 0
    FailNum = 0
    for i in question_ids:
        num += 1
        if GetOption(activity_id=activity_id, question_id=i, mode_id=mode_id):
            SucessNum += 1
        else:
            FailNum += 1
    race_code = response.json()['race_code']
    Finsh(race_code)
    print('此次成功查询%s个题，收录%s个题' % (SucessNum, FailNum))


#登录函数 -已失效
def Login():
    print('正在获取登陆二维码...')
    Random = ''.join(random.sample('qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM1234567890',random.randrange(5,10)))
    url = 'https://oauth.u.hep.com.cn/oauth/wxapp/qrcode/5f582dd3683c2e0ae3aaacee?random=%s&useSelfWxapp=true&enableFetchPhone=false'%(Random)
    a = requests.get(url)
    print("请用微信扫描二维码登陆...")
    ViewQR(a.json()['data']['qrcode'])
    print('\r正在等待扫描二维码...',end='\r')
    time.sleep(3)
    TimeNum = 1
    while True:
        print('\r正在等待扫描二维码,已等待%ss...'%(TimeNum),end='')
        a = requests.post('https://oauth.u.hep.com.cn/oauth/wxapp/confirm/qr?random=%s&useSelfWxapp=true'%(Random))
        if a.json()['data']['code'] == 200:
            _id = a.json()['data']['data']['_id']
            print('\n欢迎你,%s'%(a.json()['data']['data']['username']))
            GetToken(uid=_id)
            break
        time.sleep(1)
        print('\r',end='')
        TimeNum += 1


#获取token
def GetToken(uid='',uc_token=''):
    if uc_token=="":
        url = 'https://ssxx.univs.cn/cgi-bin/authorize/token/?t='+str(int(time.time()))+'&uid=%s'%(uid)
    else:
        url = 'https://ssxx.univs.cn/cgi-bin/authorize/token/?t='+str(int(time.time()))+'&uc_token=%s'%(uc_token)
    a = requests.get(url=url)
    global token
    token = a.json()['token']
    # print(token)
    return token


#检查验证信息
def CheckVerification():
    headers = {
        'authority': 'ssxx.univs.cn',
        'sec-ch-ua': '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
        'accept': 'application/json, text/plain, */*',
        'authorization': 'Bearer %s' % (token),
        'sec-ch-ua-mobile': '?0',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; BKL-AL20 Build/HUAWEIBKL-AL20; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.62 XWEB/2777 MMWEBSDK/201201 Mobile Safari/537.36 MMWEBID/1494 MicroMessenger/8.0.1.1841(0x28000151) Process/toolsmp WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://ssxx.univs.cn/client/exam/5f71e934bcdbf3a8c3ba5061/1/1/5f71e934bcdbf3a8c3ba51d5',
        'accept-language': 'zh,en;q=0.9,zh-CN;q=0.8',
        'cookie': cookie
    }
    code = "E5ZKeoD8xezW4TVEn20JVHPFVJkBIfPg+zvMGW+kx1s29cUNFfNka1+1Fr7lUWsyUQhjiZXHDcUhbOYJLK4rS5MflFUvwSwd1B+1kul06t1z9x0mfxQZYggbnrJe3PKEk4etwG/rm3s3FFJd/EbFSdanfslt41aULzJzSIJ/HWI="
    submit_data = {
        "activity_id": "5f71e934bcdbf3a8c3ba5061",
        "mode_id": '5f71e934bcdbf3a8c3ba51d5',
        "way": "1",
        "code": code
    }
    url = "https://ssxx.univs.cn/cgi-bin/check/verification/code/"
    response = requests.post(url, json=submit_data, headers=headers)
    result = json.loads(response.text)
    # print(result)
    return result["status"]


#提交验证
def SubmitVerification():
    headers = {
        'authority': 'ssxx.univs.cn',
        'sec-ch-ua': '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
        'accept': 'application/json, text/plain, */*',
        'authorization': 'Bearer %s' % (token),
        'sec-ch-ua-mobile': '?0',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; BKL-AL20 Build/HUAWEIBKL-AL20; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.62 XWEB/2777 MMWEBSDK/201201 Mobile Safari/537.36 MMWEBID/1494 MicroMessenger/8.0.1.1841(0x28000151) Process/toolsmp WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://ssxx.univs.cn/client/exam/5f71e934bcdbf3a8c3ba5061/1/1/5f71e934bcdbf3a8c3ba51d5',
        'accept-language': 'zh,en;q=0.9,zh-CN;q=0.8',
        'cookie': cookie
    }
    code = "HD1bhUGI4d/FhRfIX4m972tZ0g3jRHIwH23ajyre9m1Jxyw4CQ1bMKeIG5T/voFOsKLmnazWkPe6yBbr+juVcMkPwqyafu4JCDePPsVEbVSjLt8OsiMgjloG1fPKANShQCHAX6BwpK33pEe8jSx55l3Ruz/HfcSjDLEHCATdKs4="
    submit_data = {
        "activity_id": "5f71e934bcdbf3a8c3ba5061",
        "mode_id": '5f71e934bcdbf3a8c3ba51d5',
        "way": "1",
        "code": code
    }
    url = "https://ssxx.univs.cn/cgi-bin/save/verification/code/"
    response = requests.post(url, json=submit_data, headers=headers)
    result = response.json()
    # print(result)
    # if result["code"] != 0:
    #     pass
        # raise MyError(result["code"], "提交验证码失败：" + str(result))
    # return result["status"]

# token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MTU4MjU3ODgsImlhdCI6MTYxNTgxNDk4OCwiaXNzIjoiSEVQRTM6QVVUSCIsIm5iZiI6MTYxNTgxNDk4OCwidWlkIjoiNjAxOTQyNjhkMGI2MGI1Nzg4MWU5MjJjIiwibmFtZSI6Ilx1N2M3M1x1OWE2Y1x1Njc5NyIsImNvZGUiOiI2MDE5NDI2OGQwYjYwYjU3ODgxZTkyMmMiLCJpc19wZXJmZWN0Ijp0cnVlfQ.7ehyVRuorstSzZBzAE7Imdgoa_gVmDAS31Wj90l24eI'

loginInfo=input("请输入uc_token，直接回车以进行token或者uid的输入").strip()
old=False
if loginInfo=="":
    loginInfo = input('请输入uid或者token「不含Bearer，即后面那一串内容.」\n输入完成后回车:')
    old=True

judge = True
if old==False:
    try:
        token=GetToken(uc_token=loginInfo)
    except:
        judge=False
        print("使用uc_token获取token失败")
elif len(loginInfo) > 200:
    print('已更新token,正在获取信息...')
    token = loginInfo
else:
    uid = loginInfo
    print('正在获取token，请稍后...')
    try:
        token = GetToken(uid=uid)
    except:
        judge = False
        print('uid输入有误或网络问题...')
    print('token已更新...')
info = GetInfo()
try:
    info = GetInfo()['data']
except:
    judge = False
    print('输入token有误或登录已过期...')
if judge:

    print('欢迎你，来自%s的%s,当前积分:%s'%(info['university_name'],info['name'],info['integral']))
    EndNum = int(input("暂只适配英雄篇,请输入的刷题次数 (55次稳上1000分,积分更新有延迟，不用担心!): "))
    num = 0
    while num < EndNum:
        info = GetInfo()['data']
        print('\n当前积分:',info['integral'])
        num += 1
        print('\n英雄篇-正在第%s次刷题～'%(num))
        GetQuestions()

    info = GetInfo()['data']
    print('\n感谢使用!来自%s的%s,当前积分:%s'%(info['university_name'],info['name'],info['integral']))
input('感谢使用，回车退出程序:)')
