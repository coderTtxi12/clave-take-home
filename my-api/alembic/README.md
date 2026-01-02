# Alembic Migrations

Este directorio contiene las migraciones de base de datos gestionadas por Alembic.

## Estructura

```
alembic/
├── versions/              # Migraciones versionadas
│   └── xxxx_migration.py # Archivos de migración
├── env.py                 # Configuración del entorno
├── script.py.mako         # Template para nuevas migraciones
└── README                 # Este archivo
```

## Quick Start

```bash
# Ver estado actual
alembic current

# Aplicar todas las migraciones
alembic upgrade head

# Revertir última migración
alembic downgrade -1

# Crear nueva migración
alembic revision --autogenerate -m "descripcion_cambio"

# Ver historial
alembic history
```

## Modelos SQLAlchemy

Los modelos están en: `app/models/database.py`

Cualquier cambio en los modelos puede generar una migración automáticamente.

## Comandos Útiles

```bash
# Aplicar migraciones
./run_alembic_migrations.sh upgrade head

# Ver estado
./run_alembic_migrations.sh current

# Crear nueva migración
./run_alembic_migrations.sh revision "add_feature"
```

## Documentación

Ver `ALEMBIC_GUIDE.md` en el directorio `my-api` para documentación completa.

## Variables de Entorno

Las siguientes variables se leen del archivo `.env`:

- `POSTGRES_USER` - Usuario de PostgreSQL
- `POSTGRES_PASSWORD` - Contraseña
- `POSTGRES_DB` - Nombre de la base de datos
- `DB_HOST` - Host (default: localhost)
- `DB_PORT` - Puerto (default: 5432)

## Troubleshooting

### No puede conectar a la base de datos

```bash
# Iniciar PostgreSQL
docker-compose up -d

# Verificar que está corriendo
docker-compose ps
```

### Migración vacía generada

Alembic no detectó cambios. Verifica que:
1. Modificaste los modelos en `app/models/database.py`
2. Los modelos están importados en `env.py`
3. La base de datos no tiene ya esos cambios

## Recursos

- [Guía Completa de Alembic](../ALEMBIC_GUIDE.md)
- [Documentación Oficial](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)

