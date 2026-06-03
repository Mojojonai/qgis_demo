# Local GIS Stack Setup

## QGIS

- Install path: `C:\Program Files\QGIS 3.44.11`
- Executable: `C:\Program Files\QGIS 3.44.11\bin\qgis-ltr-bin.exe`

## PostgreSQL / PostGIS

- PostgreSQL version: 17.10
- Service name: `postgresql-x64-17`
- Host: `localhost`
- Port: `5764`
- Admin user: `postgres`
- Admin password: `admin`
- Project database: `transit_accessibility`
- Enabled extensions:
  - `postgis`
  - `postgis_topology`

Connection URI:

```text
postgresql://postgres:admin@localhost:5764/transit_accessibility
```

## pgAdmin

- Executable: `C:\Program Files\PostgreSQL\17\pgAdmin 4\runtime\pgAdmin4.exe`

When creating a pgAdmin server connection, use:

```text
Name: Transit Accessibility Local
Host: localhost
Port: 5764
Maintenance database: postgres
Username: postgres
Password: admin
```

## Verification

```powershell
$env:PGPASSWORD = "admin"
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -h localhost -p 5764 -U postgres -d transit_accessibility -c "SELECT postgis_full_version();"
```
