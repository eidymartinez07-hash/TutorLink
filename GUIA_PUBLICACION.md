# Publicar TutorLink y obtener un enlace público

**No hay un enlace público hasta que despliegues el proyecto en tu cuenta de alojamiento.**

## Railway + MySQL (requiere cuenta Railway y GitHub; pueden aplicarse cargos)

1. Sube el contenido de esta carpeta a un repositorio **privado** de GitHub. No subas `.env`.
2. En https://railway.com/ crea un proyecto y agrega una base de datos **MySQL**.
3. Agrega un servicio desde el repositorio de GitHub de TutorLink.
4. En las variables del servicio web configura:
   - `SECRET_KEY`: una cadena aleatoria larga (por ejemplo, generar localmente con `python -c "import secrets; print(secrets.token_hex(32))"`).
   - `DATABASE_URL`: `mysql+pymysql://USUARIO:CONTRASEÑA@HOST:PUERTO/BASE?charset=utf8mb4`. Toma los datos de las variables del servicio MySQL de Railway. Si la contraseña contiene caracteres reservados, codifícala para URL. La URL interna de Railway solo funcionará dentro de la red del proyecto.
   - `HTTPS=1` (para cookies de sesión seguras sobre el dominio HTTPS).
5. Despliega y confirma en registros que Gunicorn arranca sin errores.
6. **Antes de abrir el acceso a terceros**, inicializa las tablas y crea la cuenta de Coordinación desde una consola segura con acceso a las mismas variables del servicio: `flask --app app init-db` y `flask --app app create-admin`. Si tu plan no ofrece consola de comandos, realiza estos comandos desde tu computadora conectándote a la base mediante la conexión pública de Railway, configurando `DATABASE_URL` localmente; protege las credenciales.
7. En Railway, abre el servicio web → Networking → Generate Domain. El enlace HTTPS generado es el que podrás compartir.
8. Inicia sesión como Coordinación, crea tutores y estudiantes de prueba, asigna tutores y comprueba las operaciones.

**Importante:** El servicio requiere un servidor y base de datos permanentes; no es posible publicarlo solo subiendo `index.html` a GitHub Pages. No uses datos reales hasta completar la revisión de seguridad, copias de respaldo y autorización institucional. Los recordatorios no se ejecutan solos: programa `flask --app app send-reminders` mediante una tarea programada en tu alojamiento.
