from flask import Flask, request, jsonify
import datetime
import random
import requests
import re
import threading
import time
from hashlib import md5
from time import time as T
import secrets
import json

app = Flask(__name__)

# --- Bắt đầu phần mã Python gốc đã được điều chỉnh ---

# Lớp Signature (giữ nguyên như mã gốc)
class Signature:
    def __init__(self, params: str, data: str, cookies: str) -> None:
        self.params = params
        self.data = data
        self.cookies = cookies

    def hash(self, data: str) -> str:
        return str(md5(data.encode()).hexdigest())

    def calc_gorgon(self) -> str:
        gorgon = self.hash(self.params)
        if self.data:
            gorgon += self.hash(self.data)
        else:
            gorgon += str("0"*32)
        if self.cookies:
            gorgon += self.hash(self.cookies)
        else:
            gorgon += str("0"*32)
        gorgon += str("0"*32)
        return gorgon

    def get_value(self):
        gorgon = self.calc_gorgon()
        return self.encrypt(gorgon)

    def encrypt(self, data: str):
        unix = int(T())
        len_val = 0x14 # Đổi tên biến 'len' thành 'len_val' để tránh xung đột với hàm len()
        key = [
            0xDF, 0x77, 0xB9, 0x40, 0xB9, 0x9B, 0x84, 0x83,
            0xD1, 0xB9, 0xCB, 0xD1, 0xF7, 0xC2, 0xB9, 0x85,
            0xC3, 0xD0, 0xFB, 0xC3,
        ]

        param_list = []
        for i in range(0, 12, 4):
            temp = data[8 * i : 8 * (i + 1)]
            for j in range(4):
                H = int(temp[j * 2 : (j + 1) * 2], 16)
                param_list.append(H)

        param_list.extend([0x0, 0x6, 0xB, 0x1C])
        H = int(hex(unix), 16)
        param_list.append((H & 0xFF000000) >> 24)
        param_list.append((H & 0x00FF0000) >> 16)
        param_list.append((H & 0x0000FF00) >> 8)
        param_list.append((H & 0x000000FF) >> 0)

        eor_result_list = []
        for A, B in zip(param_list, key):
            eor_result_list.append(A ^ B)

        for i in range(len_val): # Sử dụng len_val
            C = self.reverse(eor_result_list[i])
            D = eor_result_list[(i + 1) % len_val] # Sử dụng len_val
            E = C ^ D
            F = self.rbit(E)
            H = ((F ^ 0xFFFFFFFF) ^ len_val) & 0xFF # Sử dụng len_val
            eor_result_list[i] = H

        result = ""
        for param in eor_result_list:
            result += self.hex_string(param)

        return {"X-Gorgon": ("840280416000" + result), "X-Khronos": str(unix)}

    def rbit(self, num):
        result = ""
        tmp_string = bin(num)[2:]
        while len(tmp_string) < 8:
            tmp_string = "0" + tmp_string
        for i in range(0, 8):
            result = result + tmp_string[7 - i]
        return int(result, 2)

    def hex_string(self, num):
        tmp_string = hex(num)[2:]
        if len(tmp_string) < 2:
            tmp_string = "0" + tmp_string
        return tmp_string

    def reverse(self, num):
        tmp_string = self.hex_string(num)
        return int(tmp_string[1:] + tmp_string[:1], 16)

# Biến toàn cục để kiểm soát dừng các luồng
# Sử dụng một dictionary để lưu trữ stop_flag cho từng tác vụ nếu cần quản lý nhiều tác vụ đồng thời
# Tuy nhiên, để đơn giản, chúng ta sẽ dùng một stop_flag duy nhất cho tác vụ hiện tại.
# Nếu bạn muốn chạy nhiều tác vụ độc lập, cần một cơ chế quản lý stop_flag phức tạp hơn (ví dụ: dict[task_id] = threading.Event())
current_stop_flag = threading.Event()

