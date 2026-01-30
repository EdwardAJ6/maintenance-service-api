# 🔧 Maintenance Service API

API RESTful para gestión de órdenes de mantenimiento construida con FastAPI, SQLAlchemy y Python 3.11+.

## 📋 Tabla de Contenidos

- [Características](#características)
- [Seguridad y Autenticación](#seguridad-y-autenticación)
- [Arquitectura](#arquitectura)
- [Instalación](#instalación)
- [Uso](#uso)
- [Endpoints](#endpoints)
- [Autenticación JWT](#autenticación-jwt)
- [Idempotencia](#idempotencia-en-órdenes)
- [Estructura del Proyecto](#estructura-del-proyecto)

## ✨ Características

- **CRUD completo** para ítems/repuestos
- **Gestión de órdenes** de mantenimiento con idempotencia
- **Categorización** de ítems con LEFT JOIN
- **Índice B-Tree** en columna SKU para búsquedas optimizadas
- **Decorador `@measure_time`** para monitoreo de rendimiento
- **Integración simulada con AWS S3** para subida de imágenes
- **Autenticación JWT** con contraseñas hasheadas con bcrypt
- **Usuario admin por defecto** configurable por variables de entorno
- **Documentación automática** con Swagger UI

## 🔐 Seguridad y Autenticación

### JWT (JSON Web Tokens)

La API implementa autenticación basada en JWT para proteger los endpoints. Cada usuario recibe un token de acceso válido por 60 minutos tras login/registro exitoso.

### Credenciales

La API crea automáticamente un usuario **admin** al iniciar, con credenciales configurables por variables de entorno:

```bash
ADMIN_EMAIL=admin@maintenance.api       # Email del admin
ADMIN_PASSWORD=admin123                 # Contraseña del admin
SECRET_KEY=your-secret-key              # Clave secreta para firmar JWT
```

### Hash de Contraseñas

Las contraseñas se hashean usando **bcrypt** (algoritmo bcrypt con salt).

### Endpoints de Autenticación

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/auth/register` | Registrar nuevo usuario |
| POST | `/auth/login` | Login (obtener token) |
| GET | `/auth/me` | Obtener datos del usuario actual |

## 🏗️ Arquitectura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Cliente/API   │────▶│    FastAPI      │────▶│   SQLite/DB     │
│    (HTTP)       │     │   (Routers)     │     │  (SQLAlchemy)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   AWS S3        │
                        │  (Simulado)     │
                        └─────────────────┘
```

### Diagrama de Base de Datos

```
┌───────────────────┐       ┌───────────────────┐       ┌───────────────────┐
│      users        │       │    categories     │       │      items        │
├───────────────────┤       ├───────────────────┤       ├───────────────────┤
│ id (PK)           │───┐   │ id (PK)           │◄──────│ id (PK)           │
│ email (UNQ)       │   │   │ name              │       │ name              │
│ hashed_password   │   │   │ description       │       │ sku (INDEX B-Tree)│
│ is_admin          │   │   │ created_at        │       │ price             │
│ is_active         │   │   └───────────────────┘       │ stock             │
│ created_at        │   │                               │ category_id (FK)  │
│ updated_at        │   │                               │ created_at        │
└───────────────────┘   │                               │ updated_at        │
                        │                               └───────────────────┘
                        │                                        ▲
                        │                                        │
                        │   ┌───────────────────┐                │
                        │   │ technical_reports │                │
                        │   ├───────────────────┤                │
                        └──▶│ id (PK)           │◄──────┐        │
created_by_id (FK)          │ title             │       │        │
                            │ description       │       │        │
                            │ diagnosis         │       │        │
                            │ recommendations   │       │        │
                            │ created_by_id (FK)│       │        │
                            │ created_at        │       │        │
                            │ updated_at        │       │        │
                            └───────────────────┘       │        │
                                                        │        │
┌───────────────────┐       ┌───────────────────┐       │        │
│     orders        │       │   order_items     │       │        │
├───────────────────┤       ├───────────────────┤       │        │
│ id (PK)           │◄──────│ id (PK)           │       │        │
│ request_id (UNQ)  │       │ order_id (FK)     │───────┘        │
│ technical_report  │───────│ item_id (FK)      │────────────────┘
│   _id (FK)        │       │ quantity          │
│ status            │       │ unit_price        │
│ image_url         │       └───────────────────┘
│ created_at        │
│ updated_at        │
└───────────────────┘

RELACIÓN CLAVE: Order vincula Items con TechnicalReport
Order.technical_report_id → TechnicalReport.id
OrderItem.item_id → Item.id
```

### Diseño: Vinculación de Items con Reporte Técnico

El sistema cumple con el requerimiento de **"generar órdenes que vinculen ítems con un reporte técnico"** mediante:

1. **TechnicalReport** como entidad separada con campos:
   - `title`: Título del reporte
   - `description`: Descripción detallada del trabajo
   - `diagnosis`: Diagnóstico técnico (opcional)
   - `recommendations`: Recomendaciones futuras (opcional)
   - `created_by_id`: Usuario que creó el reporte

2. **Order** vincula:
   - Un `TechnicalReport` (relación N:1)
   - Múltiples `Items` a través de `OrderItem` (relación N:M)

3. **Flujo de creación**:
   ```
   POST /orders/ → Crea TechnicalReport → Crea Order → Vincula Items
   ```

## 🗄️ DBManager

La clase `DBManager` es un gestor genérico de base de datos que proporciona operaciones CRUD reutilizables con manejo adecuado de sesiones mediante bloques `try-except-finally`.

### Métodos disponibles

| Método | Descripción |
|--------|-------------|
| `create(db, **kwargs)` | Crear un nuevo registro |
| `get(db, id)` | Obtener registro por ID |
| `get_by_field(db, field_name, value)` | Obtener por campo específico |
| `list(db, skip, limit, filters, order_by, desc)` | Listar con paginación y filtros |
| `update(db, id, **kwargs)` | Actualizar parcialmente |
| `delete(db, id)` | Eliminar registro |
| `count(db, filters)` | Contar registros |
| `exists(db, id)` | Verificar existencia |

### Ejemplo de uso

```python
from database import DBManager
from models import Item

# Inicializar manager
item_manager = DBManager(Item)

# Crear
item = item_manager.create(db, name="Filtro", sku="FIL-001", price=25.99, stock=100)

# Obtener
item = item_manager.get(db, id=1)

# Listar con filtros
items = item_manager.list(db, skip=0, limit=10, filters={"category_id": 1})

# Actualizar (parcial)
item = item_manager.update(db, id=1, stock=150, price=29.99)

# Eliminar
deleted = item_manager.delete(db, id=1)
```

## ☁️ S3 Service

El servicio de AWS S3 permite subir imágenes de mantenimiento. Soporta dos modos de operación controlados por la variable de entorno `DEBUG`.

### Modos de operación

| DEBUG | Modo | Descripción |
|-------|------|-------------|
| `True` | **Simulación** | No realiza operaciones reales. Genera URLs simuladas y logs. Ideal para desarrollo. |
| `False` | **Producción** | Operaciones reales contra AWS S3. Requiere credenciales válidas. |

### Configuración requerida (DEBUG=False)

Cuando `DEBUG=False`, el servicio valida automáticamente que existan las siguientes variables de entorno al inicializarse:

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `AWS_ACCESS_KEY_ID` | Access Key de AWS | ✅ Sí |
| `AWS_SECRET_ACCESS_KEY` | Secret Key de AWS | ✅ Sí |
| `S3_BUCKET_NAME` | Nombre del bucket S3 | ✅ Sí |
| `AWS_REGION` | Región de AWS | No (default: `us-east-1`) |

Si falta alguna variable requerida, se lanza un error descriptivo:

```
S3ConfigurationError: Missing required AWS configuration: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY.
Set DEBUG=True for simulation mode or provide valid credentials.
```

### Métodos disponibles

| Método | Descripción |
|--------|-------------|
| `upload_image(image_base64, order_id, content_type)` | Sube imagen en base64 a S3 |
| `delete_image(object_key)` | Elimina imagen de S3 |
| `get_presigned_url(object_key, expiration)` | Genera URL temporal de acceso |

### Ejemplo de uso

```python
from services import get_s3_service, S3ServiceError

s3 = get_s3_service()

# Subir imagen
try:
    url = s3.upload_image(
        image_base64="iVBORw0KGgoAAAANS...",
        order_id="ORD-2024-001",
        content_type="image/png"
    )
    print(f"Imagen subida: {url}")
except S3ServiceError as e:
    print(f"Error: {e}")

# Generar URL temporal (1 hora)
presigned_url = s3.get_presigned_url("maintenance-images/ORD-001/image.jpg")

# Eliminar imagen
s3.delete_image("maintenance-images/ORD-001/image.jpg")
```

### Logs según modo

**Modo Simulación (DEBUG=True):**
```
INFO: [S3 SIMULATION] Upload: s3://my-bucket/maintenance-images/ORD-001/... (1024 bytes)
```

**Modo Producción (DEBUG=False):**
```
INFO: [S3] Uploaded: maintenance-images/ORD-001/20240115_143022_a1b2c3d4.jpg
```

## 🚀 Instalación

### Opción 1: Docker (Recomendado)

La forma más sencilla de ejecutar el proyecto es usando Docker.

#### Prerrequisitos

- Docker
- Docker Compose

#### Pasos

1. **Clonar el repositorio**
```bash
git clone <url-del-repositorio>
cd maintenance-service-api
```

1. **Configurar variables de entorno**

```bash
cp .env.example .env
# Editar .env si deseas cambiar las configuraciones
# Importante: cambiar SECRET_KEY, ADMIN_EMAIL y ADMIN_PASSWORD 
```

#### Variables de entorno importantes

```dotenv
# JWT y Seguridad
SECRET_KEY=your-super-secret-key-change-in-production-32-chars-minimum
ADMIN_EMAIL=admin@maintenance.api
ADMIN_PASSWORD=admin123

# Base de datos
DATABASE_URL=postgresql://maintenance_user:maintenance_pass@db:5432/maintenance_db
```

**El usuario admin se crea automáticamente al iniciar la aplicación** con las credenciales especificadas en `ADMIN_EMAIL` y `ADMIN_PASSWORD`.

1. **Levantar los servicios**

```bash
# Construir y levantar en segundo plano
docker-compose up -d --build

# Ver logs
docker-compose logs -f
```

1. **Acceder a la API**

- API: http://localhost:8000

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

1. **Opcional: Levantar pgAdmin para gestionar la BD**

```bash
docker-compose --profile tools up -d
```
- pgAdmin: http://localhost:5050
- Email: admin@admin.com
- Password: admin

#### Comandos útiles de Docker

```bash
# Detener servicios
docker-compose down

# Detener y eliminar volúmenes (CUIDADO: borra datos)
docker-compose down -v

# Reconstruir imagen
docker-compose build --no-cache

# Ver logs de un servicio específico
docker-compose logs -f api
docker-compose logs -f db

# Ejecutar comandos dentro del contenedor
docker-compose exec api bash
docker-compose exec db psql -U maintenance_user -d maintenance_db

# Ver estado de los contenedores
docker-compose ps
```

### Opción 2: Local (sin Docker)

#### Prerrequisitos

- Python 3.11+
- pip

#### Pasos

1. **Clonar el repositorio**

```bash
git clone <url-del-repositorio>
cd maintenance-service-api
```

1. **Crear entorno virtual**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

1. **Instalar dependencias**

```bash
pip install -r requirements.txt
```

1. **Configurar variables de entorno** (opcional)

```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

1. **Ejecutar la aplicación**

```bash
# Desde el directorio raíz, con PYTHONPATH configurado
PYTHONPATH=app uvicorn app.main:app --reload
```

O simplemente:

```bash
cd app
uvicorn main:app --reload
```

1. **Acceder a la documentación**

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📖 Uso

### 1. Autenticarse

#### Registrar nuevo usuario

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "securepass123"
  }'
```

Respuesta:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "newuser@example.com",
    "is_admin": false,
    "is_active": true,
    "created_at": "2024-01-30T10:00:00",
    "updated_at": "2024-01-30T10:00:00"
  }
}
```

#### Login con usuario existente

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@maintenance.api",
    "password": "admin123"
  }'
```

#### Obtener datos del usuario actual

```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer <tu_token_aqui>"
```

### 2. Crear una categoría (para pruebas)

**Nota:** Requiere token de autenticación

```bash
curl -X POST "http://localhost:8000/categories/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <tu_token_aqui>" \
  -d '{"name": "Electrónica", "description": "Componentes electrónicos"}'
```

### 3. Crear un ítem/repuesto

```bash
curl -X POST "http://localhost:8000/items/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <tu_token_aqui>" \
  -d '{
    "name": "Filtro de Aceite",
    "sku": "FIL-ACE-001",
    "price": 25.99,
    "stock": 100,
    "category_id": 1
  }'
```

### 4. Listar ítems (con categorías)

```bash
curl -X GET "http://localhost:8000/items/" \
  -H "Authorization: Bearer <tu_token_aqui>"
```

### 5. Actualizar stock/precio (PATCH)

```bash
curl -X PATCH "http://localhost:8000/items/1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <tu_token_aqui>" \
  -d '{"stock": 150}'
```

### 6. Crear una orden de mantenimiento

```bash
curl -X POST "http://localhost:8000/orders/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <tu_token_aqui>" \
  -d '{
    "request_id": "ORD-2024-001",
    "technical_report": "Cambio de filtro de aceite y revisión general",
    "items": [
      {"item_id": 1, "quantity": 2}
    ]
  }'
```

## 🔌 Endpoints

| Método | Endpoint | Descripción | Código Éxito |
|--------|----------|-------------|--------------|
| POST | `/auth/register` | Registrar nuevo usuario | 201 Created |
| POST | `/auth/login` | Login (obtener token) | 200 OK |
| GET | `/auth/me` | Obtener usuario actual | 200 OK |
| POST | `/items/` | Crear nuevo repuesto | 201 Created |
| GET | `/items/` | Listar repuestos (con categorías) | 200 OK |
| GET | `/items/{id}` | Obtener repuesto por ID | 200 OK |
| PATCH | `/items/{id}` | Actualizar stock/precio | 200 OK |
| DELETE | `/items/{id}` | Eliminar repuesto | 204 No Content |
| POST | `/orders/` | Crear orden de mantenimiento | 201 Created |
| GET | `/orders/` | Listar órdenes | 200 OK |
| GET | `/orders/{id}` | Obtener orden por ID | 200 OK |
| POST | `/categories/` | Crear categoría | 201 Created |
| GET | `/categories/` | Listar categorías | 200 OK |

## 🔐 Autenticación JWT

### Flujo de autenticación

1. **Registro**: POST `/auth/register` con email y contraseña
   ```bash
   curl -X POST "http://localhost:8000/auth/register" \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "securepass123"}'
   ```
   Respuesta:
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "token_type": "bearer",
     "user": {
       "id": 1,
       "email": "user@example.com",
       "is_admin": false,
       "is_active": true
     }
   }
   ```

2. **Login**: POST `/auth/login` con credenciales
   ```bash
   curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "securepass123"}'
   ```

3. **Usar token**: Incluir en headers Authorization
   ```bash
   curl "http://localhost:8000/auth/me" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   ```

### Información del Token

- **Tipo**: JWT (JSON Web Token)
- **Algoritmo**: HS256 (HMAC-SHA256)
- **Duración**: 60 minutos (configurable)
- **Claims**: `sub` (email), `user_id`, `is_admin`, `exp` (expiración)

### Errores de autenticación

| Código | Error | Descripción |
|--------|-------|-------------|
| 401 | `Unauthorized` | Token inválido, expirado o no proporcionado |
| 403 | `Forbidden` | Usuario no tiene permisos (ej: no es admin) |
| 409 | `Conflict` | Email ya registrado |

## 🔒 Idempotencia en Órdenes

### ¿Qué es la idempotencia?

La idempotencia garantiza que múltiples solicitudes idénticas produzcan el mismo resultado que una sola solicitud. Esto es crucial para evitar duplicados en operaciones críticas como la creación de órdenes.

### Implementación

1. **Campo `request_id` único**: Cada orden debe incluir un `request_id` único proporcionado por el cliente.

2. **Verificación previa**: Antes de crear una orden, el sistema verifica si ya existe una con el mismo `request_id`.

3. **Respuesta consistente**: Si la orden ya existe, se retorna la orden existente con código `200 OK` en lugar de crear un duplicado.

```python
# Pseudocódigo de la lógica
def create_order(order_data):
    # Verificar si ya existe
    existing_order = db.query(Order).filter(
        Order.request_id == order_data.request_id
    ).first()
    
    if existing_order is not None:  # Uso de 'is not' (identidad)
        return existing_order  # Retorna la existente
    
    # Si no existe, crear nueva
    new_order = Order(**order_data)
    db.add(new_order)
    db.commit()
    return new_order
```

### Beneficios

- **Prevención de duplicados**: Evita crear múltiples órdenes por reintentos de red
- **Consistencia**: El cliente siempre recibe la misma respuesta para el mismo `request_id`
- **Seguridad transaccional**: Protege contra condiciones de carrera

### Uso

```bash
# Primera solicitud - Crea la orden
curl -X POST "http://localhost:8000/orders/" \
  -H "Content-Type: application/json" \
  -d '{"request_id": "ORD-001", ...}'
# Respuesta: 201 Created

# Segunda solicitud con mismo request_id - Retorna la existente
curl -X POST "http://localhost:8000/orders/" \
  -H "Content-Type: application/json" \
  -d '{"request_id": "ORD-001", ...}'
# Respuesta: 200 OK (orden existente)
```

## 📁 Estructura del Proyecto

```
maintenance-service-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # Punto de entrada FastAPI
│   ├── config.py            # Configuración de la aplicación
│   ├── database/
│   │   ├── __init__.py
│   │   └── connection.py    # Conexión y sesión de BD
│   ├── models/
│   │   ├── __init__.py
│   │   ├── item.py          # Modelo Item
│   │   ├── order.py         # Modelo Order
│   │   ├── category.py      # Modelo Category
│   │   └── user.py          # Modelo User (autenticación)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── item.py          # Schemas Pydantic para Items
│   │   ├── order.py         # Schemas Pydantic para Orders
│   │   ├── category.py      # Schemas Pydantic para Categories
│   │   └── user.py          # Schemas Pydantic para Users
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py          # Endpoints de Autenticación
│   │   ├── items.py         # Endpoints de Items
│   │   ├── orders.py        # Endpoints de Orders
│   │   └── categories.py    # Endpoints de Categories
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py  # Servicios de JWT y hash
│   │   ├── init_service.py  # Servicios de inicialización
│   │   └── s3_service.py    # Servicio simulado AWS S3
│   └── utils/
│       ├── __init__.py
│       ├── decorators.py    # Decorador @measure_time
│       ├── exceptions.py    # Excepciones personalizadas
│       ├── log_config.py    # Configuración de logging
│       ├── constants.py     # Constantes
│       └── security.py      # Funciones de seguridad y JWT
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Configuración y fixtures compartidas
│   ├── test_auth.py         # Tests de autenticación
│   ├── test_items.py        # Tests de items
│   ├── test_orders.py       # Tests de órdenes
│   └── test_categories.py   # Tests de categorías
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## 🧪 Tests

Ejecutar tests localmente:

```bash
# Con PYTHONPATH correcto
PYTHONPATH=app pytest app/tests/ -v

# O desde el directorio app
cd app
pytest tests/ -v

# Con cobertura
pytest app/tests/ -v --cov=app --cov-report=term-plus
```

Desde Docker:

```bash
docker-compose exec api pytest app/tests/ -v
```

## 📝 Licencia

MIT License

## 👤 Autor

Desarrollado como prueba técnica para Backend Developer Junior.