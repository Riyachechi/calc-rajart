const API = "/api";

let lastResult = null; // holds the last successful calculation (for saving + quote text)

// ---------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => {
      b.classList.remove("active");
      b.setAttribute("aria-selected", "false");
    });
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));

    btn.classList.add("active");
    btn.setAttribute("aria-selected", "true");
    document.getElementById(`view-${btn.dataset.tab}`).classList.add("active");

    if (btn.dataset.tab === "orders") loadOrders();
  });
});

// ---------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------
function money(v) {
  return "₹" + Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function showToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => (t.hidden = true), 2600);
}

function formError(msg) {
  const el = document.getElementById("form-error");
  if (!msg) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.textContent = msg;
}

// ---------------------------------------------------------------
// Load dropdown options from the backend (driven by the Excel data)
// ---------------------------------------------------------------
async function loadOptions() {
  const res = await fetch(`${API}/rates/options`);
  const opts = await res.json();

  const gsmSelect = document.getElementById("gsm");
  gsmSelect.innerHTML = opts.gsm_options
    .map((g) => `<option value="${g}">${g} GSM</option>`)
    .join("");

  const sideGroup = document.getElementById("printing_side_group");
  sideGroup.innerHTML = opts.printing_sides
    .map(
      (s, i) => `
      <label>
        <input type="radio" name="printing_side" value="${s}" ${i === 0 ? "checked" : ""} />
        ${s}
      </label>`
    )
    .join("");

  const lamSelect = document.getElementById("lamination");
  lamSelect.innerHTML = opts.lamination_options
    .map((l) => `<option value="${l}">${l}</option>`)
    .join("");
}

// ---------------------------------------------------------------
// Read the current form state
// ---------------------------------------------------------------
function readForm() {
  const printingSide = document.querySelector('input[name="printing_side"]:checked');
  return {
    gsm: parseInt(document.getElementById("gsm").value, 10),
    quantity: parseInt(document.getElementById("quantity").value, 10),
    printing_side: printingSide ? printingSide.value : null,
    lamination: document.getElementById("lamination").value,
    use_nearest_quantity: document.getElementById("use_nearest").checked,
  };
}

