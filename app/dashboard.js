(() => {
  'use strict';
  const D = JSON.parse(document.getElementById('metrics').textContent);
  const $ = id => document.getElementById(id);
  const n = value => Number.isFinite(Number(value)) ? Number(value) : 0;
  const num = value => new Intl.NumberFormat('zh-CN').format(n(value));
  const pct = (value, digits=2) => (n(value)*100).toFixed(digits)+'%';
  const fixed = (value, digits=2) => n(value).toFixed(digits);
  const signed = value => (n(value)>0?'+':'')+fixed(value);
  const txt = (id, value) => $(id).textContent = value ?? '—';
  const htmlEscape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const compact = value => {const v=n(value);return Math.abs(v)>=1e6?(v/1e6).toFixed(1)+'M':Math.abs(v)>=1e3?(v/1e3).toFixed(v>=1e4?0:1)+'k':String(Math.round(v));};
  const day = value => String(value || '').slice(0,10);
  const table = (id, headers, rows, caption) => {
    const element = $(id);
    if(!rows.length){element.innerHTML='<p class="empty">暂无符合条件的结果</p>';return;}
    element.innerHTML='<table><caption class="sr-only">'+htmlEscape(caption)+'</caption><thead><tr>'+headers.map(x=>'<th scope="col">'+htmlEscape(x)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+row.map(x=>'<td>'+htmlEscape(x)+'</td>').join('')+'</tr>').join('')+'</tbody></table>';
  };
  const bars = (id, rows, max=1) => {
    $(id).innerHTML = rows.length ? rows.map(r=>'<div class="bar-item"><div class="bar-label"><span>'+htmlEscape(r.label)+'</span><strong>'+htmlEscape(r.display)+'</strong></div><div class="bar-track" role="img" aria-label="'+htmlEscape(r.label+'：'+r.display)+'"><div class="bar-fill '+(r.className||'')+'" style="width:'+Math.max(0,Math.min(100,100*n(r.value)/(max||1)))+'%"></div></div>'+(r.sub?'<div class="bar-sub">'+htmlEscape(r.sub)+'</div>':'')+'</div>').join('') : '<p class="empty">暂无结果</p>';
  };
  const m = D.meta;
  txt('period',day(m.date_min)+' — '+day(m.date_max));
  txt('source-label',m.source || 'Retailrocket 公开行为数据');
  txt('built-date','分析更新 '+day(m.analysis_date));
  txt('kpi-events',num(m.clean_rows));txt('kpi-visitors',num(m.visitors));txt('kpi-sessions',num(m.sessions));txt('kpi-rate',pct(D.funnel.view_to_purchase_rate));
  const insights = D.insights.filter(x=>typeof x==='string' && x.trim()).slice(0,3);
  $('insights').replaceChildren(...insights.map(x=>{const p=document.createElement('p');p.textContent=x;return p;}));
  if(!insights.length)document.querySelector('.finding-strip').hidden=true;
  txt('quality-text','原始事件 '+num(m.raw_rows)+' 条；移除 '+num(m.duplicates_removed)+' 条完全重复和 '+num(m.invalid_rows)+' 条无效记录，保留 '+num(m.clean_rows)+' 条事件、'+num(m.items)+' 个商品。');
  const url = String(m.source_url || 'https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset');
  $('source-link').href = /^https:\/\//i.test(url) ? url : 'https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset';
  txt('provenance-date',m.analysis_date);txt('provenance-sha',m.data_sha256 || '未提供');
  $('download').addEventListener('click',()=>{const blob=new Blob([JSON.stringify(D,null,2)],{type:'application/json;charset=utf-8'});const href=URL.createObjectURL(blob);const a=document.createElement('a');a.href=href;a.download='shopscope-metrics.json';a.click();setTimeout(()=>URL.revokeObjectURL(href),1000);});

  const daily=[...D.daily].sort((a,b)=>day(a.date).localeCompare(day(b.date)));
  let series='views', rangeRows=daily, hoverIndex=0;
  const seriesNames={views:'浏览事件',addtocarts:'加购事件',transactions:'购买事件'};
  for(const id of ['date-start','date-end']){$(id).min=day(daily[0].date);$(id).max=day(daily[daily.length-1].date);$(id).addEventListener('change',renderTrend);}
  $('date-start').value=day(daily[0].date);$('date-end').value=day(daily[daily.length-1].date);
  $('reset').addEventListener('click',()=>{$('date-start').value=day(daily[0].date);$('date-end').value=day(daily[daily.length-1].date);renderTrend();});
  $('series-tabs').addEventListener('click',e=>{const button=e.target.closest('button[data-series]');if(!button)return;series=button.dataset.series;for(const b of $('series-tabs').querySelectorAll('button'))b.setAttribute('aria-pressed',b===button?'true':'false');renderTrend();});
  let trendGeometry=null;
  function renderTrend(){
    const start=$('date-start').value || day(daily[0].date), end=$('date-end').value || day(daily[daily.length-1].date);
    $('range-error').textContent=start>end?'开始日期应早于或等于结束日期。':'';
    rangeRows=start>end?[]:daily.filter(r=>day(r.date)>=start&&day(r.date)<=end);
    txt('range-total',num(rangeRows.reduce((sum,r)=>sum+n(r[series]),0)));
    txt('range-caption',seriesNames[series]+' · '+rangeRows.length+' 个观测日');
    $('trend-tooltip').hidden=true;
    const svg=$('trend-chart');
    const W=Math.max(280,Math.round(svg.getBoundingClientRect().width || 1120)),H=W<550?220:300,L=46,R=20,T=20,B=45,pw=W-L-R,ph=H-T-B;
    svg.setAttribute('viewBox','0 0 '+W+' '+H);
    if(!rangeRows.length){svg.innerHTML='<text x="'+(W/2)+'" y="'+(H/2)+'" text-anchor="middle" class="chart-axis">当前日期范围没有观测记录</text>';trendGeometry=null;table('daily-table',[],[],'每日明细');return;}
    const max=Math.max(1,...rangeRows.map(r=>n(r[series])))*1.12;
    const x=i=>L+(rangeRows.length===1?pw/2:i/(rangeRows.length-1)*pw), y=v=>T+ph-n(v)/max*ph;
    let parts=['<title>'+htmlEscape(seriesNames[series])+'每日趋势</title>'];
    for(let i=0;i<=4;i++){const v=max*i/4,yy=y(v);parts.push('<line class="grid-line" x1="'+L+'" y1="'+yy+'" x2="'+(W-R)+'" y2="'+yy+'"/><text class="chart-axis" x="'+(L-12)+'" y="'+(yy+4)+'" text-anchor="end">'+compact(v)+'</text>');}
    const indices=[...new Set([0,Math.floor((rangeRows.length-1)*.25),Math.floor((rangeRows.length-1)*.5),Math.floor((rangeRows.length-1)*.75),rangeRows.length-1])];
    for(const i of indices)parts.push('<text class="chart-axis" x="'+x(i)+'" y="'+(H-15)+'" text-anchor="middle">'+day(rangeRows[i].date).slice(5)+'</text>');
    const line=rangeRows.map((r,i)=>(i?'L':'M')+x(i).toFixed(2)+' '+y(r[series]).toFixed(2)).join(' ');
    parts.push('<path d="'+line+' L '+x(rangeRows.length-1)+' '+(H-B)+' L '+x(0)+' '+(H-B)+' Z" fill="#e8f4ef"/><path d="'+line+'" fill="none" stroke="#007c78" stroke-width="2.7" stroke-linecap="round" stroke-linejoin="round"/>');
    if(rangeRows.length===1)parts.push('<circle cx="'+x(0)+'" cy="'+y(rangeRows[0][series])+'" r="5" fill="#007c78"/>');
    parts.push('<line id="trend-guide" x1="0" y1="'+T+'" x2="0" y2="'+(H-B)+'" stroke="#9dbdb0" stroke-dasharray="4 4" visibility="hidden"/><circle id="trend-point" r="5" fill="#007c78" stroke="white" stroke-width="2" visibility="hidden"/>');
    svg.innerHTML=parts.join('');trendGeometry={W,H,L,pw,x,y};hoverIndex=0;
    table('daily-table',['日期（UTC）','浏览事件','加购事件','购买事件','当日访客'],rangeRows.map(r=>[day(r.date),num(r.views),num(r.addtocarts),num(r.transactions),num(r.visitors)]),'筛选区间每日事件明细。每日访客不可直接相加为区间去重访客。');
  }
  function showTrendPoint(index){
    if(!trendGeometry || !rangeRows.length)return;
    hoverIndex=Math.max(0,Math.min(rangeRows.length-1,index));
    const r=rangeRows[hoverIndex],{W,H,x,y}=trendGeometry,xx=x(hoverIndex),yy=y(r[series]);
    const guide=$('trend-guide'),point=$('trend-point');guide.setAttribute('x1',xx);guide.setAttribute('x2',xx);guide.setAttribute('visibility','visible');point.setAttribute('cx',xx);point.setAttribute('cy',yy);point.setAttribute('visibility','visible');
    const tip=$('trend-tooltip'),rect=$('trend-chart').getBoundingClientRect();
    tip.innerHTML=htmlEscape(day(r.date))+'<strong>'+htmlEscape(num(r[series]))+'</strong>'+htmlEscape(seriesNames[series]);tip.hidden=false;
    tip.style.left=Math.min(Math.max(0,xx/W*rect.width-65),Math.max(0,rect.width-tip.offsetWidth))+'px';
    tip.style.top=Math.max(0,yy/H*rect.height-84)+'px';
  }
  $('trend-chart').addEventListener('pointermove',e=>{if(!trendGeometry)return;const rect=e.currentTarget.getBoundingClientRect();const xx=(e.clientX-rect.left)/rect.width*trendGeometry.W;showTrendPoint(Math.round((xx-trendGeometry.L)/trendGeometry.pw*(rangeRows.length-1)));});
  $('trend-chart').addEventListener('pointerleave',()=>{$('trend-tooltip').hidden=true;for(const id of ['trend-guide','trend-point'])$(id)?.setAttribute('visibility','hidden');});
  $('trend-chart').addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();showTrendPoint(e.key==='Home'?0:e.key==='End'?rangeRows.length-1:hoverIndex+(e.key==='ArrowRight'?1:-1));});
  renderTrend();
  let lastTrendWidth=$('trend-chart').getBoundingClientRect().width;
  if(typeof ResizeObserver!=='undefined')new ResizeObserver(entries=>{const width=entries[0].contentRect.width;if(Math.abs(width-lastTrendWidth)>2){lastTrendWidth=width;renderTrend();}}).observe($('trend-chart'));

  const f=D.funnel;
  const paths=[['有浏览的配对',f.view_pairs,1,''],['浏览 → 加购',f.view_add_pairs,f.view_to_add_rate,'light-fill'],['浏览 → 购买',f.view_purchase_pairs,f.view_to_purchase_rate,'navy-fill'],['浏览 → 加购 → 购买',f.strict_three_step_pairs,f.strict_rate,'dark-fill']];
  bars('funnel-bars',paths.map(x=>({label:x[0],value:n(x[1]),display:num(x[1])+' · '+pct(x[2]),className:x[3]})),n(f.view_pairs));
  table('funnel-table',['有序路径','配对数','占浏览配对比例'],paths.map(x=>[x[0],num(x[1]),pct(x[2])]),'同访问、同商品的严格时间顺序路径');
  const segmentName = value=>({first_observed:'首次观测访问',first:'首次观测访问',new:'首次观测访问',returning:'已有历史访问',existing:'已有历史访问',repeat:'已有历史访问',first_observed_session:'首次观测访问',returning_session:'已有历史访问'}[value]||String(value));
  const segments=[...D.segments].sort((a,b)=>Number(!segmentName(a.segment).includes('首次'))-Number(!segmentName(b.segment).includes('首次')));
  const segmentMax=Math.max(.001,...segments.map(r=>n(r.purchase_rate)))*1.2;
  bars('segment-bars',segments.map((r,i)=>({label:segmentName(r.segment),value:r.purchase_rate,display:pct(r.purchase_rate),className:i?'navy-fill':'',sub:num(r.view_purchase_sessions)+' 次浏览后购买访问 / '+num(r.view_sessions)+' 次浏览访问'})),segmentMax);
  table('segment-table',['人群','全部访问','有浏览访问','浏览后购买访问','比例'],segments.map(r=>[segmentName(r.segment),num(r.sessions),num(r.view_sessions),num(r.view_purchase_sessions),pct(r.purchase_rate)]),'不同访问历史人群的购买比例');

  const splitOrder=value=>({validation:0,valid:0,val:0,test:1}[value]??2);
  const splits=[...new Set(D.recommendation.map(r=>r.split))].sort((a,b)=>splitOrder(a)-splitOrder(b));
  let split=splits.find(x=>String(x).toLowerCase().includes('test')||String(x).includes('测试'))||splits[0];
  const splitName=value=>({validation:'验证集',valid:'验证集',val:'验证集',test:'测试集'}[value]||String(value));
  const methodName=value=>({popular:'热门推荐',popularity:'热门推荐',popular_top10:'热门推荐',co_view:'共同浏览推荐',coview:'共同浏览推荐',co_view_top10:'共同浏览推荐',related:'共同浏览推荐',covisitation:'共同浏览推荐'}[value]||String(value));
  if(D.protocol){
    const p=D.protocol, dates=value=>(String(value||'').match(/\d{4}-\d{2}-\d{2}/g)||[]);
    const train=dates(p.train), validation=dates(p.validation), test=dates(p.test);
    if(train.length&&validation.length&&test.length){
      txt('protocol-summary','UTC 时间划分：训练 '+train[0]+' 前；验证 '+validation.join(' — ')+'；测试 '+test[0]+' 起至观测结束。'+(p.model_frozen_before_validation?'模型在验证前冻结。':''));
      $('protocol-summary').hidden=false;
    }
  }
  for(const value of splits){const b=document.createElement('button');b.type='button';b.textContent=splitName(value);b.dataset.split=value;b.setAttribute('aria-pressed',value===split?'true':'false');b.addEventListener('click',()=>{split=value;renderRecommendation();});$('split-tabs').appendChild(b);}
  function renderRecommendation(){
    for(const b of $('split-tabs').querySelectorAll('button'))b.setAttribute('aria-pressed',b.dataset.split===split?'true':'false');
    const rows=D.recommendation.filter(r=>r.split===split).sort((a,b)=>Number(!String(a.method).includes('popular'))-Number(!String(b.method).includes('popular')));
    txt('rec-queries',rows.length?num(rows[0].queries):'—');txt('rec-candidates',rows.length?num(rows[0].candidate_items):'—');
    for(const [id,key] of [['hit-bars','hit_rate_at_10'],['coverage-bars','coverage_at_10']]){
      const max=Math.max(.001,...rows.map(r=>n(r[key])))*1.2;
      bars(id,rows.map((r,i)=>({label:methodName(r.method),value:r[key],display:pct(r[key]),className:i?'':'navy-fill'})),max);
    }
    if(rows.length>=2){const best=[...rows].sort((a,b)=>n(b.hit_rate_at_10)-n(a.hit_rate_at_10))[0];txt('rec-conclusion',splitName(split)+'中，'+methodName(best.method)+'的命中比例为 '+pct(best.hit_rate_at_10)+'。结合商品覆盖和回退比例判断策略取舍，再决定是否进入线上验证。');}else txt('rec-conclusion','在相同候选范围和评估条件下比较策略表现。');
    const paired=Array.isArray(D.paired_comparison)?D.paired_comparison.find(r=>r.split===split):null;
    $('paired-conclusion').hidden=!paired;
    if(paired)txt('paired-conclusion','共同浏览 − 热门：'+signed(paired.difference_pp)+' 个百分点；'+(paired.bootstrap_unit==='visitor'?'访客级自助法':'自助法')+' 95% 区间 '+signed(paired.ci_low_pp)+' 至 '+signed(paired.ci_high_pp)+' 个百分点。');
    table('rec-table',['策略','评估样本','命中数','命中比例','命中95%区间','商品覆盖','完全回退热门'],rows.map(r=>[methodName(r.method),num(r.queries),num(r.hits),pct(r.hit_rate_at_10),pct(r.hit_ci_low)+' – '+pct(r.hit_ci_high),pct(r.coverage_at_10),String(r.method).includes('popular')?'不适用（基线）':pct(r.fallback_rate)]),'推荐策略的离线评估结果');
  }
  renderRecommendation();

  const e=D.experiment;
  txt('seed-label','随机种子 '+e.seed);txt('control-rate',pct(e.control_rate));txt('treatment-rate',pct(e.treatment_rate));txt('control-n',num(e.control_users)+' 位模拟用户');txt('treatment-n',num(e.treatment_users)+' 位模拟用户');txt('effect-value',signed(e.difference_pp)+' 个百分点');
  txt('effect-interval','95% 置信区间：'+signed(e.ci_low_pp)+' 至 '+signed(e.ci_high_pp)+' 个百分点');txt('experiment-decision',e.decision || '结合效果区间与数据质量判断实验结果。');
  const srm=n(e.srm_pvalue);txt('srm-result','分组比例检查 p = '+srm.toFixed(4)+'。'+(srm<.01?'模拟样本出现组间比例异常，应先检查分流。':'本次模拟未检出明显的分组比例异常。'));
  const lo=n(e.ci_low_pp),hi=n(e.ci_high_pp),diff=n(e.difference_pp),span=Math.max(.1,Math.abs(lo),Math.abs(hi),Math.abs(diff))*1.4;
  const L=42,R=528,y=65,x=v=>L+(v+span)/(2*span)*(R-L);
  let svg='<title>效果差异 '+signed(diff)+' 个百分点，95%区间 '+signed(lo)+' 到 '+signed(hi)+'</title><line x1="'+L+'" y1="'+y+'" x2="'+R+'" y2="'+y+'" stroke="#dfe6e2"/><line x1="'+x(0)+'" y1="20" x2="'+x(0)+'" y2="105" stroke="#9bb0a9" stroke-dasharray="4 4"/>';
  for(const v of [-span,0,span])svg+='<text x="'+x(v)+'" y="126" text-anchor="middle" class="chart-axis">'+signed(v)+' pp</text>';
  svg+='<line x1="'+x(lo)+'" y1="'+y+'" x2="'+x(hi)+'" y2="'+y+'" stroke="#007c78" stroke-width="5" stroke-linecap="round"/><line x1="'+x(lo)+'" y1="52" x2="'+x(lo)+'" y2="78" stroke="#007c78" stroke-width="2"/><line x1="'+x(hi)+'" y1="52" x2="'+x(hi)+'" y2="78" stroke="#007c78" stroke-width="2"/><circle cx="'+x(diff)+'" cy="'+y+'" r="8" fill="#142d3b" stroke="white" stroke-width="3"/>';
  $('effect-chart').innerHTML=svg;
})();
