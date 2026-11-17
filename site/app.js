/* 마켓 펄스 대시보드 — data/summary.json 하나만 읽어 그립니다. */
"use strict";

const $ = (s) => document.querySelector(s);
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const SERIES = () => [1, 2, 3, 4, 5, 6, 7, 8].map((i) => css(`--series-${i}`));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (n) => (n == null ? "–" : Number(n).toLocaleString("ko-KR"));
const short = (n) => {
  if (n == null) return "–";
  if (n >= 1e8) return (n / 1e8).toFixed(1).replace(/\.0$/, "") + "억";
  if (n >= 1e4) return (n / 1e4).toFixed(1).replace(/\.0$/, "") + "만";
  return num(n);
};
const pctHtml = (v) => {
  if (v == null) return '<span class="flat">–</span>';
  const cls = v > 2 ? "up" : v < -2 ? "down" : "flat";
  const arrow = v > 2 ? "▲" : v < -2 ? "▼" : "–";
  return `<span class="${cls}">${arrow} ${Math.abs(v).toFixed(1)}%</span>`;
};
const SIGNAL = {
  "급상승": ["--good", "급상승"], "상승": ["--good", "상승"], "반등": ["--warning", "반등"], "보합": ["--neutral", "보합"],
  "둔화": ["--serious", "둔화"], "하락": ["--critical", "하락"], "데이터 부족": ["--neutral", "데이터 부족"],
};
const badge = (s) => {
  const [v, label] = SIGNAL[s] || SIGNAL["데이터 부족"];
  const icon = s === "급상승" ? "⬆" : s === "상승" || s === "반등" ? "↗" : s === "하락" ? "⬇" : s === "둔화" ? "↘" : "→";
  return `<span class="badge"><i style="background:var(${v})"></i>${icon} ${label}</span>`;
};

let D = null;
const charts = {};
const state = { market: null, unit: "monthly", comp: "", relQ: "", relSort: "vol", shopSel: [], demoCat: null, oppMarket: "" };

