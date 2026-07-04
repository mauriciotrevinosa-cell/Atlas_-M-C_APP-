/**
 * Real estate view inputs renderer.
 * Source: Info instructions/bonampak_inputs.yaml + bonampak_inputs_README.md
 */
const BONAMPAK_INPUTS = {
  metadata: {
    generatedDate: "2026-02-18",
    source: "Info instructions/bonampak_inputs.yaml",
  },
  project: {
    name: "Bonampak / KIN Towers (Bonampak site)",
    currencyBase: "MXN",
    fxUsdMxn: 16.55,
  },
  site: {
    areaBeforeSetbacksM2: 9506.69,
    areaAfterSetbacksM2: 7267.99,
    zoning: {
      cosMax: 0.5,
      cusMax: 10.0,
      maxUnits: 190,
      maxFloors: 20,
      maxHeightM: 70.0,
    },
    landPriceEstimateMxn: 213600000.0,
  },
  program: {
    areas: {
      sellableTotalM2: 48887.59,
      parkingTotalM2: 12240.0,
      commercialAreaM2: 4600.0,
      residentialTowerM2: 15000.0,
      hotelTowerM2: 15000.0,
    },
    parking: {
      requiredResidentialStalls: 240,
      requiredCommercialStalls: 75,
      requiredTotalStalls: 315,
    },
  },
  construction: {
    costTotalConstructionMxn: 1700551800.0,
    costTotalConstructionPlusFfeeMxn: 1739691800.0,
    ffeeOsEMxn: 39140000.0,
  },
  costs: {
    studiesAndProjectsMxn: 297624720.0,
    permitsAndGovMxn: 27095703.9,
    supervisionAndPmMxn: 156145799.4,
    marketingAndSalesMxn: 105100000.0,
    contingencyAndReserveMxn: 183055180.0,
    feesMxn: 187060698.0,
    preopeningOpsIfHotelMxn: 249100000.0,
    mcCorporateMxn: 168810000.0,
    projectTotalLandAcquisitionMxn: 3574235296.3,
    projectTotalLandContributionMxn: 3496803592.4,
  },
  sales: {
    paymentStructure: {
      downPaymentPct: 0.2,
      duringConstructionPct: 0.6,
      atDeliveryPct: 0.2,
    },
    commissionBrokersPct: 0.05,
    salesPricePerM2: {
      initial: null,
      final: null,
      annualGrowth: null,
      preSaleDiscount: null,
    },
    absorptionUnitsPerQuarter: null,
  },
  simulation: {
    timestep: "monthly",
    sims: 10000,
    seed: 42,
    hurdleIrrAnnual: 0.12,
    distributions: {
      constructionOverrunPct: { type: "triangular", low: 0.0, mode: 0.05, high: 0.15 },
      constructionDelayMonths: { type: "triangular", low: 0, mode: 6, high: 18 },
      interestRateAnnual: { type: "normal", mu: 0.12, sigma: 0.03, floor: 0.06, cap: 0.22 },
    },
  },
};

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function formatNumber(value, decimals) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "Pending";
  }
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  }).format(value);
}

function formatM2(value) {
  return `${formatNumber(value, 2)} m2`;
}

function formatCurrencyMxn(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "Pending";
  }
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "Pending";
  }
  const pct = value * 100;
  const digits = Number.isInteger(pct) ? 0 : 1;
  return `${pct.toFixed(digits)}%`;
}

function renderList(containerId, rows) {
  const container = document.getElementById(containerId);
  if (!container) {
    return;
  }
  container.innerHTML = "";
  rows.forEach((row) => {
    const line = document.createElement("div");
    line.className = "realestate-list-row";

    const label = document.createElement("span");
    label.className = "realestate-list-label";
    label.textContent = row.label;

    const value = document.createElement("span");
    value.className = "realestate-list-value";
    value.textContent = row.value;

    line.appendChild(label);
    line.appendChild(value);
    container.appendChild(line);
  });
}

