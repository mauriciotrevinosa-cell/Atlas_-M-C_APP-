# 📦 FASE 1 — DATA INGESTION: Paquete de Entrega

**Generado por:** Claude (Arquitecto/Constructor)  
**Para:** Antigravity (Organizador)  
**Fecha:** 2026-02-05  
**Versión:** 1.0

---

## 🎯 OBJETIVO DE ESTA ENTREGA

Completar FASE 1 (Data Ingestion) del proyecto Atlas. Esta fase es la base de todo — sin datos, nada funciona. Al terminar, Atlas podrá:

1. Descargar datos históricos de múltiples fuentes (Yahoo, Polygon, CCXT crypto)
2. Validar calidad de datos (NaNs, gaps, anomalías)
3. Normalizar a formato estándar OHLCV
4. Cachear en disco para no re-descargar
5. Proveer interfaz unificada que el resto del sistema consume

---

## 📂 ESTRUCTURA DE ARCHIVOS

Todos los archivos van dentro de `python/src/atlas/data_layer/`. Aquí está el mapa completo de lo que YA EXISTE vs lo que es NUEVO:

```
python/src/atlas/
├── data_layer/
│   ├── __init__.py                          ← REEMPLAZAR (nuevo con exports)
│   ├── manager.py                           ← 🆕 NUEVO (coordinador central)
│   ├── normalize.py                         ← REEMPLAZAR (versión mejorada)
│   ├── cache_store.py                       ← REEMPLAZAR (versión mejorada)
│   │
│   ├── sources/
│   │   ├── __init__.py                      ← REEMPLAZAR (nuevo con exports)
│   │   │
│   │   ├── traditional/
│   │   │   ├── __init__.py                  ← 🆕 NUEVO
│   │   │   ├── yahoo_provider.py            ← 🆕 NUEVO (reemplaza yahoo.py viejo)
│   │   │   └── polygon_provider.py          ← 🆕 NUEVO
│   │   │
│   │   └── derivatives/
│   │       ├── __init__.py                  ← REEMPLAZAR (nuevo con exports)
│   │       └── ccxt_provider.py             ← 🆕 NUEVO (crypto exchanges)
│   │
│   └── quality/
│       ├── __init__.py                      ← REEMPLAZAR (nuevo con exports)
│       └── validator.py                     ← 🆕 NUEVO
│
├── interfaces/
│   └── market_data.py                       ← SIN CAMBIOS (ya está bien)
│
└── tests/
    └── test_data_layer.py                   ← 🆕 NUEVO
```

---

## 📋 INSTRUCCIONES PASO A PASO PARA ANTIGRAVITY

### PASO 1: Backup
Antes de tocar nada, haz backup de los archivos que vamos a reemplazar:
```bash
cd python/src/atlas/
cp data_layer/__init__.py data_layer/__init__.py.bak
cp data_layer/normalize.py data_layer/normalize.py.bak
cp data_layer/cache_store.py data_layer/cache_store.py.bak
```

### PASO 2: Crear carpetas nuevas
```bash
mkdir -p data_layer/sources/traditional
```
(Las carpetas `data_layer/sources/derivatives/` y `data_layer/quality/` ya existen)

### PASO 3: Colocar archivos NUEVOS
Copia cada archivo `.py` de este paquete a su ubicación correspondiente según la estructura de arriba.

**Orden de colocación:**
1. `data_layer/sources/traditional/__init__.py`
2. `data_layer/sources/traditional/yahoo_provider.py`
3. `data_layer/sources/traditional/polygon_provider.py`
4. `data_layer/sources/derivatives/__init__.py` (reemplazar el vacío)
5. `data_layer/sources/derivatives/ccxt_provider.py`
6. `data_layer/sources/__init__.py` (reemplazar el vacío)
7. `data_layer/quality/__init__.py` (reemplazar el vacío)
8. `data_layer/quality/validator.py`
9. `data_layer/normalize.py` (reemplazar)
10. `data_layer/cache_store.py` (reemplazar)
11. `data_layer/manager.py` (nuevo)
12. `data_layer/__init__.py` (reemplazar)

### PASO 4: Colocar test
```bash
mkdir -p tests/
cp test_data_layer.py tests/test_data_layer.py
```
(O en la raíz del proyecto, lo que sea más conveniente)

