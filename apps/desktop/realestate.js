/**
 * M&C Real Estate Development Module
 * Project 001: Bonampak (KiN Towers) - Cancun, Q. Roo
 * AutoCAD-like Plan Viewer + Project Data Dashboard
 */

// ============================================================
// PROJECT DATA - KiN Towers (Extracted from official documents)
// ============================================================

const KIN_TOWERS_DATA = {
  project: {
    name: 'KiN Towers',
    code: 'PROJ-001',
    developer: 'M&C, SAPI de C.V.',
    architect: 'MID4 Arquitectura y Construccion',
    location: 'Av. Bonampak, Centro de Cancun, Quintana Roo, Mexico',
    landArea: 9506.688, // m2 (before restrictions)
    landAreaNeto: 7267.988, // m2 (after restrictions/donations)
    status: 'Pre-Construction',
    phase: 'Desarrollo Ejecutivo',
    timeline: {
      ejecutivo: { start: 'Jun 2026', end: 'Dic 2026', months: 6 },
      permisos: { start: 'Jun 2026', end: 'Mar 2027', months: 9 },
      ventasFnF: { start: 'Mar 2027', end: null, months: null },
      lanzamiento: { start: 'Jun 2027', end: null, months: null },
      construccion: { start: 'Jun 2027', end: 'Jun 2032', months: 60 },
      cimentacion: { start: 'Jun 2027', end: 'Dic 2027', months: 6 },
      estructura: { start: 'Ene 2028', end: 'Dic 2029', months: 24 },
      acabados: { start: 'Ene 2030', end: 'Dic 2031', months: 24 },
      amenidades: { start: 'Ene 2031', end: 'Jun 2032', months: 18 },
      entrega: { start: 'Jun 2032', end: 'Dic 2032', months: 6 }
    }
  },

  terreno: {
    // Medidas antes de limitantes
    frenteAv: 78.18,          // m - Frente sobre Av. Bonampak
    ladoPosterior: 78.18,     // m
    fondoNorte: 121.6,        // m
    fondoSur: 121.6,          // m
    superficieBruta: 9506.688, // m2 (antes de limitantes)
    // Limitantes
    cos: { porcentaje: '50%', superficie: 4753.344 }, // m2
    cus: { coeficiente: 10, superficie: 95066.88 },   // m2
    densidadNeta: 200,        // viviendas por hectarea
    maxViviendas: 190,        // unidades
    restriccionFrente: 10,    // m
    restriccionFondo: 5,      // m
    restriccionLateralNorte: 5, // m
    restriccionLateralSur: 5,   // m
    nivelesMaximos: 20,       // pisos
    alturaMaxEntrePisos: 3.5, // m
    alturaMaxima: 70,         // m
    cajonesVivienda: 240,     // cajones para 160 unidades
    cajonesComercial: 75,     // cajones para 30 unidades
    totalCajones: 315,        // minimo acorde al proyecto
    // Medidas despues de restricciones
    donacionPerimetraria: 2238.7,  // m2
    frenteNeto: 68.18,        // m
    posteriorNeto: 68.18,     // m
    fondoNorteNeto: 106.6,    // m
    fondoSurNeto: 106.6,      // m
    superficieNeta: 7267.988, // m2
    // Precio
    precioEstimado: 213600000, // MXN
    tipoCambio: 16.55         // Pesos por Dolar
  },

  areas: {
    // Areas vendibles
    estacionamiento: 12240,         // m2
    estacionamientoExterno: 2047.59, // m2
    areaViviendaResidencial: 15000,  // m2
    areaTorreHotelera: 15000,        // m2
    areaComercial: 4600,             // m2
    totalM2Vendibles: 48887.59,      // m2

    // Totales por seccion
    plantaBaja: 7467.59,       // m2
    segundoNivel: 4520,        // m2
    terceroCuartoNivel: 7580,  // m2
    quintoNivel: 3000,         // m2
    niveles6a15: 30000,        // m2
    nivel16: 3000,             // m2
    totalM2Utilizados: 55567.59, // m2

    // Totales de areas
    areaComun: 680,            // m2
    lobbyResidencial: 1500,    // m2
    lobbyHotelero: 1500,       // m2
    rooftopResidencial: 1500,  // m2
    rooftopHotelera: 1500,     // m2
    totalArea: 55567.59        // m2
  },

  // Costos de construccion por area (from Desgloce sheet)
  costoConstruccion: {
    precioM2Estimado: 35000,   // MXN por m2
    areaComun: { total: 23800000, precioM2: 35000 },          // MXN
    estacionamiento: { total: 244800000, precioM2: 20000 },    // MXN
    estacionamientoExterno: { total: 40951800, precioM2: 20000 }, // MXN
    lobbyResidencial: { total: 45000000, precioM2: 30000 },    // MXN
    lobbyHotelero: { total: 45000000, precioM2: 30000 },       // MXN
    areaViviendaResidencial: { total: 525000000, precioM2: 35000 }, // MXN
    areaTorreHotelera: { total: 525000000, precioM2: 35000 },   // MXN
    rooftopResidencial: { total: 45000000, precioM2: 30000 },   // MXN
    rooftopHotelera: { total: 45000000, precioM2: 30000 },      // MXN
    areaComercial: { total: 161000000, precioM2: 35000 },       // MXN
    costoTotalConstruccion: 1700551800  // MXN (CTC)
  },

  unidades: {
    total: 190,
    maxViviendas: 190,
    edificioNorte: { nombre: 'Torre Residencial', deptos: 80, tipo: 'Residencial', deptoPorNivel: 8 },
    edificioSur: { nombre: 'Torre Hotelera', deptos: 80, tipo: 'Condo-Hotel', habitacionesPorNivel: 8 },
    nivelesResidenciales: '6-15',   // 10 pisos
    nivelesHoteleros: '6-15',       // 10 pisos
    dimensionTorre: { frente: 30, lado: 50, totalPorPiso: 1500 } // m2
  },

  financiero: {
    tipoCambio: 16.55,          // MXN por USD
    costoTotalConstruccion: { mxn: 1700551800, usd: 102752374.62 },
    costoTotalProyectoAdquisicion: { mxn: 3574235296.30, usd: 215965878.93 },
    costoTotalProyectoAportacion: { mxn: 3496803592.40, usd: 211287226.13 },
    costoPromedioM2AdquisicionTerreno: { mxn: 73111.30, usd: 4417.60 },
    costoPromedioM2AportacionTerreno: { mxn: 71527.43, usd: 4321.90 },
    precioM2VendibleConstruccion: { mxn: 34784.94, usd: 2101.81 }
  },

  costosDesglose: [
    { categoria: 'Terreno - Adquisicion', mxn: 274137600, usd: 16564205.44 },
    { categoria: 'Terreno - Aportacion', mxn: 223801600, usd: 13522755.29 },
    { categoria: 'Gastos Legales y Corporativos', mxn: 5800000, usd: 350453.17 },
    { categoria: 'Estudios y Proyectos', mxn: 297624720, usd: 17983366.77 },
    { categoria: 'Permisos y Tramites Gubernamentales', mxn: 27095703.90, usd: 1637202.65 },
    { categoria: 'Construccion Total', mxn: 1739691800, usd: 105117329.31 },
    { categoria: '  5.1 Obra Civil - Infraestructura (10%)', mxn: 170055180, usd: 10275237.46 },
    { categoria: '  5.2 Obra Negra y Gris (38%)', mxn: 646209684, usd: 39045902.36 },
    { categoria: '  5.3 Acabados - Obra Blanca (25%)', mxn: 425137950, usd: 25688093.66 },
    { categoria: '  5.4 Instalaciones y Equipamiento (17%)', mxn: 289093806, usd: 17467903.69 },
    { categoria: '  5.5 Areas Comunes / Amenidades / Amueblado (10%)', mxn: 209195180, usd: 12640192.15 },
    { categoria: 'Supervision y Gestion de Obra', mxn: 156145799.40, usd: 9434791.50 },
    { categoria: 'Costos de Financiamiento', mxn: 0, usd: 0 },
    { categoria: 'Marketing y Comercializacion', mxn: 105100000, usd: 6350453.17 },
    { categoria: 'Administracion y Operacion', mxn: 103900000, usd: 6277945.62 },
    { categoria: 'Gastos Legales Finales y Entrega', mxn: 16700000, usd: 1009063.44 },
    { categoria: 'Impuestos y Retenciones', mxn: 60013795, usd: 3626211.18 },
    { categoria: 'Contingencias y Fondo de Reserva', mxn: 183055180, usd: 11060735.95 },
    { categoria: 'Comisiones / Fees del Proyecto', mxn: 187060698, usd: 11302761.21 },
    { categoria: 'Pre-Apertura y Operacion Hotel', mxn: 249100000, usd: 15051359.52 },
    { categoria: 'M&C (Corporativo)', mxn: 168810000, usd: 10200000 }
  ],

  // Desglose detallado de la construccion
  construccionDetalle: {
    obraCivil: {
      nombre: 'Obra Civil - Infraestructura (10%)',
      total: { mxn: 170055180 },
      items: [
        { nombre: 'Trazo y Nivelacion (2%)', mxn: 34011036 },
        { nombre: 'Excavacion y Movimiento de Tierras (2%)', mxn: 34011036 },
        { nombre: 'Cimentacion Profunda o Superficial (3%)', mxn: 51016554 },
        { nombre: 'Muros de Contencion (1%)', mxn: 17005518 },
        { nombre: 'Rellenos Compactados (1%)', mxn: 17005518 },
        { nombre: 'Urbanizacion Interna (1%)', mxn: 17005518 }
      ]
    },
    obraNegraGris: {
      nombre: 'Construccion - Obra Negra y Gris (38%)',
      total: { mxn: 646209684 },
      items: [
        { nombre: 'Estructura de Concreto o Acero (14%)', mxn: 238077252 },
        { nombre: 'Mamposteria y Muros Divisorios (6%)', mxn: 102033108 },
        { nombre: 'Instalaciones Ocultas (7%)', mxn: 119038626 },
        { nombre: 'Elevadores y Foso (3%)', mxn: 51016554 },
        { nombre: 'Tanques Septicos o Carcamos (2%)', mxn: 34011036 },
        { nombre: 'Cisterna y Bombeo (2%)', mxn: 34011036 },
        { nombre: 'Impermeabilizacion (2%)', mxn: 34011036 },
        { nombre: 'Aislamiento Termico y Acustico (1%)', mxn: 17005518 },
        { nombre: 'Puesta a Tierra y Pararrayos (1%)', mxn: 17005518 }
      ]
    },
    obraBlanca: {
      nombre: 'Acabados - Obra Blanca (25%)',
      total: { mxn: 425137950 },
      items: [
        { nombre: 'Enjarres y Pintura (5%)', mxn: 85027590 },
        { nombre: 'Recubrimiento de Piso (6%)', mxn: 102033108 },
        { nombre: 'Ventanas y Canceleria (4%)', mxn: 68022072 },
        { nombre: 'Puertas, Closets y Carpinteria (3%)', mxn: 51016554 },
        { nombre: 'Falsos Plafones (2%)', mxn: 34011036 },
        { nombre: 'Muebles de Bano y Cocina (2%)', mxn: 34011036 },
        { nombre: 'Iluminacion Interior y Exterior (2%)', mxn: 34011036 },
        { nombre: 'Barandales y Escaleras (1%)', mxn: 17005518 }
      ]
    },
    instalaciones: {
      nombre: 'Instalaciones y Equipamiento (17%)',
      total: { mxn: 289093806 },
      items: [
        { nombre: 'Aire Acondicionado / Calefaccion (5%)', mxn: 85027590 },
        { nombre: 'Calentadores Solares o de Paso (2%)', mxn: 34011036 },
        { nombre: 'Interfon, CCTV, Seguridad (3%)', mxn: 51016554 },
        { nombre: 'Sistema Contra Incendios (3%)', mxn: 51016554 },
        { nombre: 'Planta de Emergencia (2%)', mxn: 34011036 },
        { nombre: 'Control de Acceso Automaticos (1%)', mxn: 17005518 },
        { nombre: 'Automatizacion (1%)', mxn: 17005518 }
      ]
    },
    amenidadesYAmueblado: {
      nombre: 'Areas Comunes / Amenidades / Amueblado (10%)',
      total: { mxn: 209195180 },
      items: [
        { nombre: 'Lobby, Gimnasio, Salon Usos Multiples (2%)', mxn: 34011036 },
        { nombre: 'Alberca, Spa, Roof Garden (2%)', mxn: 34011036 },
        { nombre: 'Jardines y Areas Verdes (2%)', mxn: 34011036 },
        { nombre: 'Mobiliario Areas Comunes (2%)', mxn: 34011036 },
        { nombre: 'Amueblado Hotel FF&E + OS&E', mxn: 39140000 },
        { nombre: 'Iluminacion Exterior y Paisajismo (2%)', mxn: 34011036 }
      ]
    }
  },

  equipo: {
    directorGeneral: 'Mauricio Gerardo Trevino Saldana',
    directorAdjunto: 'Carlos Pickering',
    directorProyectos: 'Azyadeh Idalia Saldana Montemayor',
    projectManager: 'Vacante',
    gerenciaObra: 'Ceron',
    construccion: 'MID4 Arquitectura y Construccion',
    ventas: 'MasterBroker'
  },

  estructuraLegal: {
    fideicomiso: 'Fideicomiso 4217 INVEX',
    fiduciario: 'INVEX',
    fideicomitente: 'Desarrolladora M&C',
    administracion: '360 Desarrolladora Inmobiliaria'
  },

  amenidades: [
    'Alberca Privada', 'Alberca de Agua Salada', 'Alberca Infinity',
    'Carril de Nado Semi-Olimpico', 'Gimnasio', 'Zen Gym', 'SPA',
    'Pool Bar', 'Restaurante Formal', 'Restaurante Informal',
    'Wellness Restaurante', 'Kids Club', 'Playground',
    'Areas de Eventos', 'Biblioteca', 'Area de Asador',
    'Pet Park', 'Estancias', 'Jardines Central',
    'Andadores Internos', 'Co-Work', 'Autoservicio',
    'Cafeteria', 'Lavanderia', 'Farmacia'
  ],

  // Medidas detalladas del proyecto por nivel
  medidasProyecto: {
    plantaBaja: {
      areaComun: { residencial: { frente: 34, lado: 10, total: 340 }, hotel: { frente: 34, lado: 10, total: 340 }, total: 680 },
      estacionamiento: { frente: 68, lado: 45, total: 3060 },
      estacionamientoExterno: {
        seccion1: { frente: 20, lado: 21, total: 420 },
        seccion2: { frente: 43, lado: 21, total: 903 },
        seccion3: { frente: 11, lado: 10, total: 110 },
        seccion4: { frente: 10, lado: 10, total: 100 },
        seccion5: { frente: 10.09, lado: 51, total: 514.59 },
        total: 2047.59
      },
      areaComercial: {
        restaurante: { frente: 20, lado: 25, total: 500 },
        locales: { frente: 35, lado: 10, total: 350 },
        circulacion: 610,
        miniSuper: { frente: 22, lado: 10, total: 220 },
        total: 1680
      },
      total: 7467.59
    },
    segundoNivel: {
      estacionamiento: { frente: 68, lado: 45, total: 3060 },
      areaComercial: { locales: 850, circulacion: 610, total: 1460 },
      total: 4520
    },
    terceroCuartoNivel: {
      estacionamiento: { total: 6120 },
      areaComercialTercer: { locales: 850, circulacion: 610, total: 1460 },
      total: 7580
    },
    quintoNivel: {
      lobbyResidencial: { frente: 30, lado: 50, total: 1500 },
      lobbyHotelero: { frente: 30, lado: 50, total: 1500 },
      total: 3000
    },
    niveles6a15: {
      torreResidencial: { frente: 30, lado: 50, porPiso: 1500, total: 15000 },
      torreHotelera: { frente: 30, lado: 50, porPiso: 1500, total: 15000 },
      total: 30000
    },
    nivel16: {
      rooftopResidencial: { frente: 30, lado: 50, total: 1500 },
      rooftopHotelera: { frente: 30, lado: 50, total: 1500 },
      total: 3000
    },
    totalProyecto: 55567.59
  },

  supuestos: {
    precioM2Estimado: 35000,  // MXN/m2
    tipoCambio: 16.55,        // MXN por USD
    precioM2USD: 2114.80      // USD/m2
  }
};