// ---------------------------------------------------------------
// Calculate
// ---------------------------------------------------------------
document.getElementById("calc-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  formError(null);

  const payload = readForm();

  if (!payload.quantity || payload.quantity < 1) {
    formError("Enter a valid number of pieces.");
    return;
  }

  try {
    const res = await fetch(`${API}/calculate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      formError(err.detail || "Could not calculate a rate for this combination.");
      document.getElementById("result-body").hidden = true;
      document.getElementById("result-empty").hidden = false;
      document.getElementById("save-btn").disabled = true;
      return;
    }

    const result = await res.json();
    lastResult = result;
    renderResult(result);
    document.getElementById("save-btn").disabled = false;
  } catch (err) {
    formError("Couldn't reach the server. Please try again.");
  }
});

function renderResult(r) {
  document.getElementById("result-empty").hidden = true;
  document.getElementById("result-body").hidden = false;

  const warn = document.getElementById("nearest-warning");
  if (r.used_nearest_quantity) {
    warn.hidden = false;
    warn.textContent = `No exact rate for ${r.quantity.toLocaleString("en-IN")} pieces — nearest bracket used: ${r.rate_quantity_used.toLocaleString("en-IN")} pieces.`;
  } else {
    warn.hidden = true;
  }

  document.getElementById("result-context").textContent =
    `${r.quantity.toLocaleString("en-IN")} pieces · ${r.gsm} GSM · ${r.printing_side} · ${r.lamination} lamination`;

  document.getElementById("total-min").textContent = money(r.total_min);
  document.getElementById("total-max").textContent = money(r.total_max);
  document.getElementById("ppc-min").textContent = money(r.final_min_per_piece);
  document.getElementById("ppc-max").textContent = money(r.final_max_per_piece);
  document.getElementById("ppc-qty").textContent = r.quantity.toLocaleString("en-IN");

  const rows = [
    ["Printing minimum per piece", money(r.printing_min)],
    ["Printing maximum per piece", money(r.printing_max)],
    ["Lamination per piece", money(r.lamination_price)],
    ["Final minimum per piece", money(r.final_min_per_piece)],
    ["Final maximum per piece", money(r.final_max_per_piece)],
    ["Rate bracket used", `${r.rate_quantity_used.toLocaleString("en-IN")} pcs`],
    ["Complete order minimum", money(r.total_min)],
    ["Complete order maximum", money(r.total_max)],
  ];
  document.getElementById("breakdown-table").innerHTML = rows
    .map(([label, value]) => `<tr><td>${label}</td><td>${value}</td></tr>`)
    .join("");

  const customerName = document.getElementById("customer_name").value.trim();
  const quote = `
RAJ ART SERVICE
SHEET PRINTING QUOTATION

Customer Name:
${customerName || "Not Specified"}

----------------------------------------

GSM:
${r.gsm} GSM

Quantity:
${r.quantity.toLocaleString("en-IN")} Pieces

Printing:
${r.printing_side}

Lamination:
${r.lamination}

----------------------------------------

RATE PER PIECE:

Minimum:
${money(r.final_min_per_piece)}

Maximum:
${money(r.final_max_per_piece)}

----------------------------------------

COMPLETE ORDER PRICE:

Minimum:
${money(r.total_min)}

Maximum:
${money(r.total_max)}

----------------------------------------

Rate bracket used:
${r.rate_quantity_used.toLocaleString("en-IN")} pieces

This quotation represents a minimum-to-maximum
selling price range.

Final rates may be confirmed before order processing.

RAJ ART SERVICE
`.trim();

  document.getElementById("quote-text").value = quote;
}

document.getElementById("copy-btn").addEventListener("click", () => {
  const ta = document.getElementById("quote-text");
  ta.select();
  navigator.clipboard.writeText(ta.value).then(() => showToast("Quotation copied"));
});

// ---------------------------------------------------------------
// Save order to the database
// ---------------------------------------------------------------
document.getElementById("save-btn").addEventListener("click", async () => {
  if (!lastResult) return;

  const payload = {
    ...readForm(),
    customer_name: document.getElementById("customer_name").value.trim(),
    customer_phone: document.getElementById("customer_phone").value.trim(),
    notes: document.getElementById("notes").value.trim(),
  };

  try {
    const res = await fetch(`${API}/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("save failed");
    showToast("Order saved");
  } catch {
    showToast("Couldn't save this order. Please try again.");
  }
});

// ---------------------------------------------------------------
// Saved orders view
// ---------------------------------------------------------------
async function loadOrders(search = "") {
  const url = new URL(`${API}/orders`, window.location.origin);
  if (search) url.searchParams.set("search", search);

  const res = await fetch(url);
  const orders = await res.json();

  const tbody = document.getElementById("orders-tbody");
  const emptyState = document.getElementById("orders-empty");

  if (orders.length === 0) {
    tbody.innerHTML = "";
    emptyState.hidden = false;
    return;
  }
  emptyState.hidden = true;

  tbody.innerHTML = orders
    .map((o) => {
      const date = new Date(o.created_at).toLocaleString("en-IN", {
        day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
      });
      return `
        <tr data-id="${o.id}">
          <td>${date}</td>
          <td>${o.customer_name || "—"}</td>
          <td>${o.customer_phone || "—"}</td>
          <td>${o.gsm}</td>
          <td>${o.quantity.toLocaleString("en-IN")}</td>
          <td>${o.printing_side}</td>
          <td>${o.lamination}</td>
          <td>${money(o.total_min)} – ${money(o.total_max)}</td>
          <td><button class="delete-link" data-id="${o.id}">Delete</button></td>
        </tr>`;
    })
    .join("");

  tbody.querySelectorAll(".delete-link").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("Delete this saved order?")) return;
      await fetch(`${API}/orders/${btn.dataset.id}`, { method: "DELETE" });
      loadOrders(document.getElementById("order-search").value.trim());
    });
  });
}

let searchTimer;
document.getElementById("order-search").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadOrders(e.target.value.trim()), 250);
});

// ---------------------------------------------------------------
// Init
// ---------------------------------------------------------------
loadOptions();
