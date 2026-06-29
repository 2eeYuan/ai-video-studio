import { useState } from "react";
import { Header } from "@/components/common/Header";
import { WorkspaceLayout } from "@/components/workspace/WorkspaceLayout";
import { SettingsDialog } from "@/components/settings/SettingsDialog";

function App() {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <div className="h-screen flex flex-col">
      <Header onSettings={() => setSettingsOpen(true)} />
      <WorkspaceLayout />
      <SettingsDialog open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}

export default App;