// ============================================================
// ARCHITECTURAL PLAN VIEWER (CAD-like Canvas)
// ============================================================

class ArchitecturalViewer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.scale = 1;
    this.offsetX = 0;
    this.offsetY = 0;
    this.isDragging = false;
    this.lastX = 0;
    this.lastY = 0;
    this.gridEnabled = true;
    this.measureMode = false;
    this.measureStart = null;
    this.measurements = [];
    this.currentTool = 'pan'; // pan, measure, annotate
    this.annotations = [];
    this.layers = {
      grid: true,
      structure: true,
      dimensions: true,
      labels: true,
      amenities: true
    };

    this.initCanvas();
    this.setupEvents();
    this.drawFloorPlan();
  }

  initCanvas() {
    const container = this.canvas.parentElement;
    this.canvas.width = container.clientWidth;
    this.canvas.height = container.clientHeight || 600;
    this.centerX = this.canvas.width / 2;
    this.centerY = this.canvas.height / 2;
  }

  setupEvents() {
    // Mouse wheel zoom
    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
      const newScale = this.scale * zoomFactor;
      if (newScale >= 0.1 && newScale <= 10) {
        this.scale = newScale;
        this.draw();
      }
    });

    // Pan
    this.canvas.addEventListener('mousedown', (e) => {
      if (this.currentTool === 'measure') {
        const pos = this.screenToWorld(e.offsetX, e.offsetY);
        if (!this.measureStart) {
          this.measureStart = pos;
        } else {
          this.measurements.push({ start: this.measureStart, end: pos });
          this.measureStart = null;
          this.draw();
        }
        return;
      }
      this.isDragging = true;
      this.lastX = e.offsetX;
      this.lastY = e.offsetY;
      this.canvas.style.cursor = 'grabbing';
    });

    this.canvas.addEventListener('mousemove', (e) => {
      if (this.isDragging) {
        this.offsetX += e.offsetX - this.lastX;
        this.offsetY += e.offsetY - this.lastY;
        this.lastX = e.offsetX;
        this.lastY = e.offsetY;
        this.draw();
      }

      // Update coordinate display
      const pos = this.screenToWorld(e.offsetX, e.offsetY);
      const coordEl = document.getElementById('cad-coordinates');
      if (coordEl) {
        coordEl.textContent = `X: ${pos.x.toFixed(1)}m  Y: ${pos.y.toFixed(1)}m  Scale: ${(this.scale * 100).toFixed(0)}%`;
      }
    });

    this.canvas.addEventListener('mouseup', () => {
      this.isDragging = false;
      this.canvas.style.cursor = this.currentTool === 'measure' ? 'crosshair' : 'grab';
    });

    this.canvas.addEventListener('mouseleave', () => {
      this.isDragging = false;
      this.canvas.style.cursor = 'grab';
    });

    // Resize
    window.addEventListener('resize', () => {
      this.initCanvas();
      this.draw();
    });
  }

  screenToWorld(sx, sy) {
    return {
      x: (sx - this.centerX - this.offsetX) / (this.scale * 5),
      y: (sy - this.centerY - this.offsetY) / (this.scale * 5)
    };
  }

  worldToScreen(wx, wy) {
    return {
      x: wx * this.scale * 5 + this.centerX + this.offsetX,
      y: wy * this.scale * 5 + this.centerY + this.offsetY
    };
  }

  draw() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Background
    this.ctx.fillStyle = '#FAFAF7';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    this.ctx.save();
    this.ctx.translate(this.centerX + this.offsetX, this.centerY + this.offsetY);
    this.ctx.scale(this.scale, this.scale);

    if (this.layers.grid) this.drawGrid();
    if (this.layers.structure) this.drawFloorPlan();
    if (this.layers.dimensions) this.drawDimensions();
    if (this.layers.labels) this.drawLabels();
    if (this.layers.amenities) this.drawAmenities();
    this.drawMeasurements();

    this.ctx.restore();
    this.drawCompass();
  }

  drawGrid() {
    const gridSize = 5; // 5m grid
    const range = 200;
    this.ctx.strokeStyle = '#E8E5DD';
    this.ctx.lineWidth = 0.3;

    for (let i = -range; i <= range; i += gridSize) {
      // Vertical
      this.ctx.beginPath();
      this.ctx.moveTo(i * 5, -range * 5);
      this.ctx.lineTo(i * 5, range * 5);
      this.ctx.stroke();
      // Horizontal
      this.ctx.beginPath();
      this.ctx.moveTo(-range * 5, i * 5);
      this.ctx.lineTo(range * 5, i * 5);
      this.ctx.stroke();
    }

    // Major grid (25m)
    this.ctx.strokeStyle = '#D0CCC2';
    this.ctx.lineWidth = 0.6;
    for (let i = -range; i <= range; i += 25) {
      this.ctx.beginPath();
      this.ctx.moveTo(i * 5, -range * 5);
      this.ctx.lineTo(i * 5, range * 5);
      this.ctx.stroke();
      this.ctx.beginPath();
      this.ctx.moveTo(-range * 5, i * 5);
      this.ctx.lineTo(range * 5, i * 5);
      this.ctx.stroke();
    }

    // Origin axes
    this.ctx.strokeStyle = '#C0392B';
    this.ctx.lineWidth = 1;
    this.ctx.beginPath();
    this.ctx.moveTo(-range * 5, 0);
    this.ctx.lineTo(range * 5, 0);
    this.ctx.stroke();
    this.ctx.strokeStyle = '#2980B9';
    this.ctx.beginPath();
    this.ctx.moveTo(0, -range * 5);
    this.ctx.lineTo(0, range * 5);
    this.ctx.stroke();
  }

  drawFloorPlan() {
    const s = 5; // scale factor: 1m = 5px

    // ===== TERRAIN BOUNDARY (9,506.69 m2 bruto) =====
    // Actual: Frente 78.18m x Fondo 121.6m (rectangular lot on Av. Bonampak)
    const terrainW = 78;  // ~78.18m frente
    const terrainH = 122; // ~121.6m fondo
    const tx = -terrainW / 2 * s;
    const ty = -terrainH / 2 * s;

    // Terrain fill
    this.ctx.fillStyle = 'rgba(197, 224, 165, 0.15)';
    this.ctx.fillRect(tx, ty, terrainW * s, terrainH * s);

    // Terrain outline
    this.ctx.strokeStyle = '#2C3E50';
    this.ctx.lineWidth = 2;
    this.ctx.setLineDash([10, 5]);
    this.ctx.strokeRect(tx, ty, terrainW * s, terrainH * s);
    this.ctx.setLineDash([]);

    // Setbacks
    this.ctx.strokeStyle = '#E74C3C';
    this.ctx.lineWidth = 0.5;
    this.ctx.setLineDash([4, 4]);
    const setF = 10, setB = 5, setL = 5;
    this.ctx.strokeRect(
      tx + setL * s, ty + setF * s,
      (terrainW - setL * 2) * s, (terrainH - setF - setB) * s
    );
    this.ctx.setLineDash([]);

    // ===== BUILDING FOOTPRINTS =====

    // Commercial Area (3 levels, ground floor)
    // Centered along Av. Bonampak (south side)
    const commercialW = 70;
    const commercialH = 15;
    const cx = -commercialW / 2 * s;
    const cy = (terrainH / 2 - setB - commercialH) * s;

    this.ctx.fillStyle = 'rgba(52, 152, 219, 0.2)';
    this.ctx.fillRect(cx, cy - 15 * s, commercialW * s, commercialH * s);
    this.ctx.strokeStyle = '#2980B9';
    this.ctx.lineWidth = 1.5;
    this.ctx.strokeRect(cx, cy - 15 * s, commercialW * s, commercialH * s);

    // Tower North (Residential) - 76 units
    const towerW = 28;
    const towerH = 35;
    const tnx = -terrainW / 2 * s + setL * s + 5 * s;
    const tny = ty + setF * s + 5 * s;

    this.ctx.fillStyle = 'rgba(155, 89, 182, 0.2)';
    this.ctx.fillRect(tnx, tny, towerW * s, towerH * s);
    this.ctx.strokeStyle = '#8E44AD';
    this.ctx.lineWidth = 2;
    this.ctx.strokeRect(tnx, tny, towerW * s, towerH * s);

    // Internal grid for Tower North (floors)
    this.ctx.strokeStyle = '#8E44AD';
    this.ctx.lineWidth = 0.3;
    for (let i = 1; i < 4; i++) {
      this.ctx.beginPath();
      this.ctx.moveTo(tnx, tny + (towerH / 4) * i * s);
      this.ctx.lineTo(tnx + towerW * s, tny + (towerH / 4) * i * s);
      this.ctx.stroke();
    }
    for (let i = 1; i < 3; i++) {
      this.ctx.beginPath();
      this.ctx.moveTo(tnx + (towerW / 3) * i * s, tny);
      this.ctx.lineTo(tnx + (towerW / 3) * i * s, tny + towerH * s);
      this.ctx.stroke();
    }

    // Tower South (Condo-Hotel) - 76 units
    const tsx = terrainW / 2 * s - setL * s - 5 * s - towerW * s;
    const tsy = ty + setF * s + 5 * s;

    this.ctx.fillStyle = 'rgba(230, 126, 34, 0.2)';
    this.ctx.fillRect(tsx, tsy, towerW * s, towerH * s);
    this.ctx.strokeStyle = '#E67E22';
    this.ctx.lineWidth = 2;
    this.ctx.strokeRect(tsx, tsy, towerW * s, towerH * s);

    // Internal grid for Tower South
    this.ctx.strokeStyle = '#E67E22';
    this.ctx.lineWidth = 0.3;
    for (let i = 1; i < 4; i++) {
      this.ctx.beginPath();
      this.ctx.moveTo(tsx, tsy + (towerH / 4) * i * s);
      this.ctx.lineTo(tsx + towerW * s, tsy + (towerH / 4) * i * s);
      this.ctx.stroke();
    }
    for (let i = 1; i < 3; i++) {
      this.ctx.beginPath();
      this.ctx.moveTo(tsx + (towerW / 3) * i * s, tsy);
      this.ctx.lineTo(tsx + (towerW / 3) * i * s, tsy + towerH * s);
      this.ctx.stroke();
    }

    // ===== AMENITIES AREA (Central) =====
    const amenityX = -15 * s;
    const amenityY = tny + towerH * s + 5 * s;
    const amenityW = 30;
    const amenityH = 20;

    // Pool area
    this.ctx.fillStyle = 'rgba(52, 152, 219, 0.3)';
    this.roundRect(amenityX, amenityY, amenityW * s, amenityH * s, 10);
    this.ctx.fill();
    this.ctx.strokeStyle = '#3498DB';
    this.ctx.lineWidth = 1;
    this.roundRect(amenityX, amenityY, amenityW * s, amenityH * s, 10);
    this.ctx.stroke();

    // Semi-olympic lane
    this.ctx.fillStyle = 'rgba(41, 128, 185, 0.4)';
    this.ctx.fillRect(amenityX + 2 * s, amenityY + 2 * s, 26 * s, 4 * s);

    // Garden areas (green patches)
    const gardens = [
      { x: -40, y: 15, w: 12, h: 18 },
      { x: 28, y: 15, w: 12, h: 18 },
      { x: -15, y: -8, w: 30, h: 6 }
    ];
    gardens.forEach(g => {
      this.ctx.fillStyle = 'rgba(39, 174, 96, 0.2)';
      this.roundRect(g.x * s, g.y * s, g.w * s, g.h * s, 8);
      this.ctx.fill();
      this.ctx.strokeStyle = '#27AE60';
      this.ctx.lineWidth = 0.8;
      this.roundRect(g.x * s, g.y * s, g.w * s, g.h * s, 8);
      this.ctx.stroke();
    });

    // ===== PARKING STRUCTURE (Underground/Adjacent) =====
    const parkX = tx + 5 * s;
    const parkY = cy - 18 * s;
    this.ctx.fillStyle = 'rgba(149, 165, 166, 0.15)';
    this.ctx.fillRect(parkX, parkY, 80 * s, 3 * s);
    this.ctx.strokeStyle = '#95A5A6';
    this.ctx.lineWidth = 0.8;
    this.ctx.setLineDash([3, 3]);
    this.ctx.strokeRect(parkX, parkY, 80 * s, 3 * s);
    this.ctx.setLineDash([]);

    // ===== ACCESS ROAD (Av. Bonampak) =====
    const roadY = terrainH / 2 * s + 2 * s;
    this.ctx.fillStyle = 'rgba(127, 140, 141, 0.3)';
    this.ctx.fillRect(tx - 10 * s, roadY, (terrainW + 20) * s, 12 * s);
    this.ctx.strokeStyle = '#7F8C8D';
    this.ctx.lineWidth = 1;
    // Road center line
    this.ctx.setLineDash([8, 8]);
    this.ctx.strokeStyle = '#F1C40F';
    this.ctx.lineWidth = 1.5;
    this.ctx.beginPath();
    this.ctx.moveTo(tx - 10 * s, roadY + 6 * s);
    this.ctx.lineTo(tx + (terrainW + 10) * s, roadY + 6 * s);
    this.ctx.stroke();
    this.ctx.setLineDash([]);

    // Elevator shafts (small squares in each tower)
    this.ctx.fillStyle = 'rgba(44, 62, 80, 0.4)';
    // North tower elevators
    this.ctx.fillRect(tnx + 12 * s, tny + 15 * s, 4 * s, 4 * s);
    // South tower elevators
    this.ctx.fillRect(tsx + 12 * s, tsy + 15 * s, 4 * s, 4 * s);
  }

  drawLabels() {
    const s = 5;
    this.ctx.textAlign = 'center';

    // Project title
    this.ctx.font = 'bold 14px Inter';
    this.ctx.fillStyle = '#2C3E50';
    this.ctx.fillText('KiN TOWERS - PLANTA GENERAL', 0, -58 * s);
    this.ctx.font = '10px Inter';
    this.ctx.fillStyle = '#7F8C8D';
    this.ctx.fillText('Av. Bonampak, Cancun, Q. Roo | Terreno: 9,506.69 m2 (Bruto) | 7,267.99 m2 (Neto)', 0, -55 * s);

    // Tower labels
    this.ctx.font = 'bold 11px Inter';
    this.ctx.fillStyle = '#8E44AD';
    const tnx = -45 / 2 * s + 5 * s + 14 * s;
    this.ctx.fillText('TORRE RESIDENCIAL', tnx - 16 * s, -47 * s + 5 * s);
    this.ctx.font = '9px Inter';
    this.ctx.fillText('80 Deptos | 8/Nivel | Pisos 6-15', tnx - 16 * s, -44 * s + 5 * s);
    this.ctx.fillText('30m x 50m = 1,500 m2/piso', tnx - 16 * s, -42 * s + 5 * s);

    this.ctx.font = 'bold 11px Inter';
    this.ctx.fillStyle = '#E67E22';
    const tsx = 45 / 2 * s - 5 * s - 14 * s;
    this.ctx.fillText('TORRE HOTELERA', tsx + 14 * s, -47 * s + 5 * s);
    this.ctx.font = '9px Inter';
    this.ctx.fillText('80 Hab. | 8/Nivel | Pisos 6-15', tsx + 14 * s, -44 * s + 5 * s);
    this.ctx.fillText('30m x 50m = 1,500 m2/piso', tsx + 14 * s, -42 * s + 5 * s);

    // Commercial
    this.ctx.font = 'bold 10px Inter';
    this.ctx.fillStyle = '#2980B9';
    this.ctx.fillText('AREA COMERCIAL (3 Niveles)', 0, 30 * s);
    this.ctx.font = '8px Inter';
    this.ctx.fillText('4,600 m2 vendible | Restaurantes + Locales + Mini Super', 0, 32 * s);

    // Pool / Amenity
    this.ctx.font = 'bold 9px Inter';
    this.ctx.fillStyle = '#3498DB';
    this.ctx.fillText('AMENIDADES', 0, 22 * s);
    this.ctx.font = '8px Inter';
    this.ctx.fillText('Alberca Semi-Olimpica + Infinity', 0, 24 * s);

    // Gardens
    this.ctx.font = '8px Inter';
    this.ctx.fillStyle = '#27AE60';
    this.ctx.fillText('Jardin', -34 * s, 25 * s);
    this.ctx.fillText('Jardin', 34 * s, 25 * s);

    // Road
    this.ctx.font = 'bold 10px Inter';
    this.ctx.fillStyle = '#34495E';
    this.ctx.fillText('AV. BONAMPAK', 0, 62 * s);

    // Parking
    this.ctx.font = '8px Inter';
    this.ctx.fillStyle = '#95A5A6';
    this.ctx.fillText('ESTACIONAMIENTO | 12,240 m2 + 2,047.59 m2 Ext.', 0, 35 * s);

    // Elevator labels
    this.ctx.font = '7px Inter';
    this.ctx.fillStyle = '#2C3E50';
    this.ctx.fillText('ELV', -45 / 2 * s + 5 * s + 14 * s, -52.5 / 2 * s + 5 * s + 17 * 5 + 12);
    this.ctx.fillText('ELV', 45 / 2 * s - 5 * s - 14 * s, -52.5 / 2 * s + 5 * s + 17 * 5 + 12);

    // Setback labels
    this.ctx.font = '7px Inter';
    this.ctx.fillStyle = '#E74C3C';
    this.ctx.fillText('Retiro: 10m', 0, -52.5 * s + 10 * s + 4 * s);
  }

  drawDimensions() {
    const s = 5;
    const terrainW = 78;
    const terrainH = 122;
    const tx = -terrainW / 2 * s;
    const ty = -terrainH / 2 * s;

    this.ctx.strokeStyle = '#E74C3C';
    this.ctx.fillStyle = '#E74C3C';
    this.ctx.lineWidth = 0.8;
    this.ctx.font = '8px Inter';
    this.ctx.textAlign = 'center';

    // Top dimension (width)
    const dimY = ty - 15;
    this.drawDimensionLine(tx, dimY, tx + terrainW * s, dimY, `${terrainW}m`);

    // Left dimension (height)
    const dimX = tx - 15;
    this.ctx.save();
    this.ctx.translate(dimX, ty + terrainH * s / 2);
    this.ctx.rotate(-Math.PI / 2);
    this.ctx.fillText(`${terrainH}m`, 0, -5);
    this.ctx.restore();
    this.ctx.beginPath();
    this.ctx.moveTo(dimX, ty);
    this.ctx.lineTo(dimX, ty + terrainH * s);
    this.ctx.stroke();
  }

  drawDimensionLine(x1, y1, x2, y2, label) {
    this.ctx.beginPath();
    this.ctx.moveTo(x1, y1);
    this.ctx.lineTo(x2, y2);
    this.ctx.stroke();

    // End ticks
    this.ctx.beginPath();
    this.ctx.moveTo(x1, y1 - 5);
    this.ctx.lineTo(x1, y1 + 5);
    this.ctx.stroke();
    this.ctx.beginPath();
    this.ctx.moveTo(x2, y2 - 5);
    this.ctx.lineTo(x2, y2 + 5);
    this.ctx.stroke();

    // Label
    this.ctx.fillText(label, (x1 + x2) / 2, y1 - 8);
  }

  drawAmenities() {
    // Small icons for amenities drawn as symbols
    const s = 5;

    // Trees (green circles in garden areas)
    const treePositions = [
      [-36, 18], [-36, 24], [-36, 30], [-32, 20], [-32, 26],
      [32, 18], [32, 24], [32, 30], [36, 20], [36, 26],
      [-10, -5], [-5, -6], [0, -5], [5, -6], [10, -5]
    ];

    treePositions.forEach(([x, y]) => {
      this.ctx.fillStyle = 'rgba(39, 174, 96, 0.5)';
      this.ctx.beginPath();
      this.ctx.arc(x * s, y * s, 2 * s, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.strokeStyle = '#27AE60';
      this.ctx.lineWidth = 0.5;
      this.ctx.stroke();
    });
  }

  drawMeasurements() {
    this.ctx.strokeStyle = '#E74C3C';
    this.ctx.fillStyle = '#E74C3C';
    this.ctx.lineWidth = 2;
    this.ctx.font = 'bold 12px Inter';
    this.ctx.textAlign = 'center';

    this.measurements.forEach(m => {
      const sx = m.start.x * 5;
      const sy = m.start.y * 5;
      const ex = m.end.x * 5;
      const ey = m.end.y * 5;

      this.ctx.beginPath();
      this.ctx.moveTo(sx, sy);
      this.ctx.lineTo(ex, ey);
      this.ctx.stroke();

      // Distance in meters
      const dist = Math.sqrt(Math.pow(m.end.x - m.start.x, 2) + Math.pow(m.end.y - m.start.y, 2));
      this.ctx.fillText(`${dist.toFixed(1)}m`, (sx + ex) / 2, (sy + ey) / 2 - 10);
    });
  }

  drawCompass() {
    // North arrow
    const cx = this.canvas.width - 50;
    const cy = 50;
    const r = 20;

    this.ctx.save();
    this.ctx.fillStyle = '#2C3E50';
    this.ctx.strokeStyle = '#2C3E50';
    this.ctx.lineWidth = 2;

    // Circle
    this.ctx.beginPath();
    this.ctx.arc(cx, cy, r, 0, Math.PI * 2);
    this.ctx.stroke();

    // North arrow
    this.ctx.beginPath();
    this.ctx.moveTo(cx, cy - r + 4);
    this.ctx.lineTo(cx - 6, cy);
    this.ctx.lineTo(cx + 6, cy);
    this.ctx.closePath();
    this.ctx.fill();

    // N label
    this.ctx.font = 'bold 10px Inter';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('N', cx, cy - r - 5);

    this.ctx.restore();
  }

  roundRect(x, y, w, h, r) {
    this.ctx.beginPath();
    this.ctx.moveTo(x + r, y);
    this.ctx.lineTo(x + w - r, y);
    this.ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    this.ctx.lineTo(x + w, y + h - r);
    this.ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    this.ctx.lineTo(x + r, y + h);
    this.ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    this.ctx.lineTo(x, y + r);
    this.ctx.quadraticCurveTo(x, y, x + r, y);
    this.ctx.closePath();
  }

  setTool(tool) {
    this.currentTool = tool;
    this.measureStart = null;
    this.canvas.style.cursor = tool === 'measure' ? 'crosshair' : 'grab';

    // Update UI
    document.querySelectorAll('.cad-tool-btn').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector(`.cad-tool-btn[data-tool="${tool}"]`);
    if (btn) btn.classList.add('active');
  }

  toggleLayer(layer) {
    this.layers[layer] = !this.layers[layer];
    this.draw();
  }

  resetView() {
    this.scale = 1;
    this.offsetX = 0;
    this.offsetY = 0;
    this.draw();
  }

  zoomIn() {
    this.scale = Math.min(10, this.scale * 1.2);
    this.draw();
  }

  zoomOut() {
    this.scale = Math.max(0.1, this.scale * 0.8);
    this.draw();
  }

  clearMeasurements() {
    this.measurements = [];
    this.draw();
  }
}

