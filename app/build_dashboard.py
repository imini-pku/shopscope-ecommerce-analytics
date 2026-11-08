"""Build an offline, self-contained dashboard from the pipeline's real aggregates.

Run from any directory: python app/build_dashboard.py
No runtime dependencies, network requests, or raw visitor records are embedded.
"""
from pathlib import Path
import argparse
import json
import math

HERE = Path(__file__).resolve().parent


def validate(data):
    required = {"meta", "daily", "funnel", "segments", "recommendation", "experiment", "insights"}
    missing = required - data.keys()
    if missing:
        raise ValueError("Missing dashboard sections: " + ", ".join(sorted(missing)))
    for name in ["daily", "segments", "recommendation", "insights"]:
        if not isinstance(data[name], list):
            raise ValueError(f"{name} must be an array")
    if not data["daily"]:
        raise ValueError("daily must contain actual analysis results")
    fields = {
        "meta": "project source source_url analysis_date raw_rows clean_rows visitors items sessions date_min date_max duplicates_removed invalid_rows data_sha256",
        "funnel": "view_pairs view_add_pairs view_purchase_pairs strict_three_step_pairs view_to_add_rate view_to_purchase_rate strict_rate",
        "experiment": "label seed control_users treatment_users control_rate treatment_rate difference_pp ci_low_pp ci_high_pp srm_pvalue decision",
        "daily": "date views addtocarts transactions visitors",
        "segments": "segment sessions view_sessions view_purchase_sessions purchase_rate",
        "recommendation": "split method queries candidate_items hits hit_rate_at_10 coverage_at_10 fallback_rate hit_ci_low hit_ci_high",
    }
    for section, required_fields in fields.items():
        records = data[section] if isinstance(data[section], list) else [data[section]]
        for i, record in enumerate(records):
            if not isinstance(record, dict):
                raise ValueError(f"{section}[{i}] must be an object")
            absent = set(required_fields.split()) - record.keys()
            if absent:
                raise ValueError(f"{section}[{i}] missing fields: " + ", ".join(sorted(absent)))
            if any(record[key] is None for key in required_fields.split()):
                raise ValueError(f"{section}[{i}] contains null required values")
    def check(value, path="root"):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"Non-finite number at {path}")
        if isinstance(value, dict):
            for k, v in value.items(): check(v, path + "." + k)
        elif isinstance(value, list):
            for i, v in enumerate(value): check(v, f"{path}[{i}]")
    check(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=HERE.parent / "reports" / "metrics.json")
    parser.add_argument("--output", type=Path, default=HERE / "index.html")
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8-sig"))
    validate(data)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    page = (HERE / "template.html").read_text(encoding="utf-8")
    page = page.replace("__STYLE__", (HERE / "dashboard.css").read_text(encoding="utf-8"))
    page = page.replace("__DATA__", payload)
    script = (HERE / "dashboard.js").read_text(encoding="utf-8").replace("</script", "<\\/script")
    page = page.replace("__SCRIPT__", script)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding="utf-8")
    print(json.dumps({"output": str(args.output), "bytes": args.output.stat().st_size,
                      "daily_rows": len(data["daily"]), "offline": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
