# Omni-Scraper 🌐

> **Modular, anti-detection stealth scraping harness** with persistent browser sessions, external CDP orchestration, organic human interaction simulation, and deduplicated SQLite storage.

---

## 🎯 ¿Qué es Omni-Scraper?

La mayoría de los scrapers web fallan rápidamente por tres razones:
1. **Detección de bots**: Inyecciones de JS torpes en el prototipo (`navigator.webdriver`) que los sistemas anti-bot (Cloudflare, Datadome, Akamai) detectan al instante.
2. **Pérdida de sesión y 2FA**: Crear navegadores efímeros que no guardan cookies ni perfiles reales.
3. **Duplicación de datos y complejidad**: Guardar archivos sueltos sin deduplicación atómica ni control de retención.

**Omni-Scraper** desacopla la infraestructura pesada de navegación y persistencia en un motor universal (`Ports & Adapters`), permitiendo conectar cualquier adaptador de plataforma (LinkedIn, Reddit, foros, ecommerce, etc.) con cero fricción.

---

## 🚀 Pilares de la Arquitectura

1. **Sesión Persistente y Perfil Real**: Navega usando tu perfil real de Brave, Chrome o Edge con cookies y credenciales guardadas permanentemente.
2. **Stealth Nativo (Sin Parches Delatores)**: Supresión limpia de automatización a nivel de Chromium (`--disable-blink-features=AutomationControlled`), sin alterar prototipos de JS que revelen el scraping.
3. **Soporte CDP Remoto**: Conexión directa a navegadores remotos o contenedores Docker (como [Fortress](https://github.com/tiliondev/fortress)) con el flag `--cdp-url`.
4. **Simulación Humana Orgánica**: Scroll con jitter aleatorio y micro-pausas gaussianas para replicar el comportamiento de un usuario real.
5. **Almacenamiento y Deduplicación Concurrente**: Base de datos SQLite embebida en modo WAL (`PRAGMA journal_mode=WAL`), clave única compuesta `(platform, item_id)` y comando de purga con `VACUUM`.
6. **Diagnóstico Pre-Vuelo (`doctor`)**: Inspección rápida de binarios, endpoints CDP y permisos de almacenamiento antes de ejecutar cualquier pipeline.

---

## 📦 Instalación

```powershell
# 1. Navegar al repositorio
cd D:\DocumentosDiscoD\omni-scraper

# 2. Crear entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Instalar en modo editable con dependencias
pip install -e .
playwright install chromium
```

---

## 🛠️ Uso del CLI

### 1. Diagnóstico Pre-Vuelo
Verificá que los binarios del navegador, permisos y base de datos estén listos:
```powershell
omni-scraper doctor
```

### 2. Conexión a Navegador Remoto por CDP (Docker o Externo)
```powershell
omni-scraper --cdp-url http://localhost:9222 doctor
```

### 3. Navegación en la Nube con TinyFish (Cloud Stealth CDP)
```powershell
$env:TINYFISH_API_KEY="tu_api_key"
omni-scraper --provider tinyfish scrape --platform reddit --target python
```

### 4. Extracción Rápida sin Navegador (TinyFish Fetch API)
```powershell
omni-scraper fetch https://news.ycombinator.com/ --format markdown
```

### 5. Inspeccionar Estadísticas de Almacenamiento
```powershell
omni-scraper db stats
```

### 6. Purgar Datos Antiguos (Retención)
```powershell
# Purgar ítems de más de 30 días y compactar espacio en disco
omni-scraper db purge --days 30 --force
```

---

## 🔌 Cómo Crear un Adaptador de Plataforma

Para scrapear un nuevo sitio web, solo tenés que heredar de `BaseScraper`:

```python
from omni_scraper.core import BaseScraper, ScrapedItem, ScraperRegistry

class RedditScraper(BaseScraper):
    platform_name = "reddit"

    def navigate(self, page, subreddit: str) -> None:
        page.goto(f"https://www.reddit.com/r/{subreddit}/hot/")

    def extract(self, page, limit: int = 20):
        items = []
        # Tu lógica de extracción con selectores DOM o intercepción
        return items

# Registrar el scraper
ScraperRegistry.register("reddit", RedditScraper)
```

---

## 🧪 Pruebas Unitarias (Strict TDD)

Ejecutá la suite de pruebas unitarias:
```powershell
python -m unittest discover tests
```

---

## 📄 Licencia
Distribuido bajo la Licencia MIT.
