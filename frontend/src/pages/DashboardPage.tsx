import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import * as api from "../api";
import { StoryCard } from "../components/StoryCard";

export function DashboardPage() {
  const [arch, setArch] = useState<Record<string, { requirement: string; implementation: string }> | null>(null);
  const [caps, setCaps] = useState<Record<string, { title: string; summary: string; details: string[] }> | null>(null);

  useEffect(() => {
    api.architecture().then(setArch).catch(() => setArch(null));
    api.capabilities().then(setCaps).catch(() => setCaps(null));
  }, []);

  const stages = arch
    ? [
        {
          key: "input_stage",
          title: "Input stage",
          icon: "upload",
          to: "/app/input",
          body:
            "Upload a dataset once and SkyPipe stores it in object storage. In Docker this is MinIO with the S3 API, and in cloud mode Google Cloud Storage is used.",
          tech: arch.input_stage.implementation,
        },
        {
          key: "processing_stage",
          title: "Processing stage",
          icon: "cpu",
          to: "/app/processing",
          body:
            "SkyPipe runs Apache Spark with PySpark to process data in parallel, infer schema types, and compute adaptive statistics for your file.",
          tech: arch.processing_stage.implementation,
        },
        {
          key: "result_stage",
          title: "Results stage",
          icon: "warehouse",
          to: "/app/results",
          body:
            "Processed outputs are written to DuckDB in layered schemas for raw data, processed data, and analytics so you can query both raw and aggregated values.",
          tech: arch.result_stage.implementation,
        },
      ]
    : [];

  return (
    <div className="mx-auto max-w-5xl space-y-10">
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <h2 className="font-display text-4xl uppercase tracking-tight text-white md:text-5xl">
          SkyPipe: A Distributed Data Processing Pipeline
        </h2>
        <p className="mx-auto mt-4 max-w-2xl font-sans text-white/70">
          SkyPipe lets you ingest structured datasets, process them with Spark, and publish query-ready
          analytics to DuckDB. Each stage below opens its page and explains the technologies making that
          stage possible.
        </p>
      </motion.div>

      <div className="grid gap-6 md:grid-cols-3">
        {stages.map((s, i) => (
          <Link key={s.key} to={s.to} className="block transition hover:-translate-y-0.5">
            <StoryCard
              title={s.title}
              icon={s.icon}
              delay={i * 0.08}
              body={`${s.body}\n\nTechnology stack: ${s.tech}`}
            />
          </Link>
        ))}
      </div>

      {caps && (
        <section className="space-y-4">
          <h3 className="font-display text-2xl uppercase tracking-wide text-white">Operational capabilities</h3>
          <div className="grid gap-4 md:grid-cols-3">
            {Object.values(caps).map((c, i) => (
              <StoryCard
                key={c.title}
                title={c.title}
                icon="shield"
                delay={i * 0.06}
                body={`${c.summary}\n${c.details.join("\n")}`}
              />
            ))}
          </div>
        </section>
      )}

      {!arch && (
        <p className="text-center text-white/50">Could not load architecture (check API).</p>
      )}
    </div>
  );
}
