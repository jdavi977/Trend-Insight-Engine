import { useState } from "react";

const TYPE_COLORS = {
  feature_request: "#6366f1",
  complaint: "#ef4444",
  usability: "#f59e0b",
  performance: "#10b981",
  pricing: "#8b5cf6",
};

function ScaleDots({ value, max = 5 }) {
  return (
    <span className="scale-dots" aria-label={`${value} of ${max}`}>
      {Array.from({ length: max }, (_, i) => (
        <span
          key={i}
          className={`scale-dot ${i < value ? "scale-dot--filled" : ""}`}
        />
      ))}
    </span>
  );
}

function RetrievedContextAccordion({ items, title = "Similar past insights", className = "" }) {
  const [open, setOpen] = useState(false);

  if (!items || items.length === 0) return null;

  const rootClass = ["retrieved-accordion", className].filter(Boolean).join(" ");

  return (
    <div className={rootClass}>
      <button
        type="button"
        className="retrieved-accordion__toggle"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span>{title}</span>
        <span className="retrieved-accordion__meta">
          <span className="pill">{items.length}</span>
          <span className={`retrieved-accordion__chevron ${open ? "retrieved-accordion__chevron--open" : ""}`}>
            ▾
          </span>
        </span>
      </button>

      {open && (
        <ul className="retrieved-accordion__list">
          {items.map((item, i) => {
            const typeColor = TYPE_COLORS[item.type] ?? "#4a4a4a";
            const similarityPct = Math.round((item.similarity ?? 0) * 100);
            return (
              <li key={i} className="retrieved-accordion__item">
                <p className="retrieved-accordion__problem">{item.problem}</p>
                <div className="problem-meta">
                  <span
                    className="pill"
                    style={{ background: typeColor + "22", color: typeColor }}
                  >
                    {item.type}
                  </span>
                  <span className="pill pill--label">
                    Severity <ScaleDots value={item.severity} />
                  </span>
                  <span className="pill pill--label">
                    Frequency <ScaleDots value={item.frequency} />
                  </span>
                  <span className="pill pill--label">
                    {item.source}
                  </span>
                  <span className="pill pill--label">
                    {similarityPct}% match
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default RetrievedContextAccordion;
