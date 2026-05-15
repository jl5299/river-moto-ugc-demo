import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { BRANDS, NAV_SECTIONS, OLY, getBrandChars, queueFor } from "./data/demoControlData";
import "./styles.css";

function App() {
  const [brandId, setBrandId] = useState(OLY.CURRENT_BRAND);
  const [brandMenuOpen, setBrandMenuOpen] = useState(false);
  const [screen, setScreen] = useState("triage");
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
                      <span className="badge">{b.id === "river" ? "4 need you" : "empty"}</span>
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
        <Kpi label="24h cost" value="$1.32" delta="HeyGen est." />
        <Kpi label="Uploads" value="1" delta="River slot" />
      </div>
      <div className="triage-grid">
        <div className="card card-pad">
          <div className="section-title">
            <h2>Review queue</h2>
            <span className="pill warn"><span className="dot" /> demo1 no backpressure</span>
          </div>
          <div className="queue-list">
            {needsReview.map((a) => <ArtifactRow key={a.id} artifact={a} onOpen={onOpen} />)}
          </div>
        </div>
        <div className="card card-pad">
          <div className="section-title">
            <h2>Readiness</h2>
            <span className="pill">configs only</span>
          </div>
          <div className="character-stack">
            {chars.map((c) => <CharacterChip key={c.id} c={c} />)}
          </div>
        </div>
      </div>
    </section>
  );
}

function Pipeline({ queue, onOpen }) {
  return (
    <section>
      <div className="page-head">
        <div>
          <div className="kicker">Pipeline</div>
          <h1>Script → render → review → upload</h1>
          <p className="subtitle">Rows mirror the artifact lifecycle from the real Revenants stack.</p>
        </div>
      </div>
      <div className="stage-board">
        {["script_review", "rendering", "pending_review", "posted", "failed"].map((stage) => (
          <div className="stage card" key={stage}>
            <div className="stage-head">{stage.replace("_", " ")}</div>
            {queue.filter((a) => a.status === stage).map((a) => (
              <button className="stage-card" type="button" key={a.id} onClick={() => onOpen(a.id)}>
                <strong>{a.template_label}</strong>
                <span>{a.persona_label} · ${a.cost_est.toFixed(2)}</span>
              </button>
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}

function Sources({ brandId }) {
  const sources = OLY.SOURCE_POOL.filter((s) => s.brand === brandId);
  return <SimpleTable title="Viral tailing" subtitle="Source clips become briefs, then artifacts." rows={sources.map((s) => [s.title, fmt(s.views), s.used_by.length ? s.used_by.join(", ") : "unused"])} />;
}

function Reddit({ brandId }) {
  const opps = OLY.REDDIT_OPPS.filter((s) => s.brand === brandId);
  return <SimpleTable title="Reddit" subtitle="Demo discussion mining queue, with private accounts removed." rows={opps.map((s) => [s.subreddit, s.topic, s.status.replace("_", " "), s.angle])} />;
}

function Characters({ chars }) {
  return (
    <section>
      <div className="page-head"><div><div className="kicker">Characters</div><h1>Persona configs</h1></div></div>
      <div className="chars-grid">{chars.map((c) => <CharacterCard key={c.id} c={c} />)}</div>
    </section>
  );
}

function YouTube({ brandId }) {
  const pack = OLY.YOUTUBE_CHANNELS[brandId];
  return <SimpleTable title="YouTube" subtitle="Demo upload slot only; OAuth stays private." rows={(pack.channels || []).map((c) => [c.label, c.handle, c.latest_title || "no upload"])} />;
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
  const health = OLY.TEMPLATE_HEALTH[brandId];
  return <SimpleTable title="Experiments" subtitle="Template health and post-render learning." rows={(health.templates || []).map((t) => [t.id, t.recommendation, t.views_30d ? fmt(t.views_30d) : "-"])} />;
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
      <div className="drawer-section">
        <div className="kicker">Render</div>
        <pre>{`render_scene_shots_heygen(
  shots=[${artifact.template}],
  keyframes=[${artifact.persona}_headshot],
  output_dir="outputs/${artifact.persona}",
)`}</pre>
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
    <article className="character-card card">
      <img src={c.avatar} alt="" />
      <div className="card-pad">
        <h2>{c.name}</h2>
        <p className="subtitle">{c.handle} · {c.niche}</p>
        <div className="char-meta"><span>{c.voice}</span><span>{c.backpressure} backpressure</span></div>
      </div>
    </article>
  );
}

function Kpi({ label, value, delta }) {
  return <div className="kpi"><div className="lbl">{label}</div><div className="val">{value}</div><div className="delta">{delta}</div></div>;
}

function fmt(n) {
  return Intl.NumberFormat("en", { notation: "compact" }).format(n);
}

createRoot(document.getElementById("root")).render(<App />);
