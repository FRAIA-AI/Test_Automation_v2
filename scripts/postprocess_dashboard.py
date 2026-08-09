"""Apply deterministic final UI upgrades to the generated dashboard HTML."""

from __future__ import annotations

from pathlib import Path

HTML_PATH = Path("public/index.html")

CSS = r"""
<style id="dashboard-v4-styles">
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
  #diarization-benchmark { margin-top:16px; overflow:hidden; }
  .benchmark-head { display:flex; align-items:flex-start; justify-content:space-between; gap:18px; padding-bottom:16px; border-bottom:1px solid var(--border); }
  .benchmark-title { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
  .benchmark-title h3 { margin:0; font-size:1.25rem; }
  .benchmark-actions,.filter-row,.case-actions { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
  .benchmark-actions a,.benchmark-actions button,.case-actions button { min-height:44px; border:1px solid var(--border); border-radius:11px; padding:0 13px; color:var(--text); background:rgba(255,255,255,.035); text-decoration:none; cursor:pointer; }
  .benchmark-actions .primary { background:var(--accent); color:#061225; border-color:transparent; font-weight:800; }
  .pilot-note { display:flex; gap:10px; align-items:flex-start; margin:14px 0; padding:12px 14px; border:1px solid rgba(255,202,98,.35); background:rgba(255,202,98,.08); border-radius:13px; color:var(--muted); }
  .pilot-note strong { color:var(--warning); white-space:nowrap; }
  .benchmark-kpis { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:10px; margin:14px 0; }
  .benchmark-kpi,.score-card,.turn-card,.speaker-card { border:1px solid var(--border); border-radius:14px; padding:13px; background:rgba(255,255,255,.025); min-width:0; }
  .benchmark-kpi span,.score-card span,.turn-card span,.speaker-card span { display:block; color:var(--muted); font-size:.72rem; }
  .benchmark-kpi strong { display:block; margin-top:6px; font-size:1.35rem; }
  .score-layout { display:grid; grid-template-columns:1.6fr 1fr; gap:14px; }
  .score-group { border:1px solid var(--border); border-radius:16px; padding:14px; background:rgba(255,255,255,.018); }
  .score-group h4,.subsection-title { margin:0 0 4px; font-size:.92rem; }
  .score-group > p,.subsection-copy { margin:0 0 12px; color:var(--muted); font-size:.76rem; }
  .score-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:9px; }
  button.score-card { color:var(--text); text-align:left; cursor:pointer; }
  button.score-card:hover,button.score-card:focus-visible { border-color:var(--accent); background:rgba(105,167,255,.08); outline:none; }
  .score-value { display:flex; align-items:baseline; justify-content:space-between; gap:8px; margin-top:7px; }
  .score-value strong { font-size:1.25rem; }
  .meter { height:5px; background:rgba(159,176,201,.16); border-radius:99px; overflow:hidden; margin-top:9px; }
  .meter i { display:block; height:100%; border-radius:inherit; background:var(--accent); }
  .score-good .meter i { background:var(--success); }.score-watch .meter i{background:var(--warning)}.score-risk .meter i{background:var(--danger)}
  .turn-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:9px; }
  .turn-card strong,.speaker-card strong { display:block; margin-top:5px; font-size:1.05rem; }
  .verdict-wrap { margin-top:14px; }
  .verdict-bar { display:flex; height:13px; border-radius:99px; overflow:hidden; background:rgba(159,176,201,.15); }
  .verdict-bar span { min-width:0; }.verdict-excellent{background:var(--success)}.verdict-good{background:var(--accent)}.verdict-degraded{background:var(--warning)}.verdict-poor{background:var(--danger)}
  .verdict-legend { display:flex; gap:14px; flex-wrap:wrap; margin-top:8px; color:var(--muted); font-size:.72rem; }
  .verdict-legend b { color:var(--text); }
  .speaker-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:9px; margin-top:10px; }
  .benchmark-table { margin-top:16px; border-top:1px solid var(--border); padding-top:16px; }
  .benchmark-table .filter-row { justify-content:space-between; margin:10px 0; }
  .benchmark-table input,.benchmark-table select { min-height:44px; border:1px solid var(--border); border-radius:11px; color:var(--text); background:var(--panel-strong); padding:0 12px; }
  .benchmark-table input { width:min(360px,100%); }
  .benchmark-table table { min-width:1180px; }
  .case-link { min-height:38px; border:1px solid var(--border); border-radius:9px; color:var(--accent); background:transparent; padding:0 10px; cursor:pointer; }
  .case-link:hover,.case-link:focus-visible { border-color:var(--accent); outline:none; }
  .case-id { font-weight:800; white-space:nowrap; }.scenario { color:var(--muted); max-width:210px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .guide-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
  .guide-section,.detail-section { border:1px solid var(--border); border-radius:14px; padding:14px; background:rgba(255,255,255,.02); }
  .guide-section h4,.detail-section h4 { margin:0 0 10px; }
  .guide-item { padding:10px 0; border-top:1px solid var(--border); }.guide-item:first-of-type{border-top:0;padding-top:0}
  .guide-item strong { display:block; }.guide-item em { display:block; color:var(--accent); font-style:normal; margin:3px 0; }.guide-item p { margin:0; color:var(--muted); font-size:.82rem; }
  .thresholds { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:8px; }.threshold { border-radius:10px; padding:10px; background:rgba(255,255,255,.035); font-size:.78rem; }
  .detail-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }.detail-list { margin:8px 0 0; padding-left:19px; color:var(--muted); }.detail-list li{margin:6px 0}.detail-summary{white-space:pre-wrap;color:var(--muted);line-height:1.55}
  :focus-visible { outline:3px solid color-mix(in srgb,var(--accent) 70%,white); outline-offset:2px; }
  @media(max-width:1100px){.benchmark-kpis{grid-template-columns:repeat(3,minmax(0,1fr))}.score-layout{grid-template-columns:1fr}.score-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
  @media(max-width:720px){ .chart-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.brand-logo{width:42px;height:42px}.benchmark-head{display:block}.benchmark-actions{margin-top:12px}.benchmark-kpis,.score-grid,.turn-grid,.speaker-grid,.guide-grid,.detail-grid{grid-template-columns:1fr 1fr}.thresholds{grid-template-columns:1fr 1fr}.pilot-note{display:block}.filter-row{align-items:stretch!important}.benchmark-table input{width:100%}.music-dock{right:8px;bottom:8px}.music-dock .music-bars,.music-dock input{display:none} }
  @media(max-width:460px){.benchmark-kpis,.score-grid,.turn-grid,.speaker-grid,.guide-grid,.detail-grid{grid-template-columns:1fr}}
  @media(prefers-reduced-motion:reduce){html{scroll-behavior:auto!important}*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}
</style>
"""

