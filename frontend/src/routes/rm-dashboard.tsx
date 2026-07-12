import { UserRoundCog } from "lucide-react";
import { PlaceholderPage } from "@/components/placeholder-page";

export default function RmDashboard() {
  return (
    <PlaceholderPage
      eyebrow="Desktop · Relationship Manager"
      title="RM Desk"
      description="Where regulated recommendations land. Every lead arrives as a structured Lead Packet — goals, risk score, suitability profile, and the exact reason the AI routed it here — so the RM never has to start a conversation cold."
      icon={UserRoundCog}
      primaryAction="Open lead queue"
      upcoming={[
        "Lead Packet detail: routing reason, goals, suitability profile",
        "Customer-360 view alongside each lead",
        "Lead accuracy and conversion feedback capture",
        "Category-routed queue (ULIPs, PMS, AIF, complex MFs)",
      ]}
    />
  );
}