// ── Chart.js 공통 ──────────────────────────────────────────
function chartDefaults() {
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.font.size = 12;
  Chart.defaults.color = css("--text-secondary");
  Chart.defaults.borderColor = css("--grid");
  Chart.defaults.plugins.legend.labels.boxWidth = 10;
  Chart.defaults.plugins.legend.labels.boxHeight = 10;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.tooltip.backgroundColor = css("--surface-1");
  Chart.defaults.plugins.tooltip.titleColor = css("--text-primary");
  Chart.defaults.plugins.tooltip.bodyColor = css("--text-secondary");
  Chart.defaults.plugins.tooltip.borderColor = css("--border");
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.boxPadding = 4;
}
function mk(id, cfg) {
  if (charts[id]) charts[id].destroy();
  const el = document.getElementById(id);
  if (!el) return;
  charts[id] = new Chart(el, cfg);
  return charts[id];
}
const lineDs = (label, pairs, color) => ({
  label, data: pairs.map(([x, y]) => ({ x, y })), borderColor: color, backgroundColor: color,
  borderWidth: 2, pointRadius: 0, pointHoverRadius: 5, pointHoverBorderWidth: 2,
  pointHoverBorderColor: css("--surface-1"), tension: 0.25,
});
const lineOpts = (opts = {}) => ({
  responsive: true, maintainAspectRatio: false, parsing: { xAxisKey: "x", yAxisKey: "y" },
  interaction: { mode: "index", intersect: false },
  plugins: {
    legend: { position: "top", align: "start", display: opts.legend !== false },
    tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${c.parsed.y == null ? "–" : c.parsed.y.toFixed(1)}` } },
  },
  scales: {
    x: { type: "category", grid: { display: false }, ticks: { maxTicksLimit: 8, maxRotation: 0, callback(v) { const l = this.getLabelForValue(v); return opts.daily ? l.slice(5) : l.slice(2, 7); } } },
    y: { type: opts.scale || "linear", beginAtZero: opts.scale !== "logarithmic", grid: { color: css("--grid") }, border: { display: false }, ticks: { maxTicksLimit: 6 } },
  },
});
const labelsOf = (series) => [...new Set(series.flatMap((s) => s.map((p) => p[0])))].sort();

// ── 부트 ───────────────────────────────────────────────────
async function boot() {
  try {
    const r = await fetch("data/summary.json?" + Date.now());
    D = await r.json();
  } catch (e) {
    $("#status").innerHTML = '<div class="empty">data/summary.json 을 불러오지 못했습니다. GitHub Actions 수집이 한 번 이상 돌았는지 확인하세요.</div>';
    return;
  }
  initTheme();
  chartDefaults();
  renderHeader();
  state.market = D.markets[0]?.id;
  renderAll();
  bindTabs();
  const h = location.hash.match(/^#insight(?:\/(\d{4}-\d{2}-\d{2}))?(?:\/([\w-]+))?/);
  if (h) { INS.date = h[1] || null; INS.slug = h[2] || null; showTab("insight"); }
}

function renderAll() {
  chartDefaults();
  renderOverview();
  renderMarket();
  renderShopping();
  renderNow();
  renderOpps();
}

function initTheme() {
  let t = null;
  try { t = localStorage.getItem("mp-theme"); } catch (e) {}
  if (t) document.documentElement.dataset.theme = t;
  $("#themeBtn").onclick = () => {
    const dark = document.documentElement.dataset.theme
      ? document.documentElement.dataset.theme === "dark"
      : matchMedia("(prefers-color-scheme: dark)").matches;
    const next = dark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("mp-theme", next); } catch (e) {}
    renderAll();
  };
}

function bindTabs() {
  document.querySelectorAll("#tabs button").forEach((b) => (b.onclick = () => showTab(b.dataset.tab)));
}
function showTab(t) {
  if (t === "insight") renderInsights();
  document.querySelectorAll("#tabs button").forEach((x) => x.classList.toggle("on", x.dataset.tab === t));
  document.querySelectorAll("section.panel").forEach((p) => p.classList.toggle("on", p.id === "p-" + t));
  Object.values(charts).forEach((c) => c.resize());
  window.scrollTo({ top: 0 });
}

function renderHeader() {
  $("#generated").textContent = `업데이트 ${D.generated}`;
  if (D.demo) $("#demoBanner").innerHTML = '<div class="demo-banner">⚠️ <b>데모 데이터</b>입니다. 모든 숫자는 임의로 만든 값이며 실제 시장 데이터가 아닙니다. API 키를 등록하고 수집이 한 번 돌면 실제 데이터로 바뀝니다.</div>';
  const src = [["naver_trend", "네이버 검색어 트렌드"], ["naver_shopping", "네이버 쇼핑인사이트"], ["naver_keywords", "네이버 검색광고"], ["youtube", "유튜브"], ["google", "구글 급상승"]];
  $("#status").innerHTML = src.map(([k, n]) => {
    const v = D.sources[k];
    return `<span class="chip"><span class="dot ${v ? "ok" : ""}"></span>${n} · ${v ? esc(v) : "미수집"}</span>`;
  }).join("");
  $("#anchorName").textContent = D.anchor;
}

// ── 개요 ───────────────────────────────────────────────────
function renderOverview() {
  const colors = SERIES();
  $("#marketCards").innerHTML = D.markets.map((m, i) => `
    <div class="card mcard" data-m="${m.id}">
      <div class="row1"><span class="name">${esc(m.name)}</span>${badge(m.total.signal)}</div>
      <div class="vol">${short(m.total.vol)}<small>회/30일</small></div>
      <div class="kpis"><span>전년비 ${pctHtml(m.total.yoy)}</span><span>28일 ${pctHtml(m.total.d28)}</span></div>
      <div style="height:48px"><canvas id="spark-${m.id}"></canvas></div>
    </div>`).join("");
  D.markets.forEach((m, i) => {
    const pts = m.total.monthly;
    mk(`spark-${m.id}`, {
      type: "line",
      data: { labels: pts.map((p) => p[0]), datasets: [{ data: pts.map((p) => p[1]), borderColor: colors[i % 8], borderWidth: 2, pointRadius: 0, tension: 0.3, fill: false }] },
      options: { responsive: true, maintainAspectRatio: false, animation: false, plugins: { legend: { display: false }, tooltip: { enabled: true, callbacks: { title: (c) => c[0].label.slice(0, 7), label: (c) => ` 지수 ${c.parsed.y.toFixed(1)}` } } },
        interaction: { mode: "index", intersect: false }, scales: { x: { display: false }, y: { display: false, beginAtZero: true } } },
    });
  });
  document.querySelectorAll(".mcard").forEach((c) => (c.onclick = () => { state.market = c.dataset.m; renderMarket(); showTab("market"); }));

  const shopYoy = (m) => {
    const v = m.shopping.map((s) => s.yoy).filter((x) => x != null);
    return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
  };
  $("#crossTable").innerHTML = `
    <thead><tr><th>시장</th><th class="num">네이버 검색 전년비</th><th class="num">검색 최근 28일</th><th class="num">쇼핑 점유율 전년비</th>
      <th class="num">유튜브 인기영상 언급 (오늘)</th><th class="num">구글 급상승 매칭 (7일)</th><th>종합 신호</th></tr></thead>
    <tbody>${D.markets.map((m) => {
      const yd = m.youtube?.daily || [];
      const yToday = yd.length ? yd[yd.length - 1][1] : null;
      const yAvg = yd.length > 1 ? yd.slice(0, -1).reduce((a, b) => a + b[1], 0) / (yd.length - 1) : null;
      const yTxt = yToday == null ? "–" : `${yToday}개 ${yAvg ? `<span class="flat">(평균 ${yAvg.toFixed(1)})</span>` : ""}`;
      return `<tr><td><b>${esc(m.name)}</b></td><td class="num">${pctHtml(m.total.yoy)}</td><td class="num">${pctHtml(m.total.d28)}</td>
        <td class="num">${m.shopping.length ? pctHtml(shopYoy(m)) : '<span class="flat">해당 없음</span>'}</td>
        <td class="num">${yTxt}</td><td class="num">${m.google ? m.google.count + "개" : "–"}</td><td>${badge(m.total.signal)}</td></tr>`;
    }).join("")}</tbody>`;

  const scale = $("#ovScale .on").dataset.v;
  const labels = labelsOf(D.markets.map((m) => m.total.monthly));
  mk("ovChart", {
    type: "line",
    data: { labels, datasets: D.markets.map((m, i) => lineDs(m.name, m.total.monthly, colors[i % 8])) },
    options: lineOpts({ scale }),
  });
  document.querySelectorAll("#ovScale button").forEach((b) => (b.onclick = () => {
    document.querySelectorAll("#ovScale button").forEach((x) => x.classList.toggle("on", x === b));
    renderOverview();
  }));
}

// ── 시장 상세 ──────────────────────────────────────────────
function renderMarket() {
  const m = D.markets.find((x) => x.id === state.market) || D.markets[0];
  if (!m) return;
  const colors = SERIES();
  $("#marketPills").innerHTML = D.markets.map((x) => `<button class="pill ${x.id === m.id ? "on" : ""}" data-m="${x.id}">${esc(x.name)}</button>`).join("");
  document.querySelectorAll("#marketPills .pill").forEach((b) => (b.onclick = () => { state.market = b.dataset.m; renderMarket(); }));
  $("#mTitle").textContent = `${m.name} · 주제어 검색 추이`;

  const daily = state.unit === "daily";
  const series = m.groups.map((g) => (daily ? g.daily : g.monthly));
  mk("mChart", {
    type: "line",
    data: { labels: labelsOf(series), datasets: m.groups.map((g, i) => lineDs(g.name, series[i], colors[i])) },
    options: lineOpts({ daily }),
  });
  document.querySelectorAll("#mUnit button").forEach((b) => {
    b.classList.toggle("on", b.dataset.v === state.unit);
    b.onclick = () => { state.unit = b.dataset.v; renderMarket(); };
  });

  $("#groupTable").innerHTML = `<thead><tr><th>주제어</th><th class="num">30일 검색수</th><th class="num">전년비</th><th class="num">3개월</th><th class="num">28일</th><th>신호</th></tr></thead>
    <tbody>${m.groups.map((g, i) => `<tr><td><span class="badge" style="background:none;border:none;padding:0"><i style="background:${colors[i]}"></i></span> <b>${esc(g.name)}</b>
      <div class="meta" style="font-size:11.5px;color:var(--text-muted)">${esc(g.keywords.join(", "))}</div></td>
      <td class="num">${num(g.vol)}</td><td class="num">${pctHtml(g.yoy)}</td><td class="num">${pctHtml(g.mom3)}</td><td class="num">${pctHtml(g.d28)}</td><td>${badge(g.signal)}</td></tr>`).join("")}</tbody>`;

  renderRelated(m);

  const yt = m.youtube;
  $("#mYtNote").textContent = yt ? `오늘 인기 영상(전체+카테고리별 차트) 중 이 시장 단어가 들어간 영상 ${yt.count}개` : "";
  $("#mYt").innerHTML = yt && yt.top.length ? yt.top.map((v, i) => `<li><span class="rank">${i + 1}</span><div class="main">
      <div class="clip"><a href="https://www.youtube.com/watch?v=${esc(v.id)}" target="_blank" rel="noopener">${esc(v.title)}</a></div>
      <div class="meta">${esc(v.channel)}</div></div><span class="right">${short(v.views)}회</span></li>`).join("")
    : '<li class="empty">오늘 인기 영상 중 매칭된 영상이 없습니다.</li>';
  const gg = m.google;
  $("#mGg").innerHTML = gg && gg.items.length ? gg.items.map((w, i) => `<li><span class="rank">${i + 1}</span><div class="main">
      <div><b>${esc(w.q)}</b></div><div class="meta clip">${w.news[0] ? `<a href="${esc(w.news[0].url)}" target="_blank" rel="noopener">${esc(w.news[0].title)}</a>` : ""}</div></div>
      <span class="right">${num(w.traffic)}+ · ${w.n}일</span></li>`).join("")
    : '<li class="empty">최근 7일 구글 급상승 검색어 중 매칭된 것이 없습니다.</li>';
}

function renderRelated(m) {
  let rows = m.related.filter((r) => (!state.comp || r.comp === state.comp) && (!state.relQ || r.kw.includes(state.relQ)));
  const k = state.relSort;
  rows = rows.slice().sort((a, b) => (b[k] ?? -1e9) - (a[k] ?? -1e9)).slice(0, 30);
  const th = (key, label) => `<th class="num sortable" data-k="${key}">${label}${state.relSort === key ? " ▾" : ""}</th>`;
  $("#relTable").innerHTML = `<thead><tr><th>#</th><th>키워드</th>${th("vol", "30일 검색수")}${th("mo", "모바일")}${th("growth", "전월비")}${th("clk", "월 평균 클릭")}<th>경쟁도</th></tr></thead>
    <tbody>${rows.map((r, i) => `<tr><td class="flat">${i + 1}</td><td><b>${esc(r.kw)}</b></td><td class="num">${num(r.vol)}</td>
      <td class="num">${r.vol ? Math.round((r.mo / r.vol) * 100) + "%" : "–"}</td><td class="num">${pctHtml(r.growth)}</td><td class="num">${num(r.clk)}</td><td>${esc(r.comp)}</td></tr>`).join("") ||
      '<tr><td colspan="7" class="empty">데이터가 없습니다.</td></tr>'}</tbody>`;
  document.querySelectorAll("#relTable th.sortable").forEach((t) => (t.onclick = () => { state.relSort = t.dataset.k; renderRelated(m); }));
  document.querySelectorAll("#relComp button").forEach((b) => {
    b.classList.toggle("on", b.dataset.v === state.comp);
    b.onclick = () => { state.comp = b.dataset.v; renderRelated(m); };
  });
  $("#relSearch").oninput = (e) => { state.relQ = e.target.value.trim(); renderRelated(m); };
}

// ── 쇼핑 ───────────────────────────────────────────────────
function renderShopping() {
  const S = D.shopping;
  if (!S) { $("#p-shopping").insertAdjacentHTML("afterbegin", '<div class="empty">쇼핑인사이트 데이터가 아직 없습니다.</div>'); return; }
  const cats = S.categories.filter((c) => !c.anchor && c.yoy != null).sort((a, b) => b.yoy - a.yoy);
  const pos = css("--pos"), neg = css("--neg");
  mk("shopYoy", {
    type: "bar",
    data: { labels: cats.map((c) => c.name), datasets: [{ label: "점유율 전년비(%)", data: cats.map((c) => c.yoy),
      backgroundColor: cats.map((c) => (c.yoy >= 0 ? pos : neg)), borderRadius: 4, borderSkipped: false, maxBarThickness: 22 }] },
    options: { indexAxis: "y", responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` 점유율 ${cats[c.dataIndex].share ?? "–"}% · 전년비 ${c.parsed.x > 0 ? "+" : ""}${c.parsed.x.toFixed(1)}% · 3개월 ${cats[c.dataIndex].mom3 == null ? "–" : cats[c.dataIndex].mom3.toFixed(1) + "%"}` } } },
      scales: { x: { grid: { color: (c) => (c.tick.value === 0 ? css("--text-muted") : css("--grid")) }, border: { display: false }, ticks: { callback: (v) => v + "%" } },
        y: { grid: { display: false } } } },
  });

  const anchor = S.categories.find((c) => c.anchor);
  $("#shopAnchor").textContent = anchor ? anchor.name : "";
  const pickable = S.categories.filter((c) => !c.anchor);
  if (!state.shopSel.length) state.shopSel = cats.slice(0, 3).map((c) => c.name);
  $("#shopPills").innerHTML = pickable.map((c) => `<button class="pill ${state.shopSel.includes(c.name) ? "on" : ""}" data-n="${esc(c.name)}">${esc(c.name)}</button>`).join("");
  document.querySelectorAll("#shopPills .pill").forEach((b) => (b.onclick = () => {
    const n = b.dataset.n;
    if (state.shopSel.includes(n)) state.shopSel = state.shopSel.filter((x) => x !== n);
    else if (state.shopSel.length < 4) state.shopSel.push(n);
    renderShopping();
  }));
  // 색은 선택 순서가 아니라 분야(엔티티)에 고정
  const colors = SERIES();
  const colorOf = (name) => colors[pickable.findIndex((c) => c.name === name) % 8];
  const sel = pickable.filter((c) => state.shopSel.includes(c.name));
  mk("shopTrend", {
    type: "line",
    data: { labels: labelsOf(sel.map((c) => c.monthly)), datasets: sel.map((c) => lineDs(c.name, c.monthly, colorOf(c.name))) },
    options: lineOpts(),
  });

  const names = Object.keys(S.demo);
  if (!state.demoCat) state.demoCat = names[0];
  $("#demoCat").innerHTML = names.map((n) => `<option ${n === state.demoCat ? "selected" : ""}>${esc(n)}</option>`).join("");
  $("#demoCat").onchange = (e) => { state.demoCat = e.target.value; renderShopping(); };
  const p = S.demo_period;
  $("#demoDesc").textContent = `최근 3개월(${p.recent[0]}~${p.recent[1]}) vs 1년 전 같은 기간(${p.prev[0]}~${p.prev[1]}) 클릭 비중`;
  const dm = S.demo[state.demoCat];
  const ages = ["10", "20", "30", "40", "50", "60"];
  const c1 = colors[0], c2 = css("--neutral");
  const barDs = (label, data, color) => ({ label, data, backgroundColor: color, borderRadius: 4, borderSkipped: "start", maxBarThickness: 26 });
  const barOpts = { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "top", align: "start" },
    tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${c.parsed.y.toFixed(1)}%` } } },
    scales: { x: { grid: { display: false } }, y: { beginAtZero: true, grid: { color: css("--grid") }, border: { display: false }, ticks: { callback: (v) => v + "%" } } } };
  mk("demoAge", { type: "bar", data: { labels: ages.map((a) => (a === "60" ? "60대+" : a + "대")),
    datasets: [barDs("1년 전", ages.map((a) => dm.age.prev[a] ?? 0), c2), barDs("최근", ages.map((a) => dm.age.recent[a] ?? 0), c1)] }, options: barOpts });
  mk("demoGender", { type: "bar", data: { labels: ["여성", "남성"],
    datasets: [barDs("1년 전", [dm.gender.prev.f ?? 0, dm.gender.prev.m ?? 0], c2), barDs("최근", [dm.gender.recent.f ?? 0, dm.gender.recent.m ?? 0], c1)] }, options: barOpts });
}

