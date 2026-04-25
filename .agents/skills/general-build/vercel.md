---
name: vercel-deploy
description: |
  Deploy Python applications on Vercel with the correct build settings and serverless configuration. Covers Vercel project type, environment variables, `vercel.json`, and the common pitfalls for FastAPI/ASGI apps.
  
  Use when: configuring Vercel deployment for Python backends, migrating from local development to Vercel, or troubleshooting Vercel build/runtime failures.
user-invocable: true
---

# Vercel Deploy Skill

Guía para desplegar aplicaciones Python en Vercel y evitar errores comunes de build, ruta o dependencias.

## Principios clave

- Vercel usa `vercel.json` para configurar builds, funciones y rutas.
- Para Python, Vercel despliega funciones serverless en `api/` o mediante un `vercel.json` que apunta a un handler ASGI.
- El comando de build debe instalar dependencias y generar los archivos necesarios.
- Las variables de entorno se configuran en el dashboard de Vercel o en `vercel env`.

## Configuración recomendada

### 1. `vercel.json` para FastAPI/ASGI

```json
{
  "version": 3,
  "builds": [
    {
      "src": "src/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/src/main.py"
    }
  ]
}
```

- `src/main.py` debe exponer el objeto `app` de FastAPI o Starlette.
- Si usas `src/app.py`, ajusta `src` en `builds` y `dest`.

### 2. `requirements.txt`

Asegúrate de listar todas las dependencias necesarias:

```
fastapi==0.128.0
uvicorn[standard]==0.22.0
sqlalchemy[asyncio]==2.0.30
pydantic==2.11.7
python-multipart==0.0.6
```

- Para entornos ASGI en Vercel, `uvicorn` no es estrictamente necesario en producción porque `@vercel/python` gestiona el app server.
- Incluye `python-dotenv` solo si lo usas en local, no en producción.

### 3. `pyproject.toml` / `requirements.txt`

Si tu proyecto usa `pyproject.toml`, añade un `requirements.txt` simple para Vercel o usa `pip install .` en el build.

### 4. Build command

Configura en Vercel:

- Framework Preset: `Python` o `None`
- Build Command: `pip install -r requirements.txt`
- Output Directory: `.`

Si necesitas un paso extra de generación:

```bash
pip install -r requirements.txt
python -m compileall src
```

### 5. Entradas de entorno

Configura variables de entorno en Vercel:

- `DATABASE_URL`
- `SECRET_KEY`
- `SENTRY_DSN`
- `API_KEY`

No guardes secretos en el repo.

## Ajustes para aplicaciones FastAPI

### Ejemplo mínimo `src/main.py`

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello Vercel"}
```

### Uso de ASGI

Vercel detecta que `src/main.py` exporta `app` y lo despliega como una función Python serverless.

## Depuración de errores comunes

### Error de build: `ModuleNotFoundError`

- Confirma que `requirements.txt` contenga todos los paquetes importados.
- Si usas un paquete local, no lo dejes fuera del `requirements.txt`.
- `@vercel/python` instala paquetes en un entorno aislado y no usa el `venv/` local.

### Error de runtime: `AttributeError: module 'src' has no attribute 'app'`

- Verifica que `src/main.py` define `app` en el nivel superior.
- Si tu app está en `src/app.py`, actualiza `vercel.json` a `dest": "/src/app.py"`.

### Error de ruta 404

- Asegúrate de usar `routes` en `vercel.json` para redirigir `/(.*)` a tu handler ASGI.
- Si tu app está en una subcarpeta, actualiza la ruta de destino.

## Recomendaciones finales

- Usa `vercel env pull` para sincronizar variables locales con el entorno de desarrollo.
- Prueba localmente con `vercel dev`.
- Mantén `vercel.json` simple y explícito.
- Si tu app es una API, no uses frontend estático a menos que también tengas páginas estáticas.
