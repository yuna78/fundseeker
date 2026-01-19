"""Interactive CLI menu."""

from __future__ import annotations

from typing import Callable, Dict


def interactive_menu(actions: Dict[str, Callable[[], None]]) -> None:
    """Render a loop-based menu for terminal usage."""
    prompt = (
        "\n请选择功能:\n"
        " 1. 初始化环境\n"
        " 2. 获取基金排行并补充评级\n"
        " 3. 根据基金清单抓取详情\n"
        " 4. 生成推荐列表\n"
        " 5. 查看帮助/说明\n"
        " 6. 查看进度\n"
        " 7. 批量下载净值（data/fund_list.csv）\n"
        " 0. 退出\n"
        "输入序号并回车: "
    )

    while True:
        choice = input(prompt).strip()
        if choice == "0":
            print("Bye~")
            return

        action = actions.get(choice)
        if not action:
            print("无效选择，请重新输入。")
            continue

        action()
