"""核对 设计决策案例_D01.md 里引用的原句：逐字在本地全文文本里查找（忽略空白、连字符、连字差异），报告页码。

用法：python verify_case_quotes.py <全文文本目录> <案例补证文本目录>
"""
import re
import sys
import unicodedata
from pathlib import Path

QUOTES = [
    ('R1', 'The coating layer can inhibit electrolyte decomposition and improve interfacial stability by blocking electron conduction between carbon and electrolyte'),
    ('R1', 'Two diﬀerent synthetic routes for sulfur cathodes are shown in Figure 1b, in which ALD-derived LPO is deposited on the surface of acetylene black (AB) and AB/sulfur (AB/S), respectively'),
    ('R1', 'The initial discharge capacities of AB/S, LPO@AB- S, and LPO@AB/S cathode are 1247, 1136, and 1322 mAh g−1, respectively'),
    ('R1', 'leaving low reversible capacities of 859 and 665 mAh g−1, corresponding to 72.5% and 59.4% capacity retention'),
    ('R1', 'LPO@AB/S retains a high discharge capacity of 1070 mAh g−1 with a capacity retention of 86.4%'),
    ('R1', 'The commercial Li7P3S11 (LPS) SSE was mixed with AB/S, LPO@AB-S and LPO@AB/S'),
    ('R1', 'LPO coating reduces the electronic conductivity of the cathode composites'),
    ('R2', 'Considering the surface area of VGCF was very low, the contact area between sulfur and VGCF was limited'),
    ('R2', 'Compared to the vapor grown carbon fibers, the ASSLSBs using PAN'),
    ('F1', 'leaving only one'),
    ('F5', 'has only 29% of its initial capacity left'),
    ('F5', 'reduces the drop in capacity, so that after 50 cycles 52% of the'),
]


def norm(s):
    return re.sub(r'[\s\-‐‑‒–—―−­]', '', unicodedata.normalize('NFKC', s)).lower()


def load(path):
    buf, spans, pos, cur = [], [], 0, None
    for part in re.split(r'(=== 第 \d+ 页 ===)', path.read_text(encoding='utf-8')):
        m = re.fullmatch(r'=== 第 (\d+) 页 ===', part)
        if m:
            cur = int(m.group(1))
            continue
        s = norm(part)
        buf.append(s)
        spans.append((pos, pos + len(s), cur))
        pos += len(s)
    return ''.join(buf), spans


def main(ft_dir, case_dir):
    texts = {}
    for d in (Path(ft_dir), Path(case_dir)):
        for p in d.glob('*.txt'):
            texts[p.stem] = load(p)
    ok = 0
    for key, q in QUOTES:
        s, spans = texts[key]
        i = s.find(norm(q))
        pg = next((p for a, b, p in spans if a <= i < b), None) if i >= 0 else None
        ok += i >= 0
        print(f"{'找到' if i >= 0 else '未找到'}｜{key} 第 {pg} 页｜{q[:70]}")
    print(f'\n合计：{ok}/{len(QUOTES)} 条找到')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
