import "./styles/global.css";

const syncThemeIcons = () => {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const sun = document.getElementById("theme-icon-sun");
  const moon = document.getElementById("theme-icon-moon");
  if (sun) sun.classList.toggle("hidden", !isDark);
  if (moon) moon.classList.toggle("hidden", isDark);
};

const initTheme = () => {
  const stored = localStorage.getItem("whisper-docs-theme");
  if (stored === "dark" || stored === "light") {
    document.documentElement.setAttribute("data-theme", stored);
  }
  syncThemeIcons();

  const btn = document.getElementById("theme-toggle-btn");
  if (btn && btn.dataset.ready !== "true") {
    btn.dataset.ready = "true";
    btn.addEventListener("click", () => {
      const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("whisper-docs-theme", next);
      syncThemeIcons();
    });
  }
};

const initCodeCopy = () => {
  document.querySelectorAll(".ds-prose pre").forEach((pre) => {
    if (pre.parentElement?.classList.contains("ds-code-wrap")) return;
    const wrap = document.createElement("div");
    wrap.className = "ds-code-wrap";
    pre.parentNode?.insertBefore(wrap, pre);
    wrap.appendChild(pre);

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ds-copy-btn";
    btn.textContent = "Copy";
    btn.setAttribute("aria-label", "Copy code");
    btn.addEventListener("click", async () => {
      const code = pre.querySelector("code")?.textContent ?? pre.textContent ?? "";
      try {
        await navigator.clipboard.writeText(code);
        btn.textContent = "Copied";
        btn.setAttribute("data-copied", "true");
        setTimeout(() => {
          btn.textContent = "Copy";
          btn.removeAttribute("data-copied");
        }, 1600);
      } catch {}
    });
    wrap.appendChild(btn);
  });
};

const initToc = () => {
  const tocNav = document.getElementById("toc-nav");
  if (!tocNav || tocNav.dataset.tocReady === "true") return;
  const tocLinks = Array.from(tocNav.querySelectorAll(".ds-toc-link"));
  if (!tocLinks.length) return;
  tocNav.dataset.tocReady = "true";

  const setActive = (slug) => {
    tocLinks.forEach((link) => {
      link.classList.toggle("is-active", link.getAttribute("data-heading") === slug);
    });
  };

  const headingElements = tocLinks
    .map((link) => link.getAttribute("data-heading"))
    .filter(Boolean)
    .map((slug) => document.getElementById(slug))
    .filter(Boolean);

  if (headingElements.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target?.id) setActive(visible.target.id);
      },
      { rootMargin: "-15% 0px -70% 0px", threshold: [0.1, 0.5, 1] }
    );
    headingElements.forEach((el) => observer.observe(el));
  }

  setActive(window.location.hash.replace(/^#/, "") || tocLinks[0].getAttribute("data-heading") || "");
};

const initSearch = () => {
  const input = document.getElementById("docs-search-input");
  const results = document.getElementById("docs-search-results");
  if (!(input instanceof HTMLInputElement) || !(results instanceof HTMLDivElement)) return;
  if (input.dataset.searchReady === "true") return;
  input.dataset.searchReady = "true";

  const allItems = JSON.parse(input.dataset.searchItems || "[]");
  let activeIndex = -1;
  let matches = [];

  const closeResults = () => {
    results.classList.add("hidden");
    results.innerHTML = "";
    activeIndex = -1;
  };

  const renderMatches = () => {
    results.innerHTML = "";
    if (!matches.length) {
      const empty = document.createElement("p");
      empty.className = "px-3 py-2 text-[13px] text-[var(--ds-ink-faint)]";
      empty.textContent = "No matching pages.";
      results.appendChild(empty);
      results.classList.remove("hidden");
      return;
    }
    matches.forEach((item, index) => {
      const link = document.createElement("a");
      link.href = item.href;
      link.className = "search-result-item block rounded-md px-3 py-2";
      if (index === activeIndex) link.classList.add("is-active");
      const titleEl = document.createElement("p");
      titleEl.className = "m-0 text-[13px] font-medium text-[var(--ds-ink)]";
      titleEl.textContent = item.title;
      link.appendChild(titleEl);
      if (item.description) {
        const descEl = document.createElement("p");
        descEl.className = "m-0 mt-0.5 text-[12px] text-[var(--ds-ink-muted)] line-clamp-1";
        descEl.textContent = item.description;
        link.appendChild(descEl);
      }
      results.appendChild(link);
    });
    results.classList.remove("hidden");
  };

  const updateSearch = (raw) => {
    const q = String(raw || "").toLowerCase().trim();
    if (!q) return closeResults();
    matches = allItems
      .filter((item) => `${item.title} ${item.description || ""} ${item.slug}`.toLowerCase().includes(q))
      .slice(0, 8);
    activeIndex = matches.length ? 0 : -1;
    renderMatches();
  };

  input.addEventListener("input", () => updateSearch(input.value));
  input.addEventListener("focus", () => {
    if (input.value.trim()) updateSearch(input.value);
  });
  input.addEventListener("keydown", (event) => {
    if (results.classList.contains("hidden") || !matches.length) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      activeIndex = (activeIndex + 1) % matches.length;
      renderMatches();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      activeIndex = (activeIndex - 1 + matches.length) % matches.length;
      renderMatches();
    } else if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault();
      window.location.href = matches[activeIndex].href;
    } else if (event.key === "Escape") {
      closeResults();
    }
  });

  document.addEventListener("click", (event) => {
    if (event.target instanceof Node && !results.contains(event.target) && event.target !== input) {
      closeResults();
    }
  });

  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      input.focus();
    }
  });
};

initTheme();
initCodeCopy();
initToc();
initSearch();