// ── 지금 뜨는 것 ──────────────────────────────────────────
function renderNow() {
  const G = D.google;
  if (G) {
    $("#ggDesc").textContent = `${G.date} 하루 동안 수집된 검색어 · 검색량은 구글이 제공하는 대략값`;
    $("#ggToday").innerHTML = G.today.slice(0, 20).map((t, i) => `<li><span class="rank">${i + 1}</span><div class="main"><b>${esc(t.q)}</b>
      <div class="meta clip">${t.news[0] ? `<a href="${esc(t.news[0].url)}" target="_blank" rel="noopener">${esc(t.news[0].title)}</a> · ${esc(t.news[0].source)}` : ""}</div></div>
      <span class="right">${esc(t.traffic_label || num(t.traffic))}</span></li>`).join("");
    $("#ggWeek").innerHTML = G.week.filter((w) => w.n >= 2).slice(0, 20).map((w, i) => `<li><span class="rank">${i + 1}</span><div class="main"><b>${esc(w.q)}</b>
      <div class="meta">마지막 ${esc(w.last)}</div></div><span class="right">${w.n}일 · 최대 ${num(w.traffic)}+</span></li>`).join("") || '<li class="empty">이틀 이상 반복된 검색어가 아직 없습니다.</li>';
  } else {
    $("#ggToday").innerHTML = $("#ggWeek").innerHTML = '<li class="empty">구글 데이터가 아직 없습니다.</li>';
  }

  const Y = D.youtube;
  if (!Y) { $("#ytTerms").innerHTML = '<div class="empty">유튜브 데이터가 아직 없습니다.</div>'; return; }
  $("#ytTerms").innerHTML = Y.rising.map((r) => `<span class="term ${r.new ? "new" : ""}" title="지난 평균 ${r.base}">${esc(r.term)}<b>${r.today}</b></span>`).join("") || '<div class="empty">급증한 단어가 없습니다 (스냅샷이 2일 이상 쌓이면 비교됩니다).</div>';
  const cs = Y.cat_share;
  mk("ytCat", {
    type: "bar",
    data: { labels: cs.map((c) => c[0]), datasets: [{ label: "영상 수", data: cs.map((c) => c[1]), backgroundColor: css("--series-1"), borderRadius: 4, borderSkipped: false, maxBarThickness: 20 }] },
    options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` ${c.parsed.x}개 (${Math.round((c.parsed.x / Math.max(Y.top.length, 1)) * 100)}%)` } } },
      scales: { x: { grid: { color: css("--grid") }, border: { display: false }, ticks: { precision: 0 } }, y: { grid: { display: false } } } },
  });
  $("#ytVel").innerHTML = Y.velocity.slice(0, 10).map((v, i) => `<li><span class="rank">${i + 1}</span><div class="main">
    <div class="clip"><a href="https://www.youtube.com/watch?v=${esc(v.id)}" target="_blank" rel="noopener">${esc(v.title)}</a></div>
    <div class="meta">${esc(v.channel)} · 총 ${short(v.views)}회</div></div><span class="right">시간당 ${short(v.vph)}</span></li>`).join("");
  $("#ytTop").innerHTML = `<thead><tr><th>#</th><th>제목</th><th>채널</th><th class="num">조회수</th><th class="num">좋아요</th><th class="num">댓글</th><th class="num">시간당 조회</th></tr></thead>
    <tbody>${Y.top.map((v) => `<tr><td class="flat">${v.rank}</td><td style="max-width:420px"><div class="clip"><a href="https://www.youtube.com/watch?v=${esc(v.id)}" target="_blank" rel="noopener">${esc(v.title)}</a></div></td>
      <td>${esc(v.channel)}</td><td class="num">${num(v.views)}</td><td class="num">${num(v.likes)}</td><td class="num">${num(v.comments)}</td><td class="num">${num(v.vph)}</td></tr>`).join("")}</tbody>`;
}

