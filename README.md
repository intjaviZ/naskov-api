<div align="center">

# 🌾 NasKob API (Backend Microservice)
### Motor Asíncrono de Decisión para Rotación de Cultivos — NASA Space Apps 2026

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-AsyncPG-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Alembic](https://img.shields.io/badge/Alembic-Migrations-orange?style=flat-square)](https://alembic.sqlalchemy.org/)
[![RFC 9457](https://img.shields.io/badge/RFC_9457-Problem_Details-blueviolet?style=flat-square)](https://datatracker.ietf.org/doc/html/rfc9457)

</div>

Para la documentación completa, arquitectura del sistema y modelos agronómicos con datos satelitales (GPM, SRTM, SMAP, POWER), consulta el **[README principal del proyecto](../../README.md)**.

---

### ⚡ Inicio Rápido

1. **Crear y activar entorno virtual**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Instalar requerimientos**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar `.env`**:
   ```bash
   cp .env.example .env
   # Configura DATABASE_URL, PWA_API_KEY y JWT_SECRET_KEY
   ```

4. **Aplicar migraciones**:
   ```bash
   alembic upgrade head
   ```

5. **Iniciar servidor**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Documentación Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
