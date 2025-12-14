"use client";

import { Sidebar } from "./Sidebar";
import { RightPanel } from "./RightPanel";

interface ThreePaneLayoutProps {
  children: React.ReactNode;
  rightPanel?: React.ReactNode;
  isRightPanelOpen?: boolean;
  onCloseRightPanel?: () => void;
}

export function ThreePaneLayout({
  children,
  rightPanel,
  isRightPanelOpen = false,
  onCloseRightPanel = () => {},
}: ThreePaneLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-gray-50">{children}</main>
      <RightPanel isOpen={isRightPanelOpen} onClose={onCloseRightPanel}>
        {rightPanel}
      </RightPanel>
    </div>
  );
}
