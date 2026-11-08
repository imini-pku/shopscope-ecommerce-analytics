# 业务问题与分析范围

## 商品发现与购买路径

TikTok Shop将短视频、直播中的商品发现与站内购买结合起来，相关产品机制见[官方2025年3月31日介绍](https://newsroom.tiktok.com/discover-tiktok-shop/?lang=en-GB)。本项目选择“下一商品发现”和“从浏览到购买”两个可由公开行为日志研究的问题。

Retailrocket不包含视频、达人或推荐曝光字段，因此本项目研究一般电商行为与离线推荐方法，不将数据中的比例解释为TikTok Shop或欧洲市场的表现。

## 策略假设

在商品详情页，根据用户当前浏览商品提供关联候选，相比统一热门列表，可能有助于继续发现商品。项目使用冻结的训练窗口比较两种策略，并以相同有标签预测点和候选目录计算离线命中率及覆盖率。

## 观察结果与后续验证

测试期共同浏览HR@10为18.27%，热门基线为0.22%；共同浏览完全回退热门的比例为37.93%。结果支持将关联推荐保留为实验候选，同时继续检查冷启动与商品时效性。离线浏览预测优势不代表购买因果增量，真实上线决策仍需用户级随机实验。

本项目已提供实验方案及独立模拟结果。实验分析先检查分流与数据完整性，再解释主指标和护栏；分流异常的诊断原则可参考[Microsoft相关研究，2019年7月](https://www.microsoft.com/en-us/research/publication/diagnosing-sample-ratio-mismatch-in-online-controlled-experiments-a-taxonomy-and-rules-of-thumb-for-practitioners/)。
