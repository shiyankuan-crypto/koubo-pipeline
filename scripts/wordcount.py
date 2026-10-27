#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
口播稿校验器：净字数 / 预估时长 / 长句检查 / 标注完整性 / 合规初筛

用法：
    python3 wordcount.py draft.md
    python3 wordcount.py draft.md --rate 5.5
    cat draft.md | python3 wordcount.py -

说明：
- 剥离停顿符号 ｜‖⏸ 与语气标注【...】后再统计净字数
- 整行只有【...】的行视为阶段标记行（如【① 钩子｜0-3秒｜语速正常】），不计入正文
- 语速默认 5.5 字/秒，同时给出 4.5 和 6.0 的区间
"""

import argparse
import re
import sys

# 停顿符号：短停、中停、长停
PAUSE_CHARS = "｜‖⏸|"
# 语气标注：【重音】【升调】等，整块剥离（内层不含【】，支持嵌套场景循环剥离）
TONE_PATTERN = re.compile(r"【[^【】]*】")
# 中文标点与空白，统计净字数时剔除
PUNCT = re.compile(r"[\s，。、？！；：,.\?!;:\"'`~·—\-…（）()《》【】\[\]]")
# 气口切分：口语里每个逗号之间就是一次呼吸，按标点切而非只按句号
SENT_SPLIT = re.compile(r"[，。？！\n；;、]")

# 合规高危词（命中即提示人工复核）
RISK_WORDS = [
    "保本", "稳赚", "翻倍", "暴富", "必涨", "包赚", "无风险",
    "内部消息", "独家爆料", "加微信", "私信我", "加我", "领资料",
    "推荐买入", "建议买入", "满仓", "梭哈", "抄底", "目标价", "看到",
]
# 免责声明关键词
DISCLAIMER = ["不构成投资建议", "不构成任何投资建议", "不代表普遍收益", "仅作信息分享"]


def strip_tone(text):
    """循环剥离语气标注，兼容【...【慢】...】这类嵌套"""
    prev = None
    while prev != text:
        prev = text
        text = TONE_PATTERN.sub("", text)
    return text


def strip_markup(line):
    """去掉语气标注与停顿符号，返回纯正文"""
    text = strip_tone(line)
    for ch in PAUSE_CHARS:
        text = text.replace(ch, "")
    return text


def is_stage_line(line):
    """整行是阶段标记（如【① 钩子｜0-3秒｜语速正常】）则跳过，不计入正文与长句检查"""
    s = line.strip()
    return s.startswith("【") and s.endswith("】") and "。" not in s


def clean_count(text):
    """剔除标点空白后的字符数"""
    return len(PUNCT.sub("", text))


def check(path, rate):
    if path == "-":
        raw = sys.stdin.read()
    else:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()

    lines = raw.split("\n")
    body_lines = []
    stage_lines = 0

    for line in lines:
        if is_stage_line(line):
            stage_lines += 1          # 阶段标记行，不计入正文
            continue
        body_lines.append(strip_markup(line))

    body = "\n".join(body_lines)
    net = clean_count(body)

    # 时长估算
    mid = net / rate if rate else 0
    slow = net / 4.5
    fast = net / 6.0

    print("=" * 52)
    print("口播稿校验报告")
    print("=" * 52)
    print(f"阶段标记行：{stage_lines} 行（已排除，不计字数）")
    print(f"净字数：{net} 字")
    print(f"预估时长（{rate} 字/秒）：{mid:.0f} 秒")
    print(f"时长区间：{fast:.0f} 秒（快 6.0）～ {slow:.0f} 秒（慢 4.5）")

    # 时长区间判定（60-90 秒对应 270-540 字）
    print("\n【时长判定】")
    if net < 270:
        print(f"  ⚠️ {net} 字偏少，撑不满 60 秒（需 270 字以上）。建议加 1 个证据点或 1 个类比")
    elif net <= 540:
        print(f"  ✅ {net} 字落在 60-90 秒区间（270-540 字）")
    elif net <= 700:
        print(f"  ⚠️ {net} 字偏多，90 秒念不完。建议删 1 个证据点或 1 个类比")
    else:
        print(f"  ❌ {net} 字属于 2-3 分钟中视频量级，不能塞进 60-90 秒。请拆分上下集")

    # 长句检查
    print("\n【长句检查】（单个气口 >20 字需断句，按逗号/句号切分）")
    long_sentences = []
    for seg in SENT_SPLIT.split(body):
        n = clean_count(seg)
        if n > 20:
            long_sentences.append((n, seg.strip()))
    if long_sentences:
        for n, s in sorted(long_sentences, reverse=True):
            print(f"  ⚠️ {n} 字：{s[:50]}")
        print(f"  共 {len(long_sentences)} 句超标")
    else:
        print("  ✅ 全部句子 ≤20 字")

    # 标注完整性（在原文上检查，正文已被剥离标注）
    print("\n【标注完整性】")
    has_pause = any(ch in raw for ch in "｜‖⏸")
    has_tone = bool(TONE_PATTERN.search(raw))
    print(f"  {'✅' if has_pause else '❌'} 停顿标注 ｜/‖/⏸")
    print(f"  {'✅' if has_tone else '❌'} 语气标注 【重音】【升调】等")
    if not (has_pause and has_tone):
        print("  → 标注缺失，稿子不算完成")

    # 合规初筛
    print("\n【合规初筛】（命中需人工复核，不自动判定违规）")
    hits = [w for w in RISK_WORDS if w in body]
    if hits:
        for w in hits:
            print(f"  ⚠️ 命中高危词：{w}")
        print("  → 逐条走 references/compliance.md 复核")
    else:
        print("  ✅ 未命中高危词")

    has_disc = any(d in body for d in DISCLAIMER)
    print(f"  {'✅' if has_disc else '❌'} 免责声明（需含「不构成投资建议」等）")
    if not has_disc:
        print("  → 财经与 Web3 类必带，口播版 + 字幕版双份")

    print("=" * 52)


def main():
    parser = argparse.ArgumentParser(description="口播稿校验器")
    parser.add_argument("file", help="口播稿文件路径，- 表示从 stdin 读")
    parser.add_argument("--rate", type=float, default=5.5, help="语速，字/秒，默认 5.5")
    args = parser.parse_args()

    if args.rate <= 0:
        print("语速必须大于 0")
        sys.exit(1)

    try:
        check(args.file, args.rate)
    except FileNotFoundError:
        print(f"文件不存在：{args.file}")
        sys.exit(1)


if __name__ == "__main__":
    main()
