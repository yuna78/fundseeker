#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天天基金网 - 基金评级数据抓取工具
从 fund.eastmoney.com 获取基金评级数据并导出为Excel
"""

import requests
import pandas as pd
from datetime import datetime
import re

def fetch_fund_rating_data():
    """
    获取基金评级数据

    返回:
        原始数据字符串
    """
    url = "https://fund.eastmoney.com/data/fundrating.html"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://fund.eastmoney.com/'
    }

    try:
        print("正在获取基金评级数据...")
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'

        content = response.text

        # 提取 var fundinfos = "..." 中的数据
        pattern = r'var fundinfos = "(.*?)";'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            fund_data = match.group(1)
            return fund_data
        else:
            print("未找到基金数据")
            return None

    except Exception as e:
        print(f"请求失败: {e}")
        return None

def parse_fund_rating_data(raw_data):
    """
    解析基金评级数据

    参数:
        raw_data: 从页面提取的原始数据字符串
    返回:
        DataFrame对象
    """
    if not raw_data:
        print("数据为空")
        return None

    funds_list = []

    # 数据格式：多个基金记录用 _ 分隔，每个基金内部用 | 分隔字段
    fund_records = raw_data.split('_')

    print(f"找到 {len(fund_records)} 条基金评级记录")

    for record in fund_records:
        if not record.strip():
            continue

        fields = record.split('|')

        # 根据观察到的数据格式解析
        # 字段顺序: 基金代码|基金简称|基金类型|基金经理|经理代码|基金公司|公司代码|...评级数据...|手续费|状态|...
        if len(fields) >= 25:
            try:
                fund_info = {
                    '基金代码': fields[0],
                    '基金简称': fields[1],
                    '基金类型': fields[2],
                    '基金经理': fields[3],
                    '基金经理代码': fields[4],
                    '基金公司': fields[5],
                    '基金公司代码': fields[6],
                    '评级字段7': fields[7],
                    '评级字段8': fields[8],
                    '评级字段9': fields[9],
                    '评级字段10': fields[10],
                    '评级字段11': fields[11],
                    '评级字段12': fields[12],
                    '评级字段13': fields[13],
                    '评级字段14': fields[14],
                    '评级字段15': fields[15],
                    '评级字段16': fields[16],
                    '评级字段17': fields[17],
                    '评级字段18': fields[18],
                    '手续费': fields[19],
                    '状态字段20': fields[20],
                    '状态字段21': fields[21],
                    '基金分类代码': fields[22] if len(fields) > 22 else '',
                    '其他标识': fields[23] if len(fields) > 23 else '',
                    '拼音缩写': fields[24] if len(fields) > 24 else '',
                    '公司简称': fields[25] if len(fields) > 25 else '',
                }

                # 添加所有剩余字段
                for i in range(26, len(fields)):
                    fund_info[f'字段{i}'] = fields[i]

                funds_list.append(fund_info)
            except Exception as e:
                print(f"解析记录失败: {e}, 字段数: {len(fields)}")
                continue

    if funds_list:
        df = pd.DataFrame(funds_list)
        return df

    return None

def main():
    """主函数"""
    print("=" * 60)
    print("天天基金网 - 基金评级数据抓取")
    print("=" * 60)

    # 获取数据
    raw_data = fetch_fund_rating_data()

    if raw_data:
        # 解析数据
        df = parse_fund_rating_data(raw_data)

        if df is not None and not df.empty:
            print(f"\n成功获取 {len(df)} 条基金评级数据")

            # 显示前几条数据
            print("\n数据预览:")
            print(df.head(5).to_string())

            # 显示所有列名
            print("\n数据列名:")
            print(df.columns.tolist())

            # 导出Excel
            output_file = f"基金评级数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(output_file, index=False, engine='openpyxl')
            print(f"\n✓ 数据已导出到: {output_file}")

            # 显示统计信息
            print("\n数据统计:")
            print(f"- 总基金数: {len(df)}")

            if '基金类型' in df.columns:
                print(f"\n基金类型分布:")
                type_counts = df['基金类型'].value_counts().head(10)
                for fund_type, count in type_counts.items():
                    print(f"  {fund_type}: {count}")

        else:
            print("解析数据失败或数据为空")
    else:
        print("获取数据失败")

if __name__ == "__main__":
    main()
