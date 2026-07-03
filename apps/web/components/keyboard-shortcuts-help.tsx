"use client";

import { X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface KeyboardShortcutsHelpProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const shortcuts = [
  { key: "R", description: "刷新市场数据" },
  { key: "F 或 /", description: "聚焦搜索框" },
  { key: "⌘K 或 Ctrl+K", description: "打开命令面板" },
  { key: "?", description: "显示快捷键帮助" },
  { key: "Esc", description: "关闭弹窗" },
];

export function KeyboardShortcutsHelp({ open, onOpenChange }: KeyboardShortcutsHelpProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>键盘快捷键</DialogTitle>
          <DialogDescription>
            使用键盘快捷键快速操作
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-2">
          {shortcuts.map((shortcut, index) => (
            <div key={index} className="flex items-center justify-between py-2 border-b last:border-0">
              <span className="text-sm text-muted-foreground">{shortcut.description}</span>
              <kbd className="px-2 py-1 text-xs font-semibold bg-muted rounded border">
                {shortcut.key}
              </kbd>
            </div>
          ))}
        </div>
        
        <div className="text-xs text-muted-foreground mt-4">
          提示: 按 <kbd className="px-1.5 py-0.5 bg-muted rounded">Esc</kbd> 或点击外部区域关闭此窗口
        </div>
      </DialogContent>
    </Dialog>
  );
}
