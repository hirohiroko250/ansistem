"use client";

import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface RightPanelProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
  className?: string;
  title?: string;
}

export function RightPanel({ isOpen, onClose, children, className, title }: RightPanelProps) {
  return (
    <div
      className={cn(
        "h-screen bg-white border-l border-gray-200 transition-all duration-300 flex flex-col",
        isOpen ? "w-[50vw]" : "w-0 overflow-hidden",
        className
      )}
    >
      {isOpen && (
        <>
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200">
            {title !== undefined ? (
              title ? <h2 className="text-lg font-semibold text-gray-900">{title}</h2> : <div />
            ) : (
              <h2 className="text-lg font-semibold text-gray-900">詳細</h2>
            )}
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="w-5 h-5" />
            </Button>
          </div>
          <div className="flex-1 overflow-y-auto">{children}</div>
        </>
      )}
    </div>
  );
}
