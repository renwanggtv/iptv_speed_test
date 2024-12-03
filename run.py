import sys
import asyncio
import aiohttp
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QTextEdit, QProgressBar, QFileDialog,
                             QLabel, QHBoxLayout, QMessageBox, QLineEdit,
                             QSpinBox, QGridLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from urllib.parse import urlparse
import re
from yt_dlp import YoutubeDL
import socket
from concurrent.futures import ThreadPoolExecutor
import asyncio
import platform
import requests
import platform
from time import time
import aiohttp
from yt_dlp import YoutubeDL
import asyncio
import subprocess

class NetworkChecker:
    @staticmethod
    def get_ip_address():
        try:
            # 获取本地IP地址
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "未知"

    @staticmethod
    def check_wifi():
        try:
            # Windows系统检查网络连接
            if platform.system() == "Windows":
                import subprocess
                output = subprocess.check_output("netsh wlan show interfaces")
                return b"connected " in output
            # Linux/Mac系统检查网络连接
            else:
                import subprocess
                output = subprocess.check_output(["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"])
                return b"yes" in output
        except:
            return False

    @staticmethod
    def check_ipv6():
        try:
            socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            # 尝试访问ipv6测试网站
            requests.get("http://ipv6.ipv6-test.ch/ip/?callback=?", timeout=3)
            return True
        except:
            return False

    @staticmethod
    def check_ipv4():
        try:
            # 尝试访问ipv4测试网站
            requests.get("http://ipv4.ipv6-test.ch/ip/?callback=?", timeout=3)
            return True
        except:
            return False

    @staticmethod
    def get_network_info():
        ipv4_support = "支持" if NetworkChecker.check_ipv4() else "不支持"
        ipv6_support = "支持" if NetworkChecker.check_ipv6() else "不支持"
        wifi_status = "已连接" if NetworkChecker.check_wifi() else "未连接"
        ip_address = NetworkChecker.get_ip_address()
        return f"网络环境: WiFi {wifi_status}, IP地址: {ip_address}\nIPv4 {ipv4_support}, IPv6 {ipv6_support}"


import aiohttp
from time import time
import asyncio
from PyQt5.QtCore import QThread, pyqtSignal
from datetime import datetime
import re


