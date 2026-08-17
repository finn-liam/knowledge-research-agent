import { CloudUpload, Loader2 } from "lucide-react";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const ACCEPT = ".pdf,.docx,.md,.txt";

/** 上传区：拖拽 + 点击选择（PDF/DOCX/MD/TXT，≤20MB×5） */
export function UploadZone({
  uploading,
  onUpload,
}: {
  uploading: boolean;
  onUpload: (files: File[]) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleFiles = (list: FileList | null) => {
    if (!list?.length) return;
    onUpload(Array.from(list).slice(0, 5));
  };

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed bg-card px-6 py-9 text-center transition-all",
        dragging ? "border-primary bg-accent/50" : "border-border hover:border-primary/50",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      {uploading ? (
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      ) : (
        <CloudUpload className="h-8 w-8 text-primary/70" />
      )}
      <div className="mt-3 text-sm font-medium text-foreground/90">
        {uploading ? "正在上传并解析..." : "点击或拖拽上传文档"}
      </div>
      <div className="mt-1 text-xs text-muted-foreground">
        支持 PDF / DOCX / MD / TXT · 单文件 ≤20MB · 单批 ≤5 个
      </div>
      {uploading && (
        <Button variant="outline" size="sm" className="mt-3" disabled>
          处理中，可离开本页
        </Button>
      )}
    </div>
  );
}
