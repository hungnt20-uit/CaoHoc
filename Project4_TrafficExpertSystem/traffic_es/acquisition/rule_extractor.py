from __future__ import annotations

import json
from typing import List

from traffic_es.acquisition.segmenter import Clause
from traffic_es.llm.client import LLMClient
from traffic_es.knowledge.rules import Rule, KetLuan, CanCu

SYSTEM = (
    "Bạn là trợ lý pháp lý. Cho một mệnh đề trong nghị định xử phạt giao thông, "
    "hãy trích thành JSON với các khóa: nhom, ap_dung_loai_xe (mảng), "
    "dieu_kien (mảng biểu thức dạng 'chiso.x > 0.4' hoặc 'boicanh.khuVuc == \"khu_dan_cu\"'), "
    "hanh_vi (mô tả ngắn). Nếu mệnh đề KHÔNG mô tả hành vi bị phạt, trả về chuỗi rỗng. "
    "TUYỆT ĐỐI không bịa số tiền phạt."
)


def _rule_id(nghi_dinh: str, clause: Clause, nhom: str) -> str:
    nd = nghi_dinh.split("/")[0]
    return f"R_{nd}_D{clause.dieu}_K{clause.khoan}_{clause.diem or 'x'}_{nhom}".upper()


def extract_rules(
    clause: Clause, nghi_dinh: str, llm: LLMClient, tien_min: int, tien_max: int
) -> List[Rule]:
    user = f"Điều {clause.dieu} ({clause.dieu_title}), Khoản {clause.khoan}: {clause.text}"
    raw = llm.complete(system=SYSTEM, user=user)
    if not raw or not raw.strip():
        return []
    data = json.loads(raw)
    if not data or not data.get("hanh_vi"):
        return []
    ket_luan = KetLuan(
        hanh_vi=data["hanh_vi"],
        tien_phat_min=tien_min,  # số tiền LẤY TỪ CLAUSE, không từ LLM
        tien_phat_max=tien_max,
        can_cu=CanCu(
            nghi_dinh=nghi_dinh, dieu=clause.dieu, khoan=clause.khoan, diem=clause.diem
        ),
    )
    rule = Rule(
        id=_rule_id(nghi_dinh, clause, data.get("nhom", "khac")),
        nhom=data.get("nhom", "khac"),
        ap_dung_loai_xe=data.get("ap_dung_loai_xe", []),
        dieu_kien=data.get("dieu_kien", []),
        ket_luan=ket_luan,
    )
    return [rule]
