# ShopScope · 电商行为与推荐分析

以 Retailrocket 完整公开行为数据为基础，连接 **SQL 数据质量 → 购物路径 → 推荐离线评估 → 实验设计 → 可交互报告**。面向数据科学求职展示，使用 Python、DuckDB SQL 与原生 HTML/JavaScript。

**数据：2,756,101 条事件，1,407,580 位匿名访客，2015-05-03 至 2015-09-18 UTC。** 2026年11月完成本次分析。

## 先看成果

- [在线交互看板](https://imini-pku.github.io/shopscope-ecommerce-analytics/) / [离线页面](app/index.html)：支持日期筛选、事件切换与验证/测试比较。
- [两页分析报告](reports/ShopScope_分析报告.pdf) / [A/B 实验设计](reports/ShopScope_AB实验设计.pdf)
- [完整结果与检查](reports/metrics.json) / [指标与评估方法](docs/methodology.md) / [5分钟演示说明](docs/demo_walkthrough.md)
- [业务问题与分析范围](docs/business_context.md)
- [完整下载包（含原始事件数据）](https://github.com/imini-pku/shopscope-ecommerce-analytics/releases/latest)

## 主要结果

| 观察 | 实测结果 | 对决策的作用 |
|---|---:|---|
| 完全重复记录 | 460 条 | 精确去重，保留不同时刻的真实重复行为 |
| 同次访问、同商品浏览后购买 | 0.740% | 描述行为路径，不把未记录的曝光当作分母 |
| 严格浏览→加购→购买 | 0.635% | 统一先后关系与计数单位 |
| 测试集共同浏览 HR@10 | 18.27% | 比较下一不同商品浏览的预测能力 |
| 测试集全局热门 HR@10 | 0.22% | 固定简单基线，方便复查 |
| 共同浏览完全回退热门 | 37.93% | 关联覆盖不足，需要新商品和冷启动策略 |

测试集有 28,166 个带后续浏览标签的预测点。两方法使用相同分母，未知商品仍计入未命中。按访客聚类的配对自助法显示 HR@10 差异为 **18.05 个百分点**。这项离线结果支持继续验证关联推荐，不代表实际订单增长或线上因果效果。

## 完整复现

需要 Python 3.10+，建议 4GB 以上可用内存。完整 Release 包已包含 `.local-data/events.csv`；普通源码下载可从原发布方取得该文件：

```bash
python -m pip install -r requirements.txt
python src/download_data.py
python -m unittest discover -s tests -v
python src/pipeline.py
python app/build_dashboard.py
```

已含数据时跳过下载步骤。原始 CSV 约 94MB。Release另提供完整DuckDB分析数据库，含清洗事件、会话、训练商品关系、逐预测点候选及评估明细，可直接查表；也可由脚本重建。输入文件经过 SHA-256 校验，报告、看板和所有指标均由同一份结果生成。

可选重建 PDF：`python -m pip install -r requirements-report.txt` 后运行 `python src/build_reports.py`。字体优先使用本机中文字体，否则使用 PDF 中文标准字体。

## 项目文件

| 目录 | 内容 |
|---|---|
| `sql/` | 12个可运行 SQL 文件：校验、清洗、用户表、会话、漏斗、分层、关联检查、推荐与评估 |
| `src/` | 原始数据下载、全量计算、报告生成 |
| `tests/` | 清洗与推荐协议的边界测试 |
| `reports/` | 实测 JSON/CSV、检查结果、分析报告与实验设计 |
| `app/` | 完整看板源码、构建脚本与离线页面 |
| `docs/` | 字段、指标、方法与演示流程 |

## 数据来源与分析范围

数据来源为 [Retailrocket 原发布页](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset)，原发布方标注 **CC BY-NC-SA 4.0**；下载包保留完整来源与许可说明。数据与衍生分析遵循该许可，原创代码采用 MIT，详见 [LICENSE](LICENSE) 和 [DATA_LICENSE.md](DATA_LICENSE.md)。

本项目基于公开历史日志完成分析。数据不含推荐曝光、价格、国家、达人或补贴字段，因此不报告曝光 CTR、GMV、欧洲市场表现或实际线上实验收益。