// ============================================================
// UI RENDERING
// ============================================================

let cadViewer = null;
let currentRETab = 'overview';

function initRealEstate() {
  renderProjectOverview();
  // Initialize CAD viewer after DOM is ready
  setTimeout(() => {
    if (document.getElementById('cad-canvas')) {
      cadViewer = new ArchitecturalViewer('cad-canvas');
      cadViewer.draw();
    }
  }, 100);
}

function switchRETab(tabName) {
  currentRETab = tabName;
  document.querySelectorAll('.re-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.re-tab-content').forEach(c => c.classList.remove('active'));

  const tab = document.querySelector(`.re-tab[data-tab="${tabName}"]`);
  const content = document.getElementById(`re-${tabName}`);
  if (tab) tab.classList.add('active');
  if (content) content.classList.add('active');

  if (tabName === 'plans' && cadViewer) {
    cadViewer.initCanvas();
    cadViewer.draw();
  }
}

function renderProjectOverview() {
  const d = KIN_TOWERS_DATA;

  // Update stat values with correct Kin Towers Excel data
  const statEls = {
    're-cost-total': `$${(d.financiero.costoTotalProyectoAdquisicion.usd / 1000000).toFixed(1)}M USD`,
    're-units': d.unidades.total.toString(),
    're-area': `${(d.areas.totalM2Utilizados / 1000).toFixed(1)}K m2`,
    're-roi': `$${(d.financiero.costoTotalConstruccion.mxn / 1000000).toFixed(0)}M MXN`
  };

  Object.entries(statEls).forEach(([id, val]) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  });
}

