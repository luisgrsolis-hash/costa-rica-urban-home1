# Costa Rica Urban Home — producción gratuita

Proyecto Flask preparado para desplegar en Render y usar Supabase PostgreSQL + Storage.

## Variables de entorno

Configura en Render:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ADMIN_PIN` = `1703`
- `STORAGE_BUCKET` = `property-images`

Nunca publiques `SUPABASE_SERVICE_ROLE_KEY` en GitHub ni en el navegador.

## Supabase

1. Abre SQL Editor.
2. Pega el contenido de `setup.sql`.
3. Ejecuta la consulta.

El backend crea automáticamente las 4 propiedades de demostración la primera vez que consulta la base vacía.

## Render

Build Command:

`pip install -r requirements.txt`

Start Command:

`gunicorn app:app`

El sitio conserva el diseño, idioma español/inglés, USD/CRC, administración con PIN 1703 y subida de imágenes desde la galería.


## Corrección de producción
La aplicación usa `description` y `description_en` en PostgreSQL y los expone al frontend como `desc` y `desc_en`, evitando la palabra reservada `DESC`.
