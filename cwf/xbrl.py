"""Flatten an XBRL instance document into numeric facts, keeping explicit dimensions.

Names are local (prefix stripped): concept "Revenue", dims {("SegmentsAxis", "GameAndNetworkServicesMember")}.
Text facts, nil facts, and facts without a context are dropped.
"""
from dataclasses import dataclass
from datetime import date
import xml.etree.ElementTree as ET

XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"


@dataclass(frozen=True)
class Fact:
    concept: str
    value: float | None
    unit: str | None
    start: date | None
    end: date
    dims: frozenset
    decimals: str | None


def _local(tag_or_qname: str) -> str:
    if "}" in tag_or_qname:
        return tag_or_qname.rsplit("}", 1)[1]
    return tag_or_qname.rsplit(":", 1)[-1]


def _date(text: str) -> date:
    return date.fromisoformat(text.strip()[:10])


def _contexts(root):
    out = {}
    for c in root.iter():
        if _local(c.tag) != "context":
            continue
        start = end = None
        dims = []
        for e in c.iter():
            name = _local(e.tag)
            if name == "startDate":
                start = _date(e.text)
            elif name in ("endDate", "instant"):
                end = _date(e.text)
            elif name == "explicitMember":
                dims.append((_local(e.get("dimension")), _local(e.text.strip())))
        if end is not None:
            out[c.get("id")] = (start, end, frozenset(dims))
    return out


def _units(root):
    out = {}
    for u in root.iter():
        if _local(u.tag) != "unit":
            continue
        measures = [_local(m.text.strip()) for m in u.iter() if _local(m.tag) == "measure"]
        out[u.get("id")] = "/".join(measures) if measures else None
    return out


def parse_instance(xml: bytes) -> list[Fact]:
    root = ET.fromstring(xml)
    ctx, units = _contexts(root), _units(root)
    facts = []
    for el in root:
        cid = el.get("contextRef")
        if cid is None or cid not in ctx or el.get(XSI_NIL) == "true":
            continue
        text = (el.text or "").strip()
        try:
            value = float(text)
        except ValueError:
            continue
        start, end, dims = ctx[cid]
        facts.append(Fact(_local(el.tag), value, units.get(el.get("unitRef")), start, end, dims, el.get("decimals")))
    return facts
