#!/usr/bin/env python3
import sys
import asyncio
import argparse
import logging
from datetime import datetime
import os
import json
from typing import List, Tuple, Dict
import aiohttp
from yt_dlp import YoutubeDL
import subprocess
import re
from time import time
import socket
import platform
import requests
from urllib.parse import urlparse


class NetworkChecker:
    @staticmethod
    def get_ip_address():
        try:
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
            if platform.system() == "Windows":
                output = subprocess.check_output("netsh wlan show interfaces")
                return b"connected" in output
            else:
                output = subprocess.check_output(["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"])
                return b"yes" in output
        except:
            return False

    @staticmethod
    def check_ipv6():
        try:
            socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            requests.get("http://ipv6.ipv6-test.ch/ip/?callback=?", timeout=3)
            return True
        except:
            return False

    @staticmethod
    def check_ipv4():
        try:
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


class SpeedTestCLI:
    def __init__(self, inputs: List[str], output_file: str, log_file: str, max_workers: int = 3):
        self.inputs = inputs
        self.output_file = output_file
        self.log_file = log_file
        self.max_workers = max_workers
        self.urls = []  # 当前分组的URLs
        self.original_formats = {}  # 保存原始格式
        self.results = []  # 当前分组的结果
        self.all_results = {}  # 当前分组的所有结果
        self.genre_groups = []  # 保存所有分组信息
        self.stop_flag = False

        # 清空并配置日志
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('')

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('')

        self.current_genre = None  # 添加当前分组标记

    async def load_from_url(self, url: str) -> List[str]:
        """从URL加载内容"""
        self.logger.info(f"从URL加载: {url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        return content.splitlines()
                    else:
                        self.logger.error(f"无法从URL加载内容, 状态码: {response.status}")
                        return []
        except Exception as e:
            self.logger.error(f"从URL加载失败: {str(e)}")
            return []

    async def load_urls(self) -> None:
        """从多个输入源加载URLs并按genre分组"""
        try:
            for input_source in self.inputs:
                if input_source.startswith(('http://', 'https://')):
                    lines = await self.load_from_url(input_source)
                else:
                    try:
                        with open(input_source, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                    except Exception as e:
                        self.logger.error(f"加载文件失败 {input_source}: {str(e)}")
                        continue

                # 处理分组
                groups = self.process_content_lines(lines)
                self.genre_groups.extend(groups)

            self.logger.info(f"成功加载 {len(self.genre_groups)} 个分组")
        except Exception as e:
            self.logger.error(f"加载URL失败: {str(e)}")
            raise

    def process_content_lines(self, lines: List[str]) -> List[dict]:
        """处理内容行，按#genre#分组"""
        groups = []
        current_group = {"genre": None, "lines": []}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "#genre#" in line:
                if current_group["lines"]:
                    groups.append(current_group)
                current_group = {"genre": line, "lines": []}
            else:
                if current_group["genre"] is not None:
                    current_group["lines"].append(line)

        # 添加最后一个分组
        if current_group["lines"]:
            groups.append(current_group)

        return groups

    async def get_speed(self, url: str, timeout: int = 10) -> float:
        """测量URL的响应速度"""
        self.logger.info(f"测试链接速度: {url}")
        async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(verify_ssl=False),
                trust_env=True
        ) as session:
            start = time()
            try:
                async with session.get(url, timeout=timeout) as response:
                    if response.status == 404:
                        self.logger.warning(f"链接返回404: {url}")
                        return float("inf")
                    content = await response.read()
                    if not content:
                        self.logger.warning(f"链接无内容: {url}")
                        return float("inf")
                    end = time()
                    speed = int(round((end - start) * 1000))
                    self.logger.info(f"测速成功: {url}, 响应时间: {speed}ms")
                    return speed
            except Exception as e:
                self.logger.error(f"链接测试出错: {url}, 错误: {str(e)}")
                return float("inf")

    def get_video_info(self, url: str, timeout: int = 10) -> str:
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
            self.logger.error(f"获取视频信息失败: {url}, 错误: {str(e)}")
            return None

    async def get_ytdlp_speed(self, url: str) -> float:
        """使用yt-dlp测试下载速度"""
        self.logger.info(f"使用yt-dlp测试: {url}")

        cmd = [
            'yt-dlp',
            '-f', 'b',
            '--no-warnings',
            '--no-check-certificate',
            url
        ]

        try:
            temp_dir = os.path.join(os.getcwd(), 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            temp_file = os.path.join(temp_dir, f'temp_{int(time())}.ts')

            if os.path.exists(temp_file):
                os.remove(temp_file)

            cmd.extend(['--output', temp_file])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            start_time = time()
            speeds = []

            try:
                while True:
                    if time() - start_time > 5:
                        process.kill()
                        break

                    if process.stdout.at_eof() and process.stderr.at_eof():
                        break

                    line = await process.stdout.readline()
                    if not line:
                        line = await process.stderr.readline()
                    if not line:
                        continue

                    output = line.decode('utf-8', errors='ignore')
                    self.logger.info(f"yt-dlp输出: {output.strip()}")

                    speed_match = re.search(r'at\s+([\d.]+)(K|M|G)iB/s', output)
                    if speed_match:
                        value = float(speed_match.group(1))
                        unit = speed_match.group(2)
                        if unit == 'K':
                            speed = value * 8 / 1024
                        elif unit == 'M':
                            speed = value * 8
                        elif unit == 'G':
                            speed = value * 8 * 1024
                        speeds.append(speed)
                        self.logger.info(f"检测到速度: {speed:.2f} Mbps")

            finally:
                try:
                    process.kill()
                except:
                    pass

                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass

            if speeds:
                if len(speeds) > 2:
                    speeds.remove(max(speeds))
                    speeds.remove(min(speeds))
                avg_speed = sum(speeds) / len(speeds)
                self.logger.info(f"最终平均速度: {avg_speed:.2f} Mbps")
                return avg_speed

            self.logger.warning("未找到有效的速度信息")
            return None

        except Exception as e:
            self.logger.error(f"yt-dlp测试出错: {str(e)}")
            return None

    def is_multicast_url(self, url: str) -> bool:
        """检查是否是组播地址"""
        return 'rtp://' in url.lower() or 'udp://' in url.lower() or any(x in url for x in ['/rtp/', '/udp/'])

    async def test_multicast_speed(self, url: str) -> float:
        """测试组播源速度"""
        self.logger.info(f"测试组播源: {url}")

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
                self.logger.info(f"FFmpeg输出: {output}")

                if 'Input #0' in output:
                    size_match = re.search(r'video:([\d.]+)([KMG])iB audio:([\d.]+)([KMG])iB', output)
                    if size_match:
                        video_size = float(size_match.group(1))
                        video_unit = size_match.group(2)
                        audio_size = float(size_match.group(3))
                        audio_unit = size_match.group(4)

                        def convert_to_mb(size, unit):
                            if unit == 'K':
                                return size / 1024
                            elif unit == 'G':
                                return size * 1024
                            return size

                        video_mb = convert_to_mb(video_size, video_unit)
                        audio_mb = convert_to_mb(audio_size, audio_unit)
                        total_mb = video_mb + audio_mb
                        mbps = (total_mb * 8) / 5

                        self.logger.info(f"计算得到比特率: {mbps:.2f} Mbps")
                        return mbps

                    bitrate_match = re.search(r'bitrate:\s*([\d.]+)\s*([kmg])b/s', output, re.IGNORECASE)
                    if bitrate_match:
                        value = float(bitrate_match.group(1))
                        unit = bitrate_match.group(2).lower()
                        if unit == 'k':
                            bitrate = value / 1000
                        elif unit == 'g':
                            bitrate = value * 1000
                        else:
                            bitrate = value

                        self.logger.info(f"从bitrate信息获取速率: {bitrate:.2f} Mbps")
                        return bitrate

                    self.logger.info("无法获取具体速率，但流是有效的")
                    return 1.0

                self.logger.warning("未能检测到有效的流信息")
                return None

            except asyncio.TimeoutError:
                self.logger.error("组播源测试超时")
                return None

        except Exception as e:
            self.logger.error(f"组播源测试出错: {str(e)}")
            return None

        finally:
            if 'process' in locals():
                try:
                    process.kill()
                except:
                    pass

    def write_to_output(self, content: str):
        """写入内容到输出文件"""
        try:
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write(content)
                f.flush()  # 确保立即写入
        except Exception as e:
            self.logger.error(f"写入输出文件失败: {str(e)}")
    async def process_url(self, url: str) -> Tuple[str, float, str, str]:
        """处理单个URL"""
        try:
            result = None
            if self.is_multicast_url(url):
                self.logger.info(f"检测到组播源: {url}")
                speed = await self.test_multicast_speed(url)
                if speed is not None:
                    result = (url, speed, "成功(组播)", "N/A")
                else:
                    result = (url, 0, "组播源无效", "N/A")
            else:
                speed = await self.get_speed(url)
                if speed == float("inf"):
                    self.logger.info(f"直接测速失败，尝试使用yt-dlp: {url}")
                    ytdlp_speed = await self.get_ytdlp_speed(url)
                    if ytdlp_speed is not None:
                        result = (url, ytdlp_speed, "成功(yt-dlp)", "N/A")
                    else:
                        result = (url, 0, "链接无效", "N/A")
                else:
                    speed_score = 1000 / speed if speed > 0 else 0
                    result = (url, speed_score, "成功(direct)", "N/A")

            # 处理结果并实时写入
            if result:
                url, speed, status, resolution = result
                self.all_results[url] = (speed, status, resolution)
                if speed > 0:
                    self.results.append((url, speed, resolution))
                    # 实时写入有效结果
                    if url in self.original_formats:
                        self.write_to_output(f"{self.original_formats[url]}\n")
                    else:
                        self.write_to_output(f"{url}\n")

            return result

        except Exception as e:
            self.logger.error(f"处理出错: {str(e)}")
            return (url, 0, f"处理错误: {str(e)}", "N/A")

    async def process_urls(self) -> None:
        """处理所有URL"""
        self.logger.info("开始测速...")
        tasks = []
        semaphore = asyncio.Semaphore(self.max_workers)

        async def process_with_semaphore(url):
            async with semaphore:
                result = await self.process_url(url)
                if result:
                    url, speed, status, resolution = result
                    self.all_results[url] = (speed, status, resolution)
                    if speed > 0:
                        self.results.append((url, speed, resolution))
                        self.results.sort(key=lambda x: x[1], reverse=True)
                    self.logger.info(f"进度: {len(self.all_results)}/{len(self.urls)}")
                    return result

        total = len(self.urls)
        processed = 0

        for url in self.urls:
            if self.stop_flag:
                break
            tasks.append(asyncio.create_task(process_with_semaphore(url)))

        self.logger.info(f"创建了 {len(tasks)} 个任务")
        for task in asyncio.as_completed(tasks):
            if self.stop_flag:
                break

            try:
                await task
                processed += 1
                self.logger.info(f"进度: {processed}/{total}")

            except Exception as e:
                self.logger.error(f"任务处理错误: {str(e)}")

    def export_results(self) -> None:
        """导出当前结果到文件"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                for url, speed, _ in self.results:
                    if url in self.original_formats:
                        f.write(f"{self.original_formats[url]}\n")
                    else:
                        f.write(f"{url}\n")
            self.logger.info(f"结果已成功导出到: {self.output_file}")
            self.logger.info(f"已测试 {len(self.all_results)}/{len(self.urls)} 个链接, "
                           f"其中 {len(self.results)} 个有效")
        except Exception as e:
            self.logger.error(f"导出结果失败: {str(e)}")
            raise

    def prepare_group(self, group: dict) -> None:
        """准备处理某个分组"""
        self.urls = []
        self.original_formats = {}
        self.results = []
        self.all_results = {}

        # 写入分组标题
        if group["genre"]:
            self.write_to_output(f"{group['genre']}\n")

        for line in group["lines"]:
            url = None
            if ',' in line:
                _, url_part = line.split(',', 1)
                if '$' in url_part:
                    url = url_part.split('$')[0].strip()
                else:
                    url = url_part.strip()
            else:
                url = line.strip()

            if any(proto in url for proto in ['http://', 'https://', 'rtmp://', 'rtp://', 'udp://']):
                self.urls.append(url)
                self.original_formats[url] = line
    def export_group_results(self, group: dict, mode: str = 'a') -> None:
        """导出分组结果到文件"""
        try:
            with open(self.output_file, mode, encoding='utf-8') as f:
                # 写入分组标题
                if group["genre"]:
                    f.write(f"{group['genre']}\n")

                # 写入有效的URL结果
                for url, speed, _ in self.results:
                    if url in self.original_formats:
                        f.write(f"{self.original_formats[url]}\n")
                    else:
                        f.write(f"{url}\n")

                # 添加空行分隔不同分组
                f.write("\n")

            self.logger.info(f"分组 '{group['genre']}' 的结果已导出")
        except Exception as e:
            self.logger.error(f"导出分组结果失败: {str(e)}")
            raise

    async def run(self) -> None:
        """运行测速程序"""
        try:
            # 记录网络状态
            network_info = NetworkChecker.get_network_info()
            self.logger.info(f"网络状态: {network_info}")

            # 加载URLs
            await self.load_urls()
            if not self.genre_groups:
                self.logger.error("没有找到有效的分组")
                return

            # 处理每个分组
            for group in self.genre_groups:
                if self.stop_flag:
                    break

                self.logger.info(f"处理分组: {group['genre']}")
                self.prepare_group(group)

                if not self.urls:
                    self.logger.warning(f"分组 '{group['genre']}' 中没有找到有效的URL")
                    continue

                # 处理当前分组的URLs
                await self.process_urls()

                # 在分组之间添加空行
                self.write_to_output("\n")

                self.logger.info(f"分组 '{group['genre']}' 测试完成. "
                                 f"共测试 {len(self.all_results)} 个链接, "
                                 f"其中 {len(self.results)} 个有效")

        except Exception as e:
            self.logger.error(f"运行失败: {str(e)}")
            raise

    def stop(self):
        """停止测试"""
        self.stop_flag = True
        self.logger.info("正在停止测试...")


def load_config(config_file: str = "config.json") -> dict:
    """加载配置文件"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 验证必要的配置项
        required_fields = ['inputs', 'output_file', 'log_file']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"配置文件缺少必要的字段: {field}")

        # 设置默认值
        if 'max_workers' not in config:
            config['max_workers'] = 3

        return config
    except FileNotFoundError:
        # 如果配置文件不存在，创建默认配置
        default_config = {
            "inputs": ["live.txt"],
            "output_file": "output.txt",
            "log_file": "speed_test.log",
            "max_workers": 3
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)

        print(f"已创建默认配置文件: {config_file}")
        return default_config
    except json.JSONDecodeError as e:
        raise ValueError(f"配置文件格式错误: {str(e)}")
    except Exception as e:
        raise Exception(f"加载配置文件时出错: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='IPTV Speed Test CLI')
    parser.add_argument('-c', '--config', default='config.json',
                        help='配置文件路径 (默认: config.json)')
    parser.add_argument('-i', '--input', nargs='+',
                        help='输入源，可以是文件路径或URL，支持多个输入源（将覆盖配置文件中的设置）')
    parser.add_argument('-o', '--output',
                        help='输出文件路径（将覆盖配置文件中的设置）')
    parser.add_argument('-l', '--log',
                        help='日志文件路径（将覆盖配置文件中的设置）')
    parser.add_argument('-w', '--workers', type=int,
                        help='并发测试数量（将覆盖配置文件中的设置）')

    args = parser.parse_args()

    try:
        # 加载配置文件
        config = load_config(args.config)

        # 命令行参数覆盖配置文件
        if args.input:
            config['inputs'] = args.input
        if args.output:
            config['output_file'] = args.output
        if args.log:
            config['log_file'] = args.log
        if args.workers:
            config['max_workers'] = args.workers

        # 确保输出目录存在
        os.makedirs(os.path.dirname(os.path.abspath(config['output_file'])), exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(config['log_file'])), exist_ok=True)

        speed_test = SpeedTestCLI(
            inputs=config['inputs'],
            output_file=config['output_file'],
            log_file=config['log_file'],
            max_workers=config['max_workers']
        )

        try:
            asyncio.run(speed_test.run())
        except KeyboardInterrupt:
            print("\n检测到Ctrl+C，正在停止并保存当前结果...")
            speed_test.stop()
        except Exception as e:
            print(f"发生错误: {str(e)}")
            speed_test.stop()

    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()