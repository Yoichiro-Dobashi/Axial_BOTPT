#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
- data/raw/ 以下の全 .dat を走査
- 「(サブ)フォルダ名/ファイル名」から station 名を自動生成
- 列推測: 1列目=時刻, 2列目=値（ヘッダがあれば 'time','timestamp','date' 等/ 'pressure','prs','kpa','psi' 等を優先）
- すべて UTC 扱い（必要なら下で TZ を変える）
- 出力: site/data/all_series.json（Plotly が読む）
"""

from pathlib import Path
import json
import pandas as pd
from dateutil import tz

# ── 設定（必要に応じて変更） ─────────────────────────
RAW_DIR = Path("data/raw")
OUT_DIR = Path("site/data")
ASSUME_UNITS = "psi"   # "psi" or "kPa"（わからなければ "psi" のまま → kPa換算します）
LOCAL_TZ = "UTC"       # ローカル時区があれば "America/Los_Angeles" などに
RESAMPLE_RULE = "15min"  # 表示負荷軽減用の間引き（"None"で無効）
# ────────────────────────────────────────────────

PSI_TO_KPA = 6.89475729

def _find_cols(df):
    lc = [c.lower().strip() for c in df.columns]
    # 候補
    time_keys = ["time", "timestamp", "date", "datetime"]
    val_keys  = ["pressure", "prs", "kpa", "psi", "value", "val"]
    # 探す
    t_idx = None
    v_idx = None
    for k in time_keys:
        if k in lc: t_idx = lc.index(k); break
    for k in val_keys:
        if k in lc: v_idx = lc.index(k); break
    # 見つからなければ 1列目=時刻, 2列目=値 とする
    if t_idx is None: t_idx = 0
    if v_idx is None:
        v_idx = 1 if len(df.columns) > 1 else 0
        if v_idx == t_idx and len(df.columns) > 1:
            v_idx = 1
    return df.columns[t_idx], df.columns[v_idx]

def load_dat(path: Path) -> pd.DataFrame:
    # 推測読み（コメント頭 # は無視）
    try:
        df = pd.read_csv(path, sep=None, engine="python", comment="#", na_values=["", "NA", "NaN"])
    except Exception:
        # 区切り推測失敗時は空白区切りにフォールバック
        df = pd.read_csv(path, sep=r"\s+", engine="python", comment="#", na_values=["", "NA", "NaN"])

    if df.empty:
        return pd.DataFrame(columns=["time", "pressure_kPa"])

    tcol, vcol = _find_cols(df)
    # 時刻パース
    t = pd.to_datetime(df[tcol], errors="coerce", utc=True)
    # 値は数値化
    y = pd.to_numeric(df[vcol], errors="coerce")

    out = pd.DataFrame({"time": t, "value": y}).dropna()
    if ASSUME_UNITS.lower() == "psi":
        out["pressure_kPa"] = out["value"] * PSI_TO_KPA
    else:
        out["pressure_kPa"] = out["value"]  # すでに kPa と仮定
    out = out.drop(columns=["value"]).sort_values("time").reset_index(drop=True)
    return out

def station_name_from_path(path: Path) -> str:
    """
    data/raw/MJ03F/PARO1/file.dat → "MJ03F/PARO1" をステーション名に。
    もう少し長い階層でもOK。
    """
    rel = path.relative_to(RAW_DIR)
    parts = rel.parts[:-1]  # ファイル名除く
    return "/".join(parts) if parts else rel.stem

def resample_df(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    if not rule or rule.lower() == "none":
        return df
    s = df.set_index("time")["pressure_kPa"].resample(rule).mean().dropna()
    return s.reset_index()

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    records = {}  # {station: DataFrame}
    for path in RAW_DIR.rglob("*.dat"):
        try:
            df = load_dat(path)
            if df.empty:
                continue
            st = station_name_from_path(path)
            records.setdefault(st, []).append(df)
        except Exception as e:
            print(f"[WARN] Failed to parse {path}: {e}")

    series = []
    for st, dfs in records.items():
        merged = pd.concat(dfs, ignore_index=True).dropna().sort_values("time")
        # 重複時刻は平均
        merged = merged.groupby("time", as_index=False)["pressure_kPa"].mean()
        # 表示用に間引き
        merged = resample_df(merged, RESAMPLE_RULE)
        # JSON へ
        series.append({
            "station": st,
            "x": merged["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ").tolist(),
            "y": merged["pressure_kPa"].round(4).tolist(),
            "unit": "kPa"
        })

    payload = {
        "meta": {
            "updated_at": pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "count_series": len(series),
            "note": "Resampled for display" if RESAMPLE_RULE else "Raw cadence",
        },
        "series": series
    }

    out_path = OUT_DIR / "all_series.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    print(f"[OK] Wrote {out_path} with {len(series)} series.")

if __name__ == "__main__":
    main()
