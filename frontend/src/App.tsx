import { Routes, Route, useLocation } from "react-router-dom";
import { TopNav } from "@/components/layout/top-nav";
import CommandCenter from "@/routes/command-center";
import CustomerChat from "@/routes/customer/index";
import RmDashboard from "@/routes/rm";
import Channels from "@/routes/channels";
import Present from "@/routes/present";
import Dev from "@/routes/dev";

function App() {
  // `?embedded=1` lets the Presenter stage iframe /app and /rm side by side
  // without a second top-nav rendering inside each pane.
  const location = useLocation();
  const embedded = new URLSearchParams(location.search).get("embedded") === "1";

  return (
    <div className="min-h-full bg-neutral-50">
      {!embedded && <TopNav />}
      <main>
        <Routes>
          <Route path="/" element={<CommandCenter />} />
          <Route path="/app" element={<CustomerChat />} />
          <Route path="/rm" element={<RmDashboard />} />
          <Route path="/channels" element={<Channels />} />
          <Route path="/present" element={<Present />} />
          <Route path="/dev" element={<Dev />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