function renderPendingSalesFields() {
  const pendingFields = [];
  const sales = BONAMPAK_INPUTS.sales;

  if (sales.salesPricePerM2.initial === null) pendingFields.push("sales_price_per_m2.initial");
  if (sales.salesPricePerM2.final === null) pendingFields.push("sales_price_per_m2.final");
  if (sales.salesPricePerM2.annualGrowth === null) pendingFields.push("sales_price_per_m2.annual_growth");
  if (sales.salesPricePerM2.preSaleDiscount === null) pendingFields.push("sales_price_per_m2.pre_sale_discount");
  if (sales.absorptionUnitsPerQuarter === null) pendingFields.push("absorption.units_per_quarter");

  const container = document.getElementById("re-sales-pending");
  if (!container) {
    return;
  }

  container.innerHTML = "";
  const title = document.createElement("div");
  title.className = "realestate-pending-title";
  title.textContent = "Pending placeholders from source inputs:";
  container.appendChild(title);

  const chips = document.createElement("div");
  chips.className = "realestate-chip-list";
  pendingFields.forEach((item) => {
    const chip = document.createElement("span");
    chip.className = "realestate-chip";
    chip.textContent = item;
    chips.appendChild(chip);
  });
  container.appendChild(chips);
}

function renderRealEstateDevelopment() {
  const data = BONAMPAK_INPUTS;
  const site = data.site;
  const program = data.program;
  const construction = data.construction;
  const costs = data.costs;
  const sales = data.sales;
  const simulation = data.simulation;

  setText("re-project-name", data.project.name);
  setText(
    "re-project-meta",
    `Generated ${data.metadata.generatedDate} | FX USD/MXN ${formatNumber(data.project.fxUsdMxn, 2)} | Source: ${data.metadata.source}`
  );
  setText("re-currency-badge", `${data.project.currencyBase} Base`);

  setText("re-site-after", formatM2(site.areaAfterSetbacksM2));
  setText("re-sellable-area", formatM2(program.areas.sellableTotalM2));
  setText("re-required-parking", `${formatNumber(program.parking.requiredTotalStalls, 0)} stalls`);
  setText("re-land-price", formatCurrencyMxn(site.landPriceEstimateMxn));
  setText("re-construction-plus-ffee", formatCurrencyMxn(construction.costTotalConstructionPlusFfeeMxn));
  setText("re-total-acquisition", formatCurrencyMxn(costs.projectTotalLandAcquisitionMxn));

  renderList("re-zoning-list", [
    { label: "Area before setbacks", value: formatM2(site.areaBeforeSetbacksM2) },
    { label: "COS max", value: formatNumber(site.zoning.cosMax, 2) },
    { label: "CUS max", value: formatNumber(site.zoning.cusMax, 2) },
    { label: "Max units", value: formatNumber(site.zoning.maxUnits, 0) },
    { label: "Max floors", value: formatNumber(site.zoning.maxFloors, 0) },
    { label: "Max height", value: `${formatNumber(site.zoning.maxHeightM, 1)} m` },
    { label: "Parking total area", value: formatM2(program.areas.parkingTotalM2) },
    { label: "Commercial area", value: formatM2(program.areas.commercialAreaM2) },
    { label: "Residential tower area", value: formatM2(program.areas.residentialTowerM2) },
    { label: "Hotel tower area", value: formatM2(program.areas.hotelTowerM2) },
  ]);

  renderList("re-cost-list", [
    { label: "Construction total", value: formatCurrencyMxn(construction.costTotalConstructionMxn) },
    { label: "FF&E / OS&E", value: formatCurrencyMxn(construction.ffeeOsEMxn) },
    { label: "Studies + projects", value: formatCurrencyMxn(costs.studiesAndProjectsMxn) },
    { label: "Permits + gov", value: formatCurrencyMxn(costs.permitsAndGovMxn) },
    { label: "Supervision + PM", value: formatCurrencyMxn(costs.supervisionAndPmMxn) },
    { label: "Marketing + sales", value: formatCurrencyMxn(costs.marketingAndSalesMxn) },
    { label: "Contingency + reserve", value: formatCurrencyMxn(costs.contingencyAndReserveMxn) },
    { label: "Fees", value: formatCurrencyMxn(costs.feesMxn) },
    { label: "Pre-opening ops (hotel)", value: formatCurrencyMxn(costs.preopeningOpsIfHotelMxn) },
    { label: "MC corporate", value: formatCurrencyMxn(costs.mcCorporateMxn) },
    { label: "Total (land acquisition)", value: formatCurrencyMxn(costs.projectTotalLandAcquisitionMxn) },
    { label: "Total (land contribution)", value: formatCurrencyMxn(costs.projectTotalLandContributionMxn) },
  ]);

  renderList("re-sales-list", [
    { label: "Down payment", value: formatPercent(sales.paymentStructure.downPaymentPct) },
    { label: "During construction", value: formatPercent(sales.paymentStructure.duringConstructionPct) },
    { label: "At delivery", value: formatPercent(sales.paymentStructure.atDeliveryPct) },
    { label: "Broker commission", value: formatPercent(sales.commissionBrokersPct) },
    { label: "Required residential parking", value: `${formatNumber(program.parking.requiredResidentialStalls, 0)} stalls` },
    { label: "Required commercial parking", value: `${formatNumber(program.parking.requiredCommercialStalls, 0)} stalls` },
  ]);
  renderPendingSalesFields();

  renderList("re-simulation-list", [
    { label: "Timestep", value: simulation.timestep },
    { label: "Simulations", value: formatNumber(simulation.sims, 0) },
    { label: "Seed", value: formatNumber(simulation.seed, 0) },
    { label: "Hurdle IRR (annual)", value: formatPercent(simulation.hurdleIrrAnnual) },
    {
      label: "Construction overrun",
      value: `${simulation.distributions.constructionOverrunPct.type} (${formatPercent(
        simulation.distributions.constructionOverrunPct.low
      )} / ${formatPercent(simulation.distributions.constructionOverrunPct.mode)} / ${formatPercent(
        simulation.distributions.constructionOverrunPct.high
      )})`,
    },
    {
      label: "Construction delay (months)",
      value: `${simulation.distributions.constructionDelayMonths.type} (${formatNumber(
        simulation.distributions.constructionDelayMonths.low,
        0
      )} / ${formatNumber(simulation.distributions.constructionDelayMonths.mode, 0)} / ${formatNumber(
        simulation.distributions.constructionDelayMonths.high,
        0
      )})`,
    },
    {
      label: "Interest rate (annual)",
      value: `${simulation.distributions.interestRateAnnual.type} (mu ${formatPercent(
        simulation.distributions.interestRateAnnual.mu
      )}, sigma ${formatPercent(simulation.distributions.interestRateAnnual.sigma)})`,
    },
  ]);
}

