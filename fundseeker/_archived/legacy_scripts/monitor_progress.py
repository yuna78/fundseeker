#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控脚本 - 查看基金详情补充脚本的运行进度
"""

import json
import os
from datetime import datetime

def monitor_progress():
    """监控进度"""
    progress_file = "进度记录_增强版_20251209.json"

    if not os.path.exists(progress_file):
        print("❌ 未找到进度文件，脚本可能还未开始运行")
        return

    with open(progress_file, 'r', encoding='utf-8') as f:
        progress = json.load(f)

    processed = progress['processed_count']
    total = 10000
    percentage = processed / total * 100
    last_update = progress['last_update']

    # 计算预计剩余时间（基于0.5秒每条的速度）
    remaining = total - processed
    estimated_seconds = remaining * 0.5
    estimated_hours = estimated_seconds / 3600

    print("=" * 80)
    print("📊 基金详情补充脚本 - 运行进度")
    print("=" * 80)
    print(f"\n当前进度: {processed}/{total} 条")
    print(f"完成百分比: {percentage:.2f}%")
    print(f"最后更新时间: {last_update}")
    print(f"\n预计剩余时间: {estimated_hours:.1f} 小时")

    # 进度条
    bar_length = 50
    filled = int(bar_length * processed / total)
    bar = '█' * filled + '░' * (bar_length - filled)
    print(f"\n进度条: [{bar}] {percentage:.1f}%")

    print("\n" + "=" * 80)

    # 显示最新的Excel文件
    import glob
    excel_files = glob.glob("基金详情补充_增强版_*.xlsx")
    if excel_files:
        latest_file = max(excel_files, key=os.path.getmtime)
        file_size = os.path.getsize(latest_file) / 1024  # KB
        print(f"\n📁 最新输出文件: {latest_file}")
        print(f"   文件大小: {file_size:.1f} KB")

    print("\n💡 提示: 脚本每处理100条会自动保存一次")
    print("   可以随时查看生成的Excel文件")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    try:
        monitor_progress()
    except Exception as e:
        print(f"错误: {e}")
