"""Apply deterministic final UI upgrades to the generated dashboard HTML."""

from __future__ import annotations

from pathlib import Path

HTML_PATH = Path("public/index.html")

CSS = r"""
<style id="dashboard-v3-styles">
  .brand-home { display:flex; align-items:center; gap:12px; color:inherit; text-decoration:none; min-width:0; }
  .brand-logo {
    width:48px; height:48px; border-radius:14px; object-fit:contain; padding:5px;
    background:#fff; border:1px solid var(--border); box-shadow:0 8px 24px rgba(0,0,0,.18);
  }
  .build-badge { color:var(--muted); font-size:.68rem; margin-top:3px; }
  select.control { min-width:154px; color:var(--text); background:var(--panel-strong); color-scheme:dark; }
  :root[data-theme="light"] select.control { color-scheme:light; }
  select.control option { color:#eef4ff; background:#0d1a30; }
  :root[data-theme="light"] select.control option { color:#11213a; background:#fff; }
  .chart-toolbar { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
  .chart-mode {
    border:1px solid var(--border); background:rgba(255,255,255,.035); color:var(--text);
    border-radius:10px; padding:7px 10px; cursor:pointer; font-size:.75rem;
  }
  .chart-mode:hover,.chart-mode.active { border-color:var(--accent); background:rgba(105,167,255,.14); }
  .chart-kpis { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:2px 0 14px; }
  .chart-kpi { border:1px solid var(--border); border-radius:12px; padding:10px; background:rgba(255,255,255,.025); }
  .chart-kpi span { display:block; color:var(--muted); font-size:.7rem; }
  .chart-kpi strong { display:block; margin-top:4px; font-size:.95rem; }
  .chart-empty { height:100%; min-height:280px; display:grid; place-items:center; text-align:center; color:var(--muted); padding:24px; }
  @media(max-width:720px){ .chart-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.brand-logo{width:42px;height:42px} }
</style>
"""

