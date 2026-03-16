# 📦 INSTALACIÓN: get_data() Tool

## Archivos a agregar

### 1. Crear carpeta `data_providers` en tools:
```
ARIA_FULL_CODE/Aria/src/aria/tools/data_providers/
```

### 2. Copiar estos archivos en `data_providers/`:
- `__init__.py`
- `base.py`
- `yahoo.py`
- `alpaca.py`

### 3. Copiar en `tools/`:
- `get_data.py`

## Estructura final:
```
ARIA_FULL_CODE/Aria/src/aria/tools/
├─ __init__.py (ya existe)
├─ base.py (ya existe)
├─ get_data.py (NUEVO)
└─ data_providers/ (NUEVA CARPETA)
   ├─ __init__.py
   ├─ base.py
   ├─ yahoo.py
   └─ alpaca.py
```

## Dependencias a instalar:

### Obligatorias:
```bash
pip install yfinance
```

### Opcionales (para real-time):
```bash
pip install alpaca-py
```

## Configuración de Alpaca (opcional pero recomendado):

### 1. Crear cuenta gratis:
https://alpaca.markets/

### 2. Obtener API keys:
- Ve a: Dashboard → API Keys → Generate New Key
- Guarda: API Key + Secret Key

### 3. Agregar a `.env`:
```env
# Alpaca API (for real-time data)
ALPACA_API_KEY=tu-api-key-aqui
ALPACA_SECRET_KEY=tu-secret-key-aqui
```

## Testing:

### Test básico (sin Alpaca):
```bash
cd ARIA_FULL_CODE/Aria
python src/aria/tools/get_data.py
```

Deberías ver:
```
⚠️ Alpaca not available: ...
   Using Yahoo Finance only (15min delay)
🧪 Testing GetDataTool...
TEST 1: Historical data
✅ Got X rows
...
✅ GetDataTool working!
```

### Test completo (con Alpaca):
Después de configurar Alpaca keys:
```bash
python src/aria/tools/get_data.py
```

Deberías ver:
```
✅ Alpaca provider initialized (real-time data available)
...
✅ GetDataTool working!
```

## Troubleshooting:

### Error: "yfinance not found"
```bash
pip install yfinance
```

### Error: "alpaca not found"
```bash
pip install alpaca-py
```

### Error: "ALPACA_API_KEY not found"
- Es normal si no configuraste Alpaca
- El tool funciona solo con Yahoo (15min delay)
- Para real-time, configura Alpaca keys en `.env`

## Próximo paso:
Una vez instalado y probado, integraremos este tool con ARIA para que pueda usarlo en conversaciones.
