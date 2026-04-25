# ZenParking API

Sistema de gestión de parqueadero REST API construido con FastAPI, siguiendo las mejores prácticas de desarrollo.

## Características

### Control de Acceso
- Registro de ingreso/salida de vehículos con ticket digital
- Validación de placas contra blacklist
- Cálculo automático de tarifa por tiempo de permanencia
- Bloqueo de salida por multas pendientes

### Gestión de Espacios
- CRUD de celdas de parqueo por tipo (carro, moto, bicicleta, discapacitados)
- Asignación automática de celdas disponibles
- Estado en tiempo real: Libre, Ocupado, Reservado, Mantenimiento
- Mapa de distribución del parqueadero

### Usuarios y Roles (RBAC)
- **Administrador**: Acceso total al sistema
- **Operador/Guardia**: Registro de ingresos/salidas, gestión de vehículos
- **Auditor**: Reportes y visualización de datos

### Tarifas y Multas
- Configuración de tarifas por tipo de vehículo
- Sistema de multas por mal parqueo, invasión, sobretiempo
- Generación de reportes PDF/CSV

### Reportes y Auditoría
- Reporte diario de movimientos
- Bitácora de auditoría (logs)
- Resumen de ingresos

## Tecnologías

- **Framework**: FastAPI (async/await)
- **Base de datos**: MySQL + SQLAlchemy
- **Auth**: JWT + Argon2/BCrypt
- **API Docs**: Swagger/ReDoc
- **Deployment**: Vercel compatible

## Requisitos

- Python 3.11+
- MySQL 8.0+

## Instalación

### 1. Clonar y crear entorno virtual

```bash
git clone <repo-url>
cd bk-zenparking
python3 -m venv venv
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Crear archivo `.env`:

```env
APP_NAME=ZenParking API
DEBUG=true
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_USER=root
DATABASE_PASSWORD=
DATABASE_NAME=zenparking_db
SECRET_KEY=your-secret-key-change-in-production
```

### 4. Crear base de datos

```sql
CREATE DATABASE zenparking_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Ejecutar migraciones

```bash
alembic upgrade head
```

### 6. Poblar datos iniciales (seed)

```bash
python alembic/seed.py
```

### 7. Iniciar servidor

```bash
uvicorn app.main:app --reload
```

La API estará disponible en `http://localhost:8000`

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Credenciales por defecto

| Rol | Username | Password |
|----|----------|-----------|
| Admin | admin | Admin123! |
| Operator | guardia1 | Guardia123! |
| Auditor | auditor | Auditor123! |

## Deployment en Vercel

### Configuración

El proyecto ya incluye `vercel.json` para deployment serverless.

### Variables de entorno en Vercel

Agregar en Vercel Project Settings:

- `DATABASE_URL`: MySQL connection string
- `SECRET_KEY`: Generate with `python -c "from app.core.auth import get_password_hash; print(get_password_hash('your-secret'))"`

### Deployment

```bash
npm i -g vercel
vercel deploy --prod
```

## Estructura del Proyecto

```
bk-zenparking/
├── app/
│   ├── core/           # Configuración y autenticación
│   │   ├── auth.py
│   │   └── config.py
│   ├── db/             # Conexión a base de datos
│   │   └── database.py
│   ├── models/         # Modelos SQLAlchemy
│   │   └── models.py
│   ├── routers/       # Endpoints de la API
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── vehicles.py
│   │   ├── sessions.py
│   │   └── ...
│   ├── schemas/       # Schemas Pydantic
│   │   └── schemas.py
│   └── main.py         # App FastAPI
├── alembic/           # Migraciones
├── requirements.txt
└── vercel.json
```

## API Endpoints

### Autenticación
- `POST /api/v1/auth/login` - Iniciar sesión
- `POST /api/v1/auth/register` - Registrar usuario (admin)
- `POST /api/v1/auth/refresh` - Refrescar token
- `POST /api/v1/auth/logout` - Cerrar sesión

### Usuarios
- `GET /api/v1/users` - Listar usuarios (admin)
- `GET /api/v1/users/me` - Usuario actual
- `POST /api/v1/users` - Crear usuario (admin)
- `PATCH /api/v1/users/{id}` - Actualizar usuario (admin)

### Vehículos
- `GET /api/v1/vehicles` - Listar vehículos
- `GET /api/v1/vehicles/plate/{plate}` - Buscar por placa
- `POST /api/v1/vehicles` - Registrar vehículo
- `GET /api/v1/vehicles/blacklist/check/{plate}` - Verificar blacklist

### Sesiones de Parqueo
- `POST /api/v1/sessions/entry` - Ingreso de vehículo
- `PATCH /api/v1/sessions/{id}/exit` - Salida de vehículo
- `GET /api/v1/sessions/active` - Sesiones activas
- `GET /api/v1/sessions/statistics` - Dashboard

### Celdas de Parqueo
- `GET /api/v1/spots` - Listar celdas
- `GET /api/v1/spots/available` - Celdas disponibles
- `POST /api/v1/spots` - Crear celda (admin)
- `POST /api/v1/spots/{id}/maintenance` - Setear mantenimiento

### Tarifas
- `GET /api/v1/rates` - Listar tarifas
- `POST /api/v1/rates` - Crear tarifa (admin)

### Multas
- `GET /api/v1/fines` - Listar multas
- `POST /api/v1/fines` - Registrar multa
- `PATCH /api/v1/fines/{id}/pay` - Pagar multa

### Blacklist
- `GET /api/v1/blacklist` - Ver blacklist
- `POST /api/v1/blacklist` - Agregar a blacklist
- `DELETE /api/v1/blacklist/{id}` - Remover de blacklist

### Reportes
- `GET /api/v1/reports/daily-movements` - Movimientos diarios
- `GET /api/v1/reports/daily-movements-csv` - Exportar CSV
- `GET /api/v1/reports/audit-logs` - Logs de auditoría
- `GET /api/v1/reports/revenue-summary` - Resumen de ingresos
- `GET /api/v1/reports/spots-utilization` - Utilización de celdas

## Regulación en Colombia

Este sistema sigue las regulaciones de la Secretaría de Movilidad de Bogotá:
- Tarifas basadas en el régimen de libertad regulada
- Cumplimiento del Código Nacional de Policía (Ley 1801/2016)
- Emisión de recibo de depósito digital

## Licencia

MIT License