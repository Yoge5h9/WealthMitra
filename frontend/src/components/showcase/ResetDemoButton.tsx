import { useState, type MouseEvent } from "react";
import { AlertDialog } from "radix-ui";
import { CheckCircle2, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useResetSpace } from "@/lib/queries";
import { cn } from "@/lib/utils";

export interface ResetDemoButtonProps {
  spaceId: string | null;
  className?: string;
}

/** Resets the current demo space back to its seeded state, behind a confirm dialog. */
export function ResetDemoButton({ spaceId, className }: ResetDemoButtonProps) {
  const [open, setOpen] = useState(false);
  const [justReset, setJustReset] = useState(false);
  const resetSpace = useResetSpace();

  function handleConfirm(event: MouseEvent) {
    // Radix's AlertDialogAction closes the dialog as soon as it's clicked —
    // prevented here so the dialog stays open (showing "Resetting…") until
    // the mutation actually completes, then closes itself on success.
    event.preventDefault();
    if (!spaceId) return;
    resetSpace.mutate(spaceId, {
      onSuccess: () => {
        setOpen(false);
        setJustReset(true);
        window.setTimeout(() => setJustReset(false), 4000);
      },
    });
  }

  return (
    <AlertDialog.Root open={open} onOpenChange={setOpen}>
      <div className={cn("flex items-center gap-2", className)}>
        <AlertDialog.Trigger asChild>
          <Button variant="outline" size="touch" disabled={!spaceId} className="gap-2">
            <RotateCcw size={18} strokeWidth={1.75} aria-hidden="true" />
            Reset demo
          </Button>
        </AlertDialog.Trigger>
        {justReset && (
          <span className="flex items-center gap-1.5 text-caption font-medium text-success-700">
            <CheckCircle2 size={14} strokeWidth={2} aria-hidden="true" />
            Space reset
          </span>
        )}
      </div>

      <AlertDialog.Portal>
        <AlertDialog.Overlay className="fixed inset-0 z-50 bg-neutral-950/40" />
        <AlertDialog.Content className="fixed top-1/2 left-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-neutral-200 bg-neutral-0 p-6 shadow-float-xl">
          <AlertDialog.Title className="font-display text-h4 font-semibold text-neutral-900">
            Reset this demo space?
          </AlertDialog.Title>
          <AlertDialog.Description className="mt-2 text-body-sm text-neutral-600">
            This clears every chat, RM lead, and nudge created in this space. Seeded persona
            data (transactions, holdings, goals) stays exactly as it started — this only
            wipes what the demo has generated so far.
          </AlertDialog.Description>
          <div className="mt-6 flex justify-end gap-3">
            <AlertDialog.Cancel asChild>
              <Button variant="ghost" size="touch">
                Cancel
              </Button>
            </AlertDialog.Cancel>
            <AlertDialog.Action asChild>
              <Button
                variant="destructive"
                size="touch"
                onClick={handleConfirm}
                disabled={resetSpace.isPending}
              >
                {resetSpace.isPending ? "Resetting…" : "Reset space"}
              </Button>
            </AlertDialog.Action>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
