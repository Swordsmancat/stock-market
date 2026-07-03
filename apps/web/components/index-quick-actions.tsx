"use client";

import { useRouter } from "next/navigation";
import { Star, Eye, Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useState } from "react";

interface IndexQuickActionsProps {
  code: string;
  name: string;
  isInWatchlist?: boolean;
  onAddToWatchlist?: (code: string) => void;
  onViewDetail?: (code: string) => void;
  onSetAlert?: (code: string) => void;
  className?: string;
}

export function IndexQuickActions({
  code,
  name,
  isInWatchlist = false,
  onAddToWatchlist,
  onViewDetail,
  onSetAlert,
  className,
}: IndexQuickActionsProps) {
  const router = useRouter();
  const [isAdding, setIsAdding] = useState(false);
  const [inWatchlist, setInWatchlist] = useState(isInWatchlist);

  const handleAddToWatchlist = async () => {
    if (isAdding) return;
    
    setIsAdding(true);
    try {
      const response = await fetch("/api/watchlist", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          symbol: code,
          market: "CN", // TODO: 从code推断市场
          name: name,
          is_active: true,
        }),
      });

      if (response.ok) {
        setInWatchlist(true);
        toast.success(`已将 ${name} 加入自选列表`);
        onAddToWatchlist?.(code);
      } else {
        toast.error("添加失败，请稍后重试");
      }
    } catch (error) {
      console.error("Add to watchlist error:", error);
      toast.error("添加失败，请检查网络连接");
    } finally {
      setIsAdding(false);
    }
  };

  const handleViewDetail = () => {
    const currentLocale = window.location.pathname.split('/')[1]; // 获取当前locale
    router.push(`/${currentLocale}/instruments/${code}`);
    onViewDetail?.(code);
  };

  const handleSetAlert = () => {
    toast.info(`提醒功能`, {
      description: `即将为 ${name} 设置价格提醒 (功能开发中)`,
      duration: 3000,
    });
    onSetAlert?.(code);
  };

  return (
    <div className={cn("flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity", className)}>
      <Button
        variant="ghost"
        size="sm"
        className="h-7 w-7 p-0"
        onClick={handleAddToWatchlist}
        disabled={isAdding || inWatchlist}
        title={inWatchlist ? "已在自选" : "加入自选"}
      >
        <Star className={cn("h-3.5 w-3.5", inWatchlist && "fill-yellow-500 text-yellow-500")} />
      </Button>
      
      <Button
        variant="ghost"
        size="sm"
        className="h-7 w-7 p-0"
        onClick={handleViewDetail}
        title="查看详情"
      >
        <Eye className="h-3.5 w-3.5" />
      </Button>
      
      <Button
        variant="ghost"
        size="sm"
        className="h-7 w-7 p-0"
        onClick={handleSetAlert}
        title="设置提醒"
      >
        <Bell className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

