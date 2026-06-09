let RAW = [],
  filtered = [],
  chart = null;

async function init() {
  try {
    const res = await fetch("/api/data");
    RAW = await res.json();
    applyFilters();
    setupNav();
  } catch (e) {
    console.error("Fetch fail", e);
  }
}

function setupNav() {
  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach((btn) => {
    btn.onclick = (e) => {
      const item = e.currentTarget;
      const viewId = item.dataset.view;

      document.querySelectorAll(".nav-item, .view").forEach((el) => {
        el.classList.remove("active");
      });

      item.classList.add("active");
      const targetView = document.getElementById("v-" + viewId);
      if (targetView) {
        targetView.classList.add("active");
        document.getElementById("view-title").textContent = item.textContent;
      }
    };
  });
}

const fmt = (val, isNum = true) => {
  if (val === null || val === undefined || val === "" || val === 0)
    return "N/A";
  return isNum ? Math.round(val).toLocaleString() : val;
};

function applyFilters() {
  const marca = document.getElementById("f-marca").value;
  const q = document.getElementById("search").value.toLowerCase();

  filtered = RAW.filter((d) => {
    const matchMarca = !marca || d.marca === marca;
    const matchSearch =
      !q || d.mop.toLowerCase().includes(q) || d.ref.toLowerCase().includes(q);
    return matchMarca && matchSearch;
  });

  renderKPIs();
  renderTables();
  renderChart();
}

function renderKPIs() {
  const total = filtered.length;
  const yoyoCount = filtered.filter((d) => d.marca === "YOYO").length;
  const stopCount = filtered.filter((d) => d.marca === "STOP").length;

  const undCut = filtered.reduce((s, d) => s + (d.comp || 0), 0);
  const backlog = filtered.reduce((s, d) => s + (d.pend || 0), 0);
  const totalPlan = filtered.reduce((s, d) => s + (d.plan || 0), 0);

  const yP = total ? Math.round((yoyoCount / total) * 100) : 0;
  const sP = total ? 100 - yP : 0;
  const cumpl = totalPlan ? Math.round((undCut / totalPlan) * 100) : 0;

  const html = `
        <div class="kpi-card">
            <div class="kpi-label">TOTAL MOPS</div>
            <div class="kpi-value text-dark">${total || "N/A"}</div>
            <div class="kpi-sub">YOYO ${yoyoCount} · STOP ${stopCount}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">UND. CORTADAS</div>
            <div class="kpi-value text-blue">${fmt(undCut)}</div>
            <div class="kpi-sub">YOYO ${yP}% · STOP ${sP}%</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">OTIF</div>
            <div class="kpi-value text-red">0%</div>
            <div class="kpi-sub">Meta ≥95% — Crítico</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">% CUMPLIMIENTO</div>
            <div class="kpi-value text-amber">${cumpl ? cumpl + "%" : "N/A"}</div>
            <div class="kpi-sub">Meta ≥95% — Anticipado</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">BACKLOG (UND.)</div>
            <div class="kpi-value text-red">${fmt(backlog)}</div>
            <div class="kpi-sub">${filtered.filter((d) => d.pend > 0).length} MOPs tardíos</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">DÍAS PROM. ATRASO</div>
            <div class="kpi-value text-purple">61</div>
            <div class="kpi-sub">Meta ≤3 días</div>
        </div>
    `;
  document.getElementById("kpis").innerHTML = html;
}

function renderTables() {
  // Entrega
  const entBody = document.querySelector("#t-entrega tbody");
  const entData = filtered.filter((d) => d.section === "entrega");
  entBody.innerHTML = entData.length
    ? entData
        .slice(0, 50)
        .map(
          (d) => `
        <tr><td>${fmt(d.mes, false)}</td><td>${d.mop}</td><td>${fmt(d.plan)}</td><td>${fmt(d.comp)}</td></tr>
    `,
        )
        .join("")
    : "<tr><td colspan='4'>N/A - SIN DATOS</td></tr>";

  // Pending
  const pendBody = document.querySelector("#t-pending tbody");
  const pendData = filtered.filter((d) => d.section === "pending");
  pendBody.innerHTML = pendData.length
    ? pendData
        .slice(0, 50)
        .map(
          (d) => `
        <tr><td>${d.mop}</td><td>${d.ref}</td><td>${fmt(d.pend)}</td><td>PENDIENTE</td></tr>
    `,
        )
        .join("")
    : "<tr><td colspan='4'>N/A - SIN DATOS</td></tr>";

  // Cut
  const cutBody = document.querySelector("#t-cut tbody");
  const cutData = filtered.filter((d) => d.section === "cut");
  cutBody.innerHTML = cutData.length
    ? cutData
        .slice(0, 50)
        .map(
          (d) => `
        <tr><td>${d.mop}</td><td>${d.ref}</td><td>${fmt(d.comp)}</td><td>CORTE OK</td></tr>
    `,
        )
        .join("")
    : "<tr><td colspan='4'>N/A - SIN DATOS</td></tr>";

  // WIP
  const wipBody = document.querySelector("#t-wip tbody");
  const wipData = filtered.filter((d) => d.section === "wip");
  wipBody.innerHTML = wipData.length
    ? wipData
        .slice(0, 50)
        .map(
          (d) => `
        <tr><td>${d.mop}</td><td>${d.ref}</td><td>PROCESO</td></tr>
    `,
        )
        .join("")
    : "<tr><td colspan='3'>N/A - SIN DATOS</td></tr>";
}

function renderChart() {
  const canvas = document.getElementById("chartUC");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (chart) chart.destroy();

  const meses = [...new Set(filtered.map((d) => d.mes))]
    .filter((m) => m)
    .sort();
  if (!meses.length) return;

  chart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: meses,
      datasets: [
        {
          label: "Unidades Cortadas",
          data: meses.map((m) =>
            filtered
              .filter((d) => d.mes === m)
              .reduce((s, d) => s + (d.comp || 0), 0),
          ),
          backgroundColor: "#1558b0",
          borderRadius: 5,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true } },
    },
  });
}

async function upload() {
  const fileInput = document.getElementById("up-file");
  const sec = document.getElementById("up-sec").value;
  const files = fileInput.files;

  if (files.length === 0) return;

  const fd = new FormData();
  fd.append("section", sec);
  for (let i = 0; i < files.length; i++) {
    fd.append("files", files[i]);
  }

  const res = await fetch("/api/upload", { method: "POST", body: fd });
  if (res.ok) {
    alert("CARGA EXITOSA");
    init();
  }
}

init();