function setLaunchStatus(message, color) {
  const el = document.getElementById("re-launch-status");
  if (!el) {
    return;
  }
  el.textContent = message;
  el.style.color = color || "#777";
}

function getRealEstateRenderTarget() {
  return {
    statusId: "re-3d-render-status",
    containerId: "re-3d-output-container",
    outputId: "re-three-output",
    legendId: "re-3d-legend",
    correlationPanelId: "re-correlation-panel",
    correlationCanvasId: "re-correlation-canvas",
  };
}

const REAL_ESTATE_RENDER = {
  renderer: null,
  scene: null,
  camera: null,
  mesh: null,
  wire: null,
  animationId: null,
  theta: Math.PI / 4,
  phi: 1.1,
  radius: 44,
  dragging: false,
  lastX: 0,
  lastY: 0,
  simTick: 0,
  containerId: null,
};

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function resolveRenderElements(target = getRealEstateRenderTarget()) {
  return {
    status: document.getElementById(target.statusId),
    container: document.getElementById(target.containerId),
    output: document.getElementById(target.outputId),
    legend: document.getElementById(target.legendId),
    correlationPanel: document.getElementById(target.correlationPanelId),
    correlationCanvas: document.getElementById(target.correlationCanvasId),
  };
}

function getRealEstateScenario() {
  const sellableM2 = BONAMPAK_INPUTS.program.areas.sellableTotalM2;
  const totalCost = BONAMPAK_INPUTS.costs.projectTotalLandAcquisitionMxn;
  const overrunMode = BONAMPAK_INPUTS.simulation.distributions.constructionOverrunPct.mode;
  const delayMode = BONAMPAK_INPUTS.simulation.distributions.constructionDelayMonths.mode;
  const interestRate = BONAMPAK_INPUTS.simulation.distributions.interestRateAnnual.mu;
  const breakEvenPriceM2 = totalCost / sellableM2;
  const targetPriceM2 = breakEvenPriceM2 * 1.25;

  return {
    sellableM2,
    totalCost,
    breakEvenPriceM2,
    targetPriceM2,
    overrunMode,
    delayMode,
    interestRate,
    payment: BONAMPAK_INPUTS.sales.paymentStructure,
  };
}

