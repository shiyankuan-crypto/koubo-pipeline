#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
口播选题五维评分计算器
用法：
    python3 score.py --topic 4 --controversy 4 --barrier 4 --timeliness 5 --compliance 4
    python3 score.py -t 4 -c 4 -b 4 -ti 5 -co 4 --name "ETF资金流选题"
不传参数则进入交互式输入。
"""

import argparse
import sys

# 五维权重：合规风险为反向计分，用 (6 - 分) 折算
WEIGHTS = {
    "topic":       0.25,  # 话题度
    "controversy": 0.20,  # 争议性
    "barrier":     0.15,  # 专业门槛
    "timeliness":  0.20,  # 时效性
    "compliance":  0.20,  # 合规风险（反向）
}

NAMES = {
    "topic":       "话题度",
    "controversy": "争议性",
    "barrier":     "专业门槛",
    "timeliness":  "时效性",
    "compliance":  "合规风险(反向)",
}


def score_one(key, value):
    """单维度折算分：合规风险反向计分，其余直接用原分"""
    if not 1 <= value <= 5:
        raise ValueError(f"{NAMES[key]} 分数必须是 1-5，收到 {value}")
    return (6 - value) if key == "compliance" else value


def evaluate(scores):
    """计算加权总分并给出决策"""
    total = sum(score_one(k, v) * WEIGHTS[k] for k, v in scores.items())

    # 合规一票否决：合规分=1 视为无法规避的高风险
    if scores["compliance"] <= 1:
        decision = "❌ 否决"
        reason = "合规分=1，触发一票否决。除非能改写规避，否则放弃该选题。"
        return total, decision, reason

    if total >= 4.0:
        decision = "✅ 立即排期"
        reason = "综合评分达标，优先做，配最好的钩子。"
    elif total >= 3.0:
        # 提级例外：时效性满分且合规安全，窗口期选题可以提级
        if scores["timeliness"] == 5 and scores["compliance"] >= 4:
            decision = "✅ 立即排期（提级）"
            reason = "3.0-3.9 分，但时效性满分且合规安全，窗口期选题过期即失效，提级排期。"
        else:
            decision = "⏸ 进池观察"
            reason = "中等选题。等新数据出现，或换个切入角度再评一次。"
    else:
        decision = "🚫 放弃"
        reason = "低于 3.0，不占用产能。"

    if scores["compliance"] == 2:
        reason += " ⚠ 合规分=2，出稿前必须走改写流程。"

    return total, decision, reason


def ask_interactive():
    """交互式输入五维分数"""
    print("请为选题打分（1-5 分，1=低，5=高；合规风险 5=无风险，1=高风险）")
    scores = {}
    hints = {
        "topic":       "话题度（小圈子自嗨=1，破圈=5）",
        "controversy": "争议性（结论唯一=1，两派对立=5）",
        "barrier":     "专业门槛（太难讲不清=1，一句话点破=5）",
        "timeliness":  "时效性（长期有效=1，48小时内=5）",
        "compliance":  "合规风险（高风险=1，无风险=5）",
    }
    for key in WEIGHTS:
        while True:
            raw = input(f"  {hints[key]}：").strip()
            try:
                val = int(raw)
                if 1 <= val <= 5:
                    scores[key] = val
                    break
            except ValueError:
                pass
            print("    请输入 1-5 的整数")
    return scores


def main():
    parser = argparse.ArgumentParser(description="口播选题五维评分计算器")
    parser.add_argument("-t",  "--topic",       type=int, help="话题度 1-5")
    parser.add_argument("-c",  "--controversy", type=int, help="争议性 1-5")
    parser.add_argument("-b",  "--barrier",     type=int, help="专业门槛 1-5")
    parser.add_argument("-ti", "--timeliness",  type=int, help="时效性 1-5")
    parser.add_argument("-co", "--compliance",  type=int, help="合规风险 1-5（5=无风险）")
    parser.add_argument("-n",  "--name",        type=str, default="未命名选题", help="选题名称")
    args = parser.parse_args()

    provided = {
        "topic":       args.topic,
        "controversy": args.controversy,
        "barrier":     args.barrier,
        "timeliness":  args.timeliness,
        "compliance":  args.compliance,
    }

    # 参数没给全就转交互式
    if any(v is None for v in provided.values()):
        print(f"选题：{args.name}")
        scores = ask_interactive()
    else:
        scores = provided

    try:
        total, decision, reason = evaluate(scores)
    except ValueError as e:
        print(f"输入错误：{e}")
        sys.exit(1)

    print("\n" + "=" * 46)
    print(f"选题：{args.name}")
    print("=" * 46)
    for key in WEIGHTS:
        raw = scores[key]
        conv = score_one(key, raw)
        mark = "→ 折算" if key == "compliance" else "     "
        print(f"{NAMES[key]:<14} 原始 {raw} 分 {mark} {conv} 分 × 权重 {WEIGHTS[key]:.2f} = {conv * WEIGHTS[key]:.2f}")
    print("-" * 46)
    print(f"加权总分：{total:.2f}")
    print(f"决策：{decision}")
    print(f"依据：{reason}")
    print("=" * 46)


if __name__ == "__main__":
    main()
