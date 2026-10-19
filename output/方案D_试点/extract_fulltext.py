"""方案D §9.2 全文表样：把 5 篇论文的正文和 SI 转成带页码的纯文本，供填表和代码核对原句。

用法：python -I extract_fulltext.py <输出目录> <编号>=<PDF路径> [<编号>=<PDF路径> ...]
每个 PDF 输出 <编号>.txt，每页前加一行 "=== 第 N 页 ==="。
"""
import sys
from pathlib import Path

import fitz  # pymupdf，只有 papertrail 环境有


def main(out_dir, pairs):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for pair in pairs:
        key, path = pair.split('=', 1)
        doc = fitz.open(path)
        parts = [f'=== 第 {i} 页 ===\n{page.get_text()}' for i, page in enumerate(doc, 1)]
        (out / f'{key}.txt').write_text('\n'.join(parts), encoding='utf-8')
        print(f'{key}: {len(doc)} 页, {sum(len(p) for p in parts):,} 字符')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
