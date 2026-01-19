"""FundSeeker CLI entry point."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable, Dict, Optional

import typer

from src.cli.menu import interactive_menu
from src.services.advanced_recommend_service import AdvancedRecommendService
from src.services.detail_service import DetailService
from src.services.nav_service import NavService
from src.services.progress_service import ProgressService
from src.services.rank_service import RankService
from src.services.recommend_service import RecommendService
from src.utils.config import AppConfig, load_config
from src.utils.io_helper import ensure_dir

app = typer.Typer(help="基金数据采集一体化 CLI")


def _prepare_base_dirs(cfg: AppConfig) -> None:
    ensure_dir(cfg.paths.output_dir)
    ensure_dir(cfg.paths.logs_dir)
    ensure_dir(cfg.paths.progress_dir)
    ensure_dir(cfg.paths.templates_dir)
    ensure_dir(cfg.paths.data_dir)
    _ensure_default_fund_list(cfg)


def _ensure_default_fund_list(cfg: AppConfig) -> None:
    """Ensure default fund list file exists by copying template if available."""
    target = cfg.paths.default_fund_list
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return

    template = cfg.paths.templates_dir / "fund_list_template.csv"
    if template.exists():
        shutil.copyfile(template, target)
    else:
        target.write_text("基金代码,基金简称,备注(可选)\n", encoding="utf-8")


def _with_config(ctx: typer.Context) -> AppConfig:
    if "config" not in ctx.obj:
        ctx.obj["config"] = load_config()
    return ctx.obj["config"]


def _run_rank(
    cfg: AppConfig,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
) -> None:
    _prepare_base_dirs(cfg)
    service = RankService(cfg)
    try:
        output_path = service.run(start_date=start_date, end_date=end_date, limit=limit)
        typer.echo(f"排行+评级数据已导出：{output_path}")
    except Exception as exc:
        typer.echo(f"执行失败: {exc}")


def _prompt_rank_limit() -> Optional[int]:
    """Ask user for a limit when running via interactive menu."""
    try:
        raw = input("\n请输入要导出的前 N 条记录（留空表示全部）: ").strip()
    except EOFError:
        return None

    if not raw:
        return None

    try:
        value = int(raw)
        if value <= 0:
            raise ValueError
        return value
    except ValueError:
        typer.echo("输入无效，将导出所有记录。")
        return None


def _run_rank_with_prompt(cfg: AppConfig) -> None:
    limit = _prompt_rank_limit()
    _run_rank(cfg, limit=limit)


def _prompt_nav_params() -> Optional[Dict[str, Optional[str]]]:
    try:
        start = input("\n开始日期 YYYY-MM-DD（可留空）: ").strip()
    except EOFError:
        return None
    end = input("结束日期 YYYY-MM-DD（可留空）: ").strip()
    fmt = input("导出格式 excel/csv（默认 excel）: ").strip().lower() or "excel"
    if fmt not in {"excel", "csv"}:
        typer.echo("格式无效，自动改为 excel。")
        fmt = "excel"
    return {"start_date": start or None, "end_date": end or None, "fmt": fmt}


def _run_nav_with_prompt(cfg: AppConfig) -> None:
    params = _prompt_nav_params()
    if params:
        _run_nav_bulk(cfg, **params)


def _prompt_recommend_mode() -> str:
    try:
        raw = input("\n选择推荐模式：1=基础八因子, 2=高级模型（默认1）: ").strip()
    except EOFError:
        return "basic"
    return "advanced" if raw == "2" else "basic"


def _run_recommend_with_prompt(cfg: AppConfig) -> None:
    mode = _prompt_recommend_mode()
    if mode == "advanced":
        _run_advanced_recommend(cfg)
    else:
        _run_basic_recommend(cfg)


def _run_details(cfg: AppConfig, input_path: Optional[str] = None, auto_resume: bool = True) -> None:
    _prepare_base_dirs(cfg)
    default_path = str(cfg.paths.default_fund_list)
    path_str = input_path or default_path
    if not Path(path_str).exists():
        typer.echo(f"未找到基金列表文件: {path_str}")
        typer.echo("请编辑或替换项目内的 data/fund_list.csv 后重试。")
        return
    service = DetailService(cfg)
    try:
        output_path = service.run(Path(path_str), auto_resume=auto_resume)
        typer.echo(f"详情数据已导出：{output_path}")
    except Exception as exc:
        typer.echo(f"执行失败: {exc}")


def _run_progress(cfg: AppConfig, date: Optional[str] = None) -> None:
    _prepare_base_dirs(cfg)
    service = ProgressService(cfg)
    try:
        service.show(date=date)
    except Exception as exc:
        typer.echo(f"读取进度失败: {exc}")


def _run_basic_recommend(cfg: AppConfig, top_n: int = 200, silent: bool = False) -> Optional[Path]:
    _prepare_base_dirs(cfg)
    service = RecommendService(cfg.paths.output_dir, cfg.recommendation_weights)
    try:
        path = service.save(top_n)
        if not silent:
            typer.echo(f"推荐结果已保存到: {path}")
            typer.echo(service.compute(top_n).head(min(10, top_n)).to_string(index=False))
        return path
    except Exception as exc:
        typer.echo(f"生成推荐失败: {exc}")
        return None


def _select_advanced_variant(cfg: AppConfig, mode: str) -> Optional[AdvancedModelConfig]:
    variants = getattr(cfg, "_advanced_variants", [])
    if not variants:
        return cfg.advanced_model
    if not mode or mode == "default":
        return variants[0]
    for variant in variants:
        if variant.label == mode:
            return variant
    typer.echo(f"未找到名为 {mode} 的高级模型配置，可用：{', '.join(v.label for v in variants)}")
    return None


def _run_advanced_recommend(
    cfg: AppConfig,
    top_n: int = 200,
    snapshot_date: Optional[str] = None,
    output_format: str = "excel",
    variant: str = "default",
) -> Optional[Path]:
    _prepare_base_dirs(cfg)
    if not cfg.advanced_model:
        typer.echo("未在 config.yaml 中配置 advanced_model，无法使用高级推荐。")
        return None
    selected = _select_advanced_variant(cfg, variant)
    if not selected:
        return None
    service = AdvancedRecommendService(selected, cfg.paths.output_dir)
    try:
        path = service.save(top_n, snapshot_date=snapshot_date, output_format=output_format)
        typer.echo(f"高级推荐结果已保存到: {path}")
        typer.echo("提示：该列表基于净值特征与自定义权重生成，数据来源 fund_reco_fit。")
        return path
    except Exception as exc:
        typer.echo(f"生成高级推荐失败: {exc}")
        return None


def _run_nav(
    cfg: AppConfig,
    fund_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    fmt: str = "excel",
) -> None:
    _prepare_base_dirs(cfg)
    service = NavService(cfg)
    try:
        path = service.download(fund_code, start_date=start_date, end_date=end_date, fmt=fmt)
        typer.echo(f"基金 {fund_code} 的净值数据已保存：{path}")
    except Exception as exc:
        typer.echo(f"下载净值失败: {exc}")


def _run_nav_bulk(
    cfg: AppConfig,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    fmt: str = "excel",
) -> None:
    _prepare_base_dirs(cfg)
    list_path = cfg.paths.default_fund_list
    if not list_path.exists():
        typer.echo(f"未找到基金列表文件: {list_path}")
        typer.echo("请先在 data/fund_list.csv 中填写基金代码。")
        return

    service = NavService(cfg)
    try:
        successes, errors = service.download_from_file(list_path, start_date=start_date, end_date=end_date, fmt=fmt)
    except Exception as exc:
        typer.echo(f"批量净值下载失败: {exc}")
        return

    if successes:
        suffix = ".xlsx" if fmt == "excel" else ".csv"
        typer.echo(
            f"✅ 已完成 {len(successes)} 只基金的净值下载，保存于 output/nav/（文件名 nav_基金代码{suffix}，重复运行会覆盖）。"
        )
    if errors:
        typer.echo("❗ 以下基金下载失败，请稍后重试或检查代码：")
        for code, message in errors.items():
            typer.echo(f" - {code}: {message}")


def _run_init(cfg: AppConfig) -> None:
    _prepare_base_dirs(cfg)
    typer.echo("✅ 环境初始化完成。")
    typer.echo(f"- 默认基金列表文件: {cfg.paths.default_fund_list}")
    typer.echo("- 请用 Excel/Numbers 打开文件并替换示例内容后再运行详情抓取。")


def _show_help() -> None:
    typer.echo("📘 更多使用说明: 请查看 doc/user_manual.md 或执行 `./fundseeker.sh` 再次选择菜单。")
    typer.echo(
        "常用命令: rank (排行+评级), details (详情), nav (净值，默认批量使用 data/fund_list.csv), progress (查看进度), recommend (推荐，可用 --mode advanced 启用高级模型)。"
    )
    typer.echo(
        "提示: 在菜单中选择“2”时，会提示输入要导出的前 N 条记录；选择“4”可在基础/高级推荐之间切换；选择“7”可拉取净值。"
    )


@app.callback()
def main_callback(ctx: typer.Context, config: Optional[Path] = typer.Option(None, help="指定配置文件路径")) -> None:
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config)
    _prepare_base_dirs(ctx.obj["config"])


@app.command()
def init(ctx: typer.Context) -> None:
    """初始化目录、模板等资源。"""
    cfg = _with_config(ctx)
    _run_init(cfg)


@app.command()
def rank(
    ctx: typer.Context,
    start_date: Optional[str] = typer.Option(None, help="起始日期，格式 YYYY-MM-DD"),
    end_date: Optional[str] = typer.Option(None, help="结束日期，格式 YYYY-MM-DD"),
    limit: Optional[int] = typer.Option(None, help="只导出前 N 条记录"),
) -> None:
    """获取基金排行并补充评级。"""
    cfg = _with_config(ctx)
    _run_rank(cfg, start_date=start_date, end_date=end_date, limit=limit)


@app.command()
def details(
    ctx: typer.Context,
    input_file: Optional[Path] = typer.Option(None, "--input", "-i", help="基金列表文件（Excel/CSV）"),
    no_resume: bool = typer.Option(False, "--no-resume", help="禁用自动断点续传"),
) -> None:
    """根据基金列表抓取详情。"""
    cfg = _with_config(ctx)
    path = str(input_file) if input_file else None
    _run_details(cfg, input_path=path, auto_resume=not no_resume)


@app.command()
def progress(
    ctx: typer.Context,
    date: Optional[str] = typer.Option(None, help="指定日期（YYYY-MM-DD）查看进度"),
) -> None:
    """查看任务进度。"""
    cfg = _with_config(ctx)
    _run_progress(cfg, date=date)


@app.command()
def recommend(
    ctx: typer.Context,
    top_n: int = typer.Option(200, help="输出前 N 条推荐"),
    mode: str = typer.Option("basic", help="basic 或 advanced"),
    snapshot_date: Optional[str] = typer.Option(None, help="高级模式可指定快照日期 (YYYY-MM-DD)"),
    output_format: str = typer.Option("excel", help="输出格式：excel/csv（仅高级模式支持 csv）"),
    adv_variant: str = typer.Option("default", help="高级模型标签（如 basic 指定 default，或 6m/12m 等）"),
) -> None:
    """生成基金推荐列表。"""
    cfg = _with_config(ctx)
    if mode.lower() == "advanced":
        fmt = output_format.lower()
        if fmt not in {"excel", "csv"}:
            raise typer.BadParameter("output-format 仅支持 excel 或 csv")
        _run_advanced_recommend(
            cfg,
            top_n=top_n,
            snapshot_date=snapshot_date,
            output_format=fmt,
            variant=adv_variant,
        )
    else:
        _run_basic_recommend(cfg, top_n=top_n)


@app.command()
def nav(
    ctx: typer.Context,
    fund_code: Optional[str] = typer.Argument(None, help="基金代码（可留空，留空则读取 data/fund_list.csv）"),
    start_date: Optional[str] = typer.Option(None, help="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = typer.Option(None, help="结束日期 YYYY-MM-DD"),
    fmt: str = typer.Option("excel", help="导出格式：excel/csv"),
) -> None:
    """下载基金的历史净值。"""
    cfg = _with_config(ctx)
    fmt = fmt.lower()
    if fmt not in {"excel", "csv"}:
        raise typer.BadParameter("fmt 必须是 excel 或 csv")
    if fund_code:
        _run_nav(cfg, fund_code, start_date=start_date, end_date=end_date, fmt=fmt)
    else:
        _run_nav_bulk(cfg, start_date=start_date, end_date=end_date, fmt=fmt)


@app.command()
def menu(ctx: typer.Context) -> None:
    """启动交互式菜单。"""
    cfg = _with_config(ctx)
    actions: Dict[str, Callable[[], None]] = {
        "1": lambda: _run_init(cfg),
        "2": lambda: _run_rank_with_prompt(cfg),
        "3": lambda: _run_details(cfg),
        "4": lambda: _run_recommend_with_prompt(cfg),
        "5": _show_help,
        "6": lambda: _run_progress(cfg),
        "7": lambda: _run_nav_with_prompt(cfg),
    }
    interactive_menu(actions)


if __name__ == "__main__":
    app()
