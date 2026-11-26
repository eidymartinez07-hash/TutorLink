# Publicación en Railway

1. Subir el proyecto a GitHub, incluidos `.gitignore` y `.env.example`, sin subir `.env`.
2. Conectar el repositorio al servicio web existente de Railway. Conservar el servicio MySQL y su volumen.
3. En Variables del servicio web, configurar `DATABASE_URL` con la URL MySQL del servicio, usando el esquema `mysql+pymysql://`, y `SECRET_KEY` con una clave aleatoria privada. Mantener la clave existente si ya funciona. No publicar valores reales.
4. Railway utiliza el comando `gunicorn --bind 0.0.0.0:$PORT app:app` definido en railway.json. Configurar HTTPS mediante el dominio público de Railway; `HTTPS=1` activa cookies seguras.
5. Para una base nueva, ejecutar `flask --app app init-db` y `flask --app app create-admin` en un entorno con las variables configuradas. Para la base existente no borrar tablas. `init-db` no migra columnas; verificar que `user.numero_control` exista antes de desplegar.
6. Verificar inicio de sesión de los tres perfiles, creación de cuentas, asignación, actividades, asistencia y solicitudes. Consultar ACCESOS_DEMO.md para cuentas ficticias.
7. SMTP es opcional; los recordatorios requieren programar `flask --app app send-reminders`. No hay envío semanal/mensual automático de reportes implementado en esta versión.