# Hàm gửi view liên tục
def send_view_thread(video_id: str):
    url_view = 'https://api16-core-c-alisg.tiktokv.com/aweme/v1/aweme/stats/?ac=WIFI&op_region=VN'
    sig = Signature(params='', data='', cookies='').get_value()
    while not current_stop_flag.is_set():
        random_hex = secrets.token_hex(16)
        headers_view = {
            'Host': 'api16-core-c-alisg.tiktokv.com',
            'Content-Length': '138',
            'Sdk-Version': '2',
            'Passport-Sdk-Version': '5.12.1',
            'X-Tt-Token': f'01{random_hex}0263ef2c096122cc1a97dec9cd12a6c75d81d3994668adfbb3ffca278855dd15c8056ad18161b26379bbf95d25d1f065abd5dd3a812f149ca11cf57e4b85ebac39d - 1.0.0',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'TikTok 37.0.4 rv:174014 (iPhone; iOS 14.2; ar_SA@calendar=gregorian) Cronet',
            'X-Ss-Stub': '727D102356930EE8C1F61B112F038D96',
            'X-Tt-Store-Idc': 'alisg',
            'X-Tt-Store-Region': 'sa',
            'X-Ss-Dp': '1233',
            'X-Tt-Trace-Id': '00-33c8a619105fd09f13b65546057d04d1-33c8a619105fd09f-01',
            'Accept-Encoding': 'gzip, deflate',
            'X-Khronos': sig['X-Khronos'],
            'X-Gorgon': sig['X-Gorgon'],
            'X-Common-Params-V2': (
                "pass-region=1&pass-route=1"
                "&language=ar"
                "&version_code=17.4.0"
                "&app_name=musical_ly"
                "&vid=0F62BF08-8AD6-4A4D-A870-C098F5538A97"
                "&app_version=17.4.0"
                "&carrier_region=VN"
                "&channel=App%20Store"
                "&mcc_mnc=45201"
                "&device_id=6904193135771207173"
                "&tz_offset=25200"
                "&account_region=VN"
                "&sys_region=VN"
                "&aid=1233"
                "&residence=VN"
                "&screen_width=1125"
                "&uoo=1"
                "&openudid=c0c519b4e8148dec69410df9354e6035aa155095"
                "&os_api=18"
                "&os_version=14.2"
                "&app_language=ar"
                "&tz_name=Asia%2FHo_Chi_Minh"
                "¤t_region=VN"
                "&device_platform=iphone"
                "&build_number=174014"
                "&device_type=iPhone14,6"
                "&iid=6958149070179878658"
                "&idfa=00000000-0000-0000-0000-000000000000"
                "&locale=ar"
                "&cdid=D1D404AE-ABDF-4973-983C-CC723EA69906"
                "&content_language="
            ),
        }
        cookie_view = {'sessionid': random_hex}
        start = datetime.datetime(2020, 1, 1, 0, 0, 0)
        end = datetime.datetime(2024, 12, 31, 23, 59, 59)
        delta_seconds = int((end - start).total_seconds())
        random_offset = random.randint(0, delta_seconds)
        random_dt = start + datetime.timedelta(seconds=random_offset)
        data = {
            'action_time': int(time.time()),
            'aweme_type': 0,
            'first_install_time': int(random_dt.timestamp()),
            'item_id': video_id,
            'play_delta': 1,
            'tab_type': 4
        }
        try:
            r = requests.post(url_view, data=data, headers=headers_view, cookies=cookie_view, timeout=1)
            # print(r.json()) # Có thể bỏ comment để debug trên console của server
            # Cập nhật sig sau mỗi request để đảm bảo X-Khronos và X-Gorgon luôn mới
            sig = Signature(params='ac=WIFI&op_region=VN', data=str(data), cookies=str(cookie_view)).get_value()
        except Exception as e:
            # print(f"Lỗi khi gửi view: {e}") # Có thể bỏ comment để debug
            continue

# Hàm chính để chạy script tăng view
def run_tiktok_booster_logic(link: str, target_seconds: int):
    global current_stop_flag
    current_stop_flag.clear() # Đảm bảo cờ dừng được reset cho mỗi lần chạy mới

    headers_id = {
        'Connection': 'close',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36',
        'Accept': 'text/html'
    }
    try:
        page = requests.get(link, headers=headers_id, timeout=10).text
        match = re.search(r'"video":\{"id":"(\d+)"', page)
        if match:
            video_id = match.group(1)
            print(f'[+] Lấy ID Video thành công: {video_id}')
            print(f'[+] Script sẽ chạy trong {target_seconds} giây')
        else:
            print('[-] Không tìm thấy ID Video')
            return {"status": "error", "message": "Không tìm thấy ID Video"}
    except Exception as e:
        print(f'[-] Lỗi khi lấy ID Video: {e}')
        return {"status": "error", "message": f"Lỗi khi lấy ID Video: {e}"}

    # Khởi tạo và chạy các luồng
    threads = []
    timer_thread = threading.Thread(target=lambda: (time.sleep(target_seconds), current_stop_flag.set()))
    timer_thread.daemon = True
    timer_thread.start()
    threads.append(timer_thread)

    for i in range(500): # Số luồng có thể điều chỉnh
        t = threading.Thread(target=send_view_thread, args=(video_id,))
        t.daemon = True
        t.start()
        threads.append(t)

    # Đợi luồng timer kết thúc để biết khi nào dừng
    timer_thread.join()
    print(f'[+] Đã chạy đủ {target_seconds} giây, dừng chạy!')
    return {"status": "success", "message": f"Đã chạy đủ {target_seconds} giây, dừng chạy!"}

