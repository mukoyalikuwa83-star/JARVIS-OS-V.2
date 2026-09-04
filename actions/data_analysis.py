"""
Data Analysis Module for JARVIS.
CSV/JSON analysis, statistics, visualization, trend detection.
Requires: csv, json (built-in), optional pandas, matplotlib
"""
import os
import time
import json
import csv
import statistics
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)

def handle(params=None):
    params = params or {}
    action = params.get("action", "status")
    
    if action == "analyze_csv":
        return _analyze_csv(params)
    elif action == "analyze_json":
        return _analyze_json(params)
    elif action == "compare":
        return _compare_data(params)
    elif action == "trend":
        return _detect_trend(params)
    elif action == "summarize":
        return _summarize(params)
    elif action == "filter":
        return _filter_data(params)
    elif action == "sort":
        return _sort_data(params)
    elif action == "convert":
        return _convert_format(params)
    elif action == "statistics":
        return _compute_statistics(params)
    elif action == "visualize":
        return _create_chart(params)
    elif action == "status":
        return "DataAnalysis: analyze_csv|analyze_json|compare|trend|summarize|filter|sort|convert|statistics|visualize"
    else:
        return "DataAnalysis: analyze_csv|analyze_json|compare|trend|summarize|filter|sort|convert|statistics|visualize"

def _analyze_csv(params):
    path = params.get("path", "")
    if not path or not os.path.exists(path):
        return "CSV file not found"
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            return "CSV is empty"
        cols = list(rows[0].keys())
        report = f"CSV Analysis: {path}\nRows: {len(rows)}\nColumns: {cols}\n"
        for col in cols:
            values = [r.get(col, "") for r in rows]
            numeric = []
            for v in values:
                try:
                    numeric.append(float(v))
                except (ValueError, TypeError):
                    pass
            if len(numeric) > len(values) * 0.5:
                avg = statistics.mean(numeric)
                med = statistics.median(numeric)
                rng = max(numeric) - min(numeric)
                report += f"  {col}: avg={avg:.2f}, median={med:.2f}, range={rng:.2f}\n"
            else:
                unique = len(set(values))
                report += f"  {col}: {unique} unique values\n"
        return report
    except Exception as e:
        return f"CSV analysis error: {e}"

def _analyze_json(params):
    path = params.get("path", "")
    if not path or not os.path.exists(path):
        return "JSON file not found"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return f"JSON array: {len(data)} items"
        elif isinstance(data, dict):
            report = f"JSON object: {len(data)} keys\n"
            for k, v in data.items():
                vtype = type(v).__name__
                if isinstance(v, list):
                    report += f"  {k}: list[{len(v)}]\n"
                elif isinstance(v, dict):
                    report += f"  {k}: dict[{len(v)} keys]\n"
                else:
                    report += f"  {k}: {vtype} = {str(v)[:100]}\n"
            return report
        return f"JSON: {type(data).__name__}"
    except Exception as e:
        return f"JSON analysis error: {e}"

def _compare_data(params):
    path1 = params.get("path1", "")
    path2 = params.get("path2", "")
    if not path1 or not path2:
        return "Two file paths required"
    try:
        with open(path1, "r", encoding="utf-8") as f1, open(path2, "r", encoding="utf-8") as f2:
            d1 = f1.read()
            d2 = f2.read()
        lines1 = d1.splitlines()
        lines2 = d2.splitlines()
        diff_count = sum(1 for a, b in zip(lines1, lines2) if a != b)
        total = max(len(lines1), len(lines2))
        return f"Files: {len(lines1)} vs {len(lines2)} lines, {diff_count} differences"
    except Exception as e:
        return f"Compare error: {e}"