JS = r"""
<script id="dashboard-v3-runtime">
(() => {
  const VERSION = 'Dashboard v3 · 2026-07-31';
  const LOGO = 'https://clinic.peoplesdoctor.ai/assets/images/peoples-doctor-logo-onboarding.png';
  const PLATFORM = 'https://clinic.peoplesdoctor.ai/';

  function upgradeBrand(){
    const brand = document.querySelector('.brand');
    if (!brand || brand.dataset.upgraded) return;
    brand.dataset.upgraded = '1';
    const text = brand.querySelector('div:last-child');
    const link = document.createElement('a');
    link.className = 'brand-home';
    link.href = PLATFORM;
    link.target = '_blank';
    link.rel = 'noopener';
    link.title = "Open People's Clinic";
    const img = document.createElement('img');
    img.className = 'brand-logo';
    img.src = LOGO;
    img.alt = "People's Clinic logo";
    img.addEventListener('error', () => { img.style.display='none'; });
    const wrapper = document.createElement('div');
    if (text) wrapper.append(...text.childNodes);
    const build = document.createElement('div');
    build.className = 'build-badge';
    build.textContent = VERSION;
    wrapper.appendChild(build);
    link.append(img, wrapper);
    brand.replaceChildren(link);
  }

  function upgradeRange(){
    const select = document.getElementById('range');
    if (!select) return;
    const current = select.value || '7';
    const options = [
      ['0.25','Last 6 hours'],['0.5','Last 12 hours'],['1','Last 24 hours'],
      ['3','Last 3 days'],['7','Last 7 days'],['14','Last 14 days'],
      ['30','Last 30 days'],['90','Last 90 days'],['all','All available runs']
    ];
    select.replaceChildren(...options.map(([value,label]) => {
      const option=document.createElement('option'); option.value=value; option.textContent=label; return option;
    }));
    select.value = options.some(([v])=>v===current) ? current : '7';
    if (typeof state !== 'undefined') state.range = select.value;
  }

  function upgradeChartHeader(){
    const chart = document.getElementById('outcome-chart');
    const article = chart?.closest('article');
    const head = article?.querySelector('.section-head');
    if (!article || !head || document.getElementById('outcome-modes')) return;
    const controls=document.createElement('div');
    controls.id='outcome-modes'; controls.className='chart-toolbar';
    controls.innerHTML='<button class="chart-mode active" data-chart-mode="runs">Runs</button><button class="chart-mode" data-chart-mode="success-rate">Success rate</button><button class="chart-mode" data-chart-mode="duration">Duration</button>';
    head.appendChild(controls);
    const kpis=document.createElement('div'); kpis.id='chart-kpis'; kpis.className='chart-kpis';
    chart.before(kpis);
    if (typeof state !== 'undefined' && !state.chartMode) state.chartMode='runs';
    controls.querySelectorAll('button').forEach(button => button.addEventListener('click', () => {
      state.chartMode=button.dataset.chartMode;
      controls.querySelectorAll('button').forEach(item=>item.classList.toggle('active',item===button));
      window.renderCharts();
    }));
  }

  function css(name){ return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function formatDuration(value){ return typeof duration==='function' ? duration(value) : `${Math.round(value||0)}s`; }
  function statusLabel(value){ return typeof label==='function' ? label(value) : value; }
  function statusColor(value){ return typeof color==='function' ? color(value) : '#69a7ff'; }

  window.renderCharts = function(){
    if (typeof state==='undefined' || !state.data || typeof echarts==='undefined') return;
    const outcomeEl=document.getElementById('outcome-chart');
    const threeEl=document.getElementById('three-chart');
    const runs=filteredRuns().slice().reverse();
    const names=['smoke','regression','fnx'];
    const palette=['#69a7ff','#55d68b','#ffbd45'];
    const muted=css('--muted'), border=css('--border'), text=css('--text'), panel=css('--panel-strong');

    if (!state.charts.outcome) state.charts.outcome=echarts.init(outcomeEl);
    if (!state.charts.three) state.charts.three=echarts.init(threeEl);

    const completed=runs.filter(run=>run.status==='completed'||run.conclusion);
    const successes=completed.filter(run=>run.conclusion==='success').length;
    const failures=completed.filter(run=>run.conclusion&& !['success','skipped'].includes(run.conclusion)).length;
    const reliability=completed.length ? successes/completed.length*100 : 0;
    const avg=completed.length ? completed.reduce((sum,run)=>sum+(Number(run.duration_seconds)||0),0)/completed.length : 0;
    const kpis=document.getElementById('chart-kpis');
    if(kpis) kpis.innerHTML=[['Runs',completed.length],['Successful',successes],['Failures',failures],['Avg duration',formatDuration(avg)],['Reliability',`${reliability.toFixed(1)}%`]].map(([k,v])=>`<div class="chart-kpi"><span>${k}</span><strong>${v}</strong></div>`).join('');

    if(!runs.length){ state.charts.outcome.clear(); state.charts.three.clear(); return; }
    const buckets=new Map();
    runs.forEach(run=>{
      const date=new Date(run.created_at);
      const key=state.range!=='all'&&Number(state.range)<=1 ? date.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : date.toLocaleDateString();
      if(!buckets.has(key)) buckets.set(key,{key,time:date.getTime(),values:{}});
      const bucket=buckets.get(key); bucket.time=Math.min(bucket.time,date.getTime());
      const value=bucket.values[run.monitor] ||= {runs:0,success:0,duration:0};
      value.runs++; value.duration+=Number(run.duration_seconds)||0; if(run.conclusion==='success') value.success++;
    });
    const ordered=[...buckets.values()].sort((a,b)=>a.time-b.time);
    const x=ordered.map(bucket=>bucket.key);
    const mode=state.chartMode||'runs';
    let series,yName,yMax=null;
    if(mode==='success-rate'){
      yName='Success %'; yMax=100;
      series=names.map((name,index)=>({name:state.data.monitors[name].label,type:'line',smooth:true,showSymbol:true,symbol:'circle',symbolSize:10,lineStyle:{width:3,color:palette[index]},itemStyle:{color:palette[index]},areaStyle:{opacity:.08,color:palette[index]},data:ordered.map(bucket=>{const value=bucket.values[name];return value?.runs?Number((value.success/value.runs*100).toFixed(1)):null;})}));
    }else if(mode==='duration'){
      yName='Avg seconds';
      series=names.map((name,index)=>({name:state.data.monitors[name].label,type:'line',smooth:true,showSymbol:true,symbol:'diamond',symbolSize:10,lineStyle:{width:3,color:palette[index]},itemStyle:{color:palette[index]},data:ordered.map(bucket=>{const value=bucket.values[name];return value?.runs?Number((value.duration/value.runs).toFixed(1)):null;})}));
    }else{
      yName='Runs';
      series=names.map((name,index)=>({name:state.data.monitors[name].label,type:'bar',barMaxWidth:30,itemStyle:{color:palette[index],borderRadius:[7,7,0,0]},data:ordered.map(bucket=>bucket.values[name]?.runs||0)}));
    }
    state.charts.outcome.setOption({animationDuration:600,backgroundColor:'transparent',color:palette,tooltip:{trigger:'axis',backgroundColor:panel,borderColor:border,textStyle:{color:text}},legend:{top:4,textStyle:{color:muted}},grid:{left:58,right:20,top:50,bottom:60},dataZoom:[{type:'inside'},{type:'slider',height:18,bottom:6,show:ordered.length>12,borderColor:border,textStyle:{color:muted}}],xAxis:{type:'category',data:x,axisLabel:{color:muted,rotate:x.length>8?30:0,hideOverlap:true},axisLine:{lineStyle:{color:border}}},yAxis:{type:'value',name:yName,max:yMax,nameTextStyle:{color:muted},axisLabel:{color:muted,formatter:mode==='success-rate'?'{value}%':'{value}'},splitLine:{lineStyle:{color:border}}},series},true);

    const points=completed.slice(-80).map((run,index)=>[names.indexOf(run.monitor),index+1,Number(run.duration_seconds)||0,run.conclusion||run.status||'unknown',run.number]).filter(point=>point[0]>=0);
    state.charts.three.setOption({animationDuration:650,backgroundColor:'transparent',tooltip:{backgroundColor:panel,borderColor:border,textStyle:{color:text},formatter:item=>`${names[item.value[0]]}<br>Run #${item.value[4]||'—'}<br>Duration: ${formatDuration(item.value[2])}<br>${statusLabel(item.value[3])}`},xAxis3D:{type:'category',name:'Monitor',data:names,nameTextStyle:{color:text,fontSize:14},axisLabel:{color:text,fontSize:12},axisLine:{lineStyle:{color:muted}},splitLine:{lineStyle:{color:border}}},yAxis3D:{type:'value',name:'Run',nameTextStyle:{color:text,fontSize:14},axisLabel:{color:text,fontSize:12},axisLine:{lineStyle:{color:muted}},splitLine:{lineStyle:{color:border}}},zAxis3D:{type:'value',name:'Seconds',nameTextStyle:{color:text,fontSize:14},axisLabel:{color:text,fontSize:12},axisLine:{lineStyle:{color:muted}},splitLine:{lineStyle:{color:border}}},grid3D:{boxWidth:105,boxDepth:125,environment:'transparent',viewControl:{autoRotate:true,autoRotateSpeed:7,distance:185,alpha:22,beta:36},light:{main:{intensity:1.35},ambient:{intensity:.8}},postEffect:{enable:false}},series:[{type:'scatter3D',symbolSize:12,data:points,itemStyle:{color:item=>statusColor(item.value[3]),opacity:1,borderWidth:1,borderColor:'#fff'}}]},true);
  };

  function initialize(){
    upgradeBrand(); upgradeRange(); upgradeChartHeader();
    const select=document.getElementById('range');
    select?.addEventListener('change',()=>setTimeout(()=>window.renderCharts(),0));
    if(typeof state!=='undefined'&&state.data) window.renderCharts();
    console.info(VERSION);
  }
  initialize();
  setTimeout(initialize,250);
})();
</script>
"""


def main() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    if "dashboard-v3-styles" not in html:
        html = html.replace("</head>", CSS + "\n</head>", 1)
    if "dashboard-v3-runtime" not in html:
        html = html.replace("</body>", JS + "\n</body>", 1)
    HTML_PATH.write_text(html, encoding="utf-8")
    print("Applied deterministic Dashboard v3 runtime and branding upgrades.")


if __name__ == "__main__":
    main()
