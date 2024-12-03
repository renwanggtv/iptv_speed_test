# IPTV Speed Test Tool

这是一个用于测试IPTV直播源速度和可用性的工具，提供GUI和CLI两个版本。支持HTTP、RTMP、组播等多种协议的直播源测试。

## 功能特点

- 支持多种协议：HTTP、HTTPS、RTMP、UDP、RTP
- 支持多线程并发测试
- 实时显示测试进度和结果
- 保留原始格式输出
- 支持按分组（#genre#）处理
- 支持从本地文件或URL加载直播源
- 详细的日志记录
- 支持中断时保存当前结果

## 系统要求

### Python版本
- Python 3.9 或更高版本

### 安装步骤

1. 安装 FFmpeg
   
   FFmpeg 是必需的依赖项，用于测试流媒体源。

   #### Windows:
   - 下载 FFmpeg: https://www.ffmpeg.org/download.html
   - 将 FFmpeg 添加到系统环境变量

   #### Mac OS:
   ```bash
   brew install ffmpeg
   ```

   #### Linux:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install ffmpeg

   # CentOS/RHEL
   sudo yum install ffmpeg

   # Fedora
   sudo dnf install ffmpeg
   ```

2. 克隆或下载项目到本地

3. 安装 Python 依赖
   ```bash
   pip install -r requirements.txt
   ```

## GUI版本 (run.py)

### 特点
- 图形界面操作
- 实时显示测试进度
- 显示网络环境信息
- 可调整并发数
- 可导出测试结果

### 使用方法
1. 运行程序：
   ```bash
   python run.py
   ```
2. 点击"浏览"选择直播源文件
3. 调整测试线程数（默认3）
4. 点击"开始测速"
5. 测试完成后可点击"导出结果"

## CLI版本 (speed_test_cli.py)

### 特点
- 命令行操作
- 支持配置文件
- 支持多输入源
- 实时输出结果
- 详细日志记录

### 配置文件 (config.json)
```json
{
    "inputs": [
        "live.txt",
        "https://example.com/live.txt"
    ],
    "output_file": "output.txt",
    "log_file": "speed_test.log",
    "max_workers": 3
}
```

### 使用方法

1. 使用配置文件运行：
   ```bash
   python speed_test_cli.py
   ```

2. 指定配置文件：
   ```bash
   python speed_test_cli.py -c my_config.json
   ```

3. 使用命令行参数：
   ```bash
   python speed_test_cli.py -i input.txt -o output.txt -l log.txt -w 3
   ```

### 命令行参数
- `-c, --config`: 指定配置文件路径（默认：config.json）
- `-i, --input`: 输入文件或URL，支持多个
- `-o, --output`: 输出文件路径
- `-l, --log`: 日志文件路径
- `-w, --workers`: 并发测试数量

## 输入文件格式

支持以下格式的直播源文件：

1. 基本格式：
```
直播源1,http://example.com/live.m3u8
```

2. 带标记的格式：
```
直播源1,http://example.com/live.m3u8$LR•IPV6『线路1』
```

3. 分组格式：
```
直播频道1,#genre#
直播源1,http://example.com/cctv1.m3u8
直播源2,http://example.com/cctv2.m3u8

直播频道2,#genre#
直播源3,http://example.com/hunan.m3u8
直播源4,http://example.com/jiangsu.m3u8
```

## 输出说明

- 输出文件保持原始格式
- 只输出测试成功的链接
- 保持分组标记和顺序
- 实时写入结果

## 错误处理

- 程序会记录详细的错误日志
- 支持Ctrl+C中断，会保存当前结果
- 网络错误会被记录但不会中断程序
- 文件读写错误会有清晰的错误提示

## 注意事项

1. 确保已正确安装 FFmpeg 并可在命令行中使用
2. 建议先用小量数据测试
3. 根据网络情况调整并发数
4. 确保有足够的磁盘空间存储日志
5. URL必须包含协议头（http://、https://等）
6. 注意检查网络环境和IPv6支持情况

## 许可证

MIT License

## 贡献

欢迎提交Issues和Pull Requests。

## 更新日志

### v1.0.0
- 初始版本发布
- 支持GUI和CLI两种使用方式
- 支持多种协议测试
- 实现分组处理功能
- 添加FFmpeg依赖支持