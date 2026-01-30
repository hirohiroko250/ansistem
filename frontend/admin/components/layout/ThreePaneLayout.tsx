"use client";

import { Sidebar } from "./Sidebar";
import { RightPanel } from "./RightPanel";
import { QuickAccessHeader } from "./QuickAccessHeader";

interface ThreePaneLayoutProps {
  children: React.ReactNode;
  rightPanel?: React.ReactNode;
  isRightPanelOpen?: boolean;
  onCloseRightPanel?: () => void;
  hideQuickAccess?: boolean;
  rightPanelTitle?: string;
}

export function ThreePaneLayout({
  children,
  rightPanel,
  isRightPanelOpen = false,
  onCloseRightPanel = () => {},
  hideQuickAccess = false,
  rightPanelTitle,
}: ThreePaneLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        {!hideQuickAccess && <QuickAccessHeader />}
        <main className="flex-1 overflow-y-auto bg-gray-50">{children}</main>
      </div>
      <RightPanel isOpen={isRightPanelOpen} onClose={onCloseRightPanel} title={rightPanelTitle}>
        {rightPanel}
      </RightPanel>
    </div>
  );
}
