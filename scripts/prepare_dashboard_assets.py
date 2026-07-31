"""Prepare and enhance the monitoring dashboard for GitHub Pages."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

SOURCE = Path("dashboard")
PUBLIC = Path("public")

EXTRA_CSS = r"""
    /* Deployment-time dashboard polish */
    select.control {
      min-width: 142px;
      color: var(--text);
      background-color: var(--panel-strong);
      border-color: var(--border);
      color-scheme: dark;
    }
    :root[data-theme="light"] select.control { color-scheme: light; }
    select.control option {
      color: #eef4ff;
      background: #0d1a30;
      padding: 10px;
    }
    :root[data-theme="light"] select.control option {
      color: #11213a;
      background: #ffffff;
    }
    .toolbar { row-gap: 10px; }
    .chart-toolbar {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      flex-wrap: wrap;
    }
    .chart-mode {
      border: 1px solid var(--border);
      background: rgba(255,255,255,.035);
      color: var(--text);
      border-radius: 10px;
      padding: 7px 10px;
      cursor: pointer;
      font-size: .75rem;
    }
    .chart-mode.active {
      border-color: var(--accent);
      background: color-mix(in srgb, var(--accent) 18%, transparent);
    }
    .chart-empty {
      height: 100%;
      min-height: 300px;
      display: grid;
      place-items: center;
      color: var(--muted);
      text-align: center;
      padding: 28px;
    }
    .chart-kpis {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin: 4px 0 14px;
    }
    .chart-kpi {
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 10px;
      background: rgba(255,255,255,.025);
    }
    .chart-kpi span { display:block; color:var(--muted); font-size:.7rem; }
    .chart-kpi strong { display:block; margin-top:4px; font-size:.95rem; }
    @media (max-width: 720px) {
      .chart-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      select.control { min-width: 120px; }
    }