function renderCostBreakdownChart() {
  const canvas = document.getElementById('cost-chart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  // Filter out sub-items (indented categories starting with spaces) for the main chart
  const allData = KIN_TOWERS_DATA.costosDesglose;
  const data = allData.filter(item => !item.categoria.startsWith('  '));
  const maxMxn = Math.max(...data.map(d => d.mxn));

  canvas.width = canvas.parentElement.clientWidth;
  canvas.height = Math.max(400, data.length * 22 + 30);

  const barH = 14;
  const gap = 4;
  const startX = 280;
  const maxW = canvas.width - startX - 120;

  ctx.font = '10px Inter';
  ctx.textBaseline = 'middle';

  data.forEach((item, i) => {
    const y = 10 + i * (barH + gap);
    const w = Math.max(2, (item.mxn / maxMxn) * maxW);

    // Label
    ctx.fillStyle = '#666';
    ctx.textAlign = 'right';
    ctx.fillText(item.categoria.substring(0, 40), startX - 10, y + barH / 2);

    // Bar
    const colors = [
      '#2C3E50', '#1A5276', '#3498DB', '#2980B9', '#1ABC9C', '#27AE60',
      '#8E44AD', '#E67E22', '#E74C3C', '#F39C12', '#16A085',
      '#D35400', '#C0392B', '#7F8C8D', '#95A5A6', '#34495E',
      '#2ECC71', '#9B59B6', '#1F618D', '#148F77', '#B7950B'
    ];
    ctx.fillStyle = item.mxn === 0 ? '#DDD' : colors[i % colors.length];
    ctx.fillRect(startX, y, w, barH);

    // Value (MXN millions)
    ctx.fillStyle = '#333';
    ctx.textAlign = 'left';
    if (item.mxn > 0) {
      ctx.fillText(`$${(item.mxn / 1000000).toFixed(1)}M MXN`, startX + w + 8, y + barH / 2);
    } else {
      ctx.fillText('$0', startX + w + 8, y + barH / 2);
    }
  });

  // Total at bottom
  const totalMxn = data.reduce((s, d) => s + d.mxn, 0);
  const totalY = 10 + data.length * (barH + gap) + 10;
  ctx.font = 'bold 11px Inter';
  ctx.fillStyle = '#2C3E50';
  ctx.textAlign = 'right';
  ctx.fillText('TOTAL PROYECTO (Adquisicion)', startX - 10, totalY);
  ctx.textAlign = 'left';
  ctx.fillText(`$${(KIN_TOWERS_DATA.financiero.costoTotalProyectoAdquisicion.mxn / 1000000).toFixed(1)}M MXN | $${(KIN_TOWERS_DATA.financiero.costoTotalProyectoAdquisicion.usd / 1000000).toFixed(1)}M USD`, startX + 8, totalY);
}

function formatMXN(num) {
  return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(num);
}

function formatUSD(num) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(num);
}

