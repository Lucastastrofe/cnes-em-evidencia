const numberFormat = new Intl.NumberFormat("pt-BR");
const percentFormat = new Intl.NumberFormat("pt-BR", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const dateFormat = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "long",
  timeStyle: "short",
  timeZone: "America/Sao_Paulo",
});

function byId(id) {
  return document.getElementById(id);
}

function setText(id, value) {
  byId(id).textContent = value;
}

function createBarRow(label, value, maximum, valueLabel) {
  const row = document.createElement("div");
  row.className = "bar-row";

  const name = document.createElement("span");
  name.className = "bar-label";
  name.textContent = label;
  name.title = label;

  const track = document.createElement("div");
  track.className = "bar-track";
  track.setAttribute("aria-hidden", "true");
  const fill = document.createElement("div");
  fill.className = "bar-fill";
  fill.style.width = `${maximum ? (value / maximum) * 100 : 0}%`;
  track.append(fill);

  const amount = document.createElement("span");
  amount.className = "bar-value";
  amount.textContent = valueLabel;

  row.append(name, track, amount);
  return row;
}

function renderBars(container, rows, labelKey = "name") {
  container.replaceChildren();
  const maximum = Math.max(...rows.map((item) => item.records), 0);
  rows.forEach((item) => {
    container.append(createBarRow(item[labelKey], item.records, maximum, numberFormat.format(item.records)));
  });
}

function renderChecks(checks) {
  const table = byId("checks-table");
  table.replaceChildren();
  checks.forEach((check) => {
    const row = document.createElement("tr");
    const resultClass = check.failures === 0 ? "status-approved" : "status-finding";
    const cells = [check.label, check.dimension];
    cells.forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    });

    const statusCell = document.createElement("td");
    const status = document.createElement("span");
    status.className = `status ${resultClass}`;
    status.textContent = check.status;
    statusCell.append(status);
    row.append(statusCell);

    const failures = document.createElement("td");
    failures.className = "number";
    failures.textContent = numberFormat.format(check.failures);
    row.append(failures);

    const rate = document.createElement("td");
    rate.className = "number";
    rate.textContent = percentFormat.format(check.failure_rate);
    row.append(rate);
    table.append(row);
  });
}

function renderStateFilter(states) {
  const select = byId("state-filter");
  states
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name, "pt-BR"))
    .forEach((state) => {
      const option = document.createElement("option");
      option.value = state.code;
      option.textContent = state.name;
      select.append(option);
    });

  function updateDetail() {
    if (select.value === "all") {
      setText("state-detail", "Selecione uma UF para comparar volume e ocorrências de regras.");
      return;
    }
    const state = states.find((item) => item.code === select.value);
    const issueRate = state.records ? state.issues / state.records : 0;
    setText(
      "state-detail",
      `${state.name}: ${numberFormat.format(state.records)} registros e ${numberFormat.format(state.issues)} ocorrências de regras (${percentFormat.format(issueRate)}).`,
    );
  }

  select.addEventListener("change", updateDetail);
  updateDetail();
}

async function loadDashboard() {
  try {
    const [dashboardResponse, auditResponse] = await Promise.all([
      fetch("data/dashboard.json"),
      fetch("data/audit-report.json"),
    ]);
    if (!dashboardResponse.ok || !auditResponse.ok) throw new Error("publicação incompleta");

    const [dashboard, audit] = await Promise.all([
      dashboardResponse.json(),
      auditResponse.json(),
    ]);
    const coordinatesCheck = dashboard.checks.find((item) => item.id === "coordinates_missing");

    setText("source-line", `Fotografia processada em ${dateFormat.format(new Date(dashboard.metadata.generated_at))}.`);
    setText("finding-rate", percentFormat.format(coordinatesCheck.failure_rate));
    setText(
      "finding-copy",
      `${numberFormat.format(coordinatesCheck.failures)} de ${numberFormat.format(coordinatesCheck.evaluated)} registros não trazem o par completo de coordenadas. O campo é usado apenas no controle e seus valores não são publicados.`,
    );
    setText("total-records", numberFormat.format(dashboard.summary.total_records));
    setText("state-count", numberFormat.format(dashboard.summary.states_with_records));
    setText("check-count", numberFormat.format(dashboard.summary.checks_run));
    setText("finding-count", numberFormat.format(dashboard.summary.checks_with_findings));

    renderStateFilter(dashboard.by_state);
    renderBars(byId("state-chart"), dashboard.by_state.slice(0, 10));
    renderChecks(dashboard.checks);
    renderBars(byId("management-chart"), dashboard.by_management, "label");

    setText("run-id", audit.run_id);
    setText("generated-at", dateFormat.format(new Date(audit.generated_at)));
    setText("source-hash", audit.source.sha256);
    setText(
      "reconciliation",
      `${numberFormat.format(audit.reconciliation.rows_read)} lidos / ${numberFormat.format(audit.reconciliation.rows_aggregated)} agregados`,
    );
    const limitations = byId("limitations");
    audit.limitations.forEach((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      limitations.append(item);
    });

    byId("loading").hidden = true;
    byId("dashboard").hidden = false;
  } catch (error) {
    console.error(error);
    byId("loading").hidden = true;
    byId("error").hidden = false;
  }
}

loadDashboard();

