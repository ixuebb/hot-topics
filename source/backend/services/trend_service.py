"""趋势与热点分析服务"""
from data_loader import DataLoader


def get_hot_topics(loader: DataLoader, limit=10, year=None):
    micro_problems = loader.micro_problems
    scored = []
    for pid, mp in micro_problems.items():
        pc = mp.get("paper_count", 0)
        if year:
            pc = mp.get("paper_count_by_year", {}).get(str(year), 0)
        if pc == 0:
            continue
        pcy = mp.get("paper_count_by_year", {})
        years = sorted(pcy.keys())
        trend = "stable"
        if len(years) >= 2:
            change = pcy.get(years[-1], 0) - pcy.get(years[-2], 0)
            trend = "rising" if change > 1 else "falling" if change < -1 else "stable"
        scored.append((pc, pid, mp, trend))
    scored.sort(key=lambda x: -x[0])
    results = []
    for rank, (cnt, pid, mp, trend) in enumerate(scored[:limit], 1):
        results.append({
            "rank": rank,
            "problem_id": pid,
            "problem_name": mp.get("name", ""),
            "paper_count": cnt,
            "paper_count_by_year": mp.get("paper_count_by_year", {}),
            "trend": trend,
            "macro_category": mp.get("macro_problem_name", ""),
        })
    return results


def get_temporal_trends(loader: DataLoader, start_year=2021, end_year=2026):
    labels = [str(y) for y in range(start_year, end_year + 1)]
    total = [len(loader.papers_by_year.get(y, [])) for y in range(start_year, end_year + 1)]

    by_category = {}
    for mp_id, mp in loader.micro_problems.items():
        cat = mp.get("macro_problem_name", "Other")
        pcy = mp.get("paper_count_by_year", {})
        # Use distinct paper counts, avoiding double count
        if cat not in by_category:
            by_category[cat] = {str(y): 0 for y in range(start_year, end_year + 1)}
        for yr_str, cnt in pcy.items():
            yr = int(yr_str)
            if start_year <= yr <= end_year:
                by_category[cat][yr_str] += cnt

    growth_rate = {}
    for i in range(start_year, end_year):
        prev = total[i - start_year]
        curr = total[i - start_year + 1]
        if prev > 0:
            growth_rate[f"{i}-{i + 1}"] = round((curr - prev) / prev, 2)
        else:
            growth_rate[f"{i}-{i + 1}"] = 0

    return {
        "labels": labels,
        "total": total,
        "by_category": {k: [v.get(str(y), 0) for y in range(start_year, end_year + 1)] for k, v in by_category.items()},
        "growth_rate": growth_rate,
    }
