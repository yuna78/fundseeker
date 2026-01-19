"""Configuration loader for the FundSeeker CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import warnings

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AppPaths:
    """Resolved project paths."""

    root: Path
    output_dir: Path
    logs_dir: Path
    progress_dir: Path
    templates_dir: Path
    data_dir: Path
    default_fund_list: Path


@dataclass(frozen=True)
class AppSettings:
    """Runtime settings for fetch tasks."""

    batch_size: int
    save_interval: int
    request_delay: float
    request_timeout: int
    user_agent: str


@dataclass(frozen=True)
class AdvancedModelConfig:
    db_path: Path
    feature_table: str
    weights_path: Path
    top_k: int
    label: str = "default"


@dataclass(frozen=True)
class AppConfig:
    """Bundled paths and settings."""

    paths: AppPaths
    settings: AppSettings
    recommendation_weights: "RecommendationWeights"
    advanced_model: Optional[AdvancedModelConfig]

    def resolve_base_dir(self, kind: str) -> Path:
        """Return the base directory for a given kind."""
        mapping = {
            "output": self.paths.output_dir,
            "logs": self.paths.logs_dir,
            "progress": self.paths.progress_dir,
            "templates": self.paths.templates_dir,
            "data": self.paths.data_dir,
        }
        if kind not in mapping:
            raise ValueError(f"Unknown base dir kind: {kind}")
        return mapping[kind]


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}

    if yaml is None:
        warnings.warn("PyYAML 未安装，忽略 config.yaml，自行使用默认配置。")
        return {}

    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _resolve_path(value: Optional[str], default: Path) -> Path:
    if not value:
        return default
    expanded = os.path.expandvars(os.path.expanduser(value))
    return Path(expanded).resolve()


@dataclass(frozen=True)
class RecommendationWeights:
    recent: float
    mid: float
    long: float
    risk_penalty: float
    manager: float
    scale: float
    rating: float
    age: float


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """Load configuration from YAML file and env overrides."""

    root_dir = Path(__file__).resolve().parents[2]
    cfg_file = config_path or root_dir / "config.yaml"
    raw = _load_yaml(cfg_file)
    defaults = raw.get("defaults", {})

    output_dir = _resolve_path(
        os.getenv("FUNDSEEKER_OUTPUT_DIR"),
        (root_dir / defaults.get("output_dir", "output")).resolve(),
    )
    logs_dir = _resolve_path(
        os.getenv("FUNDSEEKER_LOGS_DIR"),
        (root_dir / defaults.get("logs_dir", "logs")).resolve(),
    )
    progress_dir = _resolve_path(
        os.getenv("FUNDSEEKER_PROGRESS_DIR"),
        (root_dir / defaults.get("progress_dir", "progress")).resolve(),
    )
    templates_dir = _resolve_path(
        os.getenv("FUNDSEEKER_TEMPLATES_DIR"),
        (root_dir / defaults.get("templates_dir", "templates")).resolve(),
    )
    data_dir = _resolve_path(
        os.getenv("FUNDSEEKER_DATA_DIR"),
        (root_dir / defaults.get("data_dir", "data")).resolve(),
    )
    default_list_path = _resolve_path(
        os.getenv("FUNDSEEKER_DEFAULT_FUND_LIST"),
        (root_dir / defaults.get("default_fund_list", "data/fund_list.csv")).resolve(),
    )

    paths = AppPaths(
        root=root_dir,
        output_dir=output_dir,
        logs_dir=logs_dir,
        progress_dir=progress_dir,
        templates_dir=templates_dir,
        data_dir=data_dir,
        default_fund_list=default_list_path,
    )

    settings = AppSettings(
        batch_size=int(os.getenv("FUNDSEEKER_BATCH_SIZE", defaults.get("batch_size", 10))),
        save_interval=int(os.getenv("FUNDSEEKER_SAVE_INTERVAL", defaults.get("save_interval", 100))),
        request_delay=float(os.getenv("FUNDSEEKER_REQUEST_DELAY", defaults.get("request_delay", 0.5))),
        request_timeout=int(os.getenv("FUNDSEEKER_REQUEST_TIMEOUT", defaults.get("request_timeout", 30))),
        user_agent=os.getenv(
            "FUNDSEEKER_USER_AGENT",
            defaults.get(
                "user_agent",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ),
        ),
    )

    weights_cfg = defaults.get("recommendation_weights", {})
    weights = RecommendationWeights(
        recent=float(os.getenv("FUNDSEEKER_RECENT_WEIGHT", weights_cfg.get("recent", 0.35))),
        mid=float(os.getenv("FUNDSEEKER_MID_WEIGHT", weights_cfg.get("mid", 0.20))),
        long=float(os.getenv("FUNDSEEKER_LONG_WEIGHT", weights_cfg.get("long", 0.15))),
        risk_penalty=float(
            os.getenv("FUNDSEEKER_RISK_WEIGHT", weights_cfg.get("risk_penalty", 0.10))
        ),
        manager=float(os.getenv("FUNDSEEKER_MANAGER_WEIGHT", weights_cfg.get("manager", 0.10))),
        scale=float(os.getenv("FUNDSEEKER_SCALE_WEIGHT", weights_cfg.get("scale", 0.05))),
        rating=float(os.getenv("FUNDSEEKER_RATING_WEIGHT", weights_cfg.get("rating", 0.03))),
        age=float(os.getenv("FUNDSEEKER_AGE_WEIGHT", weights_cfg.get("age", 0.02))),
    )

    advanced_raw = defaults.get("advanced_model")
    advanced_model: Optional[AdvancedModelConfig] = None
    if isinstance(advanced_raw, dict):
        advanced_list = [advanced_raw]
    elif isinstance(advanced_raw, list):
        advanced_list = advanced_raw
    else:
        advanced_list = []

    advanced_configs = []
    for item in advanced_list:
        label = item.get("label") or item.get("name") or "default"
        advanced_configs.append(
            AdvancedModelConfig(
                db_path=_resolve_path(
                    os.getenv("FUNDSEEKER_ADV_DB"),
                    (root_dir / item.get("db_path", "../fund_reco_fit/data/fundseeker_nav.db")).resolve(),
                ),
                feature_table=item.get("feature_table", "features_M"),
                weights_path=_resolve_path(
                    os.getenv("FUNDSEEKER_ADV_WEIGHTS"),
                    (root_dir / item.get("weights_path", "../fund_reco_fit/models/model_params.json")).resolve(),
                ),
                top_k=int(os.getenv("FUNDSEEKER_ADV_TOP_K", item.get("top_k", 200))),
                label=label,
            )
        )

    if advanced_configs:
        advanced_model = advanced_configs[0]
    cfg = AppConfig(
        paths=paths,
        settings=settings,
        recommendation_weights=weights,
        advanced_model=advanced_model,
    )
    object.__setattr__(cfg, "_advanced_variants", tuple(advanced_configs))
    return cfg
