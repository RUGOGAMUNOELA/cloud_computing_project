import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import * as api from "../api";
import { Upload } from "lucide-react";

export function InputPage() {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  async function submit() {
    if (!file) return;
    setBusy(true);
    setErr("");
    try {
      const { job_id } = await api.createJob(file);
      navigate(`/app/processing/${job_id}`);
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <div className="text-center">
        <h2 className="font-display text-4xl uppercase text-white md:text-5xl">
          Input stage
        </h2>
        <p className="mt-3 text-white/65">
          Upload CSV, Excel, JSON, or Parquet. Files are stored in{" "}
          <strong className="text-cyan-300">distributed object storage</strong> (MinIO in Docker, optional
          GCS in cloud mode) before processing starts.
        </p>
      </div>

      <motion.div
        layout
        className="relative overflow-hidden rounded-3xl border border-white/20 bg-black/25 p-10 backdrop-blur-xl"
      >
        <motion.div
          className="pointer-events-none absolute -left-20 -top-20 h-64 w-64 rounded-full bg-fuchsia-600/30 blur-3xl"
          animate={{ x: [0, 40, 0], y: [0, 30, 0] }}
          transition={{ duration: 8, repeat: Infinity }}
        />
        <motion.div
          className="pointer-events-none absolute -bottom-16 -right-16 h-72 w-72 rounded-full bg-cyan-500/25 blur-3xl"
          animate={{ x: [0, -30, 0], y: [0, -20, 0] }}
          transition={{ duration: 10, repeat: Infinity }}
        />

        <div
          role="button"
          tabIndex={0}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
          className="relative z-10 flex cursor-pointer flex-col items-center rounded-2xl border-2 border-dashed border-white/30 bg-white/5 py-16 text-center transition hover:border-fuchsia-400/60"
        >
          <Upload className="mb-4 h-14 w-14 text-white/80" />
          <p className="font-display text-xl uppercase tracking-wide text-white">
            Drop or click to upload
          </p>
          <p className="mt-2 text-sm text-white/50">
            {file ? file.name : "No file selected yet"}
          </p>
          <input
            ref={inputRef}
            type="file"
            className="hidden"
            accept=".csv,.json,.xlsx,.xls,.parquet"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </div>

        {busy && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="relative z-20 mt-8 space-y-3 text-center"
          >
            <p className="text-sm uppercase tracking-[0.3em] text-cyan-300">
              Ingesting & staging bytes…
            </p>
            <div className="mx-auto h-2 max-w-xs overflow-hidden rounded-full bg-white/10">
              <motion.div
                className="h-full bg-gradient-to-r from-fuchsia-500 to-cyan-400"
                initial={{ width: "0%" }}
                animate={{ width: "100%" }}
                transition={{ duration: 2.2, repeat: Infinity }}
              />
            </div>
          </motion.div>
        )}

        {err && <p className="relative z-20 mt-4 text-center text-rose-300">{err}</p>}

        <motion.button
          disabled={!file || busy}
          whileHover={{ scale: file && !busy ? 1.02 : 1 }}
          onClick={submit}
          className="relative z-20 mt-8 w-full rounded-xl bg-gradient-to-r from-fuchsia-600 to-violet-600 py-4 font-display uppercase tracking-widest text-white disabled:opacity-40"
        >
          Start pipeline
        </motion.button>
      </motion.div>
    </div>
  );
}