function createRealEstateSurfaceGeometry(grid, palette) {
  const rows = grid.length;
  const cols = grid[0].length;

  let minZ = Infinity;
  let maxZ = -Infinity;
  for (let i = 0; i < rows; i += 1) {
    for (let j = 0; j < cols; j += 1) {
      const value = grid[i][j];
      if (value < minZ) minZ = value;
      if (value > maxZ) maxZ = value;
    }
  }
  const range = (maxZ - minZ) || 1;
  const spacing = 24 / Math.max(rows, cols);
  const heightScale = 14 / range;

  const positions = new Float32Array(rows * cols * 3);
  const colors = new Float32Array(rows * cols * 3);
  const tempColor = new THREE.Color();

  for (let i = 0; i < rows; i += 1) {
    for (let j = 0; j < cols; j += 1) {
      const index = (i * cols + j) * 3;
      const normalized = (grid[i][j] - minZ) / range;

      positions[index] = (j - cols / 2) * spacing;
      positions[index + 1] = (grid[i][j] - minZ) * heightScale;
      positions[index + 2] = (i - rows / 2) * spacing;

      if (palette === "margin") {
        tempColor.setHSL(0.02 + normalized * 0.35, 0.85, 0.42 + normalized * 0.1);
      } else if (palette === "correlation") {
        if (normalized >= 0.5) {
          tempColor.setHSL(0.01, 0.8, 0.5 + (normalized - 0.5) * 0.2);
        } else {
          tempColor.setHSL(0.58, 0.75, 0.45 + (0.5 - normalized) * 0.2);
        }
      } else {
        tempColor.setHSL(0.6 - normalized * 0.45, 0.8, 0.4 + normalized * 0.12);
      }

      colors[index] = tempColor.r;
      colors[index + 1] = tempColor.g;
      colors[index + 2] = tempColor.b;
    }
  }

  const indices = [];
  for (let i = 0; i < rows - 1; i += 1) {
    for (let j = 0; j < cols - 1; j += 1) {
      const a = i * cols + j;
      const b = a + 1;
      const c = a + cols;
      const d = c + 1;
      indices.push(a, b, c);
      indices.push(b, d, c);
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function updateCamera() {
  if (!REAL_ESTATE_RENDER.camera) return;
  const x = REAL_ESTATE_RENDER.radius * Math.sin(REAL_ESTATE_RENDER.phi) * Math.cos(REAL_ESTATE_RENDER.theta);
  const y = 8 + REAL_ESTATE_RENDER.radius * Math.cos(REAL_ESTATE_RENDER.phi);
  const z = REAL_ESTATE_RENDER.radius * Math.sin(REAL_ESTATE_RENDER.phi) * Math.sin(REAL_ESTATE_RENDER.theta);
  REAL_ESTATE_RENDER.camera.position.set(x, y, z);
  REAL_ESTATE_RENDER.camera.lookAt(0, 6, 0);
}

function bindOrbitControls(outputEl) {
  if (!outputEl || outputEl.dataset.reOrbitBound === "1") return;
  outputEl.dataset.reOrbitBound = "1";

  outputEl.addEventListener("mousedown", (event) => {
    REAL_ESTATE_RENDER.dragging = true;
    REAL_ESTATE_RENDER.lastX = event.clientX;
    REAL_ESTATE_RENDER.lastY = event.clientY;
    outputEl.style.cursor = "grabbing";
  });

  window.addEventListener("mouseup", () => {
    REAL_ESTATE_RENDER.dragging = false;
    if (outputEl) outputEl.style.cursor = "grab";
  });

  window.addEventListener("mousemove", (event) => {
    if (!REAL_ESTATE_RENDER.dragging) return;
    const dx = event.clientX - REAL_ESTATE_RENDER.lastX;
    const dy = event.clientY - REAL_ESTATE_RENDER.lastY;
    REAL_ESTATE_RENDER.lastX = event.clientX;
    REAL_ESTATE_RENDER.lastY = event.clientY;

    REAL_ESTATE_RENDER.theta += dx * 0.01;
    REAL_ESTATE_RENDER.phi = clamp(REAL_ESTATE_RENDER.phi + dy * 0.01, 0.2, Math.PI - 0.2);
    updateCamera();
  });

  outputEl.addEventListener("wheel", (event) => {
    event.preventDefault();
    REAL_ESTATE_RENDER.radius = clamp(REAL_ESTATE_RENDER.radius + event.deltaY * 0.03, 20, 90);
    updateCamera();
  }, { passive: false });
}

function ensureRenderer(outputEl) {
  if (!outputEl || typeof THREE === "undefined") return false;
  const sameContainer = REAL_ESTATE_RENDER.containerId === outputEl.id;

  if (!sameContainer && REAL_ESTATE_RENDER.renderer) {
    cancelAnimationFrame(REAL_ESTATE_RENDER.animationId);
    REAL_ESTATE_RENDER.animationId = null;
    REAL_ESTATE_RENDER.renderer.dispose();
    if (REAL_ESTATE_RENDER.renderer.domElement.parentElement) {
      REAL_ESTATE_RENDER.renderer.domElement.remove();
    }
    REAL_ESTATE_RENDER.renderer = null;
    REAL_ESTATE_RENDER.scene = null;
    REAL_ESTATE_RENDER.camera = null;
    REAL_ESTATE_RENDER.mesh = null;
    REAL_ESTATE_RENDER.wire = null;
  }

  if (!REAL_ESTATE_RENDER.renderer) {
    REAL_ESTATE_RENDER.containerId = outputEl.id;
    REAL_ESTATE_RENDER.scene = new THREE.Scene();
    REAL_ESTATE_RENDER.scene.background = new THREE.Color("#050f29");

    REAL_ESTATE_RENDER.camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
    updateCamera();

    const ambient = new THREE.AmbientLight(0xffffff, 0.55);
    REAL_ESTATE_RENDER.scene.add(ambient);
    const directional = new THREE.DirectionalLight(0xffffff, 0.85);
    directional.position.set(16, 24, 18);
    REAL_ESTATE_RENDER.scene.add(directional);
    const fill = new THREE.PointLight(0x5bc0ff, 0.35, 260);
    fill.position.set(-12, 14, -8);
    REAL_ESTATE_RENDER.scene.add(fill);
    REAL_ESTATE_RENDER.scene.add(new THREE.GridHelper(40, 20, 0x2a3b62, 0x18233f));

    REAL_ESTATE_RENDER.renderer = new THREE.WebGLRenderer({ antialias: true });
    REAL_ESTATE_RENDER.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    outputEl.innerHTML = "";
    outputEl.appendChild(REAL_ESTATE_RENDER.renderer.domElement);
    bindOrbitControls(outputEl);

    const animate = () => {
      REAL_ESTATE_RENDER.theta += 0.0012;
      updateCamera();
      REAL_ESTATE_RENDER.renderer.render(REAL_ESTATE_RENDER.scene, REAL_ESTATE_RENDER.camera);
      REAL_ESTATE_RENDER.animationId = requestAnimationFrame(animate);
    };
    animate();
  }

  const width = Math.max(320, Math.floor(outputEl.clientWidth || outputEl.offsetWidth || 320));
  const height = Math.max(240, Math.floor(outputEl.clientHeight || outputEl.offsetHeight || 240));
  REAL_ESTATE_RENDER.renderer.setSize(width, height);
  REAL_ESTATE_RENDER.camera.aspect = width / height;
  REAL_ESTATE_RENDER.camera.updateProjectionMatrix();
  return true;
}

function setSurface(geometry) {
  if (!REAL_ESTATE_RENDER.scene) return;

  if (REAL_ESTATE_RENDER.mesh) {
    REAL_ESTATE_RENDER.scene.remove(REAL_ESTATE_RENDER.mesh);
    REAL_ESTATE_RENDER.mesh.geometry.dispose();
    REAL_ESTATE_RENDER.mesh.material.dispose();
    REAL_ESTATE_RENDER.mesh = null;
  }
  if (REAL_ESTATE_RENDER.wire) {
    REAL_ESTATE_RENDER.scene.remove(REAL_ESTATE_RENDER.wire);
    REAL_ESTATE_RENDER.wire.geometry.dispose();
    REAL_ESTATE_RENDER.wire.material.dispose();
    REAL_ESTATE_RENDER.wire = null;
  }

  REAL_ESTATE_RENDER.mesh = new THREE.Mesh(
    geometry,
    new THREE.MeshPhongMaterial({
      vertexColors: true,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.9,
      shininess: 56,
    })
  );
  REAL_ESTATE_RENDER.scene.add(REAL_ESTATE_RENDER.mesh);

  REAL_ESTATE_RENDER.wire = new THREE.LineSegments(
    new THREE.WireframeGeometry(geometry),
    new THREE.LineBasicMaterial({ color: 0x6f86b5, transparent: true, opacity: 0.18 })
  );
  REAL_ESTATE_RENDER.scene.add(REAL_ESTATE_RENDER.wire);
}

function buildMarginSurface(scenario) {
  const rows = 24;
  const cols = 24;
  const grid = [];

  for (let i = 0; i < rows; i += 1) {
    const overrun = i / (rows - 1) * BONAMPAK_INPUTS.simulation.distributions.constructionOverrunPct.high;
    const row = [];
    for (let j = 0; j < cols; j += 1) {
      const priceFactor = 0.85 + (j / (cols - 1)) * 0.75;
      const priceM2 = scenario.targetPriceM2 * priceFactor;
      const delayPenalty = 1 - (scenario.delayMode / 24) * 0.08;
      const revenue = priceM2 * scenario.sellableM2 * delayPenalty;
      const carry = BONAMPAK_INPUTS.construction.costTotalConstructionPlusFfeeMxn * scenario.interestRate * (0.35 + overrun);
      const adjustedCost = scenario.totalCost * (1 + overrun) + carry;
      const projectMarginMxn = revenue - adjustedCost;
      row.push(projectMarginMxn / 1000000);
    }
    grid.push(row);
  }
  return grid;
}

function buildDriverCorrelation() {
  const labels = [
    "Price/m2",
    "Absorption",
    "Overrun",
    "Delay",
    "Interest",
    "Marketing",
    "Contingency",
  ];

  const matrix = [
    [1.00, 0.62, -0.55, -0.46, -0.58, 0.38, -0.24],
    [0.62, 1.00, -0.41, -0.52, -0.43, 0.44, -0.18],
    [-0.55, -0.41, 1.00, 0.66, 0.57, -0.21, 0.61],
    [-0.46, -0.52, 0.66, 1.00, 0.49, -0.15, 0.47],
    [-0.58, -0.43, 0.57, 0.49, 1.00, -0.11, 0.36],
    [0.38, 0.44, -0.21, -0.15, -0.11, 1.00, -0.22],
    [-0.24, -0.18, 0.61, 0.47, 0.36, -0.22, 1.00],
  ];

  const grid = matrix.map((row) => row.map((value) => value * 10));
  return { labels, matrix, grid };
}

function buildSimulationSurface(scenario, tick) {
  const months = 30;
  const scenarios = 24;
  const grid = [];
  const absorptionBase = (BONAMPAK_INPUTS.site.zoning.maxUnits / 12);

  for (let m = 0; m < months; m += 1) {
    const row = [];
    for (let s = 0; s < scenarios; s += 1) {
      const stress = (s / (scenarios - 1)) * 2 - 1;
      const oscillation = Math.sin((m + 1) * 0.35 + tick * 0.22 + s * 0.11);

      const overrun = clamp(scenario.overrunMode + stress * 0.05 + oscillation * 0.01, 0, 0.18);
      const delay = clamp(scenario.delayMode + Math.max(0, stress * 6) + Math.abs(oscillation) * 1.4, 0, 20);
      const interest = clamp(scenario.interestRate + stress * 0.015, 0.07, 0.20);
      const priceM2 = scenario.targetPriceM2 * (1 - stress * 0.08);
      const absorptionQ = absorptionBase * (1 - Math.max(0, stress) * 0.32);

      const elapsed = clamp((m - delay) / Math.max(1, months - delay), 0, 1);
      const prevElapsed = clamp((m - 1 - delay) / Math.max(1, months - delay), 0, 1);
      const progressDelta = Math.max(0, elapsed - prevElapsed);

      const soldRate = clamp((absorptionQ / BONAMPAK_INPUTS.site.zoning.maxUnits) * 3.2, 0.01, 0.20);
      const soldDelta = clamp(progressDelta * (0.65 + soldRate * 4), 0, 0.08);

      const totalRevenue = priceM2 * scenario.sellableM2;
      const salesCollectionFactor =
        scenario.payment.downPaymentPct +
        scenario.payment.duringConstructionPct * elapsed +
        scenario.payment.atDeliveryPct * clamp((elapsed - 0.85) / 0.15, 0, 1);
      const inflow = totalRevenue * soldDelta * salesCollectionFactor;

      const adjustedCost = scenario.totalCost * (1 + overrun);
      const constructionOutflow = adjustedCost * progressDelta;
      const carrying = adjustedCost * interest / 12 * (0.45 + (1 - elapsed) * 0.35);
      const monthlyOps = BONAMPAK_INPUTS.costs.adminAndOpsMxn ? (BONAMPAK_INPUTS.costs.adminAndOpsMxn / months) : 3500000;

      const cumulativeProxy = (inflow - constructionOutflow - carrying - monthlyOps) * (m + 1) * 0.22;
      row.push(cumulativeProxy / 1000000);
    }
    grid.push(row);
  }
  return grid;
}

function drawCorrelationHeatmap(labels, matrix, canvas) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const width = Math.max(520, Math.floor(canvas.getBoundingClientRect().width || 640));
  const height = 320;
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#0f1523";
  ctx.fillRect(0, 0, width, height);

  const n = labels.length;
  const marginLeft = 92;
  const marginTop = 18;
  const marginRight = 14;
  const marginBottom = 76;
  const plotW = width - marginLeft - marginRight;
  const plotH = height - marginTop - marginBottom;
  const cellW = plotW / n;
  const cellH = plotH / n;

  const getColor = (v) => {
    const value = clamp(v, -1, 1);
    if (value >= 0) {
      const light = 58 - value * 22;
      return `hsl(8, 78%, ${light}%)`;
    }
    const light = 60 - Math.abs(value) * 22;
    return `hsl(214, 76%, ${light}%)`;
  };

  for (let i = 0; i < n; i += 1) {
    for (let j = 0; j < n; j += 1) {
      const x = marginLeft + j * cellW;
      const y = marginTop + i * cellH;
      ctx.fillStyle = getColor(matrix[i][j]);
      ctx.fillRect(x, y, cellW, cellH);
      ctx.strokeStyle = "rgba(30, 50, 80, 0.45)";
      ctx.strokeRect(x, y, cellW, cellH);
    }
  }

  ctx.fillStyle = "#9ab";
  ctx.font = "10px Inter, Arial, sans-serif";
  for (let i = 0; i < n; i += 1) {
    const y = marginTop + (i + 0.5) * cellH;
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillText(labels[i], marginLeft - 8, y);
  }

  for (let j = 0; j < n; j += 1) {
    const x = marginLeft + (j + 0.5) * cellW;
    ctx.save();
    ctx.translate(x, marginTop + plotH + 10);
    ctx.rotate(-Math.PI / 4);
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    ctx.fillText(labels[j], 0, 0);
    ctx.restore();
  }
}

function updateRealEstateLegend(type, legendEl) {
  if (!legendEl) return;
  legendEl.style.display = "block";
  if (type === "vol_surface") {
    legendEl.textContent = "Surface: Gross Margin (MMXN) | X: Price per m2 | Y: Construction overrun.";
  } else if (type === "correlation") {
    legendEl.textContent = "Surface/Heatmap: Correlation of development drivers (price, absorption, overrun, delay, interest).";
  } else {
    legendEl.textContent = "Surface: Cashflow stress simulation (MMXN) | X: Scenario stress | Y: Month.";
  }
}

function renderRealEstateSurface(type) {
  const els = resolveRenderElements();
  if (!els.output || typeof THREE === "undefined") {
    setLaunchStatus("Renderer unavailable in this session.", "#e74c3c");
    if (els.status) {
      els.status.textContent = "Three.js not available.";
      els.status.style.color = "#e74c3c";
    }
    return false;
  }

  if (!ensureRenderer(els.output)) {
    setLaunchStatus("Could not initialize Real Estate renderer.", "#e74c3c");
    return false;
  }

  const scenario = getRealEstateScenario();
  let grid = [];
  let palette = "margin";

  if (type === "vol_surface") {
    grid = buildMarginSurface(scenario);
    palette = "margin";
    if (els.correlationPanel) els.correlationPanel.style.display = "none";
  } else if (type === "correlation") {
    const corr = buildDriverCorrelation();
    grid = corr.grid;
    palette = "correlation";
    if (els.correlationPanel) els.correlationPanel.style.display = "block";
    drawCorrelationHeatmap(corr.labels, corr.matrix, els.correlationCanvas);
  } else {
    REAL_ESTATE_RENDER.simTick += 1;
    grid = buildSimulationSurface(scenario, REAL_ESTATE_RENDER.simTick);
    palette = "simulation";
    if (els.correlationPanel) els.correlationPanel.style.display = "none";
  }

  const geometry = createRealEstateSurfaceGeometry(grid, palette);
  setSurface(geometry);
  updateRealEstateLegend(type, els.legend);

  if (els.status) {
    if (type === "vol_surface") {
      els.status.textContent = "Rendered real-estate margin surface (Bonampak inputs).";
    } else if (type === "correlation") {
      els.status.textContent = "Rendered development-driver correlation surface and matrix.";
    } else {
      els.status.textContent = "Rendered real-estate cashflow stress simulation frame.";
    }
    els.status.style.color = "#4caf50";
  }
  return true;
}

function openRealEstateRender(type) {
  setLaunchStatus("Rendering real-estate model...", "#777");
  const ok = renderRealEstateSurface(type);
  if (ok) {
    setLaunchStatus("Real Estate render generated with Bonampak development inputs.", "#4caf50");
  } else {
    setLaunchStatus("Could not generate Real Estate render.", "#e74c3c");
  }
}

function openRealEstateSimulation() {
  setLaunchStatus("Running real-estate simulation frame...", "#777");
  const ok = renderRealEstateSurface("simulation");
  if (ok) {
    setLaunchStatus("Real Estate simulation generated with development assumptions.", "#4caf50");
  } else {
    setLaunchStatus("Could not generate Real Estate simulation.", "#e74c3c");
  }
}

window.renderRealEstateDevelopment = renderRealEstateDevelopment;
window.openRealEstateRender = openRealEstateRender;
window.openRealEstateSimulation = openRealEstateSimulation;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", renderRealEstateDevelopment);
} else {
  renderRealEstateDevelopment();
}
