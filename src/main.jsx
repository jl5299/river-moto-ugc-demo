import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { BRANDS, NAV_SECTIONS, OLY, getBrandChars, queueFor } from "./data/demoControlData";
import "./styles.css";

function App() {
  const params = new URLSearchParams(window.location.search);
  const [brandId, setBrandId] = useState(params.get("brand") && BRANDS[params.get("brand")] ? params.get("brand") : OLY.CURRENT_BRAND);
  const [brandMenuOpen, setBrandMenuOpen] = useState(false);
  const [screen, setScreen] = useState(NAV_SECTIONS.some((item) => item.id === params.get("screen")) ? params.get("screen") : "triage");
  const [openId, setOpenId] = useState(null);
  const brand = BRANDS[brandId];
  const queue = queueFor(OLY, brandId);
  const chars = getBrandChars(OLY, brandId);
  const openArtifact = openId ? queue.find((item) => item.id === openId) || null : null;

  const counts = useMemo(() => {
    const review = queue.filter((i) => i.status === "script_review" || i.status === "pending_review").length;
    const failed = queue.filter((i) => i.status === "failed").length;
    const notReady = chars.filter((c) => c.ready === false).length;
    const viral = OLY.SOURCE_POOL.filter((s) => s.brand === brandId && !s.used_by?.length).length;
    const reddit = OLY.REDDIT_OPPS.filter((s) => s.brand === brandId).length;
    return {
      triage: review + failed + notReady,
      review,
      viral,
      reddit,
      chars: chars.length,
      notReady,
    };
  }, [brandId, queue, chars]);

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="topbar-lhs">
            <button className="olympus-home" type="button" onClick={() => setScreen("triage")}>
              <span className="olympus-home-mark">R</span>
              Revenants
            </button>
            <div className="brand-switcher">
              <button className="brand-switcher-btn" type="button" onClick={() => setBrandMenuOpen((v) => !v)}>
                <span className="brand-switcher-glyph" style={{ background: brand.accent }}>{brand.glyph}</span>
                <div className="brand-switcher-label">
                  <div className="brand-switcher-name">{brand.name}</div>
                  <div className="brand-switcher-sub">{brand.tagline}</div>
                </div>
                <span className="brand-switcher-caret">{brandMenuOpen ? "▴" : "▾"}</span>
              </button>
              {brandMenuOpen && (
                <div className="brand-switcher-menu">
                  <div className="brand-switcher-menu-head">Workspaces</div>
                  {Object.values(BRANDS).map((b) => (
                    <button
                      key={b.id}
                      className={`brand-switcher-row ${b.id === brandId ? "active" : ""}`}
                      type="button"
                      onClick={() => {
                        setBrandId(b.id);
                        setBrandMenuOpen(false);
                        setScreen("triage");
                        setOpenId(null);
                      }}
                    >
                      <span className="brand-switcher-glyph" style={{ background: b.accent }}>{b.glyph}</span>
                      <span className="brand-switcher-copy">
                        <span className="brand-switcher-name">{b.name}</span>
                        <span className="brand-switcher-sub">{b.tagline}</span>
                      </span>
                      <span className="badge">{b.id === "river" ? "seeded" : "demo client"}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
          <button className="topbar-cmdk" type="button">
            <span>Jump to anything</span>
            <span className="kbd">⌘K</span>
          </button>
        </div>
      </header>

      <div className="shell">
        <aside className="rail">
          <div className="brand-label">
            <span className="brand-dot" style={{ background: brand.accent, boxShadow: `0 0 0 3px ${brand.accentSoft}` }} />
            <div>
              <div className="rail-brand-name">{brand.name}</div>
              <div className="rail-brand-sub">{brand.sub}</div>
            </div>
          </div>
          {NAV_SECTIONS.map((item) => {
            const count = counts[item.countKey];
            const notReady = item.readinessKey ? counts[item.readinessKey] : 0;
            const urgent = item.urgent && count > 0;
            return (
              <button
                key={item.id}
                className={`nav-item ${screen === item.id ? "active" : ""} ${urgent ? "urgent" : ""}`}
                type="button"
                onClick={() => setScreen(item.id)}
              >
                <span className="nav-icon" />
                <span>{item.label}</span>
                {notReady > 0 && <span className="nav-warn-dot" title={`${notReady} persona not ready`} />}
                {count != null && <span className={`badge ${urgent ? "urgent" : ""}`}>{count}</span>}
              </button>
            );
          })}
        </aside>

        <main className="main">
          {screen === "triage" && <Triage brand={brand} queue={queue} chars={chars} counts={counts} onOpen={setOpenId} />}
          {screen === "pipeline" && <Pipeline brand={brand} queue={queue} onOpen={setOpenId} />}
          {screen === "sources" && <Sources brandId={brandId} />}
          {screen === "reddit" && <Reddit brandId={brandId} />}
          {screen === "characters" && <Characters chars={chars} />}
          {screen === "youtube" && <YouTube brandId={brandId} />}
          {screen === "workflow" && <Workflow />}
          {screen === "experiments" && <Experiments brandId={brandId} />}
        </main>
      </div>

      {openArtifact && <Drawer artifact={openArtifact} onClose={() => setOpenId(null)} />}
    </>
  );
}

function Triage({ brand, queue, chars, counts, onOpen }) {
  const needsReview = queue.filter((i) => ["script_review", "pending_review", "failed"].includes(i.status));
  const seeded = brand.id === "river";
  return (
    <section>
      <div className="page-head">
        <div>
          <div className="kicker">Triage · {brand.name}</div>
          <h1>What needs a human right now</h1>
          <p className="subtitle">Same Revenants control flow, seeded with public demo motorcycle configs.</p>
        </div>
        <button className="btn primary" type="button">Run demo render</button>
      </div>
      <div className="kpi-strip">
        <Kpi label="Triage" value={counts.triage} delta="review + readiness" />
        <Kpi label="Review" value={counts.review} delta="script/render" />
        <Kpi label="Viral gaps" value={counts.viral} delta="unused sources" />
        <Kpi label="Personas" value={counts.chars} delta={`${counts.notReady} blocked`} />
        <Kpi label="24h cost" value={seeded ? "$1.32" : "$0.00"} delta={seeded ? "HeyGen est." : "not seeded"} />
        <Kpi label="Uploads" value={seeded ? "1" : "0"} delta={seeded ? "River slot" : "not seeded"} />
      </div>
      <div className="triage-grid">
        <div className="card card-pad">
          <div className="section-title">
            <h2>Review queue</h2>
            <span className="pill warn"><span className="dot" /> demo1 no backpressure</span>
          </div>
          <div className="queue-list">
            {needsReview.length === 0 ? <div className="empty compact">Only River Moto is seeded for the demo recording.</div> : needsReview.map((a) => <ArtifactRow key={a.id} artifact={a} onOpen={onOpen} />)}
          </div>
        </div>
        <div className="card card-pad">
          <div className="section-title">
            <h2>Readiness</h2>
            <span className="pill">configs only</span>
          </div>
          <div className="character-stack">
            {chars.length === 0 ? <div className="empty compact">No personas configured in this public demo client.</div> : chars.map((c) => <CharacterChip key={c.id} c={c} />)}
          </div>
        </div>
      </div>
    </section>
  );
}

function Pipeline({ brand, queue, onOpen }) {
  const [stage, setStage] = useState("review");
  const stages = [
    { id: "review", label: "Review", count: queue.filter((i) => ["script_review", "pending_review"].includes(i.status)).length, sub: "script + render QA", cls: "good" },
    { id: "pending_keyframes", label: "Keyframes", count: queue.filter((i) => i.status === "pending_keyframes").length, sub: "queued", cls: "" },
    { id: "rendering", label: "Rendering", count: queue.filter((i) => i.status === "rendering").length, sub: "HeyGen", cls: "warn" },
    { id: "fixes", label: "Fixes needed", count: queue.filter((i) => i.status === "failed").length, sub: "renders + upload readiness", cls: "bad" },
  ];
  const queueItems = queue.filter((item) => {
    if (stage === "all") return true;
    if (stage === "review") return ["script_review", "pending_review"].includes(item.status);
    if (stage === "fixes") return item.status === "failed";
    return item.status === stage;
  });
  const label = stages.find((s) => s.id === stage)?.label || "All stages";

  return (
    <section>
      <div className="page-head">
        <div>
          <div className="kicker">Pipeline</div>
          <h1>Live status</h1>
          <p className="subtitle">{brand.name} · {queue.length} artifacts in flight · viewing <b>{label}</b></p>
        </div>
        <button className="btn" type="button">Pause renders</button>
      </div>
      <div className="flow">
        {stages.map((s, idx) => (
          <React.Fragment key={s.id}>
            {idx > 0 && idx < 3 && <div className="flow-arrow">→</div>}
            {idx === 3 && <div className="flow-divider">fix</div>}
            <button className={`flow-stage ${s.cls} ${stage === s.id ? "on" : ""}`} type="button" onClick={() => setStage(stage === s.id ? "all" : s.id)}>
              <div className="lbl">{s.label}</div>
              <div className="val">{s.count}</div>
              <div className="sub">{s.sub}</div>
            </button>
          </React.Fragment>
        ))}
      </div>
      <div className="pipeline-review-grid">
        <div className="queue">
          <div className="qrow pipeline-row header">
            <div />
            <div>Loop</div>
            <div>Hook + script preview</div>
            <div>Persona</div>
            <div>Status</div>
            <div>Cost</div>
          </div>
          {queueItems.length === 0 && <div className="empty queue-empty">No items in {label.toLowerCase()}.</div>}
          {queueItems.map((item) => <QueueRow key={item.id} item={item} onOpen={onOpen} />)}
        </div>
        <ActivityRail />
      </div>
    </section>
  );
}

function Sources({ brandId }) {
  const sources = OLY.SOURCE_POOL.filter((s) => s.brand === brandId);
  const adapted = sources.filter((s) => s.used_by?.length).length;
  return (
    <section>
      <div className="page-head">
        <div>
          <div className="kicker">Viral tailing</div>
          <h1>Source pool</h1>
          <p className="subtitle">Source clips become briefs, then artifacts.</p>
        </div>
        <div className="header-actions"><button className="btn" type="button">Paste URLs...</button><button className="btn primary" type="button">Run pull cron now</button></div>
      </div>
      <div className="kpi-strip three">
        <Kpi label="Clips in pool" value={sources.length} delta={`${adapted} sources adapted`} />
        <Kpi label="Fanout artifacts" value={sources.reduce((n, s) => n + (s.used_by?.length || 0), 0)} delta="demo queue" />
        <Kpi label="Tastemakers" value={sources.length ? "2" : "0"} delta="public demo" />
      </div>
      <div className="source-grid">
        {sources.length === 0 ? <div className="empty card">Only River Moto has source clips seeded.</div> : sources.map((s) => <SourceCard key={s.id} source={s} />)}
      </div>
    </section>
  );
}

function Reddit({ brandId }) {
  const opps = OLY.REDDIT_OPPS.filter((s) => s.brand === brandId);
  return (
    <section>
      <div className="page-head"><div><div className="kicker">Reddit</div><h1>Discussion mining</h1><p className="subtitle">Public demo opportunities with account automation removed.</p></div></div>
      <div className="queue">
        <div className="qrow reddit-row header"><div>Subreddit</div><div>Topic</div><div>Status</div><div>Angle</div></div>
        {opps.length === 0 ? <div className="empty queue-empty">Only River Moto has Reddit opportunities seeded.</div> : opps.map((o) => (
          <div className="qrow reddit-row" key={o.id}>
            <div className="mono">{o.subreddit}</div><div className="q-hook">{o.topic}</div><div><span className="pill accent"><span className="dot" />{o.status.replace("_", " ")}</span></div><div className="q-meta">{o.angle}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Characters({ chars }) {
  return (
    <section>
      <div className="page-head"><div><div className="kicker">Characters</div><h1>{chars.filter((c) => c.ready).length} ready · {chars.filter((c) => !c.ready).length} need attention</h1><p className="subtitle">Voice profile, account roster, posting cadence per character.</p></div></div>
      {chars.length === 0 ? <div className="empty card">Only River Moto has personas configured for the demo recording.</div> : <div className="char-grid">{chars.map((c) => <CharacterCard key={c.id} c={c} />)}</div>}
    </section>
  );
}

function YouTube({ brandId }) {
  const pack = OLY.YOUTUBE_CHANNELS[brandId] || { channels: [] };
  return <ControlTable title="YouTube" subtitle="Demo upload slot only; OAuth stays private." columns={["Channel", "Handle", "Latest upload"]} rows={(pack.channels || []).map((c) => [c.label, c.handle, c.latest_title || "no upload"])} />;
}

function Workflow() {
  return (
    <section>
      <div className="page-head"><div><div className="kicker">Workflow</div><h1>Demo render graph</h1><p className="subtitle">The public repo keeps the graph shape and stubs live worker execution.</p></div></div>
      <div className="workflow-canvas card">
        {["brief", "prompt", "keyframe", "heygen", "review", "youtube"].map((n, i) => <div className="node" key={n}>{i + 1}. {n}</div>)}
      </div>
    </section>
  );
}

function Experiments({ brandId }) {
  const health = OLY.TEMPLATE_HEALTH[brandId] || { templates: [] };
  return <ControlTable title="Experiments" subtitle="Template health and post-render learning." columns={["Template", "Recommendation", "30d views"]} rows={(health.templates || []).map((t) => [t.id, t.recommendation, t.views_30d ? fmt(t.views_30d) : "-"])} />;
}

function SimpleTable({ title, subtitle, rows }) {
  return (
    <section>
      <div className="page-head"><div><div className="kicker">{title}</div><h1>{title}</h1><p className="subtitle">{subtitle}</p></div></div>
      <div className="card table-card">
        {rows.length === 0 ? <div className="empty">No demo rows configured for this workspace.</div> : rows.map((row, i) => (
          <div className="table-row" key={i}>{row.map((cell, j) => <span key={j}>{cell}</span>)}</div>
        ))}
      </div>
    </section>
  );
}

function ControlTable({ title, subtitle, columns, rows }) {
  return (
    <section>
      <div className="page-head"><div><div className="kicker">{title}</div><h1>{title}</h1><p className="subtitle">{subtitle}</p></div></div>
      <div className="queue">
        <div className="qrow table-control-row header">{columns.map((c) => <div key={c}>{c}</div>)}</div>
        {rows.length === 0 ? <div className="empty queue-empty">No demo rows configured for this workspace.</div> : rows.map((row, i) => (
          <div className="qrow table-control-row" key={i}>{row.map((cell, j) => <div key={j} className={j === 0 ? "q-hook" : "q-meta"}>{cell}</div>)}</div>
        ))}
      </div>
    </section>
  );
}

function QueueRow({ item, onOpen }) {
  const status = statusInfo(item.status);
  return (
    <button className="qrow pipeline-row queue-button" type="button" onClick={() => onOpen(item.id)}>
      <div className="q-thumb"><img src={item.assets.thumb} alt="" /></div>
      <div>
        <div className="mono loop-label">{item.loop === "viral_tail" ? "viral tail" : item.loop}</div>
        <div className="mono muted">demo</div>
      </div>
      <div>
        <div className="q-hook">{item.hook}</div>
        <div className="q-meta">{item.script.length} lines · {item.template_label} · {item.review_hold || item.renderer}</div>
      </div>
      <div className="q-persona"><div>{item.persona_label}</div><div className="muted">{item.brand}</div></div>
      <div><span className={`pill ${status.cls}`}><span className="dot" />{status.label}</span></div>
      <div className="mono q-cost">${item.cost_est.toFixed(2)}</div>
    </button>
  );
}

function SourceCard({ source }) {
  return (
    <article className="source-card card">
      <div className="source-preview"><span>{fmt(source.views)}</span></div>
      <div className="source-body">
        <div className="q-hook">{source.title}</div>
        <div className="q-meta">{source.used_by.length ? `Adapted by ${source.used_by.join(", ")}` : "unused source"}</div>
        <div className="source-footer"><span className="pill accent"><span className="dot" />source</span><span className="mono muted">{source.id}</span></div>
      </div>
    </article>
  );
}

function ActivityRail() {
  return (
    <aside className="pipeline-activity-rail">
      <div className="rail-section-head"><h2>Activity</h2><span className="mono muted">last {OLY.ACTIVITY.length}</span></div>
      <div className="activity">
        {OLY.ACTIVITY.map((a) => (
          <div className="activity-row" key={`${a.ts}-${a.artifact_id}`}>
            <div className="ts">{a.ts}</div>
            <div className="det"><b>{a.artifact_id}</b> {a.label}</div>
          </div>
        ))}
      </div>
    </aside>
  );
}

function ArtifactRow({ artifact, onOpen }) {
  return (
    <button className="artifact-row" type="button" onClick={() => onOpen(artifact.id)}>
      <img src={artifact.assets.thumb} alt="" />
      <div>
        <div className="artifact-title">{artifact.hook}</div>
        <div className="artifact-meta">{artifact.persona_label} · {artifact.template_label} · {artifact.renderer}</div>
      </div>
      <span className={`status-pill ${artifact.status}`}>{artifact.status.replace("_", " ")}</span>
    </button>
  );
}

function Drawer({ artifact, onClose }) {
  return (
    <aside className="drawer">
      <div className="drawer-head">
        <div><div className="kicker">{artifact.id}</div><h2>{artifact.template_label}</h2></div>
        <button className="btn ghost" type="button" onClick={onClose}>Close</button>
      </div>
      <img className="drawer-thumb" src={artifact.assets.thumb} alt="" />
      <div className="drawer-section">
        <div className="kicker">Script</div>
        {artifact.script.map((line) => <p key={line.t}><span className="mono">{line.t}s</span> {line.line}</p>)}
      </div>
      {artifact.prompt?.length ? (
        <div className="drawer-section">
          <div className="kicker">Prompt</div>
          {artifact.prompt.map((line) => <p key={line}>{line}</p>)}
        </div>
      ) : null}
      <div className="drawer-section">
        <div className="kicker">Render</div>
        <pre>{`render_scene_shots_heygen(
  shots=[${artifact.template}],
  keyframes=[${artifact.persona}_headshot],
  output_dir="outputs/${artifact.persona}",
)`}</pre>
        {artifact.review_hold ? <p className="mono muted">{artifact.review_hold}</p> : null}
      </div>
    </aside>
  );
}

function CharacterChip({ c }) {
  return (
    <div className="character-chip">
      <img src={c.avatar} alt="" />
      <span><strong>{c.name}</strong><small>{c.handle} · {c.niche}</small></span>
      <span className={`pill ${c.ready ? "good" : "warn"}`}><span className="dot" />{c.ready ? "ready" : "blocked"}</span>
    </div>
  );
}

function CharacterCard({ c }) {
  return (
    <article className={`char-card ${c.ready ? "" : "not-ready"}`}>
      <div className="char-head">
        <img className="char-avatar" src={c.avatar} alt="" />
        <div className="char-identity">
          <div className="char-name">{c.name}</div>
          <div className="char-handle">{c.handle} · {c.niche}</div>
        </div>
        <span className={`pill ${c.ready ? "good" : "warn"}`}><span className="dot" />{c.ready ? "ready" : "blocked"}</span>
      </div>
      <div className="char-stats">
        <div className="char-stat"><div className="v">{c.ready ? 4 : 0}</div><div className="l">posted</div></div>
        <div className="char-stat"><div className="v" style={{ color: "var(--warn)" }}>{c.ready ? 1 : 0}</div><div className="l">pending</div></div>
        <div className="char-stat"><div className="v" style={{ color: "var(--bad)" }}>{c.ready ? 0 : 1}</div><div className="l">failed</div></div>
      </div>
      <div className="char-card-footer"><span className="mono">{c.voice}</span><span>{c.backpressure} backpressure</span></div>
    </article>
  );
}

function Kpi({ label, value, delta }) {
  return <div className="kpi"><div className="lbl">{label}</div><div className="val">{value}</div><div className="delta">{delta}</div></div>;
}

function fmt(n) {
  return Intl.NumberFormat("en", { notation: "compact" }).format(n);
}

function statusInfo(status) {
  const labels = {
    script_review: { cls: "accent", label: "script · pre-render" },
    pending_keyframes: { cls: "warn", label: "keyframes" },
    rendering: { cls: "warn", label: "rendering" },
    pending_review: { cls: "accent", label: "review · post-render" },
    posted: { cls: "good", label: "posted" },
    failed: { cls: "bad", label: "failed" },
  };
  return labels[status] || { cls: "", label: status.replace("_", " ") };
}

createRoot(document.getElementById("root")).render(<App />);