"""


def replace_once(html: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, html, count=1, flags=re.DOTALL)
    if count != 1:
        print(f"WARNING: could not replace {label}")
        return html
    return updated


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    html = (SOURCE / "index.html").read_text(encoding="utf-8")

    html = html.replace(
        "https://cdn.jsdelivr.net/npm/three@0.179.1/build/three.min.js",
        "https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js",
    )

    if "rel=\"icon\"" not in html and "rel='icon'" not in html:
        html = html.replace(
            "<title>People's Clinic Monitoring</title>",
            "<title>People's Clinic Monitoring</title>\n"
            "  <link rel=\"icon\" type=\"image/png\" href=\"favicon.png\">",
        )

    # Give users more useful time-window choices.
    html = html.replace(
        '<select class="control" id="range"><option value="1">24 hours</option><option value="7" selected>7 days</option><option value="14">14 days</option><option value="30">30 days</option><option value="all">All runs</option></select>',
        '<select class="control" id="range" aria-label="History period">'
        '<option value="0.25">Last 6 hours</option>'
        '<option value="0.5">Last 12 hours</option>'
        '<option value="1">Last 24 hours</option>'
        '<option value="3">Last 3 days</option>'
        '<option value="7" selected>Last 7 days</option>'
        '<option value="14">Last 14 days</option>'
        '<option value="30">Last 30 days</option>'
        '<option value="90">Last 90 days</option>'
        '<option value="all">All available runs</option>'
        '</select>',
    )

    # Add outcome-chart display modes without removing existing features.
    html = html.replace(
        '<article class="panel section"><div class="section-head"><div><h3>Run outcomes</h3><p>Success and failure trend over the selected period</p></div></div><div id="outcome-chart" class="chart"></div></article>',
        '<article class="panel section"><div class="section-head"><div><h3>Run outcomes</h3><p>Daily runs, failures, and reliability over the selected period</p></div><div class="chart-toolbar" id="outcome-modes"><button class="chart-mode active" data-chart-mode="runs">Runs</button><button class="chart-mode" data-chart-mode="success-rate">Success rate</button><button class="chart-mode" data-chart-mode="duration">Duration</button></div></div><div class="chart-kpis" id="chart-kpis"></div><div id="outcome-chart" class="chart"></div></article>',
    )

    html = html.replace(
        "const state = { data: null, range: '7', evidenceMonitor: 'all', charts: {}, refreshTimer: null };",
        "const state = { data: null, range: '7', evidenceMonitor: 'all', chartMode: 'runs', charts: {}, refreshTimer: null };",
    )

    # Replace chart rendering. The old chart hid symbols, so a period with only
    # one date produced an invisible line. This version always renders bars or
    # visible symbols and provides success-rate and duration modes.
    chart_function = r'''function renderCharts\(\)\{.*?\n    \}\n\n    function exportData'''
    chart_replacement = r'''function renderCharts(){
      if (!state.data || typeof echarts === 'undefined') return;
      const runs = filteredRuns().slice().reverse();
      const outcomeEl = $('outcome-chart');
      const threeEl = $('three-chart');
      const muted = getComputedStyle(document.documentElement).getPropertyValue('--muted').trim();
      const border = getComputedStyle(document.documentElement).getPropertyValue('--border').trim();
      const text = getComputedStyle(document.documentElement).getPropertyValue('--text').trim();
      const panel = getComputedStyle(document.documentElement).getPropertyValue('--panel-strong').trim();
      const names = ['smoke','regression','fnx'];
      const palette = ['#69a7ff','#55d68b','#ffbd45'];

      if (!state.charts.outcome) state.charts.outcome = echarts.init(outcomeEl);
      if (!state.charts.three && typeof echarts.init === 'function') state.charts.three = echarts.init(threeEl);

      const completed = runs.filter(r => r.status === 'completed' || r.conclusion);
      const successes = completed.filter(r => r.conclusion === 'success').length;
      const failures = completed.filter(r => r.conclusion && r.conclusion !== 'success' && r.conclusion !== 'skipped').length;
      const avgDuration = completed.length ? completed.reduce((s,r)=>s+(Number(r.duration_seconds)||0),0)/completed.length : 0;
      const reliability = completed.length ? successes/completed.length*100 : 0;
      $('chart-kpis').innerHTML = [
        ['Runs', completed.length],
        ['Successful', successes],
        ['Failures', failures],
        ['Reliability', `${reliability.toFixed(1)}%`]
      ].map(([k,v])=>`<div class="chart-kpi"><span>${k}</span><strong>${v}</strong></div>`).join('');

      if (!runs.length) {
        state.charts.outcome.clear();
        outcomeEl.innerHTML = '<div class="chart-empty">No runs are available for this period.<br>Choose a longer range or wait for scheduled monitors.</div>';
        state.charts.three.clear();
        threeEl.innerHTML = '<div class="chart-empty">3D reliability data will appear after monitor runs are available.</div>';
        return;
      }

      const buckets = new Map();
      runs.forEach(r => {
        const d = new Date(r.created_at);
        const key = state.range !== 'all' && Number(state.range) <= 1
          ? d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})
          : d.toLocaleDateString();
        if (!buckets.has(key)) buckets.set(key, {key, time:d.getTime(), values:{}});
        const bucket = buckets.get(key);
        bucket.time = Math.min(bucket.time, d.getTime());
        const item = bucket.values[r.monitor] ||= {runs:0, success:0, failure:0, duration:0};
        item.runs += 1;
        item.duration += Number(r.duration_seconds)||0;
        if (r.conclusion === 'success') item.success += 1;
        else if (r.conclusion && r.conclusion !== 'skipped') item.failure += 1;
      });
      const ordered = [...buckets.values()].sort((a,b)=>a.time-b.time);
      const x = ordered.map(b=>b.key);

      let series;
      let yName;
      let yMax;
      if (state.chartMode === 'success-rate') {
        yName = 'Success %'; yMax = 100;
        series = names.map((name,i)=>({
          name: state.data.monitors[name].label,
          type:'line', smooth:true, symbol:'circle', symbolSize:9, showSymbol:true,
          connectNulls:false,
          lineStyle:{width:3,color:palette[i]}, itemStyle:{color:palette[i]},
          areaStyle:{opacity:.08,color:palette[i]},
          data:ordered.map(b=>{const v=b.values[name];return !v||!v.runs?null:Number((v.success/v.runs*100).toFixed(1));})
        }));
      } else if (state.chartMode === 'duration') {
        yName = 'Avg seconds'; yMax = null;
        series = names.map((name,i)=>({
          name: state.data.monitors[name].label,
          type:'line', smooth:true, symbol:'diamond', symbolSize:9, showSymbol:true,
          lineStyle:{width:3,color:palette[i]}, itemStyle:{color:palette[i]},
          data:ordered.map(b=>{const v=b.values[name];return !v||!v.runs?null:Number((v.duration/v.runs).toFixed(1));})
        }));
      } else {
        yName = 'Runs'; yMax = null;
        series = names.map((name,i)=>({
          name: state.data.monitors[name].label,
          type:'bar', barMaxWidth:28,
          itemStyle:{color:palette[i],borderRadius:[7,7,0,0]},
          emphasis:{focus:'series'},
          data:ordered.map(b=>b.values[name]?.runs||0)
        }));
      }

      outcomeEl.innerHTML = '';
      state.charts.outcome.setOption({
        animationDuration:650,
        backgroundColor:'transparent',
        color:palette,
        tooltip:{trigger:'axis',backgroundColor:panel,borderColor:border,textStyle:{color:text}},
        legend:{top:4,textStyle:{color:muted},itemWidth:18,itemHeight:10},
        grid:{left:58,right:22,top:52,bottom:64},
        dataZoom:[{type:'inside'},{type:'slider',height:18,bottom:8,borderColor:border,textStyle:{color:muted},show:ordered.length>12}],
        xAxis:{type:'category',data:x,axisLabel:{color:muted,rotate:x.length>8?30:0,hideOverlap:true},axisLine:{lineStyle:{color:border}},axisTick:{alignWithLabel:true}},
        yAxis:{type:'value',name:yName,max:yMax,nameTextStyle:{color:muted},axisLabel:{color:muted,formatter:state.chartMode==='success-rate'?'{value}%':'{value}'},splitLine:{lineStyle:{color:border}}},
        series
      }, true);

      const points = completed.slice(-80).map((r,i)=>[
        names.indexOf(r.monitor), i + 1, Number(r.duration_seconds)||0, r.conclusion||r.status||'unknown', r.number
      ]).filter(p=>p[0]>=0);
      threeEl.innerHTML = '';
      state.charts.three.setOption({
        animationDuration:700,
        backgroundColor:'transparent',
        tooltip:{backgroundColor:panel,borderColor:border,textStyle:{color:text},formatter:p=>`${names[p.value[0]]}<br>Run #${p.value[4]||'—'}<br>Duration: ${duration(p.value[2])}<br>${label(p.value[3])}`},
        xAxis3D:{type:'category',name:'Monitor',data:names,nameTextStyle:{color:text,fontSize:14},axisLabel:{color:text,fontSize:12},axisLine:{lineStyle:{color:muted}},splitLine:{lineStyle:{color:border}}},
        yAxis3D:{type:'value',name:'Run',nameTextStyle:{color:text,fontSize:14},axisLabel:{color:text,fontSize:12},axisLine:{lineStyle:{color:muted}},splitLine:{lineStyle:{color:border}}},
        zAxis3D:{type:'value',name:'Seconds',nameTextStyle:{color:text,fontSize:14},axisLabel:{color:text,fontSize:12},axisLine:{lineStyle:{color:muted}},splitLine:{lineStyle:{color:border}}},
        grid3D:{boxWidth:105,boxDepth:125,environment:'transparent',viewControl:{autoRotate:true,autoRotateSpeed:7,distance:185,alpha:22,beta:36},light:{main:{intensity:1.35,shadow:true},ambient:{intensity:.75}},postEffect:{enable:false}},
        series:[{type:'scatter3D',symbolSize:11,data:points,itemStyle:{color:p=>color(p.value[3]),opacity:1,borderWidth:1,borderColor:'#ffffff'},emphasis:{itemStyle:{opacity:1}}}]
      }, true);
    }

    function exportData'''
    html = replace_once(html, chart_function, chart_replacement, "renderCharts")

    # Register chart-mode buttons.
    html = html.replace(
        "$('range').addEventListener('change',e=>{state.range=e.target.value;renderHistory();renderCharts();});",
        "$('range').addEventListener('change',e=>{state.range=e.target.value;renderHistory();renderCharts();});\n"
        "    document.querySelectorAll('[data-chart-mode]').forEach(button=>button.addEventListener('click',()=>{state.chartMode=button.dataset.chartMode;document.querySelectorAll('[data-chart-mode]').forEach(b=>b.classList.toggle('active',b===button));renderCharts();}));",
    )

    # Replace WebAudio with uploaded MP3.
    music_pattern = re.compile(
        r"\s*let audioCtx, master, playing=false, timers=\[\];.*?"
        r"\$\('volume'\)\.addEventListener\('input',e=>\{if\(master\)master\.gain\.value=Number\(e\.target\.value\)\}\);",
        re.DOTALL,
    )
    music_replacement = r'''
    const ambientAudio = new Audio('bg-music.mp3');
    ambientAudio.loop = true;
    ambientAudio.preload = 'metadata';
    ambientAudio.volume = Number($('volume').value);
    let playing = false;
    async function startMusic(){
      try { await ambientAudio.play(); playing=true; $('music-dock').classList.add('playing'); $('music').textContent='Ⅱ'; }
      catch(error){ toast(`Music could not start: ${error.message}`); }
    }
    function stopMusic(){ ambientAudio.pause(); playing=false; $('music-dock').classList.remove('playing'); $('music').textContent='♪'; }
    $('music').addEventListener('click',()=>playing?stopMusic():startMusic());
    $('volume').addEventListener('input',e=>{ambientAudio.volume=Number(e.target.value)});'''
    html, replacements = music_pattern.subn(music_replacement, html, count=1)
    if replacements != 1:
        print("WARNING: music block was not replaced; keeping original audio code")

    html = html.replace(
        "(function initThree(){ const canvas=$('three-bg'), renderer=new THREE.WebGLRenderer",
        "(function initThree(){ if (typeof THREE === 'undefined') { console.warn('Three.js unavailable; continuing without animated background'); return; } const canvas=$('three-bg'), renderer=new THREE.WebGLRenderer",
    )

    html = html.replace("  </style>", EXTRA_CSS + "\n  </style>", 1)

    (PUBLIC / "index.html").write_text(html, encoding="utf-8")

    for asset in ("favicon.png", "favicon.webp", "bg-music.mp3"):
        source = SOURCE / asset
        if source.is_file():
            shutil.copy2(source, PUBLIC / source.name)
            print(f"Copied {source} -> {PUBLIC / source.name}")

    (PUBLIC / ".nojekyll").touch()
    print("Dashboard HTML, charts, controls, and assets prepared.")


if __name__ == "__main__":
    main()
