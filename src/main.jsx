import React from "react";
import { createRoot } from "react-dom/client";
import {
  Bike,
  CheckCircle2,
  CircleDot,
  Clock3,
  Film,
  Gauge,
  GitBranch,
  Play,
  Rocket,
  ShieldCheck,
  Upload,
  WandSparkles,
} from "lucide-react";
import { demoSeed } from "./data/demoSeed";
import "./styles.css";

const statusIcon = {
  ready: CircleDot,
  rendering: WandSparkles,
  rendered: CheckCircle2,
  uploaded: Upload,
};

function App() {
  const selected = demoSeed.creators[0];
  const creatorQueue = demoSeed.queue.filter((item) => item.creatorId === selected.id);
  const totalCost = demoSeed.queue.reduce((sum, item) => sum + item.estimateUsd, 0);

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <span className="mark"><Bike size={24} /></span>
          <div>
            <p className="eyebrow">River Moto Co.</p>
            <h1>UGC Studio</h1>
          </div>
        </div>

        <nav className="creator-list" aria-label="Demo creators">
          {demoSeed.creators.map((creator) => (
            <button
              key={creator.id}
              className={creator.id === selected.id ? "creator active" : "creator"}
              type="button"
            >
              <img src={creator.avatar} alt="" />
              <span>
                <strong>{creator.name}</strong>
                <small>{creator.handle}</small>
              </span>
            </button>
          ))}
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Motorcycle UGC ad pipeline</p>
            <h2>{selected.name} content lane</h2>
          </div>
          <div className="actions">
            <button type="button" className="icon-button" title="Preview latest render">
              <Play size={18} />
            </button>
            <button type="button" className="primary-action">
              <Rocket size={18} />
              Render HeyGen shot
            </button>
          </div>
        </header>

        <section className="metrics" aria-label="Demo metrics">
          <Metric icon={ShieldCheck} label="Backpressure" value={selected.backpressure} tone="green" />
          <Metric icon={Film} label="Seeded briefs" value={String(creatorQueue.length)} tone="yellow" />
          <Metric icon={Gauge} label="Est. spend" value={`$${totalCost.toFixed(2)}`} tone="blue" />
          <Metric icon={GitBranch} label="Repo mode" value="Public demo" tone="red" />
        </section>

        <section className="main-grid">
          <div className="queue-panel">
            <div className="section-head">
              <h3>Demo1 Queue</h3>
              <span>{selected.channel}</span>
            </div>
            <div className="queue-list">
              {creatorQueue.map((item) => {
                const Icon = statusIcon[item.status] ?? Clock3;
                return (
                  <article className="queue-item" key={item.id}>
                    <div className={`status-dot ${item.status}`}>
                      <Icon size={16} />
                    </div>
                    <div className="queue-copy">
                      <div>
                        <h4>{item.title}</h4>
                        <p>{item.hook}</p>
                      </div>
                      <div className="tags">
                        {item.tags.map((tag) => <span key={tag}>{tag}</span>)}
                      </div>
                    </div>
                    <div className="queue-meta">
                      <strong>{item.status}</strong>
                      <small>${item.estimateUsd.toFixed(2)}</small>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>

          <div className="right-rail">
            <section className="persona-panel">
              <img src={selected.avatar} alt="" />
              <div>
                <p className="eyebrow">{selected.id}</p>
                <h3>{selected.angle}</h3>
                <p>{selected.bio}</p>
              </div>
            </section>

            <section className="render-panel">
              <div className="section-head">
                <h3>HeyGen render contract</h3>
                <span>Video Agent</span>
              </div>
              <pre>{demoSeed.renderContract}</pre>
            </section>

            <section className="publish-panel">
              <Upload size={20} />
              <div>
                <h3>River YouTube slot</h3>
                <p>{demoSeed.youtubePlan}</p>
              </div>
            </section>
          </div>
        </section>
      </section>
    </main>
  );
}

function Metric({ icon: Icon, label, value, tone }) {
  return (
    <div className={`metric ${tone}`}>
      <Icon size={20} />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
