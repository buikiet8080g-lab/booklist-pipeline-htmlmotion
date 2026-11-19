#!/usr/bin/env python3
# 06 出图 provider 选择策略：apimart 九家 provider 的优先序与最近成功记录（迁移自 booklist-pipeline-Lite）。
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


PREFERRED_PROVIDERS = ("gpt88", "yunwu")
THIRD_PROVIDER = "apimart"
FALLBACK_ONLY_PROVIDER = "flow2api"
KNOWN_PROVIDERS = (*PREFERRED_PROVIDERS, THIRD_PROVIDER, FALLBACK_ONLY_PROVIDER)


def load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def provider_order(state: dict[str, object]) -> list[str]:
    preferred = list(PREFERRED_PROVIDERS)
    last_success = state.get("last_successful_provider")
    if last_success in preferred:
        preferred.remove(last_success)
        preferred.insert(0, str(last_success))
    return [*preferred, THIRD_PROVIDER, FALLBACK_ONLY_PROVIDER]


def mark_success(path: Path, provider: str) -> dict[str, object]:
    if provider not in KNOWN_PROVIDERS:
        raise ValueError(f"unsupported provider: {provider}")
    state = {
        "last_successful_provider": provider,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": None,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return state


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve the Booklist Lite image provider order.")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--mark-success", choices=KNOWN_PROVIDERS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    state_path = Path(args.state_file).expanduser().resolve()
    state = mark_success(state_path, args.mark_success) if args.mark_success else load_state(state_path)
    print(
        json.dumps(
            {
                "state_file": str(state_path),
                "last_successful_provider": state.get("last_successful_provider"),
                "provider_order": provider_order(state),
                "flow2api_fallback_only": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
