#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天天基金网 - 基金排行数据抓取工具
从 fund.eastmoney.com 获取基金排行数据并导出为Excel
"""

import requests
import pandas as pd
from datetime import datetime
import json
import time

def fetch_fund_data(page=1, page_size=10000):
    """
    获取基金排行数据

    参数:
        page: 页码（从1开始）
        page_size: 每页数据量
    """
    # 天天基金网的API接口
    url = "http://fund.eastmoney.com/data/rankhandler.aspx"

    # 根据URL参数构建请求参数
    # tall: 全部类型
    # c0: 全部分类
    # s1nzf: 按1年涨幅排序
    # pn10000: 每页10000条
    # ddesc: 降序
    # qsd20241209: 起始日期
    # qed20251209: 结束日期

    params = {
        'op': 'ph',
        'dt': 'kf',  # 开放式基金
        'ft': 'all',  # 全部类型
        'rs': '',
        'gs': '0',
        'sc': '1nzf',  # 按1年涨幅排序
        'st': 'desc',  # 降序
        'sd': '2024-12-09',
        'ed': '2025-12-09',
        'pi': str(page),
        'pn': str(page_size),
        'dx': '1',  # 不分红方式
        'v': '0.1'  # 版本号
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'http://fund.eastmoney.com/data/fundranking.html'
    }

    try:
        print(f"正在请求第 {page} 页数据...")
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.encoding = 'utf-8'

        # 响应内容是JavaScript代码，需要提取JSON数据
        content = response.text

        # 检查是否有错误
        if '无访问权限' in content or 'ErrCode:-999' in content:
            print("API返回错误: 无访问权限")
            print("请求URL:", response.url)
            return None

        # 提取数据部分 (var rankData = {...})
        if 'var rankData' in content:
            # 找到JSON数据的起始和结束位置
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            json_str = content[start_idx:end_idx]

            # 处理JavaScript对象格式，需要给属性名加引号
            import re
            # 将 datas: 转换为 "datas":
            json_str = re.sub(r'(\w+):', r'"\1":', json_str)

            data = json.loads(json_str)
            return data
        else:
            print("未找到数据")
            return None

    except Exception as e:
        print(f"请求失败: {e}")
        return None

def parse_fund_data(raw_data):
    """
    解析基金数据

    参数:
        raw_data: API返回的原始数据
    返回:
        DataFrame对象
    """
    if not raw_data or 'datas' not in raw_data:
        print("数据为空或格式错误")
        return None

    funds_list = []
    datas = raw_data['datas']

    # 数据格式: "基金代码|基金简称|拼音缩写|日期|单位净值|累计净值|日增长率|近1周|近1月|近3月|近6月|近1年|近2年|近3年|今年来|成立来|自定义|手续费|可购状态|..."
    for item in datas:
        fields = item.split(',')
        if len(fields) >= 20:
            fund_info = {
                '基金代码': fields[0],
                '基金简称': fields[1],
                '拼音缩写': fields[2],
                '日期': fields[3],
                '单位净值': fields[4],
                '累计净值': fields[5],
                '日增长率(%)': fields[6],
                '近1周(%)': fields[7],
                '近1月(%)': fields[8],
                '近3月(%)': fields[9],
                '近6月(%)': fields[10],
                '近1年(%)': fields[11],
                '近2年(%)': fields[12],
                '近3年(%)': fields[13],
                '今年来(%)': fields[14],
                '成立来(%)': fields[15],
                '手续费': fields[20] if len(fields) > 20 else '',
                '可购状态': fields[21] if len(fields) > 21 else ''
            }
            funds_list.append(fund_info)

    if funds_list:
        df = pd.DataFrame(funds_list)

        # 转换数值列
        numeric_columns = ['单位净值', '累计净值', '日增长率(%)', '近1周(%)', '近1月(%)',
                          '近3月(%)', '近6月(%)', '近1年(%)', '近2年(%)', '近3年(%)',
                          '今年来(%)', '成立来(%)']

        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    return None

def main():
    """主函数"""
    print("=" * 60)
    print("天天基金网 - 基金排行数据抓取")
    print("=" * 60)

    # 获取数据
    raw_data = fetch_fund_data(page=1, page_size=10000)

    if raw_data:
        # 解析数据
        df = parse_fund_data(raw_data)

        if df is not None and not df.empty:
            print(f"\n成功获取 {len(df)} 条基金数据")

            # 显示前几条数据
            print("\n数据预览:")
            print(df.head(10).to_string())

            # 导出Excel
            output_file = f"基金排行数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(output_file, index=False, engine='openpyxl')
            print(f"\n✓ 数据已导出到: {output_file}")

            # 显示统计信息
            print("\n数据统计:")
            print(f"- 总基金数: {len(df)}")
            print(f"- 数据日期: {df['日期'].iloc[0] if len(df) > 0 else 'N/A'}")

            if '近1年(%)' in df.columns:
                df_valid = df[df['近1年(%)'].notna()]
                if not df_valid.empty:
                    print(f"- 近1年涨幅最高: {df_valid['近1年(%)'].max():.2f}%")
                    print(f"- 近1年涨幅最低: {df_valid['近1年(%)'].min():.2f}%")

        else:
            print("解析数据失败或数据为空")
    else:
        print("获取数据失败")

if __name__ == "__main__":
    main()