### PASO 5: Actualizar requirements.txt
Agregar estas líneas si no existen:
```
yfinance>=0.2.30
pandas>=2.0.0
numpy>=1.24.0
ccxt>=4.0.0
```

### PASO 6: Verificar
```bash
cd python/src/atlas
python -c "from data_layer import DataManager; print('✅ FASE 1 imports OK')"
```

---

## 🔗 DEPENDENCIAS ENTRE ARCHIVOS

```
interfaces/market_data.py (MarketDataProvider - ABC)
        ↑ hereda
        |
   ┌────┴────────────────────┐
   │                         │
yahoo_provider.py    polygon_provider.py    ccxt_provider.py
   │                         │                      │
   └────────┬────────────────┘──────────────────────┘
            ↓
      manager.py (DataManager - orquesta todo)
            │
            ├── usa → normalize.py (limpia datos)
            ├── usa → cache_store.py (guarda/lee cache)
            └── usa → quality/validator.py (valida calidad)
            
      __init__.py (exporta DataManager para uso externo)
```

**Regla clave:** `DataManager` es el ÚNICO punto de entrada. El resto del sistema NUNCA importa providers directamente — siempre pasa por `DataManager`.

---

## 📝 QUÉ HACE CADA ARCHIVO

| Archivo | Responsabilidad | Líneas aprox |
|---------|----------------|-------------|
| `manager.py` | Coordinador central. Recibe pedidos, elige provider, valida, normaliza, cachea | ~200 |
| `yahoo_provider.py` | Descarga de Yahoo Finance (OHLCV, quotes) | ~150 |
| `polygon_provider.py` | Descarga de Polygon.io (preparado, necesita API key) | ~130 |
| `ccxt_provider.py` | Descarga de exchanges crypto via CCXT (Binance, Bybit, etc.) | ~160 |
| `normalize.py` | Estandariza columnas, limpia NaNs, alinea timeframes, calcula retornos | ~130 |
| `cache_store.py` | Cache en Parquet con TTL, invalidación, stats | ~140 |
| `validator.py` | Valida calidad: gaps, spikes, volumen cero, NaN ratio | ~150 |
| `test_data_layer.py` | Tests unitarios para todo FASE 1 | ~180 |

---

## ⚠️ NOTAS IMPORTANTES

1. **NO tocar** `interfaces/market_data.py` — ya está bien, los providers heredan de ahí
2. **NO tocar** `assistants/aria/tools/data_providers/` — eso es la capa de ARIA, separada. Eventualmente ARIA usará `DataManager` en vez de sus providers directos, pero eso es para después
3. **Polygon requiere API key** — El provider está listo pero no funcionará sin key en `.env`. Eso está bien, es diseño intencional (fallback a Yahoo)
4. **CCXT requiere `pip install ccxt`** — Para crypto. Si no se instala, el sistema funciona sin él
5. **El cache usa Parquet** — Más rápido y compacto que CSV. Pandas ya lo soporta nativamente

---

## 🧪 CÓMO TESTEAR

```bash
# Test rápido (solo imports)
python -c "from data_layer import DataManager; print('OK')"

# Test completo (requiere internet para Yahoo)
pytest tests/test_data_layer.py -v

# Test individual
pytest tests/test_data_layer.py::TestDataManager::test_get_historical_yahoo -v
```

---

## 🔄 IMPACTO EN OTROS MÓDULOS

**Quién consumirá DataManager después:**
- `core_intelligence/signal_engine.py` → Para obtener datos de análisis
- `assistants/aria/tools/get_data.py` → ARIA usará DataManager (migración futura)
- `backtesting/runner.py` → Para datos de backtest
- `indicators/` → Para calcular indicadores sobre datos limpios

**Por ahora:** DataManager queda standalone, listo para ser consumido.

---

## ✅ CRITERIOS DE COMPLETITUD

FASE 1 se considera COMPLETA cuando:

- [ ] Todos los archivos están en su ubicación correcta
- [ ] `from data_layer import DataManager` funciona sin error
- [ ] `DataManager().get_historical("AAPL", "2024-01-01", "2024-12-31")` retorna DataFrame
- [ ] Cache funciona (segunda llamada es instantánea)
- [ ] Validator detecta datos con problemas
- [ ] Tests pasan: `pytest tests/test_data_layer.py`

---

**Generado:** 2026-02-05 por Claude (Arquitecto)  
**Próxima fase:** FASE 2 — Market State Detection
