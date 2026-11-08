"""Reproduce the full Retailrocket analysis. Run from the repository root."""
from pathlib import Path
import argparse, csv, hashlib, json, math, time
from datetime import datetime, timezone
import duckdb
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SOURCE_SHA256='3745aa83238b1e6d44d8fda209807899f420084398f94ddf745f3cbcfecbf9e7'

def records(con, query):
    result=con.execute(query)
    names=[d[0] for d in result.description]
    return [dict(zip(names,row)) for row in result.fetchall()]

def run_sql(con, name):
    con.execute((ROOT/'sql'/name).read_text(encoding='utf-8'))

def bootstrap_ci(con, split, method, seed=20261108):
    # Resample visitors, keeping all of a visitor's evaluation sessions together.
    a=np.array(con.execute('SELECT sum(hit),count(*) FROM evaluation_detail WHERE split=? AND method=? GROUP BY visitor_id ORDER BY visitor_id',[split,method]).fetchall(),dtype=float)
    rng=np.random.default_rng(seed)
    rates=[]
    for _ in range(600):
        b=a[rng.integers(0,len(a),len(a))]
        rates.append(b[:,0].sum()/b[:,1].sum())
    return [float(x) for x in np.quantile(rates,[.025,.975])]

def paired_bootstrap(con,split):
    a=np.array(con.execute("SELECT visitor_id,sum(CASE WHEN method='coview' THEN hit ELSE -hit END),count(*)/2 FROM evaluation_detail WHERE split=? GROUP BY visitor_id ORDER BY visitor_id",[split]).fetchall(),dtype=float)[:,1:]
    rng=np.random.default_rng(20261108)
    effects=[]
    for _ in range(600):
        b=a[rng.integers(0,len(a),len(a))]
        effects.append(b[:,0].sum()/b[:,1].sum())
    return {'split':split,'difference_pp':float(100*a[:,0].sum()/a[:,1].sum()),'ci_low_pp':float(100*np.quantile(effects,.025)),'ci_high_pp':float(100*np.quantile(effects,.975)),'bootstrap_unit':'visitor','bootstrap_replicates':600}

def simulate_experiment():
    seed=20261108
    rng=np.random.default_rng(seed)
    n=100000
    group=rng.integers(0,2,n)
    conversion=rng.random(n)<np.where(group==0,.025,.0265)
    contacts=rng.random(n)<np.where(group==0,.005,.0053)
    sizes=[int((group==i).sum()) for i in [0,1]]
    rates=[float(conversion[group==i].mean()) for i in [0,1]]
    support=[float(contacts[group==i].mean()) for i in [0,1]]
    diff=rates[1]-rates[0]
    se=math.sqrt(sum(p*(1-p)/n for p,n in zip(rates,sizes)))
    srm=math.erfc(math.sqrt(sum((n-50000)**2/50000 for n in sizes)/2))
    gdiff=support[1]-support[0]
    gse=math.sqrt(sum(p*(1-p)/n for p,n in zip(support,sizes)))
    p0,p1=.025,.0265
    pbar=(p0+p1)/2
    needed=math.ceil((1.959963984540054*math.sqrt(2*pbar*(1-pbar))+0.8416212335729143*math.sqrt(p0*(1-p0)+p1*(1-p1)))**2/(p1-p0)**2)
    return {'label':'独立模拟数据，非线上实验','seed':seed,'control_users':sizes[0],'treatment_users':sizes[1],
        'control_rate':rates[0],'treatment_rate':rates[1],'difference_pp':100*diff,'ci_low_pp':100*(diff-1.96*se),'ci_high_pp':100*(diff+1.96*se),'srm_pvalue':srm,
        'support_control_rate':support[0],'support_treatment_rate':support[1],'support_difference_pp':100*gdiff,'support_ci_high_pp':100*(gdiff+1.96*gse),
        'sample_size_per_arm':needed,'mde_absolute_pp':.15,
        'decision':'模拟转化差异区间包含0，证据不足以支持上线；预设客服接触率+0.10个百分点护栏未触发。此结论仅针对模拟数据。',
        'parameters':{'n_users':n,'allocation':.5,'p_control':.025,'p_treatment':.0265,'support_p_control':.005,'support_p_treatment':.0053}}

