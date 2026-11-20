PHI = 2.0


def find_misalignments(a, b, phi=PHI):
    flags = []
    for item in sorted(set(a["items"]) & set(b["items"])):
        x, y = a["items"][item], b["items"][item]
        for src, dst, sp, dp in ((x, y, a["party"], b["party"]), (y, x, b["party"], a["party"])):
            for w in src["含"]:
                if w in dst["含"]:
                    continue
                reason = "明確排除" if w in dst["不含"] else "未提及"
                flags.append(("範圍錯位", item, w, sp, dp, reason))
        lo, hi = sorted((x["估時_天"], y["估時_天"]))
        if hi / lo > phi:
            flags.append(("估時分歧", item, f"{lo}天 vs {hi}天"))
    return flags
