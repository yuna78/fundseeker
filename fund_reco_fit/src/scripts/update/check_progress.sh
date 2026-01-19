#!/bin/bash
# 检查基金数据更新进度

echo "=================================="
echo "基金数据更新进度监控"
echo "=================================="
echo ""

# 检查fundseeker进程
echo "📊 进程状态:"
if ps aux | grep ".main.py nav" | grep -v grep > /dev/null; then
    echo "✅ fundseeker 正在运行中"
    ps aux | grep ".main.py nav" | grep -v grep | awk '{print "   CPU: "$3"% | 内存: "$4"% | 运行时间: "$10}'
else
    echo "⏹️  fundseeker 未运行"
fi

echo ""

# 统计已下载的基金数量
nav_count=$(ls ../fundseeker/output/nav/ 2>/dev/null | wc -l | tr -d ' ')
echo "📁 已下载的NAV文件数量: $nav_count"

# 目标数量
target=3495
existing=1207
total=$((target + existing))

echo "🎯 目标: $target 只新基金"
echo "📦 数据库现有: $existing 只"
echo "📈 完成后总计: $total 只"

if [ $nav_count -gt 0 ]; then
    # 计算进度
    new_downloaded=$((nav_count - existing))
    if [ $new_downloaded -gt 0 ]; then
        progress=$((new_downloaded * 100 / target))
        echo "⏳ 新增进度: $new_downloaded / $target ($progress%)"
    fi
fi

echo ""

# 显示最新下载的文件
echo "🆕 最新下载的10个文件:"
ls -lt ../fundseeker/output/nav/ 2>/dev/null | head -11 | tail -10 | awk '{print "   "$9" - "$6" "$7" "$8}'

echo ""
echo "=================================="
echo "💡 提示:"
echo "   - 再次运行此脚本查看最新进度: bash check_progress.sh"
echo "   - 预计总时间: 2-4小时"
echo "=================================="
