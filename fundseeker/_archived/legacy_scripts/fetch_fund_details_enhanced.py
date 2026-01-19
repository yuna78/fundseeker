#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天天基金网 - 分批补充基金详情工具（增强版）
从Excel读取基金代码，分批获取详情信息（规模、成立日期、基金经理及任职信息）
支持断点续传和进度保存
"""

import requests
import pandas as pd
from datetime import datetime
import time
import re
import os
import json

# 配置参数
BATCH_SIZE = 10  # 每批处理数量
SAVE_INTERVAL = 100  # 每处理100条保存一次
DELAY_BETWEEN_REQUESTS = 0.5  # 请求之间的延迟（秒）

def fetch_manager_info(fund_code):
    """
    获取基金经理的任职信息（最新的基金经理）

    参数:
        fund_code: 基金代码
    返回:
        包含上任日期、任职期间、任职回报的字典
    """
    url = f"http://fundf10.eastmoney.com/jjjl_{fund_code}.html"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        content = response.text

        manager_info = {
            '基金经理上任日期': '',
            '基金经理任职期间': '',
            '基金经理任职回报': ''
        }

        # 从"基金经理变动一览"表格中提取数据
        # 表格结构：起始期 | 截止期 | 基金经理 | 任职期间 | 任职回报
        section_pattern = r'基金经理变动一览.*?<table[^>]*>(.*?)</table>'
        section_match = re.search(section_pattern, content, re.DOTALL)

        if section_match:
            table_html = section_match.group(0)

            # 查找所有行
            row_pattern = r'<tr[^>]*>(.*?)</tr>'
            rows = re.findall(row_pattern, table_html, re.DOTALL)

            # 跳过表头，处理第一行数据（最新的基金经理）
            if len(rows) >= 2:
                data_row = rows[1]  # 第二行是数据行

                # 提取所有单元格（th或td）
                cell_pattern = r'<t[dh][^>]*>(.*?)</t[dh]>'
                cells = re.findall(cell_pattern, data_row, re.DOTALL)

                # 清理HTML标签
                clean_cells = []
                for cell in cells:
                    clean_cell = re.sub(r'<[^>]+>', '', cell).strip()
                    clean_cells.append(clean_cell)

                # 表格列顺序：起始期 | 截止期 | 基金经理 | 任职期间 | 任职回报
                if len(clean_cells) >= 5:
                    # 检查是否是现任经理（截止期为"至今"）
                    if clean_cells[1] == '至今' or clean_cells[1] == '---':
                        manager_info['基金经理上任日期'] = clean_cells[0]
                        manager_info['基金经理任职期间'] = clean_cells[3]
                        manager_info['基金经理任职回报'] = clean_cells[4]

        # 如果表格没有提取到上任日期，尝试从简介中提取
        if not manager_info['基金经理上任日期']:
            appoint_date_match = re.search(r'<strong>上任日期：</strong>\s*([0-9-]+)', content)
            if appoint_date_match:
                manager_info['基金经理上任日期'] = appoint_date_match.group(1)

        return manager_info

    except Exception as e:
        print(f"  警告: 获取基金 {fund_code} 经理信息失败: {e}")
        return {
            '基金经理上任日期': '',
            '基金经理任职期间': '',
            '基金经理任职回报': ''
        }

def fetch_fund_detail(fund_code, fund_name=''):
    """
    获取单个基金的详情信息

    参数:
        fund_code: 基金代码
        fund_name: 基金名称（可选）
    返回:
        包含基金代码、名称、规模、成立日期、基金经理、经理详情页及任职信息的字典
    """
    url = f"http://fund.eastmoney.com/{fund_code}.html"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        content = response.text

        fund_detail = {
            '基金代码': fund_code,
            '基金名称': fund_name,
            '基金规模': '',
            '成立日期': '',
            '基金经理': '',
            '基金经理详情页': f'http://fundf10.eastmoney.com/jjjl_{fund_code}.html',
            '基金经理上任日期': '',
            '基金经理任职期间': '',
            '基金经理任职回报': ''
        }

        # 提取基金名称（如果没有传入）
        if not fund_name:
            name_match = re.search(r'<div[^>]*class="fundDetail-tit"[^>]*>.*?<div[^>]*>([^<(]+)', content, re.DOTALL)
            if name_match:
                fund_detail['基金名称'] = name_match.group(1).strip()

        # 提取基金规模
        scale_match = re.search(r'>规模</a>[：:]([\d.]+[亿万]?元)[（(]([0-9-]+)[）)]', content)
        if scale_match:
            fund_detail['基金规模'] = scale_match.group(1)

        # 提取成立日期
        date_match = re.search(r'letterSpace01\">成\s*立\s*日</span>[：:]\s*([0-9-]+)', content)
        if date_match:
            fund_detail['成立日期'] = date_match.group(1)

        # 提取基金经理
        manager_match = re.search(r'基金经理[：:].*?<a[^>]*>([^<]+)</a>', content)
        if manager_match:
            fund_detail['基金经理'] = manager_match.group(1)

        # 获取基金经理任职信息
        manager_info = fetch_manager_info(fund_code)
        fund_detail.update(manager_info)

        return fund_detail

    except Exception as e:
        print(f"  错误: 获取基金 {fund_code} 详情失败: {e}")
        return {
            '基金代码': fund_code,
            '基金名称': fund_name,
            '基金规模': '',
            '成立日期': '',
            '基金经理': '',
            '基金经理详情页': f'http://fundf10.eastmoney.com/jjjl_{fund_code}.html',
            '基金经理上任日期': '',
            '基金经理任职期间': '',
            '基金经理任职回报': ''
        }

def load_progress(progress_file):
    """加载进度记录"""
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'processed_count': 0, 'last_index': -1}

def save_progress(progress_file, processed_count, last_index):
    """保存进度记录"""
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump({
            'processed_count': processed_count,
            'last_index': last_index,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, f, ensure_ascii=False, indent=2)

def main():
    """主函数"""
    print("=" * 70)
    print("天天基金网 - 分批补充基金详情工具（增强版）")
    print("=" * 70)

    # 1. 读取输入Excel文件
    input_file = input("\n请输入基金排行数据Excel文件路径（例如：基金排行数据_20251209_213024.xlsx）: ").strip()

    if not os.path.exists(input_file):
        print(f"错误: 文件不存在: {input_file}")
        return

    print(f"\n正在读取文件: {input_file}")
    df_input = pd.read_excel(input_file)

    if '基金代码' not in df_input.columns:
        print("错误: Excel文件中没有找到'基金代码'列")
        return

    # 将基金代码转换为6位字符串（补齐前导0）
    df_input['基金代码'] = df_input['基金代码'].astype(str).str.zfill(6)

    total_funds = len(df_input)
    print(f"成功读取 {total_funds} 条基金记录")

    # 2. 准备输出文件
    output_file = f"基金详情补充_增强版_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    progress_file = f"进度记录_增强版_{datetime.now().strftime('%Y%m%d')}.json"

    # 3. 加载进度
    progress = load_progress(progress_file)
    start_index = progress['last_index'] + 1

    if start_index > 0:
        print(f"\n发现进度记录，将从第 {start_index + 1} 条开始（已处理 {progress['processed_count']} 条）")
        # 如果有进度，加载已有的结果
        if os.path.exists(output_file):
            df_output = pd.read_excel(output_file)
        else:
            df_output = pd.DataFrame(columns=['基金代码', '基金名称', '基金规模', '成立日期', '基金经理',
                                              '基金经理详情页', '基金经理上任日期', '基金经理任职期间', '基金经理任职回报'])
    else:
        print("\n开始全新抓取...")
        df_output = pd.DataFrame(columns=['基金代码', '基金名称', '基金规模', '成立日期', '基金经理',
                                          '基金经理详情页', '基金经理上任日期', '基金经理任职期间', '基金经理任职回报'])

    # 4. 分批处理
    print(f"\n配置: 每批 {BATCH_SIZE} 条，每 {SAVE_INTERVAL} 条保存一次")
    print("=" * 70)

    processed_count = progress['processed_count']
    results = df_output.to_dict('records') if start_index > 0 else []

    for i in range(start_index, total_funds):
        fund_code = df_input.iloc[i]['基金代码']
        fund_name = df_input.iloc[i]['基金简称'] if '基金简称' in df_input.columns else ''

        # 获取详情
        print(f"[{i + 1}/{total_funds}] 正在获取基金 {fund_code} ({fund_name}) 的详细信息...")
        detail = fetch_fund_detail(fund_code, fund_name)
        results.append(detail)

        processed_count += 1

        # 定期保存
        if processed_count % SAVE_INTERVAL == 0:
            df_output = pd.DataFrame(results)
            df_output.to_excel(output_file, index=False, engine='openpyxl')
            save_progress(progress_file, processed_count, i)
            print(f"\n  ✓ 已处理 {processed_count} 条，进度已保存到: {output_file}\n")

        # 批次延迟
        if (i + 1) % BATCH_SIZE == 0:
            print(f"  批次完成，已处理 {processed_count}/{total_funds}...")

        time.sleep(DELAY_BETWEEN_REQUESTS)

    # 5. 最终保存
    df_output = pd.DataFrame(results)
    df_output.to_excel(output_file, index=False, engine='openpyxl')
    save_progress(progress_file, processed_count, total_funds - 1)

    print("\n" + "=" * 70)
    print(f"✓ 全部完成！共处理 {processed_count} 条基金记录")
    print(f"✓ 结果已保存到: {output_file}")
    print(f"✓ 进度记录: {progress_file}")
    print("=" * 70)

    # 6. 显示统计信息
    print("\n数据预览:")
    print(df_output.head(5).to_string())

    print("\n统计信息:")
    print(f"- 总记录数: {len(df_output)}")
    print(f"- 成功获取规模: {df_output[df_output['基金规模'] != ''].shape[0]} 条")
    print(f"- 成功获取成立日期: {df_output[df_output['成立日期'] != ''].shape[0]} 条")
    print(f"- 成功获取基金经理: {df_output[df_output['基金经理'] != ''].shape[0]} 条")
    print(f"- 成功获取经理上任日期: {df_output[df_output['基金经理上任日期'] != ''].shape[0]} 条")
    print(f"- 成功获取经理任职期间: {df_output[df_output['基金经理任职期间'] != ''].shape[0]} 条")
    print(f"- 成功获取经理任职回报: {df_output[df_output['基金经理任职回报'] != ''].shape[0]} 条")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断，进度已保存")
    except Exception as e:
        print(f"\n\n程序发生错误: {e}")
        print("进度已保存，可以重新运行程序继续")
