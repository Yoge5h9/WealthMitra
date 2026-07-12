import { useState } from "react";
import { Mic, MicOff, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useVoiceInput } from "@/components/chat/useVoice";
import type { LanguageCode } from "@/components/shared/LangToggle";

export interface ChatInputProps {
  language: LanguageCode;
  disabled: boolean;
  onSend: (text: string) => void;
  placeholder?: string;
}

/** The composer bar: text input, optional mic (hidden if unsupported), send
 * — every control here clears the 44px touch-target minimum. */
export function ChatInput({ language, disabled, onSend, placeholder }: ChatInputProps) {
  const [value, setValue] = useState("");
  const voice = useVoiceInput(language, (transcript) => setValue((prev) => (prev ? `${prev} ${transcript}` : transcript)));

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  return (
    <div className="flex items-end gap-2 px-4 py-3">
      {voice.supported && (
        <button
          type="button"
          aria-label={voice.listening ? "Stop voice input" : "Start voice input"}
          aria-pressed={voice.listening}
          onClick={voice.toggle}
          className={cn(
            "flex size-11 shrink-0 items-center justify-center rounded-full border transition-colors duration-[var(--motion-micro)] ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
            voice.listening
              ? "border-danger-300 bg-danger-50 text-danger-600"
              : "border-neutral-200 bg-neutral-0 text-neutral-600 hover:text-structural-600"
          )}
        >
          {voice.listening ? <MicOff size={20} strokeWidth={1.75} /> : <Mic size={20} strokeWidth={1.75} />}
        </button>
      )}

      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        rows={1}
        placeholder={placeholder ?? "Ask about your money…"}
        disabled={disabled}
        className="min-h-11 flex-1 resize-none rounded-sm border border-neutral-200 bg-neutral-0 px-3 py-2 text-body text-neutral-900 placeholder:text-neutral-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] disabled:bg-neutral-50 disabled:text-neutral-400"
      />

      <Button
        type="button"
        size="icon-touch"
        onClick={submit}
        disabled={disabled || !value.trim()}
        aria-label="Send message"
      >
        <Send size={18} strokeWidth={1.75} />
      </Button>
    </div>
  );
}
