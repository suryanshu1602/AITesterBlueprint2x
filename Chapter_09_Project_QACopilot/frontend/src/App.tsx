import { NavLink, Route, Routes } from "react-router-dom";
import { MessageSquare, Search, Activity, BookOpen } from "lucide-react";
import Chat from "./pages/Chat";
import Explorer from "./pages/Explorer";
import Status from "./pages/Status";

export default function App() {
  return (
    <div className="h-full flex flex-col">
      <Header />
      <main className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/explorer" element={<Explorer />} />
          <Route path="/status" element={<Status />} />
        </Routes>
      </main>
    </div>
  );
}

function Header() {
  const linkCls = ({ isActive }: { isActive: boolean }) =>
    `inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition ${
      isActive ? "bg-accent-soft text-accent-strong font-semibold" : "text-ink-soft hover:bg-surface-card"
    }`;
  return (
    <header className="border-b border-gray-200 bg-white/90 backdrop-blur sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-gradient-to-br from-accent to-accent-strong text-white grid place-items-center text-sm font-bold shadow">
            QA
          </div>
          <div className="font-bold text-[15px]">QA Copilot</div>
          <span className="ml-1 px-2 py-0.5 rounded-full bg-accent-soft text-accent-strong text-[11px] font-semibold">
            Chapter 09
          </span>
        </div>
        <nav className="flex items-center gap-1">
          <NavLink to="/" end className={linkCls}>
            <MessageSquare size={15} /> Chat
          </NavLink>
          <NavLink to="/explorer" className={linkCls}>
            <Search size={15} /> RAG Explorer
          </NavLink>
          <NavLink to="/status" className={linkCls}>
            <Activity size={15} /> Status
          </NavLink>
          <a className={linkCls({ isActive: false })} href="/KT/index.html" target="_blank" rel="noreferrer">
            <BookOpen size={15} /> KT Doc
          </a>
        </nav>
      </div>
    </header>
  );
}