// ── 기회 키워드 ────────────────────────────────────────────
function renderOpps() {
  const markets = [...new Set(D.opportunities.map((o) => o.market))];
  $("#oppMarket").innerHTML = `<option value="">전체 시장</option>` + markets.map((m) => `<option ${m === state.oppMarket ? "selected" : ""}>${esc(m)}</option>`).join("");
  $("#oppMarket").onchange = (e) => { state.oppMarket = e.target.value; renderOpps(); };
  const rows = D.opportunities.filter((o) => !state.oppMarket || o.market === state.oppMarket).slice(0, 60);
  $("#oppTable").innerHTML = `<thead><tr><th>#</th><th>키워드</th><th>시장</th><th class="num">30일 검색수</th><th class="num">전월비</th><th class="num">월 평균 클릭</th><th>경쟁도</th><th class="num">점수</th></tr></thead>
    <tbody>${rows.map((o, i) => `<tr><td class="flat">${i + 1}</td><td><b>${esc(o.kw)}</b></td><td>${esc(o.market)}</td><td class="num">${num(o.vol)}</td>
      <td class="num">${pctHtml(o.growth)}</td><td class="num">${num(o.clk)}</td><td>${esc(o.comp)}</td><td class="num"><b>${o.score.toFixed(2)}</b></td></tr>`).join("") ||
      '<tr><td colspan="8" class="empty">데이터가 없습니다.</td></tr>'}</tbody>`;
}


