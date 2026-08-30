import { useEffect, useState, useRef } from "react";
import { useLiveFeed } from "../hooks/useLiveFeed";
import ResponseCard from "./ResponseCard";
import ScoreForm from "./ScoreForm";
import ThemeToggle from "./ThemeToggle";
import { Shield, Sparkles, Layers, Menu, X } from "lucide-react";

export default function Dashboard() {
  const { records, connected } = useLiveFeed(100);
  const [selectedUseCase, setSelectedUseCase] = useState("customer_support");
  const [policies, setPolicies] = useState<
    Record<
      string,
      {
        name: string;
        description: string;
        latency_budget_ms: number;
        score_block_below: number;
        score_log_below: number;
      }
    >
  >({});
  const [showMobileSidebar, setShowMobileSidebar] = useState(false);
  const [metrics, setMetrics] = useState<{
    feedback_coverage_percent: number;
    false_positive_rate: number | null;
    false_negative_rate: number | null;
  } | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/llm/status")
      .then((r) => r.json())
      .then((data) => {
        if (data.policies) {
          setPolicies(data.policies);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetch("/api/metrics")
      .then((r) => r.json())
      .then(setMetrics)
      .catch(() => {});
  }, [records.length]);

  const isEmpty = records.length === 0;

  // Calculate live statistics
  const counts = records.reduce(
    (acc, r) => {
      acc[r.severity] += 1;
      return acc;
    },
    { pass: 0, edit: 0, log: 0, block: 0 } as Record<
      "pass" | "edit" | "log" | "block",
      number
    >,
  );

  const activePolicy = policies[selectedUseCase] || {
    name: "Loading...",
    description: "Loading policy settings...",
    latency_budget_ms: 0,
    score_block_below: 0,
    score_log_below: 0,
  };

  // Scroll to bottom when new records arrive
  useEffect(() => {
    if (!isEmpty) {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [records.length, isEmpty]);

  const SidebarContent = () => (
    <div className="flex flex-col h-full p-5 bg-panel border-r border-hairline/60">
      {/* Brand Logo */}
      <div className="flex items-center gap-2.5 mb-6">
        <Shield className="text-brass" size={22} />
        <span className="font-display text-xl font-bold tracking-tight text-paper">
          ControlPlane <span className="text-brass">Checker</span>
        </span>
      </div>

      {/* Active connection state badge */}
      <div className="flex items-center justify-between bg-ink border border-hairline/60 rounded-xl px-3.5 py-2 mb-6">
        <span className="text-[10px] uppercase font-mono tracking-wider text-muted">
          Gateway Status
        </span>
        <div className="flex items-center gap-2">
          <span
            className={`h-2.5 w-2.5 rounded-full ${connected ? "bg-pass" : "bg-block"}`}
          />
          <span className="font-mono text-xs uppercase text-paper font-semibold">
            {connected ? "Active" : "Offline"}
          </span>
        </div>
      </div>

      {/* Use Case Profile Selector */}
      <div className="mb-6 space-y-2.5">
        <h3 className="text-[9px] uppercase tracking-widest text-muted font-mono font-bold">
          AI Use Case Profile
        </h3>
        <div className="space-y-1.5">
          {Object.keys(policies).map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => {
                setSelectedUseCase(key);
                setShowMobileSidebar(false);
              }}
              className={`w-full text-left px-3.5 py-2.5 rounded-xl border font-mono text-xs transition-all ${
                selectedUseCase === key
                  ? "border-brass bg-brass/10 text-brass font-semibold"
                  : "border-hairline bg-ink/20 text-muted hover:border-brass/35 hover:text-paper"
              }`}
            >
              {policies[key].name}
            </button>
          ))}
        </div>
      </div>

      {/* Selected Policy Metrics Details */}
      <div className="bg-ink/50 border border-hairline/40 rounded-xl p-3.5 space-y-2.5 text-xs">
        <p className="text-muted font-light leading-relaxed">
          {activePolicy.description}
        </p>
        <div className="pt-2.5 border-t border-hairline/35 space-y-2 font-mono text-[10px]">
          <div className="flex justify-between">
            <span className="text-muted">LATENCY BUDGET</span>
            <span className="text-paper font-bold">
              {activePolicy.latency_budget_ms}ms
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">BLOCK LOG THRESHOLD</span>
            <span className="text-paper font-bold">
              &lt;{activePolicy.score_block_below} score
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">WARN LOG THRESHOLD</span>
            <span className="text-paper font-bold">
              &lt;{activePolicy.score_log_below} score
            </span>
          </div>
        </div>
      </div>

      {/* Session Stats */}
      <div className="mt-auto pt-6 border-t border-hairline/40 space-y-2">
        <h3 className="text-[9px] uppercase tracking-widest text-muted font-mono font-bold">
          Compliance Counters
        </h3>
        <div className="grid grid-cols-4 gap-2 font-mono text-xs text-center">
          <div className="bg-pass-soft/10 border border-pass/20 rounded-lg p-2 text-pass">
            <div className="font-bold text-base">{counts.pass}</div>
            <div className="text-[8px] uppercase tracking-wider">Pass</div>
          </div>
          <div className="bg-brass/10 border border-brass/20 rounded-lg p-2 text-brass">
            <div className="font-bold text-base">{counts.edit}</div>
            <div className="text-[8px] uppercase tracking-wider">Edit</div>
          </div>
          <div className="bg-log-soft/10 border border-log/20 rounded-lg p-2 text-log">
            <div className="font-bold text-base">{counts.log}</div>
            <div className="text-[8px] uppercase tracking-wider">Log</div>
          </div>
          <div className="bg-block-soft/10 border border-block/20 rounded-lg p-2 text-block">
            <div className="font-bold text-base">{counts.block}</div>
            <div className="text-[8px] uppercase tracking-wider">Block</div>
          </div>
        </div>
      </div>
      {metrics && (
        <div className="pt-4 space-y-1.5 font-mono text-[10px] text-muted">
          <div className="flex justify-between">
            <span>FEEDBACK COVERAGE</span>
            <span className="text-paper">
              {metrics.feedback_coverage_percent}%
            </span>
          </div>
          <div className="flex justify-between">
            <span>FALSE POSITIVE RATE</span>
            <span className="text-paper">
              {metrics.false_positive_rate === null
                ? "—"
                : `${(metrics.false_positive_rate * 100).toFixed(1)}%`}
            </span>
          </div>
          <div className="flex justify-between">
            <span>FALSE NEGATIVE RATE</span>
            <span className="text-paper">
              {metrics.false_negative_rate === null
                ? "—"
                : `${(metrics.false_negative_rate * 100).toFixed(1)}%`}
            </span>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-ink text-paper font-sans">
      {/* Desktop Sidebar */}
      <aside className="w-72 hidden md:block flex-shrink-0 h-full">
        <SidebarContent />
      </aside>

      {/* Mobile Sidebar Modal */}
      {showMobileSidebar && (
        <div className="fixed inset-0 z-50 flex md:hidden bg-ink/80 backdrop-blur-sm">
          <div className="w-72 h-full relative">
            <SidebarContent />
            <button
              type="button"
              onClick={() => setShowMobileSidebar(false)}
              className="absolute top-4 right-[-45px] p-2 bg-panel rounded-full text-paper border border-hairline"
            >
              <X size={18} />
            </button>
          </div>
        </div>
      )}

      {/* Main Chat Interface */}
      <main className="flex-1 flex flex-col h-full min-w-0 bg-ink relative">
        {/* Mobile Header Bar */}
        <header className="flex md:hidden items-center justify-between px-4 py-3 border-b border-hairline/60 bg-panel/40">
          <button
            type="button"
            onClick={() => setShowMobileSidebar(true)}
            className="p-2 border border-hairline rounded-lg text-paper hover:bg-panel"
          >
            <Menu size={18} />
          </button>
          <span className="font-display text-sm font-semibold tracking-tight text-paper">
            ControlPlane <span className="text-brass">Checker</span>
          </span>
          <ThemeToggle />
        </header>

        {/* Desktop Header */}
        <header className="hidden md:flex justify-between items-center px-6 py-4 border-b border-hairline/30 bg-panel/10">
          <div className="flex items-center gap-2">
            <Layers size={14} className="text-brass" />
            <span className="text-xs font-mono text-muted uppercase tracking-wider">
              Monitoring Mode:{" "}
              <span className="text-paper font-semibold">
                {activePolicy.name}
              </span>
            </span>
          </div>
          <ThemeToggle />
        </header>

        {/* Chat Feed */}
        <div className="flex-1 overflow-y-auto pb-4 space-y-2">
          {isEmpty ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 max-w-md mx-auto">
              <Sparkles className="text-brass mb-4 animate-pulse" size={42} />
              <h2 className="font-display text-2xl font-semibold tracking-tight text-paper mb-2">
                Evaluate LLM Compliance
              </h2>
              <p className="text-muted text-sm leading-relaxed mb-6">
                Submit a prompt to run safety checks live. Select a policy
                profile in the sidebar to configure latency budgets and routing
                thresholds.
              </p>

              <div className="w-full bg-panel/30 border border-hairline/60 rounded-xl p-4 text-left font-mono text-xs space-y-3">
                <p className="text-brass-soft font-semibold uppercase tracking-wider text-[10px]">
                  Things to try:
                </p>
                <ul className="space-y-2 text-muted">
                  <li className="flex items-start gap-1.5">
                    <span className="text-brass-soft">•</span>
                    <span>
                      Leave response blank to generate a real LLM reply
                    </span>
                  </li>
                  <li className="flex items-start gap-1.5">
                    <span className="text-brass-soft">•</span>
                    <span>
                      Paste custom email or phone response to trigger PII block
                    </span>
                  </li>
                  <li className="flex items-start gap-1.5">
                    <span className="text-brass-soft">•</span>
                    <span>
                      Verify how routing changes under different profiles
                    </span>
                  </li>
                </ul>
              </div>
            </div>
          ) : (
            <div className="divide-y divide-hairline/20">
              {[...records].reverse().map((record) => (
                <ResponseCard key={record.id} record={record} />
              ))}
              <div ref={chatEndRef} />
            </div>
          )}
        </div>

        {/* Input prompt area */}
        <div className="py-4 border-t border-hairline/25 bg-panel/10">
          <ScoreForm useCase={selectedUseCase} />
        </div>
      </main>
    </div>
  );
}
