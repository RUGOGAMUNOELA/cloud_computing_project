import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  AreaChart,
  Area,
  Legend,
  Cell,
} from "recharts";
import * as api from "../api";
import { StoryCard } from "../components/StoryCard";

const COLORS = ["#00d4ff", "#ff2d95", "#a855f7", "#22d3ee", "#f472b6"];

function NumericOverview({ stats }: { stats: Record<string, unknown>[] }) {
  const data = (stats || []).map((s) => ({
    column: String(s.column).slice(0, 14),
    average: Number(s.mean) || 0,
    minimum: Number(s.min) || 0,
    maximum: Number(s.max) || 0,
  }));
  if (!data.length) return null;
  return (
    <div className="glass-panel p-4 md:p-6 lg:col-span-2">
      <h4 className="mb-2 font-display text-lg uppercase text-white">Numeric overview</h4>
      <p className="mb-4 text-xs text-white/55">
        Compare typical value (average) with the spread (min → max) for each number column.
      </p>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
          <XAxis dataKey="column" tick={{ fill: "rgba(255,255,255,0.65)", fontSize: 11 }} />
          <YAxis tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.2)" }}
            labelStyle={{ color: "#fff" }}
          />
          <Legend wrapperStyle={{ color: "#fff" }} />
          <Bar dataKey="minimum" fill="#6b21a8" name="Min" radius={[4, 4, 0, 0]} />
          <Bar dataKey="average" fill="#00d4ff" name="Average" radius={[4, 4, 0, 0]} />
          <Bar dataKey="maximum" fill="#ff2d95" name="Max" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function CategoryBars({
  column,
  rows,
}: {
  column: string;
  rows: { value: string; count: number }[];
}) {
  const data = rows.map((r) => ({ name: String(r.value).slice(0, 18), count: r.count }));
  return (
    <div className="glass-panel p-4 md:p-6">
      <h4 className="mb-2 font-display text-lg uppercase text-white">{column}</h4>
      <p className="mb-4 text-xs text-white/55">Top answers in your file for this text column.</p>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
          <XAxis dataKey="name" tick={{ fill: "rgba(255,255,255,0.65)", fontSize: 11 }} />
          <YAxis tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.2)" }}
            labelStyle={{ color: "#fff" }}
          />
          <Bar dataKey="count" radius={[8, 8, 0, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function AggregatedValuesPanel({ result }: { result: Record<string, unknown> }) {
  const numeric = (result.numeric_stats as Record<string, unknown>[]) || [];
  const categorical =
    (result.categorical_top as { column: string; top_values: { value: string; count: number }[] }[]) || [];
  const rowCount = Number(result.row_count) || 0;
  if (!numeric.length && !categorical.length && !rowCount) return null;

  return (
    <section className="glass-panel p-6 md:p-8">
      <h3 className="mb-2 font-display text-xl uppercase tracking-[0.15em] text-cyan-200">
        Aggregated values (computed by the pipeline)
      </h3>
      <p className="mb-6 text-sm text-white/70">
        These are real aggregate outputs generated from your uploaded dataset after distributed Spark
        processing.
      </p>

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-white/10 bg-black/20 p-4">
          <p className="text-xs uppercase tracking-widest text-white/45">Rows processed</p>
          <p className="mt-2 font-display text-3xl text-fuchsia-300">{rowCount.toLocaleString()}</p>
        </div>
        <div className="rounded-lg border border-white/10 bg-black/20 p-4">
          <p className="text-xs uppercase tracking-widest text-white/45">Numeric columns analyzed</p>
          <p className="mt-2 font-display text-3xl text-cyan-300">{numeric.length}</p>
        </div>
        <div className="rounded-lg border border-white/10 bg-black/20 p-4">
          <p className="text-xs uppercase tracking-widest text-white/45">Categorical columns analyzed</p>
          <p className="mt-2 font-display text-3xl text-violet-300">{categorical.length}</p>
        </div>
      </div>

      {numeric.length > 0 && (
        <>
          <h4 className="mb-3 font-display text-sm uppercase tracking-widest text-white/55">
            Numeric aggregates
          </h4>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {numeric.slice(0, 6).map((block, i) => (
              <div key={i} className="rounded-lg border border-white/10 bg-black/30 p-3 text-xs">
                <p className="mb-2 font-semibold uppercase tracking-wider text-white/75">
                  {String(block.column || `metric_${i + 1}`)}
                </p>
                <p className="text-white/70">Mean: {Number(block.mean ?? 0).toFixed(3)}</p>
                <p className="text-white/70">Min: {Number(block.min ?? 0).toFixed(3)}</p>
                <p className="text-white/70">Max: {Number(block.max ?? 0).toFixed(3)}</p>
                <p className="text-white/70">Std dev: {Number(block.stddev ?? 0).toFixed(3)}</p>
              </div>
            ))}
          </div>
        </>
      )}

      {categorical.length > 0 && (
        <>
          <h4 className="mb-3 mt-6 font-display text-sm uppercase tracking-widest text-white/55">
            Categorical top values
          </h4>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {categorical.slice(0, 6).map((block, i) => {
              const top = block.top_values?.[0];
              return (
                <div key={i} className="rounded-lg border border-white/10 bg-black/30 p-3 text-xs">
                  <p className="mb-2 font-semibold uppercase tracking-wider text-white/75">{block.column}</p>
                  <p className="text-white/70">Most frequent: {top?.value ?? "not available"}</p>
                  <p className="text-white/70">Count: {top?.count ?? 0}</p>
                </div>
              );
            })}
          </div>
        </>
      )}
    </section>
  );
}

type WarehouseLayersPayload = {
  ok?: boolean;
  flow?: string;
  tables?: Record<string, string | null | undefined>;
  example_queries?: string[];
  example_cli?: string;
  error?: string;
};

function WarehouseLayersPanel({ layers }: { layers: WarehouseLayersPayload | null | undefined }) {
  if (!layers) return null;
  if (!layers.ok) {
    return (
      <section className="glass-panel p-6">
        <h3 className="mb-2 font-display text-xl uppercase tracking-[0.15em] text-amber-200/90">
          Layered warehouse
        </h3>
        <p className="text-sm text-white/70">
          Medallion tables were not built for this run: {layers.error || "unknown error"} (Spark results above are still
          valid).
        </p>
      </section>
    );
  }
  const t = layers.tables || {};
  const queries = layers.example_queries || [];
  return (
    <section className="glass-panel p-6 md:p-8">
      <h3 className="mb-2 font-display text-xl uppercase tracking-[0.15em] text-cyan-200">
        DuckDB layered warehouse (connected to this job)
      </h3>
      <p className="mb-6 text-sm text-white/70">
        After Spark finished, the API loaded your file into the same <strong className="text-fuchsia-300">warehouse.duckdb</strong> file
        using schemas <span className="font-mono text-cyan-200/90">raw_data</span>,{" "}
        <span className="font-mono text-cyan-200/90">processed</span>, and{" "}
        <span className="font-mono text-cyan-200/90">analytics</span>. This mirrors what you see in the story cards
        below.
      </p>
      {layers.flow && <p className="mb-4 text-xs uppercase tracking-widest text-white/45">{layers.flow}</p>}
      <div className="mb-6 grid gap-3 sm:grid-cols-3">
        {[
          ["Raw (bronze)", t.raw],
          ["Processed (silver)", t.processed],
          ["Analytics mart", t.analytics],
        ].map(([label, fq]) => (
          <div key={label} className="rounded-lg border border-white/10 bg-black/20 p-3">
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-white/50">{label}</p>
            <p className="break-all font-mono text-[11px] text-emerald-200/90">{fq || "not available"}</p>
          </div>
        ))}
      </div>
      {(t.dimension || t.fact) && (
        <div className="mb-6 grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-white/10 bg-black/20 p-3">
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-white/50">Dimension</p>
            <p className="break-all font-mono text-[11px] text-violet-200/90">{t.dimension || "not available"}</p>
          </div>
          <div className="rounded-lg border border-white/10 bg-black/20 p-3">
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-white/50">Fact</p>
            <p className="break-all font-mono text-[11px] text-violet-200/90">{t.fact || "not available"}</p>
          </div>
        </div>
      )}
      {layers.example_cli && (
        <p className="mb-4 font-mono text-xs text-white/60">
          CLI: <span className="text-cyan-200/80">{layers.example_cli}</span>
        </p>
      )}
      {queries.length > 0 && (
        <>
          <h4 className="mb-2 font-display text-sm uppercase tracking-widest text-white/55">Example SQL</h4>
          <ul className="space-y-3">
            {queries.map((q, i) => (
              <li key={i}>
                <pre className="overflow-x-auto rounded-md border border-white/10 bg-black/40 p-3 font-mono text-[11px] leading-relaxed text-cyan-100/85">
                  {q}
                </pre>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function DayArea({ column, points }: { column: string; points: { date: string; count: number }[] }) {
  const data = (points || []).map((p) => ({ t: p.date, c: p.count }));
  if (data.length < 2) return null;
  return (
    <div className="glass-panel p-4 md:p-6">
      <h4 className="mb-2 font-display text-lg uppercase text-white">{column} activity over time</h4>
      <p className="mb-4 text-xs text-white/55">Each point is how many rows occurred on that day.</p>
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id={`g-${column}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00d4ff" stopOpacity={0.8} />
              <stop offset="100%" stopColor="#a855f7" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
          <XAxis dataKey="t" tick={{ fill: "rgba(255,255,255,0.6)", fontSize: 10 }} />
          <YAxis tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.2)" }}
          />
          <Area type="monotone" dataKey="c" stroke="#00d4ff" fillOpacity={1} fill={`url(#g-${column})`} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ResultsPage() {
  const [sp] = useSearchParams();
  const jobId = sp.get("job") || sessionStorage.getItem("skypipe_last_job") || "";
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null);
  const [story, setStory] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!jobId) return;
    api
      .getResults(jobId)
      .then(setPayload)
      .catch((e) => setErr(String(e)));
    api
      .getStory(jobId)
      .then(setStory)
      .catch(() => {});
  }, [jobId]);

  if (!jobId) {
    return (
      <p className="text-center text-white/60">
        Run a job from <strong>Input</strong> first. When it finishes, you will land here automatically.
      </p>
    );
  }

  const result = (payload?.result as Record<string, unknown>) || {};
  const numeric = (result.numeric_stats as Record<string, unknown>[]) || [];
  const cats = (result.categorical_top as { column: string; top_values: { value: string; count: number }[] }[]) || [];
  const dts = (result.datetime_trends as { column: string; by_day: { date: string; count: number }[] }[]) || [];

  return (
    <div className="mx-auto max-w-6xl space-y-12">
      <div className="text-center">
        <h2 className="font-display text-4xl uppercase text-white md:text-5xl">
          Results & warehouse
        </h2>
        <p className="mt-3 text-white/65">
          Spark charts below; each successful run also builds layered DuckDB tables (raw → processed → analytics) that you
          can inspect on this page and in the DuckDB CLI.
        </p>
      </div>

      {err && <p className="text-center text-rose-300">{err}</p>}

      {story && (
        <section className="space-y-4">
          <h3 className="font-display text-xl uppercase tracking-[0.2em] text-white/80">
            Plain language takeaways
          </h3>
          <div className="grid gap-4 md:grid-cols-2">
            {(story.chart_insights as { title: string; body: string }[])?.map((c, i) => (
              <StoryCard key={i} title={c.title} body={c.body} icon="activity" delay={i * 0.04} />
            ))}
          </div>
        </section>
      )}

      <section className="grid gap-6 lg:grid-cols-2">
        <NumericOverview stats={numeric} />
        {cats.map((block, i) => (
          <CategoryBars key={i} column={block.column} rows={block.top_values || []} />
        ))}
        {dts.map((block, i) => (
          <DayArea key={i} column={block.column} points={block.by_day || []} />
        ))}
      </section>

      <AggregatedValuesPanel result={result} />

      <WarehouseLayersPanel layers={payload?.warehouse_layers as WarehouseLayersPayload | undefined} />

      {story && (
        <section>
          <h3 className="mb-4 font-display text-xl uppercase tracking-[0.2em] text-white/80">
            Where your processed data lives
          </h3>
          <div className="grid gap-4 md:grid-cols-2">
            {(story.results_cards as { title: string; body: string; icon?: string }[])?.map((c, i) => (
              <StoryCard key={i} {...c} delay={i * 0.06} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