// Timeline / Gantt renderer
function renderTimeline() {
  const canvas = document.getElementById('timeline-chart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  canvas.width = canvas.parentElement.clientWidth;
  canvas.height = 320;

  const phases = [
    { name: 'Desarrollo Ejecutivo', start: 0, dur: 6, color: '#3498DB' },
    { name: 'Permisos y Licencias', start: 0, dur: 9, color: '#2980B9' },
    { name: 'Ventas Friends & Family', start: 9, dur: 3, color: '#27AE60' },
    { name: 'Lanzamiento Publico', start: 12, dur: 60, color: '#2ECC71' },
    { name: 'Cimentacion', start: 12, dur: 6, color: '#E67E22' },
    { name: 'Estructura', start: 18, dur: 24, color: '#E74C3C' },
    { name: 'Acabados', start: 42, dur: 24, color: '#9B59B6' },
    { name: 'Amenidades', start: 54, dur: 18, color: '#1ABC9C' },
    { name: 'Entregas', start: 72, dur: 6, color: '#F39C12' }
  ];

  const maxMonths = 78;
  const barH = 24;
  const gap = 6;
  const startX = 180;
  const maxW = canvas.width - startX - 30;
  const pxPerMonth = maxW / maxMonths;

  ctx.font = 'bold 10px Inter';
  ctx.fillStyle = '#999';
  ctx.textAlign = 'center';

  // Year markers
  for (let y = 2026; y <= 2033; y++) {
    const monthOffset = (y - 2026) * 12;
    const x = startX + monthOffset * pxPerMonth;
    ctx.fillText(y.toString(), x, 12);
    ctx.strokeStyle = '#E0E0E0';
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    ctx.moveTo(x, 18);
    ctx.lineTo(x, canvas.height);
    ctx.stroke();
  }

  ctx.textBaseline = 'middle';

  phases.forEach((phase, i) => {
    const y = 25 + i * (barH + gap);
    const x = startX + phase.start * pxPerMonth;
    const w = phase.dur * pxPerMonth;

    // Label
    ctx.font = '11px Inter';
    ctx.fillStyle = '#555';
    ctx.textAlign = 'right';
    ctx.fillText(phase.name, startX - 10, y + barH / 2);

    // Bar
    ctx.fillStyle = phase.color;
    ctx.beginPath();
    ctx.roundRect(x, y, w, barH, 4);
    ctx.fill();

    // Duration label on bar
    ctx.font = '9px Inter';
    ctx.fillStyle = '#fff';
    ctx.textAlign = 'center';
    if (w > 40) {
      ctx.fillText(`${phase.dur}m`, x + w / 2, y + barH / 2);
    }
  });
}

// Gallery management
let galleryIndex = 0;
const galleryImages = [
  { src: 'assets/realestate/slide1_img0.png', caption: 'KiN Towers - Vista Principal' },
  { src: 'assets/realestate/slide5_img5.png', caption: 'Justificacion del Proyecto' },
  { src: 'assets/realestate/slide22_img15.png', caption: 'Proyecto Conceptual - Albercas' },
  { src: 'assets/realestate/slide23_img22.png', caption: 'Areas Comunes y Jardines' },
  { src: 'assets/realestate/slide24_img23.png', caption: 'Gastronomia y Comercio' },
  { src: 'assets/realestate/slide25_img32.png', caption: 'SPA, Gym y Eventos' },
  { src: 'assets/realestate/slide21_img12.png', caption: 'Status del Proyecto' },
  { src: 'assets/realestate/slide4_img3.png', caption: 'Estructura de Inversion' },
  { src: 'assets/realestate/slide11_img10.png', caption: 'Plan de Trabajo' },
  { src: 'assets/realestate/slide30_img39.png', caption: 'Equipo Directivo' }
];

function nextGalleryImage() {
  galleryIndex = (galleryIndex + 1) % galleryImages.length;
  updateGallery();
}

function prevGalleryImage() {
  galleryIndex = (galleryIndex - 1 + galleryImages.length) % galleryImages.length;
  updateGallery();
}

function updateGallery() {
  const img = document.getElementById('gallery-image');
  const caption = document.getElementById('gallery-caption');
  const counter = document.getElementById('gallery-counter');
  if (img) {
    img.src = galleryImages[galleryIndex].src;
    img.alt = galleryImages[galleryIndex].caption;
  }
  if (caption) caption.textContent = galleryImages[galleryIndex].caption;
  if (counter) counter.textContent = `${galleryIndex + 1} / ${galleryImages.length}`;
}

// ============================================================
// SCENARIO SIMULATOR - What-If Analysis Engine
// ============================================================

const SCENARIO_BASE = {
  tc: 16.55,
  precioM2: 35000,
  contingencia: 5.12, // % of CTC used as contingency
  terreno: 213600000,
  fees: 5.23,  // % of total used for comisiones/fees
  units: 190,
  // Derived base values (computed once)
  ctcBase: 1700551800,
  totalProyectoBase: 3574235296.30,
  totalUSDBase: 215965878.93,
  costoM2Base: 73111.30,
  costoUnidadBase: 3574235296.30 / 190,
  ctcM2USDBase: 2101.81
};

function updateSimulator() {
  const tc = parseFloat(document.getElementById('sim-tc').value);
  const pm2 = parseFloat(document.getElementById('sim-pm2').value);
  const cont = parseFloat(document.getElementById('sim-cont').value);
  const terreno = parseFloat(document.getElementById('sim-terreno').value);
  const fees = parseFloat(document.getElementById('sim-fees').value);
  const units = parseInt(document.getElementById('sim-units').value);

  // Update displayed values
  document.getElementById('sim-tc-value').textContent = `$${tc.toFixed(2)}`;
  document.getElementById('sim-pm2-value').textContent = `$${pm2.toLocaleString('en-US')}`;
  document.getElementById('sim-cont-value').textContent = `${cont.toFixed(1)}%`;
  document.getElementById('sim-terreno-value').textContent = `$${(terreno / 1000000).toFixed(1)}M`;
  document.getElementById('sim-fees-value').textContent = `${fees.toFixed(1)}%`;
  document.getElementById('sim-units-value').textContent = units.toString();

  // === RECALCULATE ===
  // CTC scales linearly with precio/m2 change
  const pm2Ratio = pm2 / SCENARIO_BASE.precioM2;
  const newCTC = SCENARIO_BASE.ctcBase * pm2Ratio;

  // Contingency recalculation (base contingency was ~$183M on CTC of $1,700M => ~10.76% of CTC)
  // But user controls the general contingency % of the CTC
  const baseContingencia = 183055180; // original contingency
  const newContingencia = newCTC * (cont / 100);

  // Fees recalculation
  const baseFeesAmount = 187060698; // original fees
  const baseFeesPct = SCENARIO_BASE.fees;

  // Terreno diff
  const baseTerrenoAdq = 274137600; // terreno adquisicion includes extra costs over raw estimate
  const terrenoRatio = terreno / 213600000;
  const newTerrenoAdq = baseTerrenoAdq * terrenoRatio;

  // Total project = terreno + CTC + estudios + supervision + marketing + admin + legal + impuestos + contingencia + fees + preApertura + myCorp + extras
  // We recalculate the variable components:
  const fixedCosts = 297624720  // Estudios y Proyectos
    + 156145799.40   // Supervision
    + 5800000         // Gastos Legales Corp
    + 27095703.90     // Permisos
    + 105100000       // Marketing
    + 103900000       // Admin y Operacion
    + 16700000        // Gastos Legales Finales
    + 60013795        // Impuestos
    + 249100000       // Pre-Apertura Hotel
    + 168810000;      // M&C Corporativo

  // Construction total = CTC + extras (~$39M above CTC for supervision extras)
  const construccionTotal = newCTC + (1739691800 - SCENARIO_BASE.ctcBase); // keep the delta above CTC

  const newFeesAmount = (newCTC + fixedCosts + newTerrenoAdq) * (fees / 100);

  const newTotalMXN = newTerrenoAdq + construccionTotal + fixedCosts + newContingencia + newFeesAmount;
  const newTotalUSD = newTotalMXN / tc;
  const newCostoM2 = newTotalMXN / KIN_TOWERS_DATA.areas.totalM2Vendibles;
  const newCostoUnidad = newTotalMXN / units;
  const newCTCM2USD = (newCTC / KIN_TOWERS_DATA.areas.totalM2Vendibles) / tc;

  // Update result cards
  setSimResult('sim-res-ctc', `$${(newCTC / 1000000).toFixed(1)}M MXN`, 'sim-delta-ctc', newCTC, SCENARIO_BASE.ctcBase);
  setSimResult('sim-res-total', `$${(newTotalMXN / 1000000).toFixed(1)}M MXN`, 'sim-delta-total', newTotalMXN, SCENARIO_BASE.totalProyectoBase);
  setSimResult('sim-res-usd', `$${(newTotalUSD / 1000000).toFixed(1)}M USD`, 'sim-delta-usd', newTotalUSD, SCENARIO_BASE.totalUSDBase);
  setSimResult('sim-res-m2', `$${Math.round(newCostoM2).toLocaleString('en-US')} MXN`, 'sim-delta-m2', newCostoM2, SCENARIO_BASE.costoM2Base);
  setSimResult('sim-res-unit', `$${(newCostoUnidad / 1000000).toFixed(1)}M MXN`, 'sim-delta-unit', newCostoUnidad, SCENARIO_BASE.costoUnidadBase);
  setSimResult('sim-res-ctcusd', `$${Math.round(newCTCM2USD).toLocaleString('en-US')} USD`, 'sim-delta-ctcusd', newCTCM2USD, SCENARIO_BASE.ctcM2USDBase);

  // Impact bar (overall delta vs base total)
  const overallDelta = ((newTotalMXN - SCENARIO_BASE.totalProyectoBase) / SCENARIO_BASE.totalProyectoBase) * 100;
  const impactFill = document.getElementById('sim-impact-fill');
  const impactMarker = document.getElementById('sim-impact-marker');
  const impactPct = document.getElementById('sim-impact-pct');

  // Map delta to 0-100% (50% = no change, 0% = -50% decrease, 100% = +50% increase)
  const clampedDelta = Math.max(-50, Math.min(50, overallDelta));
  const fillPct = 50 + clampedDelta;

  impactFill.style.width = `${fillPct}%`;
  impactMarker.style.left = `${fillPct}%`;

  if (overallDelta > 0) {
    impactFill.style.background = 'linear-gradient(90deg, var(--accent-green), var(--accent-orange), var(--accent-red))';
    impactPct.textContent = `+${overallDelta.toFixed(1)}%`;
    impactPct.style.color = overallDelta > 10 ? '#E85656' : '#E8A856';
  } else if (overallDelta < 0) {
    impactFill.style.background = 'linear-gradient(90deg, #3498DB, var(--accent-green))';
    impactPct.textContent = `${overallDelta.toFixed(1)}%`;
    impactPct.style.color = '#27AE60';
  } else {
    impactFill.style.background = 'var(--accent-green)';
    impactPct.textContent = '0.0%';
    impactPct.style.color = 'var(--text-secondary)';
  }
}

function setSimResult(valueId, valueText, deltaId, newVal, baseVal) {
  const el = document.getElementById(valueId);
  const deltaEl = document.getElementById(deltaId);
  if (el) el.textContent = valueText;
  if (deltaEl) {
    const pctChange = ((newVal - baseVal) / baseVal) * 100;
    if (Math.abs(pctChange) < 0.05) {
      deltaEl.textContent = '+0.0%';
      deltaEl.className = 'sim-result-delta neutral';
    } else if (pctChange > 0) {
      deltaEl.textContent = `+${pctChange.toFixed(1)}%`;
      deltaEl.className = 'sim-result-delta up';
    } else {
      deltaEl.textContent = `${pctChange.toFixed(1)}%`;
      deltaEl.className = 'sim-result-delta down';
    }
  }
}

function resetSimulator() {
  document.getElementById('sim-tc').value = SCENARIO_BASE.tc;
  document.getElementById('sim-pm2').value = SCENARIO_BASE.precioM2;
  document.getElementById('sim-cont').value = SCENARIO_BASE.contingencia;
  document.getElementById('sim-terreno').value = SCENARIO_BASE.terreno;
  document.getElementById('sim-fees').value = SCENARIO_BASE.fees;
  document.getElementById('sim-units').value = SCENARIO_BASE.units;
  updateSimulator();
}

// ============================================================
// WORKFLOW AUTOMATION - Alerts & Notifications Engine
// ============================================================

const WORKFLOW_RULES = [
  {
    id: 'tc-alert',
    name: 'Alerta Tipo de Cambio',
    description: 'Notifica cuando el TC supera un umbral critico',
    condition: (data) => data.tc > 20,
    severity: 'high',
    message: (data) => `⚠️ TC critico: $${data.tc.toFixed(2)} MXN/USD — El costo en USD ha cambiado significativamente.`
  },
  {
    id: 'budget-overrun',
    name: 'Desborde Presupuestal',
    description: 'Alerta si el costo total supera el +10% del presupuesto base',
    condition: (data) => data.totalDelta > 10,
    severity: 'critical',
    message: (data) => `🚨 Costo total excede +${data.totalDelta.toFixed(1)}% sobre el presupuesto base ($${(data.total / 1e9).toFixed(2)}B MXN)`
  },
  {
    id: 'contingency-low',
    name: 'Contingencia Baja',
    description: 'Alerta si el % de contingencia es menor al 3%',
    condition: (data) => data.contingencia < 3,
    severity: 'warning',
    message: (data) => `⚠️ Contingencia baja: ${data.contingencia.toFixed(1)}% — Riesgo elevado ante imprevistos.`
  },
  {
    id: 'cost-per-unit-high',
    name: 'Costo por Unidad Alto',
    description: 'Alerta si el costo promedio por unidad supera $22M MXN',
    condition: (data) => data.costoUnidad > 22000000,
    severity: 'warning',
    message: (data) => `⚠️ Costo por unidad alto: $${(data.costoUnidad / 1e6).toFixed(1)}M MXN — Revisar viabilidad comercial.`
  },
  {
    id: 'milestone-reminder',
    name: 'Hito Proximo',
    description: 'Recordatorio de hitos del proyecto dentro de 90 dias',
    condition: () => {
      const now = new Date();
      const nextMilestone = new Date('2026-06-01'); // Inicio Desarrollo Ejecutivo
      const diff = (nextMilestone - now) / (1000 * 60 * 60 * 24);
      return diff > 0 && diff <= 90;
    },
    severity: 'info',
    message: () => {
      const now = new Date();
      const nextMilestone = new Date('2026-06-01');
      const days = Math.ceil((nextMilestone - now) / (1000 * 60 * 60 * 24));
      return `📅 Hito proximo: "Inicio Desarrollo Ejecutivo" en ${days} dias (Jun 2026)`;
    }
  }
];

let activeAlerts = [];
let alertsShown = new Set();

function evaluateWorkflowRules(simData) {
  activeAlerts = [];
  WORKFLOW_RULES.forEach(rule => {
    if (rule.condition(simData)) {
      activeAlerts.push({
        id: rule.id,
        severity: rule.severity,
        message: rule.message(simData),
        name: rule.name,
        timestamp: new Date()
      });
    }
  });
  renderAlerts();
}

function renderAlerts() {
  let alertsContainer = document.getElementById('sim-alerts');
  if (!alertsContainer) {
    // Create alerts container dynamically after the simulator
    const simCard = document.querySelector('.re-simulator-card');
    if (!simCard) return;
    alertsContainer = document.createElement('div');
    alertsContainer.id = 'sim-alerts';
    alertsContainer.className = 'sim-alerts-container';
    simCard.appendChild(alertsContainer);
  }

  if (activeAlerts.length === 0) {
    alertsContainer.innerHTML = '<div class="sim-alert sim-alert-ok">✅ Todos los parametros dentro de rango normal.</div>';
    return;
  }

  alertsContainer.innerHTML = activeAlerts.map(alert => {
    const severityClass = `sim-alert-${alert.severity}`;
    return `<div class="sim-alert ${severityClass}">
      <span class="sim-alert-badge">${alert.severity.toUpperCase()}</span>
      <span>${alert.message}</span>
    </div>`;
  }).join('');
}

// Hook alerts into the simulator update
const _originalUpdateSimulator = updateSimulator;
updateSimulator = function() {
  _originalUpdateSimulator();

  // Gather sim data for workflow rules
  const tc = parseFloat(document.getElementById('sim-tc').value);
  const cont = parseFloat(document.getElementById('sim-cont').value);
  const totalEl = document.getElementById('sim-res-total');
  const totalMatch = totalEl ? totalEl.textContent.match(/([\d,.]+)/) : null;
  const totalVal = totalMatch ? parseFloat(totalMatch[1].replace(/,/g, '')) * 1000000 : SCENARIO_BASE.totalProyectoBase;
  const units = parseInt(document.getElementById('sim-units').value);

  evaluateWorkflowRules({
    tc,
    contingencia: cont,
    total: totalVal,
    totalDelta: ((totalVal - SCENARIO_BASE.totalProyectoBase) / SCENARIO_BASE.totalProyectoBase) * 100,
    costoUnidad: totalVal / units
  });
};

// Initialize when DOM ready
document.addEventListener('DOMContentLoaded', () => {
  // Will be called when user navigates to realestate view
});
