import { useEffect, useRef } from "react";
import { CONFIG } from "./data/config.js";
import { useLang } from "./hooks/useLang.jsx";
import { useScrollY } from "./lib/hooks.js";
import {
  useParticleCanvas,
  useThreeBackground,
} from "./hooks/useBackground.js";
import { useRevealObserver } from "./hooks/useMotion.js";
import { Navbar } from "./components/Navbar.jsx";
import { Hero } from "./components/Hero.jsx";
import { Features } from "./components/Features.jsx";
import { Commands } from "./components/Commands.jsx";
import { Stats } from "./components/Stats.jsx";
import { LiveStatus } from "./components/LiveStatus.jsx";
import { Community } from "./components/Community.jsx";
import { About } from "./components/About.jsx";
import { Premium } from "./components/Premium.jsx";
import { Changelog } from "./components/Changelog.jsx";
import { Faq } from "./components/Faq.jsx";
import { InviteCta } from "./components/InviteCta.jsx";
import { Footer } from "./components/Footer.jsx";

export default function App() {
  const inviteUrl = CONFIG.SERVER_INVITE_URL || CONFIG.INVITE_URL;
  const { t } = useLang();
  const scrollY = useScrollY();
  const canvasRef = useRef(null);
  const rootRef = useRef(null);

  useParticleCanvas(canvasRef);
  useThreeBackground();
  useRevealObserver(rootRef);

  // Scroll-to-top button visibility.
  const showScrollTop = scrollY > 500;
  useEffect(() => {
    if (!showScrollTop) return;
    const el = document.getElementById("scroll-top");
    el?.classList.add("visible");
  }, [showScrollTop]);

  // Keep the command toolbar pinned while the catalog is in view.
  useEffect(() => {
    const onScroll = () => {
      const toolbar = document.querySelector(".cmd-toolbar");
      const section = document.getElementById("commands");
      const search = document.getElementById("cmd-search");
      if (!toolbar || !section || !search) return;
      const rect = section.getBoundingClientRect();
      const inputRect = search.getBoundingClientRect();
      toolbar.classList.toggle("sticky", rect.top < 0 && inputRect.bottom > 0);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Smooth-scroll to a hash target that lands above the fixed navbar.
  useEffect(() => {
    const go = () => {
      const id = window.location.hash.slice(1).split("?")[0];
      if (!id) return;
      const target = document.getElementById(id);
      if (!target) return;
      const top = target.getBoundingClientRect().top + window.scrollY - 84;
      window.scrollTo({ top, behavior: "smooth" });
    };
    window.addEventListener("hashchange", go);
    return () => window.removeEventListener("hashchange", go);
  }, []);

  return (
    <div ref={rootRef}>
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <canvas id="bg-canvas" ref={canvasRef} />

      <Navbar inviteUrl={inviteUrl} />

      <main id="main">
        <Hero inviteUrl={inviteUrl} />
        <Features />
        <Commands />
        <Stats />
        <LiveStatus />
        <Community />
        <About />
        <Premium inviteUrl={inviteUrl} />
        <Changelog />
        <Faq />
        <InviteCta inviteUrl={inviteUrl} />
      </main>

      <Footer />

      <button
        id="scroll-top"
        aria-label={t("ui.scrolltop")}
        className={showScrollTop ? "visible" : ""}
        onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      >
        ↑
      </button>
    </div>
  );
}
