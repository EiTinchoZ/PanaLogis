/* PanaLogis - main.js */

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function countUp(element) {
  const target = Number(element.dataset.countup || "0");
  if (!Number.isFinite(target)) return;

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced) {
    element.textContent = String(target);
    return;
  }

  const duration = 900;
  const start = performance.now();

  function frame(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 4);
    element.textContent = String(Math.round(target * eased));
    if (progress < 1) {
      requestAnimationFrame(frame);
    }
  }

  requestAnimationFrame(frame);
}

function fadeAlerts() {
  document.querySelectorAll(".alert").forEach(function (el) {
    setTimeout(function () {
      el.style.transition = "opacity 0.3s";
      el.style.opacity = "0";
      setTimeout(function () {
        el.remove();
      }, 320);
    }, 5000);
  });
}

function revealOnScroll(reduced) {
  const reveals = document.querySelectorAll(".reveal");
  if (reduced) {
    reveals.forEach(function (el) {
      el.classList.add("is-visible");
    });
    return;
  }

  const observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12 }
  );

  reveals.forEach(function (el, index) {
    el.style.setProperty("--reveal-delay", `${Math.min(index * 70, 420)}ms`);
    observer.observe(el);
  });
}

function animateProgress(reduced) {
  document.querySelectorAll(".progress-fill").forEach(function (bar) {
    const width = Math.max(0, Math.min(100, Number(bar.dataset.width || "0")));
    if (reduced) {
      bar.style.width = `${width}%`;
      return;
    }

    requestAnimationFrame(function () {
      bar.style.width = `${width}%`;
    });
  });
}

function renderCopilotResponse(container, payload) {
  const bullets = (payload.bullets || [])
    .map(function (item) {
      return `<li>${escapeHtml(item)}</li>`;
    })
    .join("");
  const actions = (payload.actions || [])
    .map(function (item) {
      return `<li>${escapeHtml(item)}</li>`;
    })
    .join("");

  container.innerHTML = `
    <div class="ai-response-card">
      <div class="ai-response-header">
        <div>
          <div class="ai-response-title">${escapeHtml(payload.title || "Copiloto operativo")}</div>
          <div class="ai-response-time">Actualizado ${escapeHtml(payload.timestamp || "--:--")}</div>
        </div>
      </div>
      <p class="ai-response-summary">${escapeHtml(payload.summary || "")}</p>
      ${bullets ? `<ul class="ai-response-list">${bullets}</ul>` : ""}
      ${actions ? `<div class="ai-response-actions-label">Siguiente paso</div><ul class="ai-response-actions">${actions}</ul>` : ""}
    </div>
  `;
}

function initCopilot() {
  const shell = document.querySelector("[data-ai-copilot]");
  if (!shell) return;

  const output = shell.querySelector("[data-ai-output]");
  const provider = shell.querySelector("[data-ai-provider]");
  const form = shell.querySelector("[data-ai-form]");
  const input = shell.querySelector(".ai-copilot-input");

  async function sendRequest(url, payload) {
    output.innerHTML = `
      <div class="ai-copilot-skeleton ai-copilot-skeleton--busy">
        <span></span><span></span><span></span>
      </div>
    `;

    try {
      const response = await fetch(url, {
        method: payload ? "POST" : "GET",
        headers: payload ? { "Content-Type": "application/json" } : {},
        body: payload ? JSON.stringify(payload) : undefined,
      });
      const data = await response.json();
      provider.textContent = data.provider || "Motor local";
      renderCopilotResponse(output, data);
    } catch (error) {
      provider.textContent = "Motor local";
      output.innerHTML = `
        <div class="ai-response-card">
          <div class="ai-response-title">Copiloto no disponible</div>
          <p class="ai-response-summary">No pude completar la lectura automática ahora mismo. Reintenta en unos segundos.</p>
        </div>
      `;
    }
  }

  sendRequest("/api/ai/briefing");

  shell.querySelectorAll("[data-ai-prompt]").forEach(function (button) {
    button.addEventListener("click", function () {
      const question = button.getAttribute("data-ai-prompt") || "";
      if (input) input.value = question;
      sendRequest("/api/ai/ask", { question });
    });
  });

  if (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      const question = (input && input.value.trim()) || "";
      sendRequest("/api/ai/ask", { question });
    });
  }
}

document.addEventListener("DOMContentLoaded", function () {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  fadeAlerts();
  revealOnScroll(reduced);
  document.querySelectorAll("[data-countup]").forEach(countUp);
  animateProgress(reduced);
  initCopilot();
});
