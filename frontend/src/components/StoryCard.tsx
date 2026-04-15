import type React from "react";
import { motion } from "framer-motion";
import * as Lucide from "lucide-react";

const iconMap: Record<string, string> = {
  upload: "Upload",
  database: "Database",
  layers: "Layers",
  cpu: "Cpu",
  search: "Search",
  activity: "Activity",
  share: "Share",
  "bar-chart": "BarChart3",
  warehouse: "Warehouse",
  cloud: "Cloud",
  disc: "Disc3",
  hash: "Hash",
  "git-branch": "GitBranch",
  table: "Table2",
  shield: "ShieldCheck",
};

export function StoryCard({
  title,
  body,
  icon,
  delay = 0,
}: {
  title: string;
  body: string;
  icon?: string;
  delay?: number;
}) {
  const iconName = (icon && iconMap[icon]) || "Sparkles";
  const I =
    (Lucide as unknown as Record<string, React.ComponentType<{ className?: string; strokeWidth?: number }>>)[
      iconName
    ] || Lucide.Sparkles;
  return (
    <motion.article
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.45 }}
      className="glass-panel p-6 text-white"
    >
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-white/40 bg-white/5">
        <I className="h-7 w-7 text-white" strokeWidth={1.5} />
      </div>
      <h3 className="font-display text-lg uppercase tracking-wide text-white">
        {title}
      </h3>
      <p className="mt-2 whitespace-pre-line font-sans text-sm leading-relaxed text-white/85">{body}</p>
    </motion.article>
  );
}
