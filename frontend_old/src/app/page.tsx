import { TopologyMap } from "@/components/war-room/TopologyMap";
import { BrainScanner } from "@/components/war-room/BrainScanner";
import { GuardianPanel } from "@/components/war-room/GuardianPanel";
import { CommandBar } from "@/components/war-room/CommandBar";
import { KpiCards } from "@/components/war-room/KpiCards";
import { DomainSwitcher } from "@/components/war-room/DomainSwitcher";

export default function Home() {
  return (
    <div className="flex flex-col h-screen w-screen bg-background text-foreground overflow-hidden">
      {/* Top Header Row */}
      <header className="flex-none h-16 border-b border-border/50 bg-card/50 flex items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <div className="h-8 w-8 rounded-md bg-primary/20 flex items-center justify-center border border-primary/50">
            <span className="text-primary font-bold">⚡</span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-primary">OmniNode War Room</h1>
        </div>
        <DomainSwitcher />
      </header>

      {/* KPI Cards Row */}
      <div className="flex-none p-4">
        <KpiCards />
      </div>

      {/* Main Grid: 3 columns (Left panel, Center map, Right panel) */}
      <main className="flex-1 min-h-0 flex gap-4 px-4 pb-4">
        {/* Left Panel: Safety Guardian */}
        <aside className="w-80 flex-none flex flex-col gap-4">
          <GuardianPanel />
        </aside>

        {/* Center: Topology Map */}
        <section className="flex-1 min-w-0 bg-card/30 rounded-xl border border-border/50 overflow-hidden relative shadow-inner">
          <TopologyMap />
        </section>

        {/* Right Panel: AI Brain Scanner */}
        <aside className="w-96 flex-none flex flex-col gap-4">
          <BrainScanner />
        </aside>
      </main>

      {/* Bottom Command Bar */}
      <footer className="flex-none h-16 border-t border-border/50 bg-card/50 flex items-center px-4">
        <CommandBar />
      </footer>
    </div>
  );
}
