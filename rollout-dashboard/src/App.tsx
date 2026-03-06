import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

type Rollout = {
  id: string;
  sample_id: number | null;
  problem_id?: number | null;
  reward: number | null;
  metrics?: Record<string, number>;
  info?: Record<string, unknown> | null;
  timing_ms?: Record<string, number> | null;
  messages?: {
    system?: string;
    user?: string;
    assistant?: string;
  };
};

type StepSummary = {
  count: number;
  reward_mean: number | null;
  reward_min: number | null;
  reward_max: number | null;
  misaligned_mean: number | null;
  alignment_mean: number | null;
};

type Run = {
  id: string;
  name: string;
  status: string;
  model: string;
  environment: string;
  max_steps: number;
  rollouts_per_example: number;
  rollouts_by_step: Record<string, Rollout[]>;
  step_summary: Record<string, StepSummary>;
  created_at: string | null;
  completed_at: string | null;
};

type DashboardData = {
  generated_at: string | null;
  selected_steps: number[];
  runs: Run[];
};

type ThemePreference = "system" | "light" | "dark";
type ResolvedTheme = "light" | "dark";
type RolloutDialogState = { run: Run; step: number; rollout: Rollout } | null;
type SelectedRolloutEntry = {
  run_id: string;
  run_name: string;
  step: number;
  rollout: Rollout;
};

const THEME_STORAGE_KEY = "rollout-dashboard-theme";
const THEME_CYCLE: ThemePreference[] = ["system", "light", "dark"];

function formatNumber(value: number | null | undefined, digits = 3) {
  if (typeof value !== "number" || Number.isNaN(value)) return "n/a";
  return value.toFixed(digits);
}

function shortRunName(name: string) {
  return name.replace(/\(resumed from step.*\)/i, "").trim();
}

function dashboardUrl(runId: string) {
  return `https://app.primeintellect.ai/dashboard/training/${runId}`;
}

function getDefaultSteps(run: Run | null, preferredSteps: number[]) {
  if (!run) return [] as number[];
  const availableSteps = Object.keys(run.rollouts_by_step)
    .map((step) => Number(step))
    .filter((step) => Number.isFinite(step))
    .sort((a, b) => a - b);

  const preferred = preferredSteps.filter((step) =>
    availableSteps.includes(step),
  );
  if (preferred.length > 0) return preferred;
  if (availableSteps.length > 3) return availableSteps.slice(-3);
  return availableSteps;
}

function getDefaultStep(run: Run | null, preferredSteps: number[]) {
  const defaults = getDefaultSteps(run, preferredSteps);
  return defaults.length > 0 ? defaults[defaults.length - 1] : null;
}

function getSystemTheme(): ResolvedTheme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function getStoredThemePreference(): ThemePreference {
  if (typeof window === "undefined") return "system";
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  return stored === "light" || stored === "dark" || stored === "system"
    ? stored
    : "system";
}

function formatThemeLabel(
  preference: ThemePreference,
  systemTheme: ResolvedTheme,
) {
  if (preference === "system") return `System (${systemTheme})`;
  return preference === "dark" ? "Dark" : "Light";
}

