import os.path
from flask import Flask, jsonify, request, send_from_directory
import json, os, boto3, requests, subprocess, atexit
from apscheduler.schedulers.background import BackgroundScheduler

# 导入必要的库。
# 本文件旨在利用flask库开发简易的web和API。

app = Flask(__name__)  # 创建flask应用实例
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))  #得 到的json的文件位置预定义

S3_BUCKET = '4642projectzzz'
S3_REGION = 'ap-southeast-2'
S3_URL = f'https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com'
s3_client = boto3.client('s3')

# 本文件利用aws s3 储存云完成将流量json文件上传的功能。上述4行是定义s3的储存桶、地区、URL等信息。

stored_bridge_name = None  # 预定义需要测量的桥名。


def get_ovs_statistics(bridge_name):
    command = f"sudo -S ovs-ofctl dump-ports {bridge_name}"  # 定义CLI命令，通过此命令可以在mininet 获取交换机的流量信息。
    password = "theorem"  # 使用者请把此处theorem换成你电脑的密码。
    try:
        result = subprocess.run(command.split(), input=password + '\n', capture_output=True, text=True,
                                check=True)  # 捕捉得到的流量信息，并储存在result变量中。
        print("OVS Statistics Raw Data:\n", result.stdout)  # 打印原始数据
        print("OVS Statistics Error Output:\n", result.stderr)  # 打印错误输出
        return result.stdout
    except subprocess.CalledProcessError as e:  # 错误日志
        print(f"Error running command: {e}")
        print(f"Standard Output: {e.stdout}")
        print(f"Standard Error: {e.stderr}")
        return ""


# 定义函数以获取流量信息。

def parse_statistics(stats, bridge_name):  # 主要的函数，用以处理原始数据并上传到S3云。
    data = {}  # 预定义 数据变量。
    print("parsing stats data:\n", stats)  # 调试语句，可删去。
    for line in stats.split('coll=0\n'):  # 将获取到的原始数据根据端口分开，理论上此处有更优的分割算法。
        print("processing lines: ", line)  # 调试语句，可删去。
        if 'port ' in line:  # 对已分开的每个端口的数据进行处理。
            print("Found port line:", line)  # 调试语句，可删去。
            port = line.split(':')[0].split(' ')[-1]  # 分割取得的字符串，得到端口号
            print(port)  # 调试语句，可删去。
            # rx和tx 分别代表接收和发送
            rx_packets = line.split('rx pkts=')[1].split(',')[0]
            rx_bytes = line.split('bytes=')[1].split(',')[0]
            tx_packets = line.split('tx pkts=')[1].split(',')[0]
            tx_bytes = line.split('bytes=')[-1].split(',')[0]
            data[port] = {
                'rx_packets': int(rx_packets),
                'rx_bytes': int(rx_bytes),
                'tx_packets': int(tx_packets),
                'tx_bytes': int(tx_bytes),
            }
    print("parsed data: ", data)  # 调试语句，可删去。
    json_path = os.path.join(STATIC_DIR, f'ovs_statistics_of_{bridge_name}.json')  # json文件的路径
    with open(f'ovs_statistics_of_{bridge_name}.json', 'w') as json_file:  # 将json文件存到本地
        json.dump(data, json_file, indent=4)

    s3_client.upload_file(json_path, S3_BUCKET, f'ovs_statistics_of_{bridge_name}.json',  # 将json文件上传到S3云端并输出URL
                          # ，并令此文件公共访问
                          ExtraArgs={'ACL': 'public-read'})
    s3_url = f"{S3_URL}/ovs_statistics_of_{bridge_name}.json"
    print(f"file uploaded to {s3_url}")  # 日志语句
    return data


@app.route('/api/v1/ovs/stats', methods=['GET'])  # API利用GET取得交换机数据
def ovs_stats():
    global stored_bridge_name  # 全局变量 交换机名称
    bridge_name = request.args.get('bridge_name')  # 在终端需输入交换机名称以继续。格式：
    # curl "http://localhost:5000/api/v1/ovs/stats?bridge_name=a1" a1是交换机名称
    if not bridge_name:  # 若无，报错
        return jsonify({"error": "bridge_name parameter is required"}), 400

    stored_bridge_name = bridge_name
    stats = get_ovs_statistics(bridge_name)
    parsed_data = parse_statistics(stats, bridge_name)
    # 运行函数取得数据，返回所需。

    return jsonify(parsed_data)


def refresh_stats():
    global stored_bridge_name
    if stored_bridge_name is not None:
        stats = get_ovs_statistics(stored_bridge_name)
        parsed_data = parse_statistics(stats, stored_bridge_name)
        print("Stats refreshed and uploaded to S3.")
    else:
        print("No Bridge_name set. Skip Refresh.")


scheduler = BackgroundScheduler()
scheduler.add_job(func=refresh_stats, trigger="interval", seconds=60)
scheduler.start()
# 以上是定时更新功能的实现。每隔60秒。


atexit.register(lambda: scheduler.shutdown())
# 防止调度器在 Flask 关闭时关闭
# 似乎可删去

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) # 0.0.0.0 和5000 表示对所有端口和地址进行测量
# 直接运行本文件，随后在终端输入 curl "http://localhost:5000/api/v1/ovs/stats?bridge_name=a1" 即可。