class SpeedTestWorker(QThread):
    progress = pyqtSignal(int)
    result = pyqtSignal(tuple)  # (url, speed, status, resolution)
    finished = pyqtSignal()
    status_update = pyqtSignal(str)
    log_update = pyqtSignal(str)

    def __init__(self, urls, max_workers):
        super().__init__()
        self.urls = urls
        self.max_workers = max_workers
        self.stop_flag = False

    def log(self, message):
        """输出日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.log_update.emit(log_message)

    async def get_speed(self, url, timeout=10):
        """测量URL的响应速度"""
        self.log(f"测试链接速度: {url}")
        async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(verify_ssl=False),
                trust_env=True
        ) as session:
            start = time()
            end = None
            try:
                async with session.get(url, timeout=timeout) as response:
                    if response.status == 404:
                        self.log(f"链接返回404: {url}")
                        return float("inf")
                    content = await response.read()
                    if content:
                        end = time()
                    else:
                        self.log(f"链接无内容: {url}")
                        return float("inf")
            except Exception as e:
                self.log(f"链接测试出错: {url}, 错误: {str(e)}")
                return float("inf")

            speed = int(round((end - start) * 1000)) if end else float("inf")
            if speed != float("inf"):
                self.log(f"测速成功: {url}, 响应时间: {speed}ms")
            return speed

    def get_video_info(self, url, timeout=10):
        """使用yt-dlp获取视频信息"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'best',
                'socket_timeout': timeout,
            }
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                resolution = f"{info['width']}x{info['height']}" if 'width' in info and 'height' in info else None
                return resolution
        except Exception as e:
            self.log(f"获取视频信息失败: {url}, 错误: {str(e)}")
            return None

    async def get_ytdlp_speed(self, url):
        """使用yt-dlp测试下载速度，限制5秒"""
        self.log(f"使用yt-dlp测试: {url}")

        cmd = [
            'yt-dlp',
            '-f', 'b',  # 使用 -f b 代替 -f best
            '--no-warnings',  # 禁用警告
            '--no-check-certificate',  # 不检查证书
            url
        ]

        try:
            # 创建临时目录
            temp_dir = os.path.join(os.getcwd(), 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            temp_file = os.path.join(temp_dir, f'temp_{int(time.time())}.ts')

            if os.path.exists(temp_file):
                os.remove(temp_file)

            cmd.extend(['--output', temp_file])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            start_time = time.time()
            speeds = []

            try:
                while True:
                    # 检查是否超过5秒
                    if time.time() - start_time > 5:
                        process.kill()
                        break

                    # 非阻塞地读取输出
                    if process.stdout.at_eof() and process.stderr.at_eof():
                        break

                    # 读取输出
                    line = await process.stdout.readline()
                    if not line:
                        line = await process.stderr.readline()
                    if not line:
                        continue

                    output = line.decode('utf-8', errors='ignore')
                    self.log(f"输出: {output.strip()}")

                    # 匹配速度信息
                    speed_match = re.search(r'at\s+([\d.]+)(K|M|G)iB/s', output)
                    if speed_match:
                        value = float(speed_match.group(1))
                        unit = speed_match.group(2)
                        # 转换为Mbps
                        if unit == 'K':
                            speed = value * 8 / 1024  # KiB/s to Mbps
                        elif unit == 'M':
                            speed = value * 8  # MiB/s to Mbps
                        elif unit == 'G':
                            speed = value * 8 * 1024  # GiB/s to Mbps
                        speeds.append(speed)
                        self.log(f"检测到速度: {speed:.2f} Mbps")

            except asyncio.CancelledError:
                process.kill()
            finally:
                # 确保进程被终止
                try:
                    process.kill()
                except:
                    pass

                # 清理临时文件
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass

            # 计算平均速度（去除最高和最低值）
            if speeds:
                if len(speeds) > 2:
                    speeds.remove(max(speeds))
                    speeds.remove(min(speeds))
                avg_speed = sum(speeds) / len(speeds)
                self.log(f"最终平均速度: {avg_speed:.2f} Mbps")
                return avg_speed

            self.log("未找到有效的速度信息")
            return None

        except Exception as e:
            self.log(f"yt-dlp测试出错: {str(e)}")
            if process:
                try:
                    process.kill()
                except:
                    pass
            return None

    def is_multicast_url(self, url):
        """检查是否是组播地址"""
        return 'rtp://' in url.lower() or 'udp://' in url.lower() or any(x in url for x in ['/rtp/', '/udp/'])

    async def test_multicast_speed(self, url):
        """测试组播源速度"""
        self.log(f"测试组播源: {url}")

        cmd = [
            'ffmpeg',
            '-i', url,
            '-t', '5',
            '-c', 'copy',
            '-f', 'null',
            '-'
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=8)
                output = stderr.decode('utf-8', errors='ignore')
                self.log(f"FFmpeg输出: {output}")

                # 检查是否成功读取到流信息
                if 'Input #0' in output:
                    # 从输出中提取处理的数据大小
                    size_match = re.search(r'video:([\d.]+)([KMG])iB audio:([\d.]+)([KMG])iB', output)
                    if size_match:
                        video_size = float(size_match.group(1))
                        video_unit = size_match.group(2)
                        audio_size = float(size_match.group(3))
                        audio_unit = size_match.group(4)

                        # 转换为MB
                        def convert_to_mb(size, unit):
                            if unit == 'K':
                                return size / 1024
                            elif unit == 'G':
                                return size * 1024
                            return size

                        video_mb = convert_to_mb(video_size, video_unit)
                        audio_mb = convert_to_mb(audio_size, audio_unit)

                        # 总数据量(MB)
                        total_mb = video_mb + audio_mb
                        # 计算Mbps (总数据量*8/时间)
                        mbps = (total_mb * 8) / 5  # 5秒的测试时间

                        self.log(f"计算得到比特率: {mbps:.2f} Mbps")
                        return mbps

                    # 如果没有找到具体大小，尝试从bitrate信息中获取
                    bitrate_match = re.search(r'bitrate:\s*([\d.]+)\s*([kmg])b/s', output, re.IGNORECASE)
                    if bitrate_match:
                        value = float(bitrate_match.group(1))
                        unit = bitrate_match.group(2).lower()
                        # 转换为Mbps
                        if unit == 'k':
                            bitrate = value / 1000
                        elif unit == 'g':
                            bitrate = value * 1000
                        else:
                            bitrate = value

                        self.log(f"从bitrate信息获取速率: {bitrate:.2f} Mbps")
                        return bitrate

                    # 如果以上都没找到，但确实有流，返回一个默认值
                    self.log("无法获取具体速率，但流是有效的")
                    return 1.0  # 返回一个默认值表示流是有效的

                self.log("未能检测到有效的流信息")
                return None

            except asyncio.TimeoutError:
                self.log("组播源测试超时")
                return None

            finally:
                if process and process.returncode is None:
                    try:
                        process.kill()
                    except:
                        pass

        except Exception as e:
            self.log(f"组播源测试出错: {str(e)}")
            return None

    async def process_url(self, url):
        """处理单个URL"""
        if self.stop_flag:
            return None

        try:
            # 检查是否是组播源
            if self.is_multicast_url(url):
                self.log(f"检测到组播源: {url}")
                speed = await self.test_multicast_speed(url)
                if speed is not None:
                    return (url, speed, "成功(组播)", "N/A")
                return (url, 0, "组播源无效", "N/A")

            # 非组播源使用普通测速
            speed = await self.get_speed(url)
            if speed == float("inf"):
                self.log(f"直接测速失败，尝试使用yt-dlp: {url}")
                ytdlp_speed = await self.get_ytdlp_speed(url)
                if ytdlp_speed is not None:
                    return (url, ytdlp_speed, "成功(yt-dlp)", "N/A")
                return (url, 0, "链接无效", "N/A")

            speed_score = 1000 / speed if speed > 0 else 0
            return (url, speed_score, "成功(direct)", "N/A")

        except Exception as e:
            self.log(f"处理出错: {str(e)}")
            return (url, 0, f"处理错误: {str(e)}", "N/A")

    async def process_urls(self):
        """处理所有URL"""
        self.log("开始测速...")
        tasks = []
        semaphore = asyncio.Semaphore(self.max_workers)

        async def process_with_semaphore(url):
            async with semaphore:
                return await self.process_url(url)

        total = len(self.urls)
        processed = 0

        for url in self.urls:
            if self.stop_flag:
                break
            tasks.append(asyncio.create_task(process_with_semaphore(url)))

        for task in asyncio.as_completed(tasks):
            if self.stop_flag:
                break

            try:
                result = await task
                processed += 1
                self.progress.emit(int((processed / total) * 100))
                self.status_update.emit(f"处理中: {processed}/{total}")

                if result:
                    self.result.emit(result)

            except Exception as e:
                self.log(f"任务处理错误: {str(e)}")

    def run(self):
        """QThread运行方法"""
        try:
            # 创建事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 运行异步任务
            loop.run_until_complete(self.process_urls())

        except Exception as e:
            self.log(f"运行出错: {str(e)}")
        finally:
            self.log("测试完成")
            self.finished.emit()

    def stop(self):
        """停止测试"""
        self.stop_flag = True
        self.log("正在停止测试...")
class IPTVSpeedTestGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.results = []
        self.all_results = {}  # 存储所有URL的测试状态

    def initUI(self):
        self.setWindowTitle('IPTV Speed Test')
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Network status
        self.network_label = QLabel()
        self.update_network_status()
        layout.addWidget(self.network_label)

        # File selection area
        file_layout = QHBoxLayout()
        self.file_path = QLineEdit(self)
        self.file_path.setReadOnly(True)
        self.browse_btn = QPushButton('浏览', self)
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(QLabel('文件路径:'))
        file_layout.addWidget(self.file_path)
        file_layout.addWidget(self.browse_btn)
        layout.addLayout(file_layout)

        # Thread control and buttons
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel('测速线程数:'))
        self.thread_spinbox = QSpinBox()
        self.thread_spinbox.setRange(1, 5)
        self.thread_spinbox.setValue(3)
        control_layout.addWidget(self.thread_spinbox)

        self.start_btn = QPushButton('开始测速', self)
        self.start_btn.clicked.connect(self.start_speed_test)
        self.start_btn.setEnabled(False)
        control_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton('停止测速', self)
        self.stop_btn.clicked.connect(self.stop_speed_test)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)

        self.export_btn = QPushButton('导出结果', self)
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        control_layout.addWidget(self.export_btn)

        layout.addLayout(control_layout)

        # Status and progress
        self.status_label = QLabel('就绪', self)
        layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)


        self.log_text = QTextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)  # 限制日志区域高度
        layout.addWidget(QLabel('测试日志:'))
        layout.addWidget(self.log_text)

        # Results text area
        self.results_text = QTextEdit(self)
        self.results_text.setReadOnly(True)
        layout.addWidget(QLabel('测试结果:'))
        layout.addWidget(self.results_text)

    def update_network_status(self):
        self.network_label.setText(NetworkChecker.get_network_info())

    def clean_url(url_line):
        """
        清理 URL，去除频道名称和线路标记
        示例输入: "CCTV1,http://[2409:8087:5e00:24::1e]:6060/200000001898/460000089800010011/1.m3u8$LR•IPV6『线路3』"
        示例输出: "http://[2409:8087:5e00:24::1e]:6060/200000001898/460000089800010011/1.m3u8"
        """
        # 如果包含逗号，取逗号后面的部分
        if ',' in url_line:
            url_line = url_line.split(',', 1)[1]

        # 如果包含$，取$前面的部分
        if '$' in url_line:
            url_line = url_line.split('$')[0]

        return url_line.strip()

    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, '选择文件', '', 'Text Files (*.txt);;All Files (*)')
        if file_name:
            self.file_path.setText(file_name)
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                    self.urls = []  # 存储纯URL
                    self.original_formats = {}  # 存储原始格式

                    for line in lines:
                        if line.strip():
                            # 保存原始行
                            original_line = line.strip()

                            # 提取URL
                            url = None
                            if ',' in line:
                                # 分割频道名和URL
                                _, url_part = line.split(',', 1)
                                if '$' in url_part:
                                    url = url_part.split('$')[0].strip()
                                else:
                                    url = url_part.strip()
                            else:
                                url = line.strip()

                            # 确保是有效的URL
                            if any(proto in url for proto in ['http://', 'https://', 'rtmp://', 'rtp://', 'udp://']):
                                self.urls.append(url)
                                self.original_formats[url] = original_line

                    self.start_btn.setEnabled(True)
                    self.status_label.setText(f'已导入 {len(self.urls)} 个链接')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导入文件时出错：{str(e)}')

    def start_speed_test(self):
        if not hasattr(self, 'urls') or not self.urls:
            QMessageBox.warning(self, '警告', '请先选择文件导入链接')
            return

        self.start_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.thread_spinbox.setEnabled(False)
        self.progress_bar.setValue(0)
        self.results = []
        self.all_results = {}
        self.results_text.clear()
        self.log_text.clear()  # 清除旧日志
        self.update_network_status()

        self.worker = SpeedTestWorker(self.urls, self.thread_spinbox.value())
        self.worker.progress.connect(self.update_progress)
        self.worker.result.connect(self.handle_result)
        self.worker.finished.connect(self.handle_finished)
        self.worker.status_update.connect(self.update_status)
        self.worker.log_update.connect(self.update_log)  # 连接日志信号
        self.worker.start()

    def update_log(self, message):
        """更新日志显示"""
        self.log_text.append(message)
        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def stop_speed_test(self):
        if hasattr(self, 'worker'):
            self.worker.stop()
            self.status_label.setText('正在停止测速...')
            self.stop_btn.setEnabled(False)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_status(self, status):
        self.status_label.setText(status)

    def handle_result(self, result):
        """处理测速结果"""
        url, speed, status, resolution = result
        self.log_text.append(f"收到结果: URL={url}, 速度={speed}, 状态={status}, 分辨率={resolution}")

        self.all_results[url] = (speed, status, resolution)
        if speed > 0:
            self.results.append((url, speed, resolution))
            self.results.sort(key=lambda x: x[1], reverse=True)
        self.update_results_text()

    def update_results_text(self):
        """更新结果显示"""
        text = "=== 测试结果 ===\n\n"

        # 显示有效链接（按速度排序）
        text += "【有效链接】\n"
        for i, (url, speed, resolution) in enumerate(self.results, 1):
            text += f"[{i}] 速度: {speed:.2f} Mbps | 分辨率: {resolution}\n{url}\n\n"

        # 显示其他测试过的链接
        text += "\n【其他链接】\n"
        other_count = 1
        for url, (speed, status, resolution) in self.all_results.items():
            if speed <= 0:  # 无效或测试失败的链接
                text += f"[{other_count}] 状态: {status}\n链接: {url}\n分辨率: {resolution}\n\n"
                other_count += 1

        # 添加测试信息
        text += "\n【测试信息】\n"
        text += f"总链接数: {len(self.all_results)}\n"
        text += f"有效链接数: {len(self.results)}\n"
        text += f"无效链接数: {len(self.all_results) - len(self.results)}\n"
        text += f"测试线程数: {self.thread_spinbox.value()}\n"

        self.results_text.setText(text)
        # 滚动到底部
        scrollbar = self.results_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def export_results(self):
        if not self.all_results:
            QMessageBox.warning(self, '警告', '没有可导出的结果')
            return

        file_name, _ = QFileDialog.getSaveFileName(self, '保存文件', '', 'Text Files (*.txt);;All Files (*)')
        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    # 只导出有效链接
                    for url, speed, _ in self.results:
                        # 使用原始格式如果存在，否则使用URL
                        if url in self.original_formats:
                            f.write(f"{self.original_formats[url]}\n")
                        else:
                            f.write(f"{url}\n")

                QMessageBox.information(self, '成功', '结果已成功导出')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导出文件时出错：{str(e)}')

    def handle_finished(self):
        self.status_label.setText(f'测速完成，共 {len(self.results)} 个有效链接')
        self.start_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.thread_spinbox.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    gui = IPTVSpeedTestGUI()
    gui.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()