import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import * as api from "../api";
import { StoryCard } from "../components/StoryCard";

type Story = {
  status: string;
  input_cards: { title: string; body: string; icon?: string }[];
  processing_cards: { title: string; body: string; icon?: string }[];
};

export function ProcessingPage() {
  const { jobId: routeJobId } = useParams();
  const jobId = routeJobId || sessionStorage.getItem("skypipe_last_job") || "";
  const navigate = useNavigate();
  const [story, setStory] = useState<Story | null>(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!jobId) {
      navigate("/app/input");
      return;
    }
    let alive = true;
    const tick = async () => {
      try {
        const j = await api.getJob(jobId);
        if (!alive) return;
        setProgress(j.progress_pct);
        setStatus(j.status);
        const s = await api.getStory(jobId);
        if (!alive) return;
        setStory(s);
        if (j.status === "completed") {
          sessionStorage.setItem("skypipe_last_job", jobId);
          setDone(true);
        }
        if (j.status === "failed") {
          sessionStorage.setItem("skypipe_last_job", jobId);
        }
      } catch {
        /* ignore poll errors */
      }
    };
    tick();
    const id = setInterval(tick, 900);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [jobId, navigate]);

  if (!jobId) return null;

  return (
    <div className="mx-auto max-w-6xl space-y-10">
      <div className="text-center">
        <h2 className="font-display text-4xl uppercase text-white md:text-5xl">
          Processing stage
        </h2>
        <p className="mt-3 text-white/65">
          Apache Spark is analysing your file in parallel. The cards below describe each processing step.
        </p>
        <div className="mx-auto mt-6 max-w-lg">
          <div className="mb-2 flex justify-between text-xs uppercase tracking-widest text-white/50">
            <span>{status}</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="h-3 overflow-hidden rounded-full bg-white/10">
            <motion.div
              className="h-full bg-gradient-to-r from-cyan-400 via-fuchsia-500 to-purple-500"
              animate={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {story?.input_cards?.length ? (
        <section>
          <h3 className="mb-4 font-display text-xl uppercase tracking-[0.2em] text-white/80">
            Input stage activity
          </h3>
          <div className="grid gap-4 md:grid-cols-3">
            {story.input_cards.map((c, i) => (
              <StoryCard key={i} {...c} delay={i * 0.06} />
            ))}
          </div>
        </section>
      ) : null}

      {story?.processing_cards?.length ? (
        <section>
          <h3 className="mb-4 font-display text-xl uppercase tracking-[0.2em] text-white/80">
            Spark engine adaptive steps
          </h3>
          <div className="grid gap-4 md:grid-cols-2">
            {story.processing_cards.map((c, i) => (
              <StoryCard key={i} {...c} delay={i * 0.05} />
            ))}
          </div>
        </section>
      ) : null}

      {status === "failed" && (
        <p className="text-center text-rose-300">
          Job failed. Open <strong>Results</strong> from the menu if available or retry upload. Check API logs
          for Spark/Java errors.
        </p>
      )}

      {done && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center gap-4"
        >
          <p className="font-display text-2xl uppercase text-cyan-300">Processing complete</p>
          <button
            type="button"
            onClick={() => navigate(`/app/results?job=${jobId}`)}
            className="rounded-xl bg-gradient-to-r from-fuchsia-600 to-cyan-500 px-10 py-4 font-display uppercase tracking-widest text-white shadow-lg"
          >
            View results & charts
          </button>
        </motion.div>
      )}
    </div>
  );
}
