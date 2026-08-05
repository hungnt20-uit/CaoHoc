"""Chạy hệ chuyên gia qua LLM local thật, đối chiếu với heuristic offline.

    PYTHONPATH=. python scripts/compare_local_llm.py <base_url>
"""
import sys
import time
from pathlib import Path

from traffic_es.engine.reasoner import Reasoner
from traffic_es.llm.client import CachingLLM
from traffic_es.llm.providers import LocalOpenAICompatLLM
from traffic_es.nlu.extractor import HeuristicExtractor
from traffic_es.nlu.llm_extractor import LLMExtractor
from traffic_es.nlu.llm_semantic_infer import LLMCircumstanceInferrer
from traffic_es.nlu.pipeline import NLUPipeline
from traffic_es.nlu.semantic_infer import KeywordInferrer
from traffic_es.service import TrafficESService

CASES = [
    "Tối qua nhậu xong tôi vẫn cầm lái con xe hơi về nhà, bị thổi ra 0,45 mg/l khí thở.",
    "Chạy xe máy trong khu dân cư mà kim đồng hồ chỉ 70 trong khi biển ghi 50.",
    "Tôi đi xe máy không đội mũ bảo hiểm và vượt đèn đỏ ở ngã tư.",
    "Tôi vượt đèn đỏ rồi bỏ chạy khi CSGT ra hiệu dừng xe.",
    "Tôi dừng đèn đỏ đúng luật, có đội mũ bảo hiểm, và không gây tai nạn gì cả.",
]


def main(base_url: str) -> None:
    llm = LocalOpenAICompatLLM(base_url=base_url, timeout=180)
    print("health:", llm.health())

    rules = Path(__file__).resolve().parents[1] / "traffic_es" / "knowledge" / "rules"
    reasoner = Reasoner.from_rules_dir(rules)
    cached = CachingLLM(llm)
    svc_llm = TrafficESService(
        reasoner,
        NLUPipeline(LLMExtractor(cached), inferrer=LLMCircumstanceInferrer(cached)),
    )
    svc_heu = TrafficESService(
        reasoner, NLUPipeline(HeuristicExtractor(), inferrer=KeywordInferrer())
    )

    for text in CASES:
        print("\n" + "=" * 78)
        print("CÂU:", text)
        start = time.time()
        answer = svc_llm.answer(text)
        print(f"[Qwen {time.time() - start:5.1f}s] facts = {answer.facts}")
        print(f"           tiền = {answer.ket_qua.tong_tien:,}đ "
              f"· {len(answer.ket_qua.chi_tiet)} lỗi")
        for item in answer.ket_qua.chi_tiet:
            print("           -", item.can_cu)
        for tt in answer.nlu_meta.get("inferred", []):
            print(f"           tình tiết: {tt['fact']} ← '{tt.get('nguon')}'")
        for warning in answer.nlu_meta.get("warnings", []):
            print("           ⚠", warning)

        heuristic = svc_heu.answer(text)
        print(f"[Heur     ] tiền = {heuristic.ket_qua.tong_tien:,}đ "
              f"· {len(heuristic.ket_qua.chi_tiet)} lỗi")


if __name__ == "__main__":
    main(sys.argv[1])
