"""Create concise Chinese PDF reports directly from frozen metrics.json."""
from pathlib import Path
import json, math
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit

ROOT=Path(__file__).resolve().parents[1]
M=json.loads((ROOT/'reports/metrics.json').read_text(encoding='utf-8'))
FONT='ReportChinese'
for fp in [Path('C:/Windows/Fonts/simhei.ttf'),Path('/usr/share/fonts/truetype/arphic/uming.ttc')]:
    if fp.exists():
        pdfmetrics.registerFont(TTFont(FONT,str(fp)));break
else:
    FONT='STSong-Light';pdfmetrics.registerFont(UnicodeCIDFont(FONT))
INK='#172E45';MUTED='#506377';BLUE='#176D99';TEAL='#168778';LIGHT='#EDF4F8'

def text(c,x,y,s,size=10,color=INK):
    c.setFillColor(HexColor(color));c.setFont(FONT,size);c.drawString(x,y,str(s))

def wrap(c,s,y,size=10,width=499,leading=17,color=INK):
    # Character wrapping works for Chinese and embedded Latin labels.
    line=''
    for ch in s:
        if ch=='\n' or pdfmetrics.stringWidth(line+ch,FONT,size)>width:
            text(c,48,y,line,size,color);y-=leading;line=''
        if ch!='\n':line+=ch
    if line:text(c,48,y,line,size,color);y-=leading
    return y

def head(c,label,title,sub,page,total):
    c.setFillColor(HexColor(BLUE));c.rect(0,831,595,11,fill=1,stroke=0)
    text(c,48,793,label,9,TEAL);text(c,48,754,title,25)
    text(c,48,727,sub,9,MUTED)
    c.setStrokeColor(HexColor('#DCE5EB'));c.line(48,710,547,710)
    text(c,48,30,'ShopScope | Tianxiong Wu | 2026-11-08',8,MUTED)
    text(c,504,30,f'{page} / {total}',8,MUTED)

def section(c,label,y):text(c,48,y,label,13,BLUE);return y-26
def metric(c,x,y,value,label):
    c.setFillColor(HexColor(LIGHT));c.roundRect(x,y-64,159,78,7,fill=1,stroke=0)
    text(c,x+13,y-12,value,21);text(c,x+13,y-40,label,9,MUTED)
def bar(c,label,value,maxv,x,y,w=300,color=TEAL,unit='%'):
    text(c,48,y+3,label,10);c.setFillColor(HexColor(LIGHT));c.rect(x,y,w,15,fill=1,stroke=0)
    c.setFillColor(HexColor(color));c.rect(x,y,max(w*value/maxv,1),15,fill=1,stroke=0)
    text(c,x+w+10,y+3,f'{value:.2f}{unit}',10)

def report():
    p=ROOT/'reports/ShopScope_分析报告.pdf';c=canvas.Canvas(str(p),pagesize=(595,842));c.setTitle('ShopScope 电商行为与推荐分析')
    head(c,'DATA ANALYSIS / 01','从购物行为到推荐候选','Retailrocket 全量公开日志 · SQL / Python / DuckDB · AI辅助实现',1,2)
    metric(c,48,671,'275.61万','原始事件记录');metric(c,218,671,'140.76万','匿名访客');metric(c,388,671,'176.17万','按30分钟间隔划分的访问')
    y=section(c,'01  核心判断',565)
    y=wrap(c,'共同浏览比全局热门更能预测下一件被浏览的商品，适合作为推荐候选继续验证；但约38%的测试预测点完全回退热门，覆盖与商品时效性仍是优先问题。历史日志中的较高命中率不足以直接决定上线。',y)
    y=wrap(c,'业务连接：内容电商连接商品发现与站内购买，本项目据此练习“下一商品发现→购买”的分析链。平台机制参考TikTok官方2025-03-31介绍，原文链接见docs/interview_notes.md；本数据不用于推断欧洲市场表现。',y-3,size=9,leading=15,color=MUTED)
    y=section(c,'02  数据口径先于业务解释',y-15)
    y=wrap(c,'完整读取2,756,101条事件，删除460条五字段完全重复记录，保留不同时刻的重复浏览；清洗后2,755,641条，非法记录0条。建立用户与访问表，并检查主键、关联前后行数与孤立记录。观测期间为2015年5月3日至9月18日（UTC）。',y)
    y=section(c,'03  从浏览到购买：以同一商品、同次访问计数',y-16)
    f=M['funnel'];bar(c,'浏览后加购',100*f['view_to_add_rate'],2.1,176,y-20,w=285)
    bar(c,'浏览后购买',100*f['view_to_purchase_rate'],2.1,176,y-51,w=285)
    bar(c,'严格三步',100*f['strict_rate'],2.1,176,y-82,w=285)
    y=wrap(c,'共同分母为2,330,774个有浏览的“访客-访问-商品”配对。严格三步要求浏览、加购、购买按毫秒严格递增；加购与购买同毫秒不认定为先后。图中比例不是曝光CTR，也不是全站订单转化率。',y-110,size=9,leading=15,color=MUTED)
    y=section(c,'04  行动建议',y-12)
    y=wrap(c,'先审查跨访问购买、缺失加购与事件埋点，再决定是否把某一步视为流失。已有历史访问的浏览会话购买比例约1.51%，首次观测访问约0.49%；建议进一步分解活跃程度与商品结构，而非把差异直接归因于回访。',y)
    wrap(c,'来源：Retailrocket / Kaggle，CC BY-NC-SA 4.0。原始数据和全部SQL在完整下载包保留；指标、方法与校验见仓库reports/及docs/。',78,size=8,leading=12,color=MUTED)
    c.showPage()
    head(c,'RECOMMENDATION / 02','离线结果如何支持下一步','模型冻结于2015-08-01之前 · 8月验证 · 9月测试',2,2)
    test={r['method']:r for r in M['recommendation'] if r['split']=='test'}
    y=section(c,'05  同一测试集上的推荐比较',674)
    bar(c,'共同浏览',100*test['coview']['hit_rate_at_10'],20,176,y-15,w=285)
    bar(c,'全局热门',100*test['popular']['hit_rate_at_10'],20,176,y-49,w=285,color=BLUE)
    diff=next(d for d in M['paired_comparison'] if d['split']=='test')
    y=wrap(c,f"28,166个有标签预测点；共同浏览命中5,147次，全局热门命中63次。配对差异为{diff['difference_pp']:.2f}个百分点，按访客聚类自助法95%区间为[{diff['ci_low_pp']:.2f}, {diff['ci_high_pp']:.2f}]个百分点。",y-80)
    y=section(c,'06  为什么这个比较可复查',y-14)
    y=wrap(c,'只用训练期会话构建商品共现与热门排序。每次留出访问第一次浏览时预测下一次严格更晚的不同商品；两方法均推荐10件、去重且排除当前商品。3,166个未见商品标签仍留在分母。验证标签不跨入测试期，模型不按测试结果调参。',y)
    y=wrap(c,'测试期200,912个预测点中只有28,166个带合规后续标签，结果描述这一子样本的下一商品预测。候选目录固定为199,510件训练商品；共同浏览推荐覆盖10.17%，完全回退热门37.93%。与8月相比测试命中率下降，应优先检查新商品与行为漂移。',y-6)
    y=section(c,'07  实验演示给出的决定：暂不支持上线',y-14)
    e=M['experiment'];y=wrap(c,f"独立模拟100,000名用户，分流检查p={e['srm_pvalue']:.3f}；对照购买比例{e['control_rate']:.3%}，处理{e['treatment_rate']:.3%}。差异{e['difference_pp']:.3f}个百分点，95%区间[{e['ci_low_pp']:.3f}, {e['ci_high_pp']:.3f}]包含0。客服接触率护栏未触发，但转化证据不足，不作上线判断。",y)
    y=wrap(c,f"以2.5%为假设基线、识别0.15个百分点差异、双侧5%显著性和80%功效，规划约{e['sample_size_per_arm']:,}人/组；本次模拟规模低于该目标。真实验证需按用户稳定随机、固定观察窗口，并在实验前锁定指标和停止规则。",y-5)
    y=section(c,'08  可交付与复现',y-14)
    wrap(c,'12个SQL文件、全量质量检查、边界测试、原始数据校验值、交互看板、逐项结果表及一页实验设计。源代码由Codex辅助实现，输出已按固定口径计算和检查。没有使用TikTok内部数据，也未实施真实线上实验。',y)
    c.save();return p

