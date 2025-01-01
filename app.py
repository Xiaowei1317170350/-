from flask import Flask, request
import requests
import json
import base64
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv  # 用于加载环境变量
import os
import re  # 用于正则表达式验证身份证号格式

app = Flask(__name__)

# 加载环境变量中的userToken
load_dotenv()
user_token = os.getenv('USER_TOKEN')

@app.route('/', methods=['GET'])
def index():
    return """
    <html>
    <head>
        <title>来自小玮批量人脸验证</title>
    </head>
    <body style="font-size: 18px;">
        <h1 style="text-align: center;">来自小玮批量人脸验证</h1>
        <form action="/verify_face" method="post" style="width: 500px; margin: 0 auto;">
            <label for="name" style="display: block;">姓名:</label>
            <input type="text" id="name" name="name" required style="width: 100%; padding: 5px;"><br>
            <label for="id_card_file" style="display: block;">身份证号（每行一个身份证）:</label>
            <textarea id="id_card_file" name="id_card_file" rows="4" cols="50" required style="width: 100%;"></textarea><br>
            <label for="image_url" style="display: block;">图片链接（用于人脸识别）:</label>
            <input type="text" id="image_url" name="image_url" required style="width: 100%; padding: 5px;"><br>
            <input type="submit" value="提交验证" style="display: block; margin-top: 10px;">
        </form>
    </body>
    </html>
    """

@app.route('/verify_face', methods=['POST'])
def verify_face():
    success_list = []
    fail_list = []
    user_name = request.form.get('name')
    id_card_numbers = request.form.get('id_card_file').splitlines()

    # 验证身份证号格式，只保留合法的身份证号
    valid_id_card_numbers = []
    for id_card_number in id_card_numbers:
        if re.match(r'^\d{17}[\dXx]$', id_card_number):
            valid_id_card_numbers.append(id_card_number)
        else:
            print(f"{id_card_number} 格式不符合身份证号规范，已忽略。")

    image_url = request.form.get('image_url')

    base_headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.54(0x1800362c) NetType/4G Language/zh_CN',
        'Accept': "application/json, text/plain, */*",
        'Accept-Encoding': "gzip, deflate, br, zstd",
        'Content-Type': "application/json",
        'sec-ch-ua-platform': "\"Android\"",
        'sec-ch-ua': "\"Chromium\";v=\"130\", \"Android WebView\";v=\"130\", \"Not?A_Brand\";v=\"99\"",
        'sec-ch-ua-mobile': "?1",
        'Origin': "https://mp.4wgj.com",
        'X-Requested-With': "com.tencent.mm",
        'Sec-Fetch-Site': "same-site",
        'Sec-Fetch-Mode': "cors",
        'Sec-Fetch-Dest': "empty",
        'Referer': "https://mp.4wgj.com/",
        'Accept-Language': "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    base64_image = image_to_base64(image_url)
    if base64_image:
        def verify_id_card(id_card_number):
            nonlocal success_list
            nonlocal fail_list
            face_url = "https://4wgj.com/user-server/user/wechat/newMp/page/realnameAuth"
            params = {
                'userToken': user_token
            }
            face_payload = {
                'facePhotoBase64': f"data:image/jpeg;base64,{base64_image}",
                'name': user_name,
                'idNumber': id_card_number,
                "placeId": None
            }
            face_headers = base_headers.copy()
            try:
                face_response = requests.post(face_url, params=params, data=json.dumps(face_payload),
                                              headers=face_headers, timeout=10)
                face_result_json = face_response.json()
                if face_result_json["code"] == 100000:
                    print(f"{user_name}——{id_card_number}——✅人脸识别成功✅")
                    success_list.append((user_name, id_card_number))
                else:
                    print(f"{user_name}——{id_card_number}——❌人脸识别失败❌——{face_result_json['message']}")
                    fail_list.append((user_name, id_card_number, face_result_json['message']))
            except requests.RequestException as e:
                print(f"人脸识别请求出现异常，身份证号：{id_card_number}，异常信息：{e}")
                fail_list.append((user_name, id_card_number, str(e)))

        with ThreadPoolExecutor(max_workers=15) as executor:
            executor.map(verify_id_card, valid_id_card_numbers)

    result_message = ""
    for info in success_list:
        result_message += f"{info[0]}——{info[1]}✅人脸识别成功✅<br>"
    for info in fail_list:
        result_message += f"{info[0]}——{info[1]}——❌人脸识别失败❌——{info[2]}<br>"
    if not success_list and not fail_list:
        result_message = "本次验证无任何记录，请检查输入信息及相关情况。"
    return result_message


def image_to_base64(image_url):
    try:
        response = requests.get(image_url, timeout=5)
        response.raise_for_status()
        return base64.b64encode(response.content).decode('utf-8')
    except requests.RequestException as e:
        print(f"无法获取图片，错误信息: {e}")
        return None


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