def export_csv(path, rows):
    if not rows:return
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--events',type=Path,default=ROOT/'.local-data/events.csv')
    parser.add_argument('--database',type=Path,default=ROOT/'.local-data/shopscope.duckdb')
    parser.add_argument('--analysis-date',default='2026-11-08')
    args=parser.parse_args()
    digest=hashlib.sha256(args.events.read_bytes()).hexdigest()
    if digest!=SOURCE_SHA256:raise ValueError('Source checksum differs; review the new version before running the frozen analysis.')
    args.database.parent.mkdir(parents=True,exist_ok=True)
    con=duckdb.connect(str(args.database));con.execute("SET TimeZone='UTC'; SET threads=4; SET memory_limit='3GB';")
    con.execute("CREATE OR REPLACE TABLE raw_events AS SELECT row_number() OVER() AS source_row,* FROM read_csv(?,header=true,all_varchar=true,parallel=false)",[str(args.events)])
    ms=lambda s:int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()*1000)
    con.execute('CREATE OR REPLACE TABLE config(train_end_ms BIGINT,validation_end_ms BIGINT)')
    con.execute('INSERT INTO config VALUES (?,?)',[ms('2015-08-01'),ms('2015-09-01')])
    timings={}
    for file in sorted((ROOT/'sql').glob('*.sql')):
        start=time.monotonic();run_sql(con,file.name);timings[file.name]=round(time.monotonic()-start,3)
        print(file.name,timings[file.name],flush=True)
    quality=records(con,'SELECT * FROM quality_summary')[0]
    dimensions=records(con,"SELECT count(*) AS clean_rows,count(DISTINCT visitor_id) AS visitors,count(DISTINCT item_id) AS items,min(event_time)::VARCHAR AS date_min,max(event_time)::VARCHAR AS date_max FROM events")[0]
    meta={'project':'ShopScope','source':'Retailrocket公开行为数据','source_url':'https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset','analysis_date':args.analysis_date,
        **quality,**dimensions,'sessions':con.execute('SELECT count(*) FROM sessions').fetchone()[0],
        'duplicates_removed':quality['raw_rows']-quality['invalid_rows']-dimensions['clean_rows'],'data_sha256':digest}
    daily=records(con,'SELECT * FROM daily_metrics ORDER BY date')
    funnel=records(con,'SELECT * FROM funnel_metrics')[0]
    segments=records(con,'SELECT * FROM segment_metrics ORDER BY segment')
    rec=records(con,'SELECT * FROM evaluation_metrics ORDER BY split,method')
    for row in rec:
        row['hits']=int(row['hits'])
        row['hit_ci_low'],row['hit_ci_high']=bootstrap_ci(con,row['split'],row['method'])
    eligibility=records(con,"SELECT p.split,count(*) AS prediction_points,count(q.query_id) AS labelled_queries,count(*)-count(q.query_id) AS no_future_distinct_view,count(*) FILTER(WHERE q.query_id IS NOT NULL AND c.item_id IS NULL) AS unseen_target_queries FROM prediction_points p LEFT JOIN eval_queries q USING(visitor_id,session_no) LEFT JOIN popular c ON c.item_id=q.target_item GROUP BY p.split ORDER BY p.split")
    paired=[paired_bootstrap(con,x) for x in ['validation','test']]
    experiment=simulate_experiment()
    checks=records(con,'SELECT * FROM join_checks')[0]
    invariants={
        'join_rows_preserved':checks['before_rows']==checks['after_rows'],
        'user_key_unique':checks['duplicate_user_keys']==0,
        'no_unmatched_users':checks['unmatched_rows']==0,
        'strict_funnel_subset':funnel['strict_three_step_pairs']<=funnel['view_purchase_pairs']<=funnel['view_pairs'],
        'strict_funnel_subset_of_cart':funnel['strict_three_step_pairs']<=funnel['view_add_pairs']<=funnel['view_pairs'],
        'training_before_validation':con.execute('SELECT max(ts_ms)<(SELECT train_end_ms FROM config) FROM train_views').fetchone()[0],
        'labels_after_prediction':con.execute('SELECT count(*) FROM eval_queries WHERE target_ms<=prediction_ms').fetchone()[0]==0,
        'validation_labels_within_period':con.execute("SELECT count(*) FROM eval_queries,config WHERE split='validation' AND target_ms>=validation_end_ms").fetchone()[0]==0,
        'same_query_denominator':all(len({x['queries'] for x in rec if x['split']==s})==1 for s in ['validation','test']),
        'ten_unique_candidates':con.execute('SELECT count(*) FROM (SELECT query_id,method FROM recommendations GROUP BY ALL HAVING count(*)<>10 OR count(DISTINCT item_id)<>10)').fetchone()[0]==0,
        'no_seed_recommended':con.execute('SELECT count(*) FROM recommendations r JOIN eval_queries q USING(query_id) WHERE r.item_id=q.seed_item').fetchone()[0]==0,
        'fixed_training_catalog':con.execute('SELECT count(*) FROM recommendations r LEFT JOIN popular p USING(item_id) WHERE p.item_id IS NULL').fetchone()[0]==0,
        'valid_coverage':all(0<=x['coverage_at_10']<=1 for x in rec)}
    assert all(invariants.values()),invariants
    test={x['method']:x for x in rec if x['split']=='test'}
    insights=[
        f"完整事件表共{meta['raw_rows']:,}行，去除{meta['duplicates_removed']:,}条完全重复记录后保留{meta['clean_rows']:,}行。",
        f"浏览商品-访问配对中，浏览后购买比例为{funnel['view_to_purchase_rate']:.2%}，严格浏览→加购→购买比例为{funnel['strict_rate']:.2%}。",
        f"测试集共同浏览Hit Rate@10为{test['coview']['hit_rate_at_10']:.2%}，热门基线为{test['popular']['hit_rate_at_10']:.2%}；这是下一不同商品浏览的离线命中率。"]
    result={'meta':meta,'daily':daily,'funnel':funnel,'segments':segments,'recommendation':rec,'eligibility':eligibility,'paired_comparison':paired,'experiment':experiment,'insights':insights,
        'protocol':{'train':'before 2015-08-01 UTC','validation':'2015-08-01 through 2015-08-31 UTC','test':'2015-09-01 through data end UTC','minimum_pair_support':2,'max_distinct_items_per_training_session':50,'k':10,'model_frozen_before_validation':True,'bootstrap_unit':'visitor','bootstrap_seed':20261108},'checks':invariants}
    out=ROOT/'reports';out.mkdir(exist_ok=True)
    (out/'metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'validation.json').write_text(json.dumps({'checks':invariants,'timings_seconds':timings,'duckdb_version':duckdb.__version__,'numpy_version':np.__version__},ensure_ascii=False,indent=2),encoding='utf-8')
    for name,data in [('daily_metrics',daily),('funnel',[funnel]),('segments',segments),('recommendation',rec),('eligibility',eligibility),('paired_comparison',paired),('simulated_experiment',[{k:v for k,v in experiment.items() if not isinstance(v,dict)}])]:export_csv(out/(name+'.csv'),data)
    print(json.dumps({'meta':meta,'funnel':funnel,'recommendation':rec,'paired':paired},ensure_ascii=False,indent=2))
    con.close()

if __name__=='__main__':main()