def _detect_trend(params):
    values = params.get("values", [])
    if isinstance(values, str):
        values = [float(x.strip()) for x in values.split(",") if x.strip()]
    if len(values) < 3:
        return "Need at least 3 data points"
    try:
        values = [float(v) for v in values]
        avg = statistics.mean(values)
        recent_avg = statistics.mean(values[-3:])
        first_avg = statistics.mean(values[:3])
        change = ((recent_avg - first_avg) / first_avg * 100) if first_avg else 0
        if change > 10:
            trend = "UPWARD"
        elif change < -10:
            trend = "DOWNWARD"
        else:
            trend = "STABLE"
        return f"Trend: {trend} ({change:+.1f}%), avg={avg:.2f}, recent={recent_avg:.2f}"
    except Exception as e:
        return f"Trend error: {e}"

def _summarize(params):
    text = params.get("text", "")
    path = params.get("path", "")
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    if not text:
        return "No text to summarize"
    words = text.split()
    sentences = [s.strip() for s in text.replace(".", ".").split(".") if s.strip()]
    return f"Summary: {len(words)} words, {len(sentences)} sentences. First sentence: {sentences[0] if sentences else 'N/A'}"

def _filter_data(params):
    path = params.get("path", "")
    column = params.get("column", "")
    value = params.get("value", "")
    if not path or not os.path.exists(path):
        return "File not found"
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            filtered = [r for r in reader if value.lower() in str(r.get(column, "")).lower()]
        return f"Filtered: {len(filtered)} rows where {column} contains '{value}'"
    except Exception as e:
        return f"Filter error: {e}"

def _sort_data(params):
    path = params.get("path", "")
    column = params.get("column", "")
    if not path or not os.path.exists(path):
        return "File not found"
    try:
        with open(path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        reverse = params.get("reverse", False)
        rows.sort(key=lambda r: r.get(column, ""), reverse=reverse)
        return f"Sorted {len(rows)} rows by {column} ({'desc' if reverse else 'asc'})"
    except Exception as e:
        return f"Sort error: {e}"

def _convert_format(params):
    src = params.get("src", "")
    dst = params.get("dst", "")
    fmt = params.get("to", "json")
    if not src or not os.path.exists(src):
        return "Source file not found"
    try:
        if src.endswith(".csv") and fmt == "json":
            with open(src, "r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            if not dst:
                dst = src.rsplit(".", 1)[0] + ".json"
            with open(dst, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2)
            return f"Converted {src} -> {dst} ({len(rows)} records)"
        return f"Conversion not supported: {src} -> {fmt}"
    except Exception as e:
        return f"Convert error: {e}"

def _compute_statistics(params):
    values = params.get("values", [])
    if isinstance(values, str):
        values = [float(x.strip()) for x in values.split(",") if x.strip()]
    if not values:
        return "No values provided"
    try:
        values = [float(v) for v in values]
        return json.dumps({
            "count": len(values),
            "mean": round(statistics.mean(values), 4),
            "median": round(statistics.median(values), 4),
            "stdev": round(statistics.stdev(values), 4) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
            "range": max(values) - min(values),
        }, indent=2)
    except Exception as e:
        return f"Statistics error: {e}"

def _create_chart(params):
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use("Agg")
        values = params.get("values", [])
        labels = params.get("labels", [])
        title = params.get("title", "Chart")
        chart_type = params.get("type", "bar")
        if isinstance(values, str):
            values = [float(x.strip()) for x in values.split(",") if x.strip()]
        if isinstance(labels, str):
            labels = [x.strip() for x in labels.split(",") if x.strip()]
        fig, ax = plt.subplots(figsize=(8, 5))
        if chart_type == "bar":
            ax.bar(range(len(values)), values)
        elif chart_type == "line":
            ax.plot(values, marker="o")
        elif chart_type == "pie":
            ax.pie(values, labels=labels[:len(values)] if labels else None, autopct="%1.1f%%")
        ax.set_title(title)
        if labels and chart_type != "pie":
            ax.set_xticks(range(len(values)))
            ax.set_xticklabels(labels[:len(values)], rotation=45)
        path = str(_DATA_DIR / f"chart_{int(time.time())}.png")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        return f"Chart saved: {path}"
    except ImportError:
        return "matplotlib not installed. Run: pip install matplotlib"
    except Exception as e:
        return f"Chart error: {e}"
