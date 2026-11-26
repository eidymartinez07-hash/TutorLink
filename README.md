# TutorLink — Flask + MySQL

Sistema de apoyo a tutorías del Instituto Tecnológico de Matehuala. Incluye tres roles (estudiante, tutor y coordinación), actividades de cuadernillo, sesiones, asistencia, solicitudes, asignación de tutor, notificaciones internas, reportes CSV y recordatorios opcionales por correo.

## Requisitos
- Windows 11, Python 3.10+ (probado a nivel de sintaxis con Python 3), MySQL Server 8.x.
- La base de datos debe estar creada previamente.

## Instalación en Windows (PowerShell, carpeta del proyecto)
1. En MySQL Workbench, ejecuta:
```sql
CREATE DATABASE IF NOT EXISTS tutorlink CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'tutorlink'@'localhost' IDENTIFIED BY 'TU_PASSWORD_SEGURO';
GRANT ALL PRIVILEGES ON tutorlink.* TO 'tutorlink'@'localhost';
```
2. Abre PowerShell dentro de la carpeta `TutorLink_Flask`:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```
3. En `.env` cambia `SECRET_KEY` por una cadena aleatoria larga y reemplaza `CAMBIA_PASSWORD` con `TU_PASSWORD_SEGURO` (si tu contraseña contiene @, #, : u otros caracteres especiales, codifícalos en la URL). Puedes generar la clave con `py -c "import secrets; print(secrets.token_hex(32))"`.
4. Inicializa y crea tu primera cuenta de Coordinación:
```powershell
flask --app app init-db
flask --app app create-admin
```
5. Ejecuta:
```powershell
flask --app app run --debug
```
6. Abre `http://127.0.0.1:5000`. Inicia sesión como Coordinación, crea una cuenta de tutor y una de estudiante, y asigna el estudiante al tutor.

## Flujo de prueba
1. Coordinación: crear tutor, estudiante y asignación.
2. Tutor: crear sesión y actividad de cuadernillo.
3. Estudiante: responder actividad y solicitar apoyo.
4. Tutor: revisar actividad, registrar asistencia y actualizar solicitud.
5. Coordinación: revisar seguimiento; tutor o coordinación: exportar CSV.

## Recordatorios automáticos
La orden `flask --app app send-reminders` registra notificaciones internas para sesiones que ocurrirán aproximadamente entre 24 y 48 horas después de la ejecución. Puedes programar la orden diariamente con el Programador de tareas de Windows (usando el Python del entorno virtual y el directorio del proyecto). Para correos, configura SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD y SMTP_FROM en `.env`. **No se envían correos sin SMTP configurado**. Prueba primero con cuentas de laboratorio.

## Seguridad y límites
- Las contraseñas se almacenan con hash y los formularios usan token CSRF; hay controles de permisos por rol.
- Es una versión funcional de desarrollo, **no un despliegue institucional auditado**. Antes de usar datos reales: habilitar HTTPS, servidor WSGI de producción, copias de seguridad cifradas, restablecimiento de contraseñas, políticas de retención, consentimiento y revisión institucional de privacidad y permisos. No guardes datos sensibles de salud en solicitudes.
- No incluye integración con Teams/Microsoft 365 ni un sistema de canalización con acceso independiente para departamentos externos.
- El archivo `.env` contiene secretos: no lo subas a repositorios públicos.

## Publicación y demostración
Consultar [GUIA_PUBLICACION.md](GUIA_PUBLICACION.md) y [ACCESOS_DEMO.md](ACCESOS_DEMO.md). Los accesos de ejemplo no se muestran en la interfaz. No usar contraseñas públicas con datos reales.

El registro de estudiantes usa número de control de ocho dígitos y NIP de ocho a doce dígitos. Tutor y Coordinación usan correo y contraseña. El enlace de exportación CSV se muestra en Coordinación; el backend también permite al tutor exportar sus propias asistencias. No hay envío automático semanal o mensual de reportes en esta versión.