JS = r"""
<script id="dashboard-v4-runtime">
(() => {
  const VERSION = 'Dashboard v4 · 2026-08-09';
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

  const scoreNumber = value => Number.isFinite(Number(value)) ? Number(value) : null;
  const scoreText = value => scoreNumber(value) == null ? '—' : `${scoreNumber(value).toFixed(scoreNumber(value)%1 ? 2 : 0)}%`;
  const scoreClass = value => scoreNumber(value) == null ? '' : Number(value)>=95 ? 'score-good' : Number(value)>=85 ? '' : Number(value)>=65 ? 'score-watch' : 'score-risk';
  const metricCard = (title,value,guideKey) => `<button class="score-card ${scoreClass(value)}" data-guide="${guideKey}" aria-label="${title}: ${scoreText(value)}. Open score explanation"><span>${title}</span><div class="score-value"><strong>${scoreText(value)}</strong><small>Explain</small></div><div class="meter" aria-hidden="true"><i style="width:${Math.max(0,Math.min(100,scoreNumber(value)||0))}%"></i></div></button>`;
  const countCard = (title,value) => `<div class="turn-card"><span>${title}</span><strong>${Number(value||0).toLocaleString()}</strong></div>`;
  const titleCase = value => String(value||'').replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());

  function normalizedCases(evaluation){
    if(evaluation?.cases?.length) return evaluation.cases;
    return (evaluation?.summary?.case_results||[]).map(item=>({
      case_id:item.case_id,scenario:item.scenario,verdict:item.diarization?.verdict,
      content_retention_score:item.diarization?.content_retention,doctor_attribution_score:item.diarization?.doctor_attribution,
      patient_side_attribution_score:item.diarization?.patient_side_attribution,overall_attribution_score:item.diarization?.overall_attribution,
      hallucination_score:item.diarization?.transcription_integrity,overall_score:item.diarization?.overall,
      misattributed_turns:item.diarization?.misattributed_turns,missing_turns:item.diarization?.missing_turns,
      clinical_fact_retention_score:item.clinical_note?.fact_retention,clinical_note_fidelity_score:item.clinical_note?.fidelity,
      clinical_note_hallucination_score:item.clinical_note?.hallucination_integrity,
      clinically_missing_facts:Array(item.clinical_note?.missing_fact_count||0).fill('See the downloadable case evaluation for details.'),
      clinically_invented_facts:Array(item.clinical_note?.invented_fact_count||0).fill('See the downloadable case evaluation for details.')
    }));
  }

  function scoreGuideMarkup(){
    const item=(name,question,copy)=>`<div class="guide-item"><strong>${name}</strong>${question?`<em>“${question}”</em>`:''}<p>${copy}</p></div>`;
    return `<div class="guide-grid">
      <section class="guide-section" id="guide-transcription"><h4>Diarization / transcription scores</h4>
        ${item('Content retention','Did the system capture what was actually said?','100% means essentially nothing important from the conversation was lost.')}
        ${item('Doctor attribution','Did the doctor’s words stay under Læge?','100% means all doctor speech was assigned correctly.')}
        ${item('Patient-side attribution','Did patient, parent, child, or family speech stay under Patient?','100% means all non-doctor speech was routed correctly.')}
        ${item('Overall attribution','How well did the system separate doctor vs patient-side speech overall?','This combines both sides.')}
        ${item('Transcription integrity','Did the transcript invent anything that wasn’t said?','100% means no meaningful invented content.')}
        ${item('Diarization overall','What is the combined transcription-layer quality?','The formula is 55% overall attribution + 35% content retention + 10% transcription integrity.')}
      </section>
      <section class="guide-section" id="guide-turns"><h4>Turn counts</h4>
        ${item('Expected source turns','','Number of original dialogue turns in the oracle.')}
        ${item('Evaluated source turns','','Number of those turns the AI could actually match and evaluate.')}
        ${item('Correctly attributed','','How many original turns appeared under the correct bucket.')}
        ${item('Misattributed turns','','How many appeared under the wrong bucket—for example, a child’s sentence appears under Læge.')}
        ${item('Missing turns','','How many original turns disappeared completely.')}
      </section>
      <section class="guide-section" id="guide-clinical"><h4>Generated clinical note scores</h4>
        ${item('Clinical fact retention','Did the final note keep the important medical facts?','Examples include symptom, duration, medication, fever, and negative findings.')}
        ${item('Clinical note fidelity','Is what the note says actually accurate compared with the conversation?','A note can include most facts but still distort them, so this is separate from retention.')}
        ${item('Clinical hallucination integrity','Did the note invent medical findings that were never mentioned?','100% means no invented medical facts. A low score means many unsupported findings.')}
        <div class="guide-item"><strong>Case 25 example</strong><p>The note included unsupported findings such as “Strength 5/5,” “Sensation intact,” “No meningism,” and “No palpable tenderness.” Those were not in the source dialogue, which lowered this score.</p></div>
      </section>
      <section class="guide-section" id="guide-verdict"><h4>Verdict</h4><p class="subsection-copy">The verdict applies only to the diarization / transcription layer.</p><div class="thresholds"><div class="threshold success"><strong>Excellent</strong><br>95–100</div><div class="threshold running"><strong>Good</strong><br>85–94</div><div class="threshold stale"><strong>Degraded</strong><br>65–84</div><div class="threshold failure"><strong>Poor</strong><br>Below 65</div></div></section>
    </div>`;
  }

  function openScoreGuide(section='transcription'){
    const dialog=document.getElementById('score-guide');
    document.getElementById('score-guide-body').innerHTML=scoreGuideMarkup();
    dialog.showModal();
    requestAnimationFrame(()=>document.getElementById(`guide-${section}`)?.scrollIntoView({block:'start'}));
  }

  function listMarkup(items,empty){
    return items?.length ? `<ul class="detail-list">${items.map(item=>`<li>${esc(typeof item==='string'?item:JSON.stringify(item))}</li>`).join('')}</ul>` : `<p class="subsection-copy">${empty}</p>`;
  }

  function openCaseDetail(caseItem){
    const dialog=document.getElementById('case-detail');
    document.getElementById('case-detail-title').textContent=`${caseItem.case_id} · ${titleCase(caseItem.scenario)}`;
    document.getElementById('case-detail-body').innerHTML=`
      <div class="benchmark-kpis">${[['Diarization',caseItem.overall_score],['Attribution',caseItem.overall_attribution_score],['Clinical retention',caseItem.clinical_fact_retention_score],['Clinical fidelity',caseItem.clinical_note_fidelity_score],['Clinical integrity',caseItem.clinical_note_hallucination_score]].map(([k,v])=>`<div class="benchmark-kpi"><span>${k}</span><strong>${scoreText(v)}</strong></div>`).join('')}</div>
      <div class="detail-grid">
        <section class="detail-section"><h4>Turn accounting</h4><div class="turn-grid">${countCard('Expected',caseItem.expected_turn_count)}${countCard('Evaluated',caseItem.evaluated_turn_count)}${countCard('Correct',caseItem.correctly_attributed_turns)}${countCard('Misattributed',caseItem.misattributed_turns)}${countCard('Missing',caseItem.missing_turns)}</div></section>
        <section class="detail-section"><h4>Case context</h4><p class="detail-summary">Expected speakers: ${esc((caseItem.expected_speakers||[]).join(', ')||'Not recorded')}\nSpeaker count: ${esc(caseItem.expected_speaker_count??'—')}\nAudio duration: ${esc(formatDuration(caseItem.duration_seconds))}\nVerdict: ${esc(titleCase(caseItem.verdict))}</p></section>
        <section class="detail-section"><h4>Attribution errors</h4>${listMarkup(caseItem.attribution_errors,'No attribution errors were recorded.')}</section>
        <section class="detail-section"><h4>Missing transcript content</h4>${listMarkup(caseItem.missing_content,'No meaningful source content was missing.')}</section>
        <section class="detail-section"><h4>Invented transcript content</h4>${listMarkup(caseItem.hallucinated_content,'No meaningful invented transcript content was found.')}</section>
        <section class="detail-section"><h4>Missing clinical facts</h4>${listMarkup(caseItem.clinically_missing_facts,'No missing clinical facts were recorded.')}</section>
        <section class="detail-section"><h4>Unsupported / invented clinical facts</h4>${listMarkup(caseItem.clinically_invented_facts,'No unsupported clinical facts were recorded.')}</section>
        <section class="detail-section"><h4>Evaluation summary</h4><p class="detail-summary">${esc(caseItem.summary||caseItem.clinical_note_summary||'No narrative summary was included.')}</p></section>
      </div>`;
    dialog.showModal();
  }

  function renderCaseTable(cases){
    const query=(document.getElementById('case-search')?.value||'').toLowerCase();
    const verdict=document.getElementById('case-verdict')?.value||'all';
    const filtered=cases.filter(item=>(verdict==='all'||String(item.verdict).toLowerCase()===verdict)&&`${item.case_id} ${item.scenario}`.toLowerCase().includes(query));
    const body=document.getElementById('case-table-body');
    const count=document.getElementById('case-count');
    if(count) count.textContent=`${filtered.length} of ${cases.length} cases`;
    if(!body)return;
    body.innerHTML=filtered.length?filtered.map((item,index)=>`<tr><td class="case-id">${esc(item.case_id)}</td><td class="scenario" title="${esc(titleCase(item.scenario))}">${esc(titleCase(item.scenario))}</td><td>${esc(item.expected_speaker_count??'—')}</td><td><strong>${scoreText(item.overall_score)}</strong></td><td>${scoreText(item.overall_attribution_score)}</td><td>${scoreText(item.content_retention_score)}</td><td>${scoreText(item.hallucination_score)}</td><td>${scoreText(item.clinical_fact_retention_score)}</td><td>${scoreText(item.clinical_note_fidelity_score)}</td><td>${scoreText(item.clinical_note_hallucination_score)}</td><td>${Number(item.misattributed_turns||0)} / ${Number(item.missing_turns||0)}</td><td><span class="badge ${String(item.verdict).toLowerCase()==='excellent'?'success':String(item.verdict).toLowerCase()==='good'?'running':String(item.verdict).toLowerCase()==='degraded'?'stale':'failure'}">${esc(titleCase(item.verdict))}</span></td><td><button class="case-link" data-case-index="${index}">View</button></td></tr>`).join(''):`<tr><td colspan="13"><div class="empty">No cases match these filters.</div></td></tr>`;
    body.querySelectorAll('[data-case-index]').forEach(button=>button.addEventListener('click',()=>openCaseDetail(filtered[Number(button.dataset.caseIndex)])));
  }

  window.renderDiarization=function(){
    const root=document.getElementById('diarization-benchmark');
    const monitor=state.data?.monitors?.diarization;
    if(!root||!monitor)return;
    const run=monitor.latest_completed||monitor.latest;
    const evaluation=monitor.evidence?.evaluation;
    const summary=evaluation?.summary;
    if(!summary){root.innerHTML=`<div class="benchmark-head"><div><div class="eyebrow">Clinical AI quality</div><div class="benchmark-title"><h3 id="diarization-title">Diarization & clinical-note evaluation</h3><span class="badge ${run?.conclusion==='success'?'success':'unknown'}">${run?.conclusion==='success'?'Run succeeded':'Awaiting evaluation'}</span></div><p class="subsection-copy">The workflow is visible, but its latest artifact did not contain a readable evaluation summary.</p></div><div class="benchmark-actions"><button class="primary" data-open-guide>Score system</button><a href="${esc(run?.url||monitor.workflow_url)}" target="_blank" rel="noopener">Open workflow run</a></div></div>`; root.querySelector('[data-open-guide]')?.addEventListener('click',()=>openScoreGuide()); return;}
    const dia=summary.diarization||{}, clinical=summary.clinical_note||{}, turns=evaluation.turns||{}, cases=normalizedCases(evaluation), expected=monitor.expected_case_count||25, evaluated=Number(summary.cases_evaluated||cases.length), partial=evaluated<expected;
    const verdicts=dia.verdict_counts||{}, total=Object.values(verdicts).reduce((sum,value)=>sum+Number(value||0),0)||1;
    const docs=(monitor.evidence?.documents||[]).filter(path=>/evaluation-summary|evaluation-report|batch-summary/i.test(path));
    const speakerGroups=summary.by_original_speaker_count||{};
    root.innerHTML=`
      <div class="benchmark-head"><div><div class="eyebrow">Clinical AI quality · Latest completed benchmark</div><div class="benchmark-title"><h3 id="diarization-title">Diarization & clinical-note evaluation</h3><span class="badge ${run?.conclusion==='success'?'success':'failure'}">${run?.conclusion==='success'?'Succeeded':titleCase(run?.conclusion||'Unknown')}</span></div><p class="subsection-copy">Speaker separation, transcription integrity, turn accounting, and generated-note quality in one auditable view.</p></div><div class="benchmark-actions"><button class="primary" data-open-guide>Score system</button><a href="${esc(run?.url||monitor.workflow_url)}" target="_blank" rel="noopener">Open run</a>${docs[0]?`<a href="${esc(docs[0])}" target="_blank" rel="noopener">Download report</a>`:''}</div></div>
      ${partial?`<div class="pilot-note"><strong>Pilot sample</strong><span>This result covers ${evaluated} of ${expected} benchmark cases. It confirms the online workflow works, but it is not the full 25-case benchmark result.</span></div>`:''}
      <div class="benchmark-kpis"><div class="benchmark-kpi"><span>Cases evaluated</span><strong>${evaluated} / ${expected}</strong></div><div class="benchmark-kpi"><span>Diarization overall</span><strong>${scoreText(dia.average_overall_score)}</strong></div><div class="benchmark-kpi"><span>Overall attribution</span><strong>${scoreText(dia.average_overall_attribution)}</strong></div><div class="benchmark-kpi"><span>Clinical fidelity</span><strong>${scoreText(clinical.average_fidelity)}</strong></div><div class="benchmark-kpi"><span>Latest run</span><strong>${esc(relative(run?.updated_at))}</strong></div></div>
      <div class="score-layout"><section class="score-group"><h4>Transcription layer</h4><p>What was captured, whether speakers stayed in the right bucket, and whether content was invented.</p><div class="score-grid">${metricCard('Content retention',dia.average_content_retention,'transcription')}${metricCard('Doctor attribution',dia.average_doctor_attribution,'transcription')}${metricCard('Patient-side attribution',dia.average_patient_side_attribution,'transcription')}${metricCard('Overall attribution',dia.average_overall_attribution,'transcription')}${metricCard('Transcription integrity',dia.average_transcription_integrity,'transcription')}${metricCard('Diarization overall',dia.average_overall_score,'transcription')}</div></section>
      <section class="score-group"><h4>Generated clinical note</h4><p>Retention, accuracy, and unsupported medical findings are assessed independently.</p><div class="score-grid">${metricCard('Fact retention',clinical.average_fact_retention,'clinical')}${metricCard('Note fidelity',clinical.average_fidelity,'clinical')}${metricCard('Hallucination integrity',clinical.average_hallucination_integrity,'clinical')}</div><div class="turn-grid" style="margin-top:9px">${countCard('Missing facts',clinical.total_missing_clinical_facts)}${countCard('Invented facts',clinical.total_invented_clinical_facts)}</div></section></div>
      <section class="score-group" style="margin-top:14px"><h4>Turn accounting</h4><p>Every oracle turn is reconciled against the evaluated transcript.</p><div class="turn-grid">${countCard('Expected source turns',turns.expected_turn_count)}${countCard('Evaluated source turns',turns.evaluated_turn_count)}${countCard('Correctly attributed',turns.correctly_attributed_turns)}${countCard('Misattributed turns',turns.misattributed_turns??dia.total_misattributed_turns)}${countCard('Missing turns',turns.missing_turns??dia.total_missing_turns)}</div>
      <div class="verdict-wrap"><div class="verdict-bar" aria-label="Verdict distribution">${['excellent','good','degraded','poor'].map(key=>`<span class="verdict-${key}" style="width:${Number(verdicts[key]||0)/total*100}%" title="${titleCase(key)}: ${Number(verdicts[key]||0)}"></span>`).join('')}</div><div class="verdict-legend">${['excellent','good','degraded','poor'].map(key=>`<span><b>${Number(verdicts[key]||0)}</b> ${titleCase(key)}</span>`).join('')}</div></div></section>
      ${Object.keys(speakerGroups).length?`<section class="score-group" style="margin-top:14px"><h4>Complexity by original speaker count</h4><p>Compare where speaker complexity begins to affect attribution or note quality.</p><div class="speaker-grid">${Object.entries(speakerGroups).map(([speakers,item])=>`<div class="speaker-card"><span>${speakers} original speakers · ${item.cases} cases</span><strong>${scoreText(item.average_diarization_overall)} diarization</strong><span style="margin-top:7px">Attribution ${scoreText(item.average_attribution)} · Clinical fidelity ${scoreText(item.average_clinical_note_fidelity)} · Clinical integrity ${scoreText(item.average_clinical_note_hallucination_integrity)}</span></div>`).join('')}</div></section>`:''}
      <section class="benchmark-table"><h4 class="subsection-title">Case explorer</h4><p class="subsection-copy">Search, filter, and open any case to inspect turn errors and clinical-note findings.</p><div class="filter-row"><input id="case-search" type="search" placeholder="Search case or scenario" aria-label="Search benchmark cases"><div class="filter-row"><select id="case-verdict" aria-label="Filter cases by verdict"><option value="all">All verdicts</option><option value="excellent">Excellent</option><option value="good">Good</option><option value="degraded">Degraded</option><option value="poor">Poor</option></select><span class="badge unknown" id="case-count"></span></div></div><div class="history-wrap"><table><thead><tr><th>Case</th><th>Scenario</th><th>Speakers</th><th>Overall</th><th>Attribution</th><th>Retention</th><th>Transcript integrity</th><th>Clinical retention</th><th>Fidelity</th><th>Clinical integrity</th><th>Wrong / missing turns</th><th>Verdict</th><th>Details</th></tr></thead><tbody id="case-table-body"></tbody></table></div></section>`;
    root.querySelectorAll('[data-open-guide],[data-guide]').forEach(button=>button.addEventListener('click',()=>openScoreGuide(button.dataset.guide||'transcription')));
    document.getElementById('case-search')?.addEventListener('input',()=>renderCaseTable(cases));
    document.getElementById('case-verdict')?.addEventListener('change',()=>renderCaseTable(cases));
    renderCaseTable(cases);
  };

  function wireDialog(id,closeId){const dialog=document.getElementById(id),close=document.getElementById(closeId);close?.addEventListener('click',()=>dialog.close());dialog?.addEventListener('click',event=>{if(event.target===dialog)dialog.close()});}

  function initialize(){
    upgradeBrand(); upgradeRange(); upgradeChartHeader();
    wireDialog('score-guide','score-guide-close'); wireDialog('case-detail','case-detail-close');
    const select=document.getElementById('range');
    select?.addEventListener('change',()=>setTimeout(()=>window.renderCharts(),0));
    if(typeof state!=='undefined'&&state.data){ window.renderCharts(); window.renderDiarization(); }
    console.info(VERSION);
  }
  initialize();
  setTimeout(initialize,250);
})();
</script>
"""


def main() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    if "dashboard-v4-styles" not in html:
        html = html.replace("</head>", CSS + "\n</head>", 1)
    if "dashboard-v4-runtime" not in html:
        html = html.replace("</body>", JS + "\n</body>", 1)
    HTML_PATH.write_text(html, encoding="utf-8")
    print("Applied deterministic Dashboard v4 runtime and branding upgrades.")


if __name__ == "__main__":
    main()
