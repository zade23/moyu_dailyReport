#!/bin/bash

# 记录执行时间
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始执行摸鱼日报脚本" >> /home/ai/ai-site/moyu_dailyReport/cron.log

# 切换到脚本目录
cd /home/ai/ai-site/moyu_dailyReport/

# 指定Python解释器路径（如果使用虚拟环境，请修改为虚拟环境的Python路径）
# 例如: /home/ai/venv/bin/python
PYTHON_PATH=$(which python3)

# 执行脚本，并记录输出
$PYTHON_PATH dailyReport.py >> /home/ai/ai-site/moyu_dailyReport/cron.log 2>&1

# 记录执行结束
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 摸鱼日报脚本执行结束" >> /home/ai/ai-site/moyu_dailyReport/cron.log
echo "----------------------------------------" >> /home/ai/ai-site/moyu_dailyReport/cron.log
