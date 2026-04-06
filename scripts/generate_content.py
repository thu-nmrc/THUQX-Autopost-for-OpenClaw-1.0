#!/usr/bin/env python3
"""
根据主题生成四平台文案，输出 JSON 到 stdout（供 run_social_publish_v5.sh 解析）。
与 OpenClaw skill zeelin-social-autopublisher 内脚本保持一致。
"""
import json
import sys

topic = sys.argv[1] if len(sys.argv) > 1 else "AI认知债务"

content = {}

content["twitter"] = f"""You are reading about: {topic}

Hot take:
Most people think AI tools make them smarter.
But the real difference is between people who think WITH AI and those who let AI think for them.

What do you think?

#AI #Tech"""

content["weibo"] = f"""很多人觉得AI让人更聪明。

但现实可能正好相反。

当越来越多人习惯让AI替自己思考时，人与人的差距反而会被放大。

真正会使用AI的人，是用AI放大思考能力的人。

而不是让AI替自己完成思考。

你怎么看？

主题：{topic}
#人工智能 #AI"""

content["xhs_title"] = f"关于「{topic}」，一个被忽视的真相"

content["xhs_body"] = f"""最近越来越多人每天都在用AI。

写方案、写报告、做研究、写代码。

但一个问题开始出现：

如果有一天没有AI，我们还会不会思考？

AI其实像一条龙。

你越强，它会让你更强。

但如果你完全依赖它，它也会放大你的弱点。

真正的差距不是AI能力，而是人的思考能力。

主题：{topic}
#深度思考 #AI"""

content["wechat_title"] = f"{topic}：当工具越强，人该怎么用"

content["wechat_body"] = f"""最近几年，AI工具开始进入越来越多人的工作流程。

写作、研究、数据分析、编程。

很多人认为，AI让人类整体能力提升。

但一个更深层的问题正在出现。

当越来越多人习惯让AI完成思考任务时，人类之间的认知差距反而会被放大。

AI像一条龙。

它既能放大你的能力，也能放大你的弱点。

真正的关键不是AI有多强，而是人类是否还保持独立思考。

未来的世界，很可能分成两类人。

一类人用AI放大思维。

另一类人，被AI逐渐替代。

本文围绕主题：{topic}。
"""

print(json.dumps(content, ensure_ascii=False))