def experiment():
    p=ROOT/'reports/ShopScope_AB实验设计.pdf';c=canvas.Canvas(str(p),pagesize=(595,842));c.setTitle('ShopScope A/B实验设计与模拟结果')
    head(c,'EXPERIMENT DESIGN','关联推荐：验证方案与模拟判读','设计练习 · 所有概率和规模均为模拟假设 · 非已实施线上实验',1,1)
    e=M['experiment']; y=675
    blocks=[
    ('业务假设与干预','在商品详情页相关推荐位置，使用共同浏览候选替代全局热门，能提高7日购买用户比例，同时不增加客服负担。保持UI、推荐条数和其他流量规则一致。'),
    ('分流与观察窗口','对象为首次符合资格并触发推荐位置的用户；按稳定用户ID进行1:1随机，保留所有分配用户作意向处理分析。用户跨设备需先定义统一ID；无法统一时记录污染风险。每人观察7日，最后入组后再等7日成熟。'),
    ('指标与护栏','主指标：7日内至少一次支付成功的分配用户数 / 全部分配用户数。护栏：7日内至少一次客服接触的分配用户比例；处理-对照的95%上界不得超过+0.10个百分点。另检查退款、延迟、库存和曝光日志完整性；未有数据时不宣称通过。'),
    ('样本量与停止规则',f"假设基线2.5%，最小可识别差异+0.15个百分点，双侧α=0.05、功效80%。两比例正态近似规划{e['sample_size_per_arm']:,}人/组；至少覆盖完整周周期且达到目标样本，预设一次终点分析，不根据中途显著性提前停止。"),
    ('质量与判读','先检查1:1分流偏离（SRM）及分组前特征、丢失日志、重复ID和窗口成熟情况。主效应报告绝对百分点差和95%区间，结合业务价值与全部护栏。若事后探索多个分层，标为探索并另行验证，不挑显著分组。'),
    ('本次固定种子的模拟结果',f"种子20261108；对照{e['control_users']:,}人、处理{e['treatment_users']:,}人。购买差异{e['difference_pp']:.3f}个百分点，95%区间[{e['ci_low_pp']:.3f}, {e['ci_high_pp']:.3f}]；SRM p={e['srm_pvalue']:.3f}；客服差异上界{e['support_ci_high_pp']:.3f}个百分点。结论：主效应证据不足，不支持上线；本模拟只演示流程。")]
    for label,body in blocks:
        y=section(c,label,y);y=wrap(c,body,y,size=9.5,leading=16)-11
    wrap(c,'样本量公式：n = [1.960*sqrt(2*p_bar*(1-p_bar)) + 0.842*sqrt(p0*(1-p0)+p1*(1-p1))]^2 / (p1-p0)^2，p_bar为两组假设概率的平均值，最终向上取整。\n实现、输入参数和结果：src/pipeline.py / reports/simulated_experiment.csv。',y,size=8,leading=13,color=MUTED)
    c.save();return p

if __name__=='__main__':
    print(report());print(experiment())
