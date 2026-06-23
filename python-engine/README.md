# Motor Algoritmico Local

Este script vive en tu PC. No se sube a InfinityFree.

## Uso

```powershell
cd python-engine
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edita `.env` con tu dominio y el mismo token de `infinityfree/api/config.php`.

```powershell
python planificar.py
```

El flujo es:

1. Descarga `exportar_csv.php`.
2. Calcula sobrecarga, descarga o rotacion tactica.
3. Envia los pesos nuevos a `actualizar_plan.php`.
