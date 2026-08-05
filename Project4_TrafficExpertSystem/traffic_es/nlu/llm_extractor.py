from __future__ import annotations

import json
import re
from typing import Dict, List, Tuple

from traffic_es.llm.client import LLMClient
from traffic_es.nlu.evidence import cites_source, number_appears
from traffic_es.nlu.extractor import HeuristicExtractor
from traffic_es.nlu.grounding import ground

SYSTEM = (
    "Bạn trích thông tin hiện trường giao thông từ câu tiếng Việt thành JSON gồm 2 khóa: "
    "'facts' (map node ontology hợp lệ) và 'raw_events' (mảng câu sự kiện thô). "
    'Mỗi node viết dạng "<node>": {"value": <giá trị>, "nguon": "<trích nguyên văn>"}. '
    "'nguon' phải COPY Y HỆT một cụm chữ có trong câu gốc — không diễn giải, không thêm "
    "chữ nào, không viết kiểu \"cụm chữ '...'\". Node nào không trích dẫn được sẽ bị loại. "
    "Node hợp lệ: phuongtien.loai ('o_to'|'xe_may'|'xe_dap'); chiso.nongDoCon_khiTho (mg/l); "
    "chiso.nongDoCon_mau (mg/100ml); chiso.tocDo; chiso.tocDoGioiHan (km/h); "
    "boicanh.khuVuc ('khu_dan_cu'|'do_thi'|'ngoai_do_thi'|'cao_toc'); "
    "nguoi.khong_mu_bao_hiem/khong_day_an_toan (bool); nguoi.coGPLX (bool); "
    "hanhvi.vuot_den_do/vuot_den_vang/khong_chap_hanh_csgt (bool); "
    "hanhvi.cam_dien_thoai (bool); hanhvi.su_dung_thiet_bi_am_thanh (bool); "
    "hanhvi.sai_lan/sai_phan_duong/dung_do_sai (bool). "
    "Hiểu ngữ nghĩa chủ đề: "
    "(A) NỒNG ĐỘ CỒN — 'uống rượu', 'uống bia', 'nhậu', 'say', 'say xỉn', 'say rượu', "
    "'có cồn', kể cả viết sai/thiếu dấu gần nghĩa (vd 'uống rựu'). Khi đó: đưa cụm vào "
    "raw_events; CHỈ điền chiso.nongDoCon_khiTho/chiso.nongDoCon_mau nếu câu có CON SỐ đo "
    "(mg/l hoặc mg/100ml) — không bịa số, không gán mức mặc định. "
    "(B) VƯỢT TỐC ĐỘ — 'quá tốc độ', 'vượt tốc độ', 'chạy quá tốc độ', 'phóng nhanh', "
    "'chạy nhanh', 'lố tốc độ', kể cả diễn đạt gần nghĩa. Khi đó: đưa cụm vào raw_events; "
    "CHỈ điền chiso.tocDo / chiso.tocDoGioiHan nếu câu nêu rõ số km/h (tốc độ chạy và/hoặc "
    "giới hạn) — không bịa số, không tự suy tốc độ giới hạn theo luật. "
    "(C) VƯỢT ĐÈN ĐỎ / TÍN HIỆU — 'vượt đèn đỏ', 'vượt đèn', 'đèn đỏ', 'phóng qua đèn đỏ', "
    "'không chấp hành hiệu lệnh của đèn tín hiệu', 'không chấp hành đèn tín hiệu', "
    "'không chấp hành hiệu lệnh', 'vượt đèn vàng' (nếu câu nói rõ là tín hiệu đèn), "
    "kể cả diễn đạt gần nghĩa. Khi đó: đặt hanhvi.vuot_den_do=true với nguon là cụm "
    "trong câu (KHÔNG đặt nếu câu phủ định kiểu 'không vượt đèn'). "
    "(D) CẦM ĐIỆN THOẠI / TAI NGHE — 'cầm điện thoại', 'dùng điện thoại', 'nghe điện thoại', "
    "'cầm điện thoai' (sai chính tả), 'đeo tai nghe', 'tai nghe', 'thiết bị âm thanh'. "
    "Khi đó: hanhvi.cam_dien_thoai=true (điện thoại) hoặc "
    "hanhvi.su_dung_thiet_bi_am_thanh=true (tai nghe), nguon là cụm trong câu. "
    "(E) SAI LÀN / DỪNG ĐỖ — 'lấn làn', 'sai làn', 'không đúng làn', 'đỗ nơi cấm', "
    "'đậu nơi cấm', 'cấm đỗ' → hanhvi.sai_lan hoặc hanhvi.dung_do_sai = true. "
    "Sự kiện va chạm/tái phạm/bỏ chạy cũng để trong raw_events. "
    "TUYỆT ĐỐI không bịa số và không tự điền giá trị mặc định theo luật: chỉ ghi những gì "
    "câu nói rõ. "
    "Chỉ trả JSON."
)

_FENCE = re.compile(r"^```[a-zA-Z]*\n?|\n?```$")