// ── 오늘의 인사이트 ────────────────────────────────────────
const INS = { index: null, cache: {}, date: null, slug: null };
const CAT_ICON = { "쇼핑·유통": "🛍", "디지털 자산": "🪙", "금융·투자": "📈", "마케팅·미디어": "📣", "테크·AI": "🤖" };

async function loadInsightIndex() {
  if (INS.index) return INS.index;
  try { INS.index = await (await fetch("insights/index.json?" + Date.now())).json(); }
  catch (e) { INS.index = { days: [] }; }
  return INS.index;
}
async function loadInsightDay(date) {
  if (!INS.cache[date]) INS.cache[date] = await (await fetch(`insights/${date}.json?` + Date.now())).json();
  return INS.cache[date];
}
function fmtKDate(d) { const [y, m, dd] = d.split("-"); return `${y}년 ${+m}월 ${+dd}일`; }

async function renderInsights() {
  const idx = await loadInsightIndex();
  if (!idx.days.length) {
    $("#insPicks").innerHTML = "";
    $("#insArticle").innerHTML = '<div class="empty">아직 발행된 인사이트가 없습니다. 매일 오전 9시대에 3개씩 올라옵니다.</div>';
    return;
  }
  if (!INS.date) INS.date = idx.days[0].date;
  $("#insDate").innerHTML = idx.days.map((d) => `<option value="${d.date}" ${d.date === INS.date ? "selected" : ""}>${fmtKDate(d.date)}</option>`).join("");
  $("#insDate").onchange = (e) => { INS.date = e.target.value; INS.slug = null; renderInsights(); };
  const day = await loadInsightDay(INS.date);
  if (!INS.slug || !day.items.some((i) => i.slug === INS.slug)) INS.slug = day.items[0].slug;
  $("#insPicks").innerHTML = day.items.map((it) => `<button class="ins-pick ${it.slug === INS.slug ? "on" : ""}" data-s="${esc(it.slug)}">
      <div class="cat">${CAT_ICON[it.category] || "•"} ${esc(it.category)}</div><div class="kw">${esc(it.keyword)}</div><div class="t">${esc(it.title)}</div></button>`).join("");
  document.querySelectorAll(".ins-pick").forEach((b) => (b.onclick = () => { INS.slug = b.dataset.s; renderInsights(); setHash(); $("#insArticle").scrollIntoView({ behavior: "smooth" }); }));
  renderInsightArticle(day, day.items.find((i) => i.slug === INS.slug));
}