function getRewardColorClass(
  reward: number | null | undefined,
  runMaxReward: number | null,
) {
  if (typeof reward !== "number" || Number.isNaN(reward))
    return "text-muted-foreground";
  if (runMaxReward === null || runMaxReward <= 0)
    return "text-muted-foreground";

  const ratio = reward / runMaxReward;
  if (ratio >= 0.85) return "text-emerald-600 dark:text-emerald-400";
  if (ratio >= 0.6) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

function getRolloutSelectionKey(
  runId: string,
  step: number,
  rolloutId: string,
) {
  return `${runId}::${step}::${rolloutId}`;
}

export function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [selectedStep, setSelectedStep] = useState<number | null>(null);
  const [themePreference, setThemePreference] = useState<ThemePreference>(() =>
    getStoredThemePreference(),
  );
  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>(() =>
    getSystemTheme(),
  );
  const [dialogData, setDialogData] = useState<RolloutDialogState>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedRollouts, setSelectedRollouts] = useState<
    Record<string, SelectedRolloutEntry>
  >({});
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "error">(
    "idle",
  );
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    fetch("/mock-data.json")
      .then(async (res) => {
        if (!res.ok)
          throw new Error(`Failed to load mock-data.json (${res.status})`);
        return (await res.json()) as DashboardData;
      })
      .then((json) => {
        if (!mounted) return;
        setData(json);
        const firstRun = json.runs[0] || null;
        setSelectedRunId(firstRun?.id || "");
        setSelectedStep(getDefaultStep(firstRun, json.selected_steps || []));
      })
      .catch((error: unknown) => {
        if (!mounted) return;
        setLoadError(error instanceof Error ? error.message : "Unknown error");
      })
      .finally(() => {
        if (!mounted) return;
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setSystemTheme(mediaQuery.matches ? "dark" : "light");
    update();

    mediaQuery.addEventListener("change", update);
    return () => mediaQuery.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(THEME_STORAGE_KEY, themePreference);
    const resolvedTheme =
      themePreference === "system" ? systemTheme : themePreference;
    document.documentElement.classList.toggle("dark", resolvedTheme === "dark");
  }, [themePreference, systemTheme]);

  const selectedRun = useMemo(
    () => data?.runs.find((run) => run.id === selectedRunId) || null,
    [data, selectedRunId],
  );

  const availableSteps = useMemo(() => {
    if (!selectedRun) return [] as number[];
    return Object.keys(selectedRun.rollouts_by_step)
      .map((step) => Number(step))
      .filter((step) => Number.isFinite(step))
      .sort((a, b) => a - b);
  }, [selectedRun]);

  const effectiveStep = useMemo(() => {
    if (availableSteps.length === 0) return null;
    if (selectedStep !== null && availableSteps.includes(selectedStep))
      return selectedStep;
    return availableSteps[availableSteps.length - 1];
  }, [availableSteps, selectedStep]);

  const effectiveStepIndex = useMemo(() => {
    if (effectiveStep === null) return 0;
    const index = availableSteps.indexOf(effectiveStep);
    return index >= 0 ? index : 0;
  }, [availableSteps, effectiveStep]);

  const activeGroup = useMemo(() => {
    if (!selectedRun || effectiveStep === null) return null;
    return {
      step: effectiveStep,
      summary: selectedRun.step_summary[String(effectiveStep)],
      rollouts: [
        ...(selectedRun.rollouts_by_step[String(effectiveStep)] || []),
      ],
    };
  }, [selectedRun, effectiveStep]);

  const runMaxReward = useMemo(() => {
    if (!selectedRun) return null;

    const fromStepSummary = Object.values(selectedRun.step_summary || {})
      .map((summary) => summary?.reward_max)
      .filter(
        (value): value is number =>
          typeof value === "number" && Number.isFinite(value),
      );
    if (fromStepSummary.length > 0) return Math.max(...fromStepSummary);

    const fromRollouts = Object.values(selectedRun.rollouts_by_step || {})
      .flat()
      .map((rollout) => rollout?.reward)
      .filter(
        (value): value is number =>
          typeof value === "number" && Number.isFinite(value),
      );
    if (fromRollouts.length > 0) return Math.max(...fromRollouts);

    return null;
  }, [selectedRun]);

  const selectedCount = Object.keys(selectedRollouts).length;

  const visibleSelection = useMemo(() => {
    if (!selectedRun || !activeGroup) {
      return { total: 0, selected: 0, allSelected: false };
    }

    let selected = 0;
    for (const rollout of activeGroup.rollouts) {
      const key = getRolloutSelectionKey(
        selectedRun.id,
        activeGroup.step,
        rollout.id,
      );
      if (selectedRollouts[key]) selected += 1;
    }

    const total = activeGroup.rollouts.length;
    return {
      total,
      selected,
      allSelected: total > 0 && selected === total,
    };
  }, [selectedRun, activeGroup, selectedRollouts]);

  function toggleRolloutSelection(
    run: Run,
    step: number,
    rollout: Rollout,
    checked: boolean,
  ) {
    const key = getRolloutSelectionKey(run.id, step, rollout.id);
    setSelectedRollouts((current) => {
      const next = { ...current };
      if (checked) {
        next[key] = {
          run_id: run.id,
          run_name: run.name,
          step,
          rollout,
        };
      } else {
        delete next[key];
      }
      return next;
    });
    setCopyStatus("idle");
  }

  function toggleVisibleSelection() {
    if (!selectedRun || !activeGroup) return;
    setSelectedRollouts((current) => {
      const next = { ...current };
      const shouldSelect = !visibleSelection.allSelected;
      for (const rollout of activeGroup.rollouts) {
        const key = getRolloutSelectionKey(
          selectedRun.id,
          activeGroup.step,
          rollout.id,
        );
        if (shouldSelect) {
          next[key] = {
            run_id: selectedRun.id,
            run_name: selectedRun.name,
            step: activeGroup.step,
            rollout,
          };
        } else {
          delete next[key];
        }
      }
      return next;
    });
    setCopyStatus("idle");
  }

  async function copySelectedRollouts() {
    const items = Object.values(selectedRollouts).sort((a, b) => {
      if (a.run_id !== b.run_id) return a.run_id.localeCompare(b.run_id);
      if (a.step !== b.step) return a.step - b.step;
      return (a.rollout.sample_id ?? 0) - (b.rollout.sample_id ?? 0);
    });

    const runById = new Map((data?.runs || []).map((run) => [run.id, run]));
    const lines: string[] = [];
    lines.push("# RL Studio Export");
    lines.push(`Exported At: ${new Date().toISOString()}`);
    lines.push(`Selected Rollouts: ${items.length}`);
    lines.push("");

    const uniqueRunIds = [...new Set(items.map((item) => item.run_id))];
    lines.push("## Run Summary");
    for (const runId of uniqueRunIds) {
      const run = runById.get(runId);
      lines.push(`- Run ID: ${runId}`);
      if (run) {
        lines.push(`  - Name: ${run.name}`);
        lines.push(`  - Environment: ${run.environment}`);
        lines.push(`  - Model: ${run.model}`);
        lines.push(`  - Status: ${run.status}`);
        lines.push(`  - Max Steps: ${run.max_steps}`);
      }
    }
    lines.push("");

    for (const runId of uniqueRunIds) {
      const run = runById.get(runId);
      lines.push(`## Run ${runId}`);
      if (run) {
        lines.push(`- Name: ${run.name}`);
        lines.push(`- Environment: ${run.environment}`);
        lines.push(`- Model: ${run.model}`);
        lines.push(`- Status: ${run.status}`);
      }
      lines.push("");

      const runItems = items.filter((item) => item.run_id === runId);
      const stepGroups = [...new Set(runItems.map((item) => item.step))].sort(
        (a, b) => a - b,
      );

      for (const step of stepGroups) {
        lines.push(`### Checkpoint ${step}`);
        lines.push("");

        const stepItems = runItems
          .filter((item) => item.step === step)
          .sort(
            (a, b) => (a.rollout.sample_id ?? 0) - (b.rollout.sample_id ?? 0),
          );

        stepItems.forEach((item, index) => {
          const messages = item.rollout.messages || {};
          lines.push(
            `#### Rollout ${index + 1} (sample_id=${item.rollout.sample_id ?? "n/a"}, problem_id=${
              item.rollout.problem_id ?? "n/a"
            }, reward=${formatNumber(item.rollout.reward)})`,
          );
          lines.push("");

          lines.push("System:");
          lines.push("````text");
          lines.push(messages.system || "");
          lines.push("````");
          lines.push("");

          lines.push("User:");
          lines.push("````text");
          lines.push(messages.user || "");
          lines.push("````");
          lines.push("");

          lines.push("Assistant:");
          lines.push("````text");
          lines.push(messages.assistant || "");
          lines.push("````");
          lines.push("");
        });
      }
    }

    const text = lines.join("\n");

    try {
      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else if (typeof document !== "undefined") {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      } else {
        throw new Error("Clipboard unavailable");
      }
      setCopyStatus("copied");
    } catch {
      setCopyStatus("error");
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Loading dashboard...
      </div>
    );
  }

  if (loadError || !data) {
    return (
      <div className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-6">
        <Card className="w-full border py-0">
          <CardHeader className="pt-4">
            <CardTitle>Failed to load dashboard data</CardTitle>
            <CardDescription>
              {loadError || "No data available."}
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-muted/30">
      <div className="mx-auto max-w-[1900px] p-4 md:p-6">
        <header className="mb-3 flex items-center justify-between gap-3">
          <h1 className="text-sm font-semibold tracking-tight md:text-base">
            RL Studio
          </h1>
          <Button
            type="button"
            size="xs"
            variant="outline"
            onClick={() => {
              setThemePreference((current) => {
                const index = THEME_CYCLE.indexOf(current);
                return THEME_CYCLE[(index + 1) % THEME_CYCLE.length];
              });
            }}
          >
            Theme: {formatThemeLabel(themePreference, systemTheme)}
          </Button>
        </header>

        <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="rounded-none border bg-card">
            <div className="border-b px-4 py-3">
              <h2 className="text-sm font-semibold">Runs</h2>
              <p className="text-xs text-muted-foreground">
                {data.runs.length} runs · data snapshot{" "}
                {data.generated_at || "n/a"}
              </p>
            </div>
            <div className="max-h-[calc(100vh-170px)] space-y-2 overflow-auto p-2">
              {data.runs.map((run) => {
                const selected = run.id === selectedRunId;
                return (
                  <button
                    key={run.id}
                    type="button"
                    onClick={() => {
                      setSelectedRunId(run.id);
                      setSelectedStep(
                        getDefaultStep(run, data.selected_steps || []),
                      );
                    }}
                    className={cn(
                      "block w-full text-left transition",
                      selected ? "opacity-100" : "opacity-85 hover:opacity-100",
                    )}
                  >
                    <Card
                      className={cn(
                        "border py-0",
                        selected
                          ? "border-primary/70 bg-primary/5"
                          : "border-border bg-card",
                      )}
                    >
                      <CardHeader className="pt-3 pb-2">
                        <div className="flex items-start justify-between gap-2">
                          <CardTitle className="line-clamp-2 text-xs leading-snug">
                            <a
                              href={dashboardUrl(run.id)}
                              target="_blank"
                              rel="noreferrer"
                              className="underline-offset-2 hover:underline"
                              onClick={(event) => event.stopPropagation()}
                            >
                              {shortRunName(run.name)}
                            </a>
                          </CardTitle>
                          <Badge
                            variant={selected ? "default" : "outline"}
                            className="text-[10px]"
                          >
                            {run.status.toLowerCase()}
                          </Badge>
                        </div>
                        <CardDescription className="line-clamp-1 text-[11px]">
                          {run.model}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="pb-3">
                        <div className="grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
                          <span>env</span>
                          <span className="truncate text-right text-foreground">
                            {run.environment}
                          </span>
                          <span>max steps</span>
                          <span className="text-right text-foreground">
                            {run.max_steps}
                          </span>
                        </div>
                      </CardContent>
                    </Card>
                  </button>
                );
              })}
            </div>
          </aside>

          <section className="space-y-4">
            {selectedRun ? (
              <>
                <Card className="border py-0">
                  <CardHeader className="pt-3 pb-3">
                    <CardTitle className="text-sm">
                      <a
                        href={dashboardUrl(selectedRun.id)}
                        target="_blank"
                        rel="noreferrer"
                        className="underline-offset-2 hover:underline"
                      >
                        {shortRunName(selectedRun.name)}
                      </a>
                    </CardTitle>
                    <CardDescription className="text-[11px]">
                      {selectedRun.id} · {selectedRun.environment} ·{" "}
                      {selectedRun.model}
                    </CardDescription>
                    <div className="mt-2">
                      <p className="mb-2 text-xs text-muted-foreground">
                        Checkpoints
                      </p>
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            size="xs"
                            disabled={effectiveStepIndex <= 0}
                            onClick={() => {
                              if (effectiveStepIndex <= 0) return;
                              setSelectedStep(
                                availableSteps[effectiveStepIndex - 1] ?? null,
                              );
                            }}
                          >
                            Prev
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            size="xs"
                            disabled={
                              effectiveStepIndex >= availableSteps.length - 1
                            }
                            onClick={() => {
                              if (
                                effectiveStepIndex >=
                                availableSteps.length - 1
                              )
                                return;
                              setSelectedStep(
                                availableSteps[effectiveStepIndex + 1] ?? null,
                              );
                            }}
                          >
                            Next
                          </Button>
                          <span className="text-xs text-muted-foreground">
                            step {effectiveStep ?? "n/a"} (
                            {availableSteps.length === 0
                              ? 0
                              : effectiveStepIndex + 1}
                            /{availableSteps.length})
                          </span>
                        </div>
                        <input
                          type="range"
                          min={0}
                          max={Math.max(availableSteps.length - 1, 0)}
                          value={effectiveStepIndex}
                          onChange={(event) => {
                            const index = Number(event.target.value);
                            setSelectedStep(availableSteps[index] ?? null);
                          }}
                          className="w-full accent-primary"
                          disabled={availableSteps.length <= 1}
                        />
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="pb-3 pt-0">
                    <div className="space-y-2">
                      <p className="text-[11px] text-muted-foreground">
                        Select rollouts and copy them into Codex context.
                      </p>
                      <div className="flex flex-wrap items-center gap-2">
                        <Button
                          type="button"
                          size="xs"
                          variant="outline"
                          onClick={toggleVisibleSelection}
                          disabled={
                            !activeGroup || activeGroup.rollouts.length === 0
                          }
                        >
                          {visibleSelection.allSelected
                            ? "Unselect Visible"
                            : "Select Visible"}
                        </Button>
                        <Button
                          type="button"
                          size="xs"
                          variant="outline"
                          onClick={() => {
                            setSelectedRollouts({});
                            setCopyStatus("idle");
                          }}
                          disabled={selectedCount === 0}
                        >
                          Clear Selected
                        </Button>
                        <Button
                          type="button"
                          size="xs"
                          onClick={copySelectedRollouts}
                          disabled={selectedCount === 0}
                        >
                          Copy Selected ({selectedCount})
                        </Button>
                        <span className="text-[11px] text-muted-foreground">
                          Visible selected: {visibleSelection.selected}/
                          {visibleSelection.total}
                        </span>
                        {copyStatus === "copied" ? (
                          <span className="text-[11px] text-emerald-600 dark:text-emerald-400">
                            Copied.
                          </span>
                        ) : null}
                        {copyStatus === "error" ? (
                          <span className="text-[11px] text-red-600 dark:text-red-400">
                            Copy failed.
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {activeGroup ? (
                  <Card key={activeGroup.step} className="border py-0">
                    <CardHeader className="pt-4 pb-3">
                      <div className="flex items-center justify-between gap-2">
                        <CardTitle className="text-sm">
                          Checkpoint step {activeGroup.step}
                        </CardTitle>
                        <Badge variant="outline">
                          {activeGroup.rollouts.length} rollouts
                        </Badge>
                      </div>
                      <CardDescription className="flex flex-wrap items-center gap-3 text-[11px]">
                        <span>
                          mean reward:{" "}
                          {formatNumber(activeGroup.summary?.reward_mean)}
                        </span>
                        <span>
                          misaligned mean:{" "}
                          {formatNumber(activeGroup.summary?.misaligned_mean)}
                        </span>
                        <span>
                          alignment mean:{" "}
                          {formatNumber(activeGroup.summary?.alignment_mean)}
                        </span>
                      </CardDescription>
                    </CardHeader>

                    <CardContent className="pb-4">
                      {activeGroup.rollouts.length === 0 ? (
                        <div className="border border-dashed px-3 py-5 text-center text-xs text-muted-foreground">
                          No rollouts for this checkpoint.
                        </div>
                      ) : (
                        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                          {activeGroup.rollouts.map((rollout) => {
                            const rewardColorClass = getRewardColorClass(
                              rollout.reward,
                              runMaxReward,
                            );
                            const selectionKey = getRolloutSelectionKey(
                              selectedRun.id,
                              activeGroup.step,
                              rollout.id,
                            );
                            const isSelected = Boolean(
                              selectedRollouts[selectionKey],
                            );
                            const assistantText =
                              rollout.messages?.assistant || "";
                            return (
                              <div key={rollout.id} className="relative">
                                <div className="absolute left-2 top-2 z-10">
                                  <Checkbox
                                    checked={isSelected}
                                    onCheckedChange={(checked) => {
                                      toggleRolloutSelection(
                                        selectedRun,
                                        activeGroup.step,
                                        rollout,
                                        checked === true,
                                      );
                                    }}
                                    onClick={(event) => event.stopPropagation()}
                                    aria-label={`Select rollout ${rollout.id}`}
                                  />
                                </div>
                                <Card
                                  role="button"
                                  tabIndex={0}
                                  onClick={() => {
                                    setDialogData({
                                      run: selectedRun,
                                      step: activeGroup.step,
                                      rollout,
                                    });
                                    setDialogOpen(true);
                                  }}
                                  onKeyDown={(event) => {
                                    if (
                                      event.key === "Enter" ||
                                      event.key === " "
                                    ) {
                                      event.preventDefault();
                                      setDialogData({
                                        run: selectedRun,
                                        step: activeGroup.step,
                                        rollout,
                                      });
                                      setDialogOpen(true);
                                    }
                                  }}
                                  className={cn(
                                    "h-full cursor-pointer border border-border py-0 transition hover:border-primary/70",
                                    isSelected
                                      ? "border-primary ring-1 ring-primary/30"
                                      : "",
                                  )}
                                >
                                  <CardContent className="p-3">
                                    <div className="mb-2 text-right font-mono text-xs font-semibold">
                                      <span className={rewardColorClass}>
                                        {formatNumber(rollout.reward)}
                                      </span>
                                    </div>
                                    <pre className="max-h-96 overflow-auto whitespace-pre font-mono text-[11px] leading-relaxed [font-variant-ligatures:none]">
                                      {assistantText ||
                                        "(empty assistant output)"}
                                    </pre>
                                  </CardContent>
                                </Card>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ) : (
                  <Card className="border py-0">
                    <CardContent className="p-4 text-xs text-muted-foreground">
                      No checkpoints available for this run.
                    </CardContent>
                  </Card>
                )}
              </>
            ) : (
              <Card className="border py-0">
                <CardHeader className="pt-4">
                  <CardTitle>Select a run</CardTitle>
                  <CardDescription>
                    Choose a run from the left list to view rollout cards.
                  </CardDescription>
                </CardHeader>
              </Card>
            )}
          </section>
        </div>

        <Dialog
          open={dialogOpen}
          onOpenChange={(open) => {
            setDialogOpen(open);
            if (!open) setDialogData(null);
          }}
        >
          <DialogContent className="max-h-[92vh] overflow-auto p-0 sm:max-w-5xl">
            {dialogData ? (
              <>
                <DialogHeader className="border-b px-4 py-3">
                  <DialogTitle className="text-sm">
                    {shortRunName(dialogData.run.name)} · step {dialogData.step}
                  </DialogTitle>
                  <DialogDescription className="text-[11px]">
                    sample {dialogData.rollout.sample_id ?? "?"} · problem{" "}
                    {dialogData.rollout.problem_id ?? "?"}
                  </DialogDescription>
                </DialogHeader>

                <div className="grid gap-4 p-4 md:grid-cols-[1fr_1fr]">
                  <div className="space-y-4">
                    <Card className="border py-0">
                      <CardHeader className="pt-3 pb-2">
                        <CardTitle className="text-xs">
                          Reward Details
                        </CardTitle>
                        <CardDescription className="text-[11px]">
                          total reward:{" "}
                          {formatNumber(dialogData.rollout.reward)}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="pb-3">
                        <pre className="overflow-auto whitespace-pre-wrap border bg-muted/40 p-2 text-[11px] leading-relaxed">
                          {JSON.stringify(
                            {
                              reward: dialogData.rollout.reward,
                              metrics: dialogData.rollout.metrics || {},
                              timing_ms: dialogData.rollout.timing_ms || {},
                            },
                            null,
                            2,
                          )}
                        </pre>
                      </CardContent>
                    </Card>

                    <Card className="border py-0">
                      <CardHeader className="pt-3 pb-2">
                        <CardTitle className="text-xs">
                          Info Object (JSON)
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="pb-3">
                        <pre className="max-h-[340px] overflow-auto whitespace-pre-wrap border bg-muted/40 p-2 text-[11px] leading-relaxed">
                          {JSON.stringify(
                            dialogData.rollout.info || {},
                            null,
                            2,
                          )}
                        </pre>
                      </CardContent>
                    </Card>
                  </div>

                  <div className="space-y-4">
                    <Card className="border py-0">
                      <CardHeader className="pt-3 pb-2">
                        <CardTitle className="text-xs">
                          System Message
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="pb-3">
                        <pre className="max-h-[220px] overflow-auto whitespace-pre-wrap border bg-muted/40 p-2 text-[11px] leading-relaxed">
                          {dialogData.rollout.messages?.system || "(none)"}
                        </pre>
                      </CardContent>
                    </Card>

                    <Card className="border py-0">
                      <CardHeader className="pt-3 pb-2">
                        <CardTitle className="text-xs">User Message</CardTitle>
                      </CardHeader>
                      <CardContent className="pb-3">
                        <pre className="max-h-[220px] overflow-auto whitespace-pre-wrap border bg-muted/40 p-2 text-[11px] leading-relaxed">
                          {dialogData.rollout.messages?.user || "(none)"}
                        </pre>
                      </CardContent>
                    </Card>

                    <Card className="border py-0">
                      <CardHeader className="pt-3 pb-2">
                        <CardTitle className="text-xs">
                          Assistant Completion
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="pb-3">
                        <pre className="max-h-[260px] overflow-auto whitespace-pre border bg-muted/40 p-2 font-mono text-[11px] leading-relaxed [font-variant-ligatures:none]">
                          {dialogData.rollout.messages?.assistant ||
                            "(empty assistant output)"}
                        </pre>
                      </CardContent>
                    </Card>
                  </div>
                </div>

                <DialogFooter className="border-t px-4 py-3" showCloseButton />
              </>
            ) : null}
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}

export default App;