# --- Kết thúc phần mã Python gốc đã được điều chỉnh ---


# --- Bắt đầu phần Flask app ---

@app.route('/')
def index():
    # Nhúng toàn bộ HTML vào đây
    html_content = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TikTok View Booster</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 40px;
                background-color: #f0f2f5;
                color: #333;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 80vh;
            }
            .container {
                background-color: #fff;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                width: 100%;
                max-width: 500px;
                text-align: center;
            }
            h1 {
                color: #1a73e8;
                margin-bottom: 25px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                font-weight: bold;
                text-align: left;
            }
            input[type="text"],
            input[type="number"] {
                width: calc(100% - 20px);
                padding: 10px;
                margin-bottom: 20px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 16px;
            }
            button {
                background-color: #28a745;
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 18px;
                transition: background-color 0.3s ease;
            }
            button:hover {
                background-color: #218838;
            }
            #statusMessage {
                margin-top: 25px;
                padding: 15px;
                border-radius: 5px;
                font-weight: bold;
                display: none; /* Ẩn ban đầu */
            }
            .status-success {
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .status-error {
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .status-info {
                background-color: #d1ecf1;
                color: #0c5460;
                border: 1px solid #bee5eb;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>TikTok View Booster</h1>
            <label for="videoLink">Link Video TIKTOK:</label>
            <input type="text" id="videoLink" placeholder="Dán link video TikTok vào đây" required>

            <label for="targetSeconds">Số giây muốn chạy:</label>
            <input type="number" id="targetSeconds" value="60" min="1" required>

            <button onclick="startBoost()">Bắt đầu Tăng View</button>

            <div id="statusMessage"></div>
        </div>

        <script>
            async function startBoost() {
                const videoLink = document.getElementById('videoLink').value;
                const targetSeconds = document.getElementById('targetSeconds').value;
                const statusMessageDiv = document.getElementById('statusMessage');

                statusMessageDiv.style.display = 'block';
                statusMessageDiv.className = 'status-info';
                statusMessageDiv.textContent = 'Đang gửi yêu cầu...';

                if (!videoLink || !targetSeconds) {
                    statusMessageDiv.className = 'status-error';
                    statusMessageDiv.textContent = 'Vui lòng nhập đầy đủ Link Video và Số giây muốn chạy.';
                    return;
                }

                try {
                    const response = await fetch('/start_boost', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ link: videoLink, seconds: targetSeconds })
                    });

                    const data = await response.json();

                    if (response.ok) {
                        statusMessageDiv.className = 'status-success';
                        statusMessageDiv.textContent = data.message;
                    } else {
                        statusMessageDiv.className = 'status-error';
                        statusMessageDiv.textContent = `Lỗi: ${data.message || 'Không xác định'}`;
                    }
                } catch (error) {
                    console.error('Lỗi khi gửi yêu cầu:', error);
                    statusMessageDiv.className = 'status-error';
                    statusMessageDiv.textContent = 'Đã xảy ra lỗi khi kết nối đến máy chủ.';
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content

@app.route('/start_boost', methods=['POST'])
def start_boost_endpoint():
    data = request.get_json()
    link = data.get('link')
    seconds = data.get('seconds')

    if not link or not seconds:
        return jsonify({"status": "error", "message": "Vui lòng cung cấp đầy đủ link và số giây."}), 400

    try:
        seconds = int(seconds)
        if seconds <= 0:
            return jsonify({"status": "error", "message": "Số giây phải lớn hơn 0."}), 400
    except ValueError:
        return jsonify({"status": "error", "message": "Số giây không hợp lệ."}), 400

    # Chạy tác vụ trong một luồng riêng để không chặn request HTTP
    # Lưu ý: Với cách này, chỉ có thể chạy một tác vụ tại một thời điểm.
    # Nếu bạn muốn chạy nhiều tác vụ đồng thời, cần một cơ chế quản lý phức tạp hơn.
    thread = threading.Thread(target=run_tiktok_booster_logic, args=(link, seconds))
    thread.daemon = True # Đảm bảo luồng sẽ kết thúc khi ứng dụng chính kết thúc
    thread.start()

    return jsonify({"status": "success", "message": "Đã bắt đầu quá trình tăng view. Vui lòng kiểm tra console server để xem tiến độ."})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) # Chạy trên cổng 5000
