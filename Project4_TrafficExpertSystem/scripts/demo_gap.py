"""Demo Gap #1 (Mạng tính toán + A*) & Gap #2 (Legal-Onto KG + subgraph matching).

Chạy:  python -m scripts.demo_gap
"""

from __future__ import annotations

from pathlib import Path

from traffic_es.service import TrafficESService

RULES_DIR = Path(__file__).resolve().parents[1] / "traffic_es" / "knowledge" / "rules"

CASES = [
    "Ô tô chạy 80 km/h trên đoạn giới hạn 50 km/h thì đâm vào xe máy.",
    "Đi xe máy không đội mũ bảo hiểm và vượt đèn đỏ.",
    "Lái ô tô với nồng độ cồn 0,45 mg/l khí thở rồi gây tai nạn.",
]


def main() -> None:
    svc = TrafficESService.default(RULES_DIR)
    for i, text in enumerate(CASES, 1):
        ans = svc.answer(text)
        print(f"\n{'='*70}\nCA {i}: {text}")
        if ans.sample_problem:
            print(f"  🧩 Mẫu bài toán: {ans.sample_problem.name} — {ans.sample_problem.goal}")
        mc = ans.nlu_meta.get("matched_concepts") or []
        if mc:
            print("  🕸️ Concept khớp (question-graph → subgraph):")
            for m in mc:
                print(f"     - {m['concept']} (điểm {m['score']})")
        astar = [s for s in ans.trace.steps if s.kind == "ASTAR"]
        for s in astar:
            print(f"  ⭐ {s.detail}")
        print(f"  ⚖️ Tổng tiền phạt: {ans.ket_qua.tong_tien:,} đ; "
              f"tước GPLX tối đa: {ans.ket_qua.tuoc_gplx_thang_max or 0} tháng")


if __name__ == "__main__":
    main()