function setHash() { history.replaceState(null, "", `#insight/${INS.date}/${INS.slug}`); }

function heroTitle(t) {
  // 첫 쉼표 앞부분을 강조색으로 (참고 페이지의 2색 헤드라인)
  const i = t.indexOf(",");
  return i > 0 ? `<span class="a1">${esc(t.slice(0, i))}</span>,<br>${esc(t.slice(i + 1).trim())}` : esc(t);
}

function renderInsightArticle(day, it) {
  const points = (arr, cls = "") => `<ol class="ins-points ${cls}">${arr.map((p) => `<li>${esc(p)}</li>`).join("")}</ol>`;
  const others = day.items.filter((x) => x.slug !== it.slug);
  $("#insArticle").innerHTML = `
  <div class="ins-article">
    <div class="ins-tags">${it.tags.map((t) => `<span>${esc(t.startsWith("#") ? t : "#" + t)}</span>`).join("")}</div>
    <h1 class="ins-h1">${esc(it.title)}</h1>
    <div class="ins-date">${fmtKDate(day.date)} · ${esc(it.category)}</div>
    <div class="ins-key"><h3>핵심 인사이트</h3>${it.summary.map((p) => `<p>${esc(p)}</p>`).join("")}</div>

    <div class="ins-report">
      <div class="ins-eyebrow">Market Pulse · ${day.date.replaceAll("-", ".")} Daily Insight</div>
      <h2 class="ins-hero">${heroTitle(it.title)}</h2>
      <p class="ins-lead">${esc(it.lead)}</p>
      <div class="ins-meta">
        ${(it.signals.from || []).map((f) => `<span>포착 · ${esc(f)}</span>`).join("")}
        <span>${esc(it.category)}</span><span>키워드 · ${esc(it.keyword)}</span>
      </div>

      <div class="ins-sec">
        <span class="ins-pill">한눈에 보기</span>
        <h4>숫자로 보는 ${esc(it.keyword)}</h4>
        ${it.signals.note ? `<p class="sub">${esc(it.signals.note)}</p>` : ""}
        <div class="ins-kpis">${it.kpis.map((k) => `<div class="ins-kpi ${esc(k.tone || "teal")}">
          <div class="l">${esc(k.label)}</div><div class="v">${esc(k.value)}<small>${esc(k.unit || "")}</small></div><div class="n">${esc(k.note || "")}</div></div>`).join("")}</div>
      </div>

      <div class="ins-sec"><span class="ins-pill blue">현상 · 무슨 일이 있나</span><h4>${esc(it.phenomenon.title)}</h4>${points(it.phenomenon.points)}</div>
      <div class="ins-sec"><span class="ins-pill violet">원인 · 왜 지금인가</span><h4>${esc(it.cause.title)}</h4>${points(it.cause.points)}</div>
      <div class="ins-sec"><span class="ins-pill teal">시사점 · 사업 관점</span><h4>${esc(it.implication.title)}</h4>${points(it.implication.points, "ins-impl")}</div>

      <div class="ins-sec"><span class="ins-pill">앞으로 볼 지표</span><div class="ins-watch">${it.watch.map((w) => `<span>👀 ${esc(w)}</span>`).join("")}</div></div>

      <div class="ins-sec"><span class="ins-pill">출처</span>
        <ul class="ins-src">${it.sources.map((s) => `<li>${esc(s.publisher || "")} · <a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a></li>`).join("")}</ul>
      </div>
      <p class="ins-foot">이 브리핑은 공개 보도와 마켓 펄스 수집 데이터를 바탕으로 AI(Claude)가 작성했습니다. 수치는 출처 기준이며, 투자·법률 판단의 근거로 쓰기 전 원문을 확인하세요.</p>
    </div>

    <div class="ins-share"><button class="pill" id="insCopy">🔗 이 인사이트 링크 복사</button></div>

    ${others.length ? `<div class="ins-more"><h3>같은 날 다른 인사이트</h3><div class="ins-picks">${others.map((o) => `<button class="ins-pick" data-s="${esc(o.slug)}">
      <div class="cat">${CAT_ICON[o.category] || "•"} ${esc(o.category)}</div><div class="kw">${esc(o.keyword)}</div><div class="t">${esc(o.title)}</div></button>`).join("")}</div></div>` : ""}
  </div>`;
  document.querySelectorAll(".ins-more .ins-pick").forEach((b) => (b.onclick = () => { INS.slug = b.dataset.s; renderInsights(); setHash(); $("#insPicks").scrollIntoView({ behavior: "smooth" }); }));
  $("#insCopy").onclick = async () => {
    setHash();
    try { await navigator.clipboard.writeText(location.href); $("#insCopy").textContent = "✓ 복사됨"; } catch (e) { $("#insCopy").textContent = location.href; }
  };
}

boot();
