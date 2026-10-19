# Requerimientos del sistema de reservas hoteleras

Estos requerimientos se derivan de la entrevista incluida en
[`entrevista.pdf`](./entrevista.pdf).

## Requerimientos funcionales

| ID | Requerimiento |
|---|---|
| R1 | El sistema debe permitir registrar hoteles con nombre, dirección, teléfono, correo, ubicación, descripción, servicios, fotos y políticas de pago y cancelación. |
| R2 | El sistema debe permitir registrar habitaciones con tipo, descripción, precio por huésped y noche, capacidad, servicios incluidos y fotos. |
| R3 | El sistema debe permitir configurar ofertas con vigencia y porcentaje de descuento para un hotel. |
| R4 | El sistema debe permitir configurar temporadas con vigencia y un multiplicador de tarifa para un hotel. |
| R5 | El sistema debe permitir activar y desactivar hoteles y habitaciones. |
| R6 | El sistema debe permitir programar cierres de habitaciones por un intervalo de fechas y un motivo, por ejemplo, mantenimiento o remodelación. |
| R7 | El sistema debe permitir registrar clientes con nombre completo, teléfono, correo electrónico y dirección. |
| R8 | El sistema debe permitir buscar habitaciones por intervalo de fechas, ubicación, capacidad, calificación mínima y precio máximo por noche. |
| R9 | El sistema debe mostrar el detalle de hoteles y habitaciones, incluidos servicios, fotos, políticas, comentarios y calificaciones. |
| R10 | El sistema debe permitir reservar una habitación disponible para un cliente y un número válido de huéspedes. |
| R11 | El sistema debe permitir consultar y cancelar las reservas de un cliente, y calcular el reembolso de acuerdo con la política de cancelación del hotel. |
| R12 | El sistema debe permitir que el cliente califique y comente su estancia después de la salida. |
| R13 | El sistema debe calcular y mostrar las calificaciones promedio del hotel y de cada habitación. |
| R14 | El sistema debe conservar hoteles, habitaciones, clientes, temporadas, ofertas, cierres, reservas y reseñas entre ejecuciones. |
| R15 | El sistema debe permitir definir políticas de cancelación diferentes por tipo de habitación y temporada. |

## Reglas de negocio

- Solo hoteles y habitaciones activos participan en búsquedas y nuevas reservas.
- Una habitación no se puede reservar durante un cierre ni mientras otra reserva
  confirmada se superponga con las fechas solicitadas.
- La fecha de entrada se incluye y la fecha de salida se excluye del intervalo
  ocupado; por eso, una nueva estancia puede comenzar el mismo día en que termina
  otra.
- El número de huéspedes debe ser al menos uno y no puede superar la capacidad de
  la habitación.
- El precio por noche es la tarifa base por huésped multiplicada por el factor
  estacional vigente y por el descuento de la mejor oferta vigente. La cotización
  suma las noches de la estancia y multiplica cada noche por el número de
  huéspedes.
- Los intervalos de temporada del mismo hotel no pueden superponerse. Las fechas
  finales de temporadas, ofertas y cierres son exclusivas.
- El porcentaje de penalidad se aplica cuando la cancelación se solicita con
  menos días de anticipación que los indicados para la cancelación gratuita.
- La política de cancelación de la reserva se selecciona por tipo de habitación
  y fecha de entrada. Si coinciden varias reglas, se prefiere la regla específica
  para el tipo de habitación y luego la regla limitada a fechas; sin reglas
  coincidentes, se usa la política general del hotel.
- Solo el titular, identificado por el correo registrado, puede cancelar una
  reserva o dejar una reseña.
- La reseña se habilita después de la fecha de salida; cada reserva admite una
  calificación de 1 a 5 y un comentario.
- El importe de reembolso es informativo. No se realiza ningún movimiento de
  dinero.

## Alcance

La aplicación persiste los datos en JSON local y está pensada para un ejercicio
académico de consola. No integra pagos, autenticación, correo electrónico,
despliegue web ni servicios externos de mapas o almacenamiento de imágenes. Las
fotos se registran como rutas o enlaces.
