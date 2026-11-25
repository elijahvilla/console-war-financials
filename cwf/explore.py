"""Dev tool: list every annual gaming-segment fact shape across all filings, to build tag_map.yaml.

python -m cwf.explore sony|microsoft
"""
import re
import sys
from collections import defaultdict

from cwf.filings import list_annual_filings
from cwf.sec import SecClient
from cwf.xbrl import parse_instance

PATTERNS = {"sony": re.compile(r"GameAndNetwork", re.I), "microsoft": re.compile(r"Gaming|XBOX", re.I)}


def main(company: str):
    client = SecClient()
    shapes = defaultdict(list)  # (concept, dims) -> [(fy, accession, value)]
    for f in list_annual_filings(client, company):
        for fact in parse_instance(client.get(f.instance_url)):
            if fact.start is None or not (330 <= (fact.end - fact.start).days <= 380):
                continue
            if not any(PATTERNS[company].search(m) for _, m in fact.dims):
                continue
            if not re.search(r"Revenue|OperatingIncome|ProfitLossFromOperating", fact.concept):
                continue
            shapes[(fact.concept, tuple(sorted(fact.dims)))].append((fact.end.year, f.accession, fact.value))
    for (concept, dims), vals in sorted(shapes.items()):
        years = sorted({v[0] for v in vals})
        print(f"{concept} | {' ; '.join(f'{a}={m}' for a, m in dims)} | FY{years[0]}-FY{years[-1]} n={len(vals)}")
    print(f"network calls: {client.network_calls}")


if __name__ == "__main__":
    main(sys.argv[1])
