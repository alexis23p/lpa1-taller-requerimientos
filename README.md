# Sistema de reservas hoteleras

Aplicación de consola en Python para consultar hoteles, buscar habitaciones y
administrar reservas de acuerdo con las necesidades descritas en
[`docs/entrevista.pdf`](./docs/entrevista.pdf).

## Funcionalidades

- Registrar hoteles y habitaciones con información de contacto, ubicación,
  servicios, capacidad, precio y fotos.
- Buscar disponibilidad por fechas, ubicación, número de huéspedes, calificación
  mínima y precio máximo por noche.
- Calcular precios por huésped y noche, con tarifas de temporada y ofertas.
- Configurar políticas de cancelación por tipo de habitación y temporada.
- Registrar clientes, crear reservas y consultar o cancelar estancias.
- Calcular el reembolso aplicable según la política de cancelación del hotel.
- Desactivar temporalmente hoteles o habitaciones y programar cierres de
  habitaciones por mantenimiento u otros motivos.
- Registrar comentarios y calificaciones después de la estancia; mostrar los
  promedios del hotel y de cada habitación.
- Guardar los datos en un archivo JSON local para conservarlos entre ejecuciones.

Los hoteles y habitaciones de demostración se cargan cuando se inicia la
aplicación por primera vez. Los datos se guardan en `data/reservas.json`, que no
se incluye en Git.

## Requerimientos

La lista completa de requerimientos funcionales y sus reglas de negocio está en
[`docs/requerimientos.md`](./docs/requerimientos.md). El modelo de clases está
en [`docs/diagrama_clases.mmd`](./docs/diagrama_clases.mmd).

## Tecnologías

- Python 3.10 o posterior
- [Rich](https://github.com/Textualize/rich) para la interfaz de consola
- `unittest` para las pruebas automatizadas

## Instalación

Clona el repositorio y crea un entorno virtual:

```bash
git clone https://github.com/clubdecomputacion/lpa1-taller-requerimientos.git
cd lpa1-taller-requerimientos
python3 -m venv .venv
source .venv/bin/activate
```

En Windows PowerShell, activa el entorno con:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instala las dependencias:

```bash
python -m pip install -r requirements.txt
```

## Ejecución

Con el entorno virtual activo, ejecuta:

```bash
python app.py
```

Usa las opciones del menú para buscar y reservar habitaciones, consultar o
cancelar reservas, agregar reseñas y administrar hoteles, temporadas y cierres.
Las fechas se ingresan en formato `AAAA-MM-DD`; la fecha de salida no se cuenta
como noche ocupada.

## Precios, cancelaciones y pagos

El precio base de cada habitación se expresa por huésped y por noche. Al cotizar,
se aplican el multiplicador de temporada y el mayor descuento disponible para
cada noche. La capacidad de la habitación limita el número de huéspedes.

El sistema calcula el reembolso usando los días de anticipación y la penalidad
configurados para el hotel. Es un cálculo informativo: la aplicación no cobra,
transfiere ni devuelve dinero y no se integra con una pasarela de pagos.

## Pruebas

Desde la raíz del repositorio, ejecuta:

```bash
python -m unittest discover -s tests -v
```