def _parse(raw: str) -> dict:
    s = (raw or "").strip()
    s = _FENCE.sub("", s).strip()
    try:
        data = json.loads(s)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        pass
    # fallback: trích khối {...} đầu-cuối (khi LLM kèm chữ quanh JSON)
    i, j = s.find("{"), s.rfind("}")
    if 0 <= i < j:
        try:
            data = json.loads(s[i : j + 1])
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def _value_and_source(raw: object) -> Tuple[object, str]:
    """Tách (giá trị, trích dẫn) khỏi một mục fact, chấp nhận cả dạng không trích dẫn."""
    if isinstance(raw, dict) and "value" in raw:
        return raw["value"], str(raw.get("nguon") or raw.get("nguồn") or "")
    return raw, ""


def _as_fact_map(facts: object) -> Dict[str, Tuple[object, str]]:
    """Chuẩn hóa mọi dạng `facts` LLM hay trả về map {key: (giá trị, trích dẫn)}.

    Prompt yêu cầu map kèm trích dẫn, nhưng model nhỏ chạy local lệch dạng khá thường
    xuyên — khi thì map phẳng {key: value}, khi thì mảng [{"key":…, "value":…}]. Lệch
    dạng không nên làm sập luồng suy diễn: các tầng sau vẫn kiểm chứng và chặn node lạ.
    """
    if isinstance(facts, dict):
        return {str(k): _value_and_source(v) for k, v in facts.items()}
    if isinstance(facts, list):
        out: Dict[str, Tuple[object, str]] = {}
        for item in facts:
            if not isinstance(item, dict):
                continue
            key = item.get("key") or item.get("node") or item.get("fact")
            if isinstance(key, str) and "value" in item:
                out[key] = (item["value"], str(item.get("nguon") or ""))
        return out
    return {}


def _as_events(events: object) -> List[str]:
    if isinstance(events, str):
        return [events] if events.strip() else []
    if not isinstance(events, list):
        return []
    return [str(e) for e in events if isinstance(e, (str, int, float)) and str(e).strip()]


_SO_DAU_CHUOI = re.compile(r"^-?\d+(?:[.,]\d+)?")


def _coerce_value(v: object) -> object:
    """Ép chuỗi về bool/số, chấp nhận cả chuỗi mang đơn vị.

    Qwen hay trả `"0.45 mg/l"` hoặc `"50 km/h"` thay vì con số trần; để nguyên thì
    grounding loại vì sai kiểu, và mất luôn một lỗi vi phạm có thật.
    """
    if not isinstance(v, str):
        return v
    low = v.strip().lower()
    if low in ("true", "false"):
        return low == "true"
    found = _SO_DAU_CHUOI.match(low)
    if found:
        return float(found.group(0).replace(",", "."))
    return v


def _verify(
    pairs: Dict[str, Tuple[object, str]], text: str
) -> Tuple[Dict[str, object], Dict[str, str], Dict[str, str]]:
    """Chỉ giữ fact truy được về một cụm chữ có thật trong câu.

    Số bị soi riêng và soi trước: đó là chốt duy nhất còn hiệu lực khi LLM bịa luôn cả
    phần trích dẫn, và cũng là loại ảo giác nguy hiểm nhất vì một con số sai đủ sức đẻ
    ra một lỗi vi phạm không tồn tại.
    """
    facts: Dict[str, object] = {}
    evidences: Dict[str, str] = {}
    dropped: Dict[str, str] = {}
    for key, (raw_value, nguon) in pairs.items():
        value = _coerce_value(raw_value)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if not number_appears(text, float(value)):
                dropped[key] = f"Bỏ '{key}={value}': con số này không có trong câu."
                continue
        if not nguon:
            dropped[key] = f"Bỏ '{key}': LLM không trích dẫn được nguồn trong câu."
            continue
        if not cites_source(text, nguon):
            dropped[key] = f"Bỏ '{key}': trích dẫn '{nguon}' không dẫn đúng câu gốc."
            continue
        facts[key] = value
        evidences[key] = nguon
    return facts, evidences, dropped


class LLMExtractor:
    def __init__(self, llm: LLMClient):
        self.llm = llm
        # Kết quả kiểm chứng của lượt gần nhất, cho bảng "Chi tiết phân tích" trên UI.
        # Tách riêng fact bị loại theo khóa vì tầng đồ thị tri thức phía sau còn có thể
        # bổ sung lại chính fact đó — khi ấy không nên báo là đã bỏ.
        self.last_dropped: Dict[str, str] = {}
        self.last_warnings: List[str] = []

    def extract(self, text: str) -> Tuple[Dict[str, object], Dict[str, str], List[str]]:
        self.last_dropped, self.last_warnings = {}, []
        # Heuristic luôn chạy: vá fact LLM hay bỏ sót (vd. cầm điện thoại ngoài closed-vocab cũ).
        heur_facts, heur_ev, heur_raw = HeuristicExtractor().extract(text)
        data = _parse(self.llm.complete(system=SYSTEM, user=text))
        if not data:
            return heur_facts, heur_ev, heur_raw
        facts, evidences, dropped = _verify(_as_fact_map(data.get("facts")), text)
        facts, ground_warns = ground(facts)  # grounding chống ảo giác / node lạ
        for key, value in heur_facts.items():
            if key not in facts:
                facts[key] = value
                if key in heur_ev:
                    evidences[key] = heur_ev[key]
        facts, ground_warns2 = ground(facts)
        self.last_dropped = dropped
        self.last_warnings = ground_warns + ground_warns2
        evidences = {k: v for k, v in evidences.items() if k in facts}
        raw = _as_events(data.get("raw_events"))
        for e in heur_raw:
            if e not in raw:
                raw.append(e)
        return facts, evidences, raw
