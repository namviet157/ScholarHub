import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate, useSearchParams } from "react-router-dom";
import Explore from "./pages/Explore";
import PaperViewer from "./pages/PaperViewer";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

function LegacySearchRedirect() {
  const [params] = useSearchParams();
  const s = params.toString();
  return <Navigate to={s ? `/?${s}` : "/"} replace />;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/" element={<Explore />} />
          <Route path="/search" element={<LegacySearchRedirect />} />
          <Route path="/paper/:id" element={<PaperViewer />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
