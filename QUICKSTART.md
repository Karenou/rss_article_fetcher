# Quick Start Guide

## 快速开始指南

### 1. 安装依赖

```bash
cd /Users/karenou/Desktop/AI/rss_article_fetcher
pip install -r requirements.txt
```

### 2. 配置

复制配置模板并编辑：

```bash
cp config/config.yaml.example config/config.yaml
```

编辑 `config/config.yaml`，至少需要配置：

- **Gemini API Key**: 从 [Google AI Studio](https://makersuite.google.com/app/apikey) 获取
- **企业微信 Webhook**: 从企业微信群机器人获取（可选）

或者使用环境变量：

```bash
export GEMINI_API_KEY="your_gemini_api_key"
export WECOM_WEBHOOK_URL="your_wecom_webhook_url"
```

### 3. 准备RSS订阅源

确保 `/rss_article_fetcher/data/subscribe_rss.txt` 文件存在并包含RSS源。

### 4. 运行

#### 基础运行（抓取最近24小时的文章）

```bash
python main.py
```

#### 指定时间范围

```bash
# 抓取最近2天的文章
python main.py --start "2 days ago"

# 抓取指定日期范围
python main.py --start "2024-01-01" --end "2024-01-02"
```

#### 测试运行（不推送到微信）

```bash
python main.py --no-push
```

#### 强制重新处理（忽略去重）

```bash
python main.py --force
```

#### 调试模式

```bash
python main.py --debug
```

### 5. 查看日志

日志文件位于 `logs/` 目录：

```bash
# 查看今天的日志
tail -f logs/rss_fetcher_$(date +%Y%m%d).log

# 查看错误日志
tail -f logs/rss_fetcher_error_$(date +%Y%m%d).log
```

### 6. 定时任务

#### 方式1：使用内置调度器

编辑 `config/config.yaml`：

```yaml
scheduler:
  enabled: true
  interval_hours: 24  # 每24小时运行一次
```

然后运行：

```bash
python main.py
```

#### 方式2：使用系统 cron

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天早上9点运行）
0 9 * * * cd /Users/karenou/Desktop/AI/rss_article_fetcher && python main.py
```

## 常见问题

### Q: 如何获取 Gemini API Key？

A: 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)，登录后创建 API Key。

### Q: 如何获取企业微信 Webhook？

A: 
1. 在企业微信群中添加机器人
2. 选择"自定义机器人"
3. 复制 Webhook URL

### Q: 程序报错怎么办？

A: 
1. 查看 `logs/` 目录下的日志文件
2. 使用 `--debug` 参数运行获取详细信息
3. 检查配置文件是否正确

### Q: 如何清理旧数据？

A: 数据库会自动去重，如需清理旧记录：

```python
from src.storage import Storage
from src.logger import get_logger

logger = get_logger()
storage = Storage("/Users/karenou/Desktop/AI/rss_article_fetcher/data", logger)

# 删除90天前的记录
storage.cleanup_old_records(days=90)
```

## 下一步

- 查看 [README.md](README.md) 了解更多功能
- 调整 `config/config.yaml` 中的参数优化性能
- 添加更多RSS订阅源到 `subscribe_rss.txt`

## 技术支持

遇到问题请查看日志文件，大多数问题都能从详细的错误信息中找到原因。
