# Guía Completa de Setup - Restaurant Analytics

Esta guía te muestra todos los pasos para configurar y ejecutar la base de datos, migraciones y ETL.

---

## 📋 Tabla de Contenidos

1. [Docker - Base de Datos PostgreSQL](#1-docker---base-de-datos-postgresql)
2. [Migraciones de Base de Datos con Alembic](#2-migraciones-de-base-de-datos-con-alembic)
3. [Funciones PostgreSQL para ETL](#3-funciones-postgresql-para-etl)
4. [ETL - Carga de Datos](#4-etl---carga-de-datos)
5. [Alembic - Guía Completa](#5-alembic---guía-completa)

---

## 1. Docker - Base de Datos PostgreSQL

### ¿Qué es Docker Compose?

Docker Compose permite definir y ejecutar múltiples contenedores Docker. En este proyecto, usamos Docker para ejecutar PostgreSQL sin instalarlo directamente en tu máquina.

### Pasos para Levantar la Base de Datos

#### Paso 1: Navegar al directorio
```bash
cd my-api
```

#### Paso 2: Iniciar PostgreSQL con Docker
```bash
# Iniciar en modo detached (en segundo plano)
docker-compose up -d
```

**¿Qué hace este comando?**
- Lee el archivo `docker-compose.yml`
- Descarga la imagen de PostgreSQL 15 (si no existe)
- Crea un contenedor llamado `restaurant_analytics_db`
- Expone el puerto 5433 en tu máquina local (mapeado desde 5432 del contenedor)
- Crea un volumen persistente para los datos

#### Paso 3: Verificar que está corriendo
```bash
# Ver el estado de los contenedores
docker-compose ps

# Deberías ver algo como:
# NAME                      STATUS          PORTS
# restaurant_analytics_db   Up X minutes     0.0.0.0:5433->5432/tcp
```

#### Paso 4: Ver los logs (opcional)
```bash
# Ver logs en tiempo real
docker-compose logs -f postgres

# Ver últimas 50 líneas
docker-compose logs --tail=50 postgres
```

### Comandos Útiles de Docker

```bash
# Detener la base de datos (mantiene los datos)
docker-compose stop

# Iniciar de nuevo
docker-compose start

# Detener y eliminar contenedores (mantiene los datos)
docker-compose down

# Detener y eliminar contenedores Y datos (⚠️ CUIDADO)
docker-compose down -v

# Reiniciar el servicio
docker-compose restart postgres

# Reconstruir si cambias docker-compose.yml
docker-compose up -d --build
```

### Verificar Conexión a la Base de Datos

```bash
# Conectar con psql
psql -h localhost -p 5433 -U postgres -d restaurant_analytics

# O usando la cadena de conexión
psql postgresql://postgres:postgres@localhost:5433/restaurant_analytics
```

**Credenciales por defecto:**
- Host: `localhost`
- Port: `5433` (puerto externo, el contenedor usa 5432 internamente)
- Database: `restaurant_analytics`
- User: `postgres`
- Password: `postgres`

### Solución de Problemas

**Error: "port 5433 already in use"**
```bash
# Encontrar qué proceso usa el puerto
lsof -i :5433  # Mac/Linux
netstat -ano | findstr :5433  # Windows

# Si necesitas cambiar el puerto, edita docker-compose.yml
# Cambiar "5433:5432" a otro puerto, ej: "5434:5432"
```

**Error: "Cannot connect to Docker daemon"**
```bash
# Asegúrate de que Docker Desktop esté corriendo
# En Mac: Abre Docker Desktop app
# En Linux: sudo systemctl start docker
```

---

## 2. Migraciones de Base de Datos con Alembic

### ¿Qué es Alembic?

**Alembic** es una herramienta de migraciones de base de datos para SQLAlchemy. Permite:
- ✅ Versionado automático del esquema
- ✅ Historial completo de cambios
- ✅ Rollback fácil de migraciones
- ✅ Auto-generación desde modelos SQLAlchemy

### Prerequisitos

```bash
# Activar virtual environment
source .venv/bin/activate

# Instalar dependencias (si no lo has hecho)
pip install -r requirements.txt
```

### Aplicar Migraciones

#### Opción 1: Usar el Script Helper (Recomendado)

```bash
cd my-api

# Aplicar todas las migraciones
./run_alembic_migrations.sh upgrade head

# Ver estado actual
./run_alembic_migrations.sh current

# Ver historial
./run_alembic_migrations.sh history
```

#### Opción 2: Usar Alembic Directamente

```bash
# Activar virtual environment
source .venv/bin/activate

# Aplicar todas las migraciones
alembic upgrade head

# Ver versión actual
alembic current

# Ver historial
alembic history
```

**¿Qué hace `alembic upgrade head`?**
1. Lee las migraciones en `alembic/versions/`
2. Verifica qué migraciones ya se ejecutaron
3. Ejecuta solo las migraciones pendientes
4. Actualiza la tabla `alembic_version` con el estado

### Verificar que las Migraciones Funcionaron

```bash
# Conectar a la base de datos
psql -h localhost -p 5433 -U postgres -d restaurant_analytics

# Dentro de psql, ejecutar:
\dt                    # Lista todas las tablas
\d                     # Lista todos los objetos

# Verificar tablas principales
SELECT COUNT(*) FROM locations;
SELECT COUNT(*) FROM categories;
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM orders;
```

### Resetear la Base de Datos (Empezar de Cero)

```bash
# ⚠️ CUIDADO: Esto borra TODOS los datos

# Opción 1: Usar Docker (recomendado)
docker-compose down -v
docker-compose up -d
sleep 5
alembic upgrade head

# Opción 2: Eliminar y recrear manualmente
psql -h localhost -p 5433 -U postgres -d postgres -c "DROP DATABASE IF EXISTS restaurant_analytics;"
psql -h localhost -p 5433 -U postgres -d postgres -c "CREATE DATABASE restaurant_analytics;"
alembic upgrade head
```

### Revertir Migraciones

```bash
# Revertir última migración
alembic downgrade -1

# Revertir hasta una versión específica
alembic downgrade <revision_id>

# Revertir todas las migraciones
alembic downgrade base
```

---

## 3. Funciones PostgreSQL para ETL

### ¿Por qué Necesitas Estas Funciones?

Los scripts ETL usan funciones PostgreSQL helper que **NO están incluidas** en las migraciones de Alembic (son lógica de negocio, no estructura de base de datos).

### Funciones Incluidas

1. **`get_location_id_by_source(source, source_id)`**
   - Mapea source IDs a location IDs

2. **`get_or_create_category(category_name)`**
   - Normaliza y crea categorías automáticamente
   - **Usado por:** `scripts/etl_utils.py`

3. **`validate_etl_data()`**
   - Valida integridad de datos después de cargar
   - **Usado por:** `scripts/load_all_data.py`

### Instalación

#### Opción 1: Script Automático (Recomendado)

```bash
cd my-api

# Instalar funciones ETL
./install_etl_functions.sh
```

**¿Qué hace el script?**
1. Verifica conexión a la base de datos
2. Ejecuta `sql/etl_functions.sql`
3. Crea las 3 funciones necesarias
4. Muestra confirmación

#### Opción 2: Manual

```bash
# Ejecutar archivo SQL directamente
psql -h localhost -p 5433 -U postgres -d restaurant_analytics -f sql/etl_functions.sql
```

### Verificar Instalación

```bash
# Conectar a la base de datos
psql -h localhost -p 5433 -U postgres -d restaurant_analytics

# Dentro de psql:
\df get_location_id_by_source
\df get_or_create_category
\df validate_etl_data

# Probar una función
SELECT get_or_create_category('Test Category');
```

### ⚠️ Importante

**DEBES instalar estas funciones ANTES de ejecutar los scripts ETL**, de lo contrario fallarán con:

```
ERROR: function get_or_create_category(character varying) does not exist
```

---

## 4. ETL - Carga de Datos

### ¿Qué es ETL?

ETL significa **Extract, Transform, Load** (Extraer, Transformar, Cargar):
- **Extract:** Lee los archivos JSON de las fuentes (Toast, DoorDash, Square)
- **Transform:** Normaliza, limpia y unifica los datos
- **Load:** Inserta los datos en PostgreSQL

### Prerequisitos

1. ✅ PostgreSQL corriendo (ver sección 1)
2. ✅ Migraciones de Alembic ejecutadas (ver sección 2)
3. ✅ **Funciones ETL instaladas** (ver sección 3) ⚠️ **NUEVO**
4. ✅ Archivos JSON en `../data/sources/`:
   - `toast_pos_export.json`
   - `doordash_orders.json`
   - `square/catalog.json`
   - `square/locations.json`
   - `square/orders.json`
   - `square/payments.json`

### Opción 1: Script Automático (Recomendado)

```bash
cd my-api

# Dar permisos de ejecución (solo la primera vez)
chmod +x load_data.sh

# Cargar todos los datos
./load_data.sh

# O para borrar datos existentes antes de cargar
./load_data.sh --clear
```

**¿Qué hace el script?**
1. Verifica que PostgreSQL esté corriendo
2. Verifica que las migraciones estén ejecutadas
3. Verifica que los archivos JSON existan
4. Instala dependencias de Python (psycopg2-binary)
5. Ejecuta el script de ETL
6. Muestra estadísticas de carga

### Opción 2: Ejecutar ETL Manualmente

```bash
cd my-api/scripts

# Instalar dependencias (solo la primera vez)
pip install psycopg2-binary

# Configurar variables de entorno
export DB_HOST=localhost
export DB_PORT=5433
export DB_NAME=restaurant_analytics
export DB_USER=postgres
export DB_PASSWORD=postgres

# Cargar todos los datos
python load_all_data.py

# O borrar datos existentes primero
python load_all_data.py --clear
```

### Cargar Fuentes Individuales

```bash
cd my-api/scripts

# Solo Toast POS
python load_toast_data.py [--clear]

# Solo DoorDash
python load_doordash_data.py [--clear]

# Solo Square POS
python load_square_data.py [--clear]
```

### ¿Qué Datos se Cargan?

#### Toast POS (`toast_pos_export.json`)
- ✅ Locations (restaurantes)
- ✅ Orders (órdenes)
- ✅ Checks (cuentas)
- ✅ Order Items (items con modifiers)
- ✅ Payments (pagos)

#### DoorDash (`doordash_orders.json`)
- ✅ Stores → Locations
- ✅ Orders
- ✅ Order Items con options
- ✅ Delivery Orders (info de entrega)
- ✅ Payments

#### Square POS (`square/*.json`)
- ✅ Catalog items → Products
- ✅ Locations
- ✅ Orders con line items
- ✅ Payments con detalles de tarjeta

### Verificar que los Datos se Cargaron

```bash
# Conectar a la base de datos
psql -h localhost -p 5433 -U postgres -d restaurant_analytics

# Dentro de psql, ejecutar:
SELECT 'orders' as table_name, COUNT(*) FROM orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL
SELECT 'payments', COUNT(*) FROM payments
UNION ALL
SELECT 'products', COUNT(*) FROM products;

# Ver ventas por fuente
SELECT source, COUNT(*) as orders, SUM(total_amount) as revenue
FROM orders
GROUP BY source;

# Validar integridad (usa función ETL)
SELECT * FROM validate_etl_data();
```

### Actualizar Materialized Views

Después de cargar datos, actualiza las vistas materializadas para que los reportes estén actualizados:

```bash
psql -h localhost -p 5433 -U postgres -d restaurant_analytics

# Dentro de psql:
SELECT refresh_all_materialized_views();

# O actualizar individualmente:
REFRESH MATERIALIZED VIEW CONCURRENTLY daily_sales_summary;
REFRESH MATERIALIZED VIEW CONCURRENTLY product_performance;
REFRESH MATERIALIZED VIEW CONCURRENTLY hourly_sales;
REFRESH MATERIALIZED VIEW CONCURRENTLY category_performance;
REFRESH MATERIALIZED VIEW CONCURRENTLY payment_method_summary;
REFRESH MATERIALIZED VIEW CONCURRENTLY location_comparison;
```

### Solución de Problemas ETL

**Error: "ModuleNotFoundError: No module named 'psycopg2'"**
```bash
pip install psycopg2-binary
```

**Error: "connection refused"**
```bash
# Verificar que PostgreSQL esté corriendo
docker-compose ps
docker-compose up -d
```

**Error: "relation does not exist"**
```bash
# Ejecutar migraciones primero
alembic upgrade head
```

**Error: "function get_or_create_category does not exist"**
```bash
# Instalar funciones ETL
./install_etl_functions.sh
```

**Error: "duplicate key value violates unique constraint"**
```bash
# Usar --clear para borrar datos existentes
python load_all_data.py --clear
```

---

## 5. Alembic - Guía Completa

### ¿Qué es Alembic?

**Alembic** es una herramienta de migraciones de base de datos para SQLAlchemy (ORM de Python). Es el equivalente a herramientas como:
- **Django Migrations** (Django)
- **Rails Migrations** (Ruby on Rails)
- **Flyway** (Java)
- **Liquibase** (Java)

### Características de Alembic

1. **Migraciones Versionadas:** Cada cambio se guarda como un archivo Python
2. **Historial de Cambios:** Rastrea qué migraciones se han ejecutado
3. **Rollback:** Puede revertir migraciones
4. **Auto-generación:** Puede generar migraciones automáticamente desde modelos SQLAlchemy
5. **Dependencias:** Maneja dependencias entre migraciones

### Comandos Básicos

```bash
# Ver versión actual
alembic current

# Aplicar todas las migraciones
alembic upgrade head

# Revertir última migración
alembic downgrade -1

# Ver historial
alembic history

# Crear nueva migración
alembic revision --autogenerate -m "add_new_field"
```

### Crear Nueva Migración

#### Paso 1: Modificar Modelos

Edita `app/models/database.py`:

```python
class Product(Base):
    # ... campos existentes ...
    is_featured = Column(Boolean, default=False)  # ← Nuevo campo
```

#### Paso 2: Generar Migración

```bash
alembic revision --autogenerate -m "add_is_featured_to_products"
```

#### Paso 3: Revisar Archivo Generado

Revisa `alembic/versions/xxxx_add_is_featured_to_products.py` para verificar que detectó el cambio.

#### Paso 4: Aplicar Migración

```bash
alembic upgrade head
```

### Ventajas de Alembic

| Característica | Beneficio |
|----------------|-----------|
| **Versionado** | Historial automático de cambios |
| **Rollback** | `alembic downgrade -1` fácil |
| **Auto-generación** | Detecta cambios en modelos automáticamente |
| **Team-friendly** | Merge automático de migraciones |
| **Historial** | `alembic history` muestra todo |

### Ver Documentación Completa

Para más detalles, ver:
- **[ALEMBIC_GUIDE.md](./ALEMBIC_GUIDE.md)** - Guía completa de Alembic
- **[alembic/README.md](./alembic/README.md)** - Quick reference

---

## 📝 Resumen de Comandos Rápidos

### Setup Completo (Primera Vez)

```bash
# 1. Iniciar PostgreSQL
cd my-api
docker-compose up -d

# 2. Aplicar migraciones de Alembic
source .venv/bin/activate
alembic upgrade head

# 3. Instalar funciones ETL (NUEVO PASO)
./install_etl_functions.sh

# 4. Cargar datos
./load_data.sh

# 5. Verificar
psql -h localhost -p 5433 -U postgres -d restaurant_analytics
SELECT * FROM validate_etl_data();
```

### Comandos Diarios

```bash
# Iniciar base de datos
docker-compose up -d

# Ver logs
docker-compose logs -f postgres

# Conectar a la base de datos
psql -h localhost -p 5433 -U postgres -d restaurant_analytics

# Ver estado de migraciones
alembic current

# Detener base de datos
docker-compose stop
```

### Resetear Todo (Empezar de Cero)

```bash
# ⚠️ CUIDADO: Borra todos los datos
docker-compose down -v
docker-compose up -d
sleep 5
alembic upgrade head
./install_etl_functions.sh
./load_data.sh --clear
```

---

## 🔗 Recursos Adicionales

- [README.md](./README.md) - Documentación completa del API
- [ALEMBIC_GUIDE.md](./ALEMBIC_GUIDE.md) - Guía completa de Alembic
- [sql/README.md](./sql/README.md) - Documentación de funciones ETL
- [scripts/README.md](./scripts/README.md) - Documentación de ETL
- [QUICK_START.md](../QUICK_START.md) - Guía rápida

---

## ❓ Preguntas Frecuentes

**P: ¿Por qué usar Alembic en lugar de SQL directo?**
R: Alembic proporciona versionado automático, rollback fácil, historial completo y auto-generación desde modelos. Es mejor para proyectos en equipo y cambios frecuentes.

**P: ¿Cómo sé qué migraciones se han ejecutado?**
R: Usa `alembic current` para ver la versión actual, o `alembic history` para ver todas las migraciones.

**P: ¿Puedo revertir una migración?**
R: Sí, usa `alembic downgrade -1` para revertir la última migración, o `alembic downgrade <revision_id>` para una específica.

**P: ¿Por qué necesito instalar funciones ETL por separado?**
R: Las funciones ETL son lógica de negocio, no estructura de base de datos. No están en las migraciones de Alembic porque son independientes del esquema.

**P: ¿Qué pasa si ejecuto una migración dos veces?**
R: Alembic rastrea qué migraciones se ejecutaron. No ejecutará la misma migración dos veces automáticamente.

**P: ¿Puedo modificar las migraciones después de ejecutarlas?**
R: No es recomendable. Mejor crear una nueva migración con los cambios adicionales.

---

**¿Necesitas ayuda?** Revisa los logs de Docker o los mensajes de error para más detalles.

