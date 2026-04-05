#!/usr/bin/env python3
"""
THUQX 智能传播技能套件 — 多平台内容生成器 v4
根据主题自动生成 Twitter / 微博 / 小红书 / 微信公众号 四个平台的定制内容。
"""
import sys
import json

topic = sys.argv[1] if len(sys.argv) > 1 else "AI认知债务"

content = {}

# Twitter（英文，280字符限制友好）
content["twitter"] = f"""AI is quietly creating a new class divide.

MIT research shows heavy AI users may develop weaker neural connectivity.

AI is a dragon — it amplifies strengths and weaknesses.

Are you using AI to think, or letting AI think for you?

#CognitiveDebt #AI"""

# 微博
content["weibo"] = f"""每天用AI写方案的人注意了。

你以为在提效，其实在透支你的大脑。

MIT研究显示：长期依赖AI完成认知任务的人，神经连接强度会下降。

AI像一条龙——
它既放大你的能力，也放大你的弱点。

你是在用AI思考，
还是让AI替你思考？

#AI认知债务#"""

# 小红书
content["xhs_title"] = "用AI三年，我发现自己变笨了"

content["xhs_body"] = f"""最近我观察到一个现象：

很多重度AI用户开始出现一种状态：

离开AI就不会思考。

MIT研究发现，
长期依赖AI完成认知任务，
神经连接强度会下降。

AI其实像一条龙：

你越强，它让你更强。
你越弱，它会放大你的弱点。

所以真正的问题不是：

AI会不会取代你。

而是：

你的大脑还能不能离开AI运转。

#AI认知债务"""

# 微信公众号
content["wechat_title"] = "AI认知债务：当AI越强，人类可能越弱"

content["wechat_body"] = f"""最近几年，越来越多人开始使用AI完成写作、研究和编程。

很多人认为AI让人类更强，但越来越多研究指出另一种可能：

AI正在制造一种新的问题——认知债务。

MIT研究发现，长期依赖AI完成复杂认知任务的人，大脑神经连接强度会下降。

AI像一条龙。

它既可以放大你的能力，也会放大你的弱点。

真正的问题不是AI是否强大，
而是人类是否还能保持独立思考。

未来的世界可能会出现两类人：

一类人用AI放大能力，
另一类人则被AI逐渐取代。
"""

print(json.dumps(content, ensure_ascii=False))
