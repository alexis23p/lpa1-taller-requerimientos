"""Interactive console application for the hotel reservation system."""

from __future__ import annotations

from datetime import date
from math import isfinite
from pathlib import Path

from rich.console import Console
from rich.table import Table

from hotel_booking import BookingError, BookingSystem, Customer, Hotel, Room

console = Console()
DATA_FILE = Path(__file__).parent / "data" / "reservas.json"


def _ask(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = console.input(f"{label}{suffix}: ").strip()
    return value or (default or "")


def _ask_int(label: str, minimum: int = 0) -> int:
    while True:
        try:
            value = int(_ask(label))
            if value < minimum:
                raise ValueError
            return value
        except ValueError:
            console.print(f"[red]Ingrese un número entero igual o mayor que {minimum}.[/red]")


def _ask_float(label: str, minimum: float = 0) -> float:
    while True:
        try:
            value = float(_ask(label).replace(",", "."))
            if not isfinite(value) or value < minimum:
                raise ValueError
            return value
        except ValueError:
            console.print(f"[red]Ingrese un número igual o mayor que {minimum}.[/red]")


def _ask_date(label: str) -> date:
    while True:
        try:
            return date.fromisoformat(_ask(f"{label} (AAAA-MM-DD)"))
        except ValueError:
            console.print("[red]Use una fecha válida en formato AAAA-MM-DD.[/red]")


def _ask_optional_date(label: str) -> date | None:
    while True:
        value = _ask(f"{label} (AAAA-MM-DD; vacío para cualquier fecha)")
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            console.print("[red]Use una fecha válida en formato AAAA-MM-DD.[/red]")


def _ask_list(label: str) -> list[str]:
    return [value.strip() for value in _ask(f"{label} (separados por coma)").split(",") if value.strip()]


def _show_hotel_details(system: BookingSystem, hotel: Hotel) -> None:
    console.print(f"\n[bold cyan]{hotel.name}[/bold cyan] — {hotel.location}")
    console.print(hotel.description)
    console.print(f"Dirección: {hotel.address or 'No registrada'}")
    console.print(f"Teléfono: {hotel.phone or 'No registrado'} | Correo: {hotel.email}")
    console.print(f"Servicios: {', '.join(hotel.services) or 'No especificados'}")
    console.print(f"Fotos: {', '.join(hotel.photos) or 'No registradas'}")
    console.print(f"Pago: {hotel.payment_policy}")
    console.print(f"Cancelación: {hotel.cancellation_policy}")
    rules = [
        rule
        for rule in system.cancellation_rules.values()
        if rule.hotel_id == hotel.id
    ]
    for rule in rules:
        room_type = rule.room_type or "Todos los tipos"
        period = (
            f"{rule.start_date} a {rule.end_date} (fin exclusivo)"
            if rule.start_date
            else "Todo el año"
        )
        console.print(
            f"Política {rule.name}: {room_type}, {period}; reembolso completo "
            f"con {rule.free_cancellation_days} días de anticipación."
        )
    console.print(f"Calificación promedio: {system.hotel_rating(hotel.id):.1f}/5")
    rooms = [room for room in system.rooms.values() if room.hotel_id == hotel.id]
    if rooms:
        table = Table(title="Habitaciones")
        table.add_column("ID", style="dim")
        table.add_column("Nombre")
        table.add_column("Tipo")
        table.add_column("Capacidad", justify="right")
        table.add_column("Precio/noche", justify="right")
        table.add_column("Servicios")
        table.add_column("Fotos")
        table.add_column("Calificación", justify="right")
        for room in rooms:
            table.add_row(
                room.id,
                room.name,
                room.room_type,
                str(room.capacity),
                f"${room.nightly_rate:,.0f}",
                ", ".join(room.services) or "—",
                ", ".join(room.photos) or "—",
                f"{system.room_rating(room.id):.1f}/5",
            )
        console.print(table)
    reviews = system.hotel_reviews(hotel.id)
    if reviews:
        console.print("\n[bold]Comentarios de huéspedes[/bold]")
        for review in reviews:
            customer = system.customer(review.customer_id)
            console.print(f"★ {review.rating}/5 — {customer.full_name}: {review.comment}")


def _ensure_customer(system: BookingSystem) -> Customer:
    email = _ask("Correo electrónico del titular")
    customer = system.find_customer_by_email(email)
    if customer:
        console.print(f"Reserva a nombre de [bold]{customer.full_name}[/bold].")
        return customer
    console.print("Registro de cliente nuevo:")
    return system.register_customer(
        full_name=_ask("Nombre completo"),
        phone=_ask("Teléfono"),
        email=email,
        address=_ask("Dirección"),
    )


def search_and_book(system: BookingSystem) -> None:
    check_in = _ask_date("Fecha de entrada")
    check_out = _ask_date("Fecha de salida")
    guests = _ask_int("Número de huéspedes", minimum=1)
    location = _ask("Ciudad o nombre del hotel")
    minimum_rating = _ask_float("Calificación mínima (0-5)", minimum=0)
    maximum_input = _ask("Precio máximo por noche total (dejar vacío para omitir)")
    maximum = float(maximum_input.replace(",", ".")) if maximum_input else None

    matches = system.search_rooms(
        check_in,
        check_out,
        guests,
        location=location,
        minimum_rating=minimum_rating,
        maximum_nightly_rate=maximum,
    )
    if not matches:
        console.print("[yellow]No se encontraron habitaciones disponibles.[/yellow]")
        return

    table = Table(title="Habitaciones disponibles")
    table.add_column("#", justify="right")
    table.add_column("Hotel")
    table.add_column("Ubicación")
    table.add_column("Habitación")
    table.add_column("Huéspedes", justify="right")
    table.add_column("1.ª noche", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Calificación", justify="right")
    for index, match in enumerate(matches, start=1):
        hotel: Hotel = match["hotel"]
        room: Room = match["room"]
        table.add_row(
            str(index),
            hotel.name,
            hotel.location,
            f"{room.name} ({room.room_type})",
            str(room.capacity),
            f"${match['nightly_rate'] * guests:,.0f}",
            f"${match['total_price']:,.0f}",
            f"{match['hotel_rating']:.1f}/5",
        )
    console.print(table)
    selection = _ask("Número de habitación para reservar (0 para volver)")
    if not selection.isdigit() or int(selection) == 0:
        return
    index = int(selection) - 1
    if index >= len(matches):
        raise BookingError("La selección no corresponde a una habitación de la lista.")
    customer = _ensure_customer(system)
    booking = system.create_booking(
        customer.id,
        matches[index]["room"].id,
        check_in,
        check_out,
        guests,
    )
    hotel = system.hotel_for_room(booking.room_id)
    console.print(
        f"\n[green]Reserva confirmada.[/green] Código: [bold]{booking.id}[/bold]\n"
        f"Hotel: {hotel.name} | Total: ${booking.total_price:,.0f}\n"
        f"Política de pago: {hotel.payment_policy}"
    )


def show_bookings(system: BookingSystem) -> None:
    email = _ask("Correo electrónico del titular")
    bookings = system.bookings_for_customer(email)
    if not bookings:
        console.print("[yellow]No hay reservas para ese correo.[/yellow]")
        return
    table = Table(title="Reservas")
    table.add_column("Código", style="dim")
    table.add_column("Hotel")
    table.add_column("Habitación")
    table.add_column("Entrada")
    table.add_column("Salida")
    table.add_column("Personas", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Estado")
    for booking in bookings:
        room = system.room_for_booking(booking)
        table.add_row(
            booking.id,
            system.hotel_for_room(room.id).name,
            room.name,
            booking.check_in.isoformat(),
            booking.check_out.isoformat(),
            str(booking.guests),
            f"${booking.total_price:,.0f}",
            booking.status,
        )
    console.print(table)

    if _ask("¿Desea cancelar una reserva? (s/n)", "n").casefold() != "s":
        return
    booking_id = _ask("Código de reserva")
    booking = system.cancel_booking(booking_id, email)
    console.print(
        f"[green]Reserva cancelada. Reembolso calculado: "
        f"${booking.refund_amount:,.0f}.[/green]"
    )
    console.print(
        "La devolución efectiva depende del método de pago y se gestiona "
        "según la política del hotel."
    )


def write_review(system: BookingSystem) -> None:
    email = _ask("Correo electrónico del titular")
    bookings = [
        booking
        for booking in system.bookings_for_customer(email)
        if booking.status == "confirmed" and booking.check_out <= date.today()
    ]
    if not bookings:
        console.print("[yellow]No hay estancias completadas para reseñar.[/yellow]")
        return
    table = Table(title="Estancias completadas")
    table.add_column("Código")
    table.add_column("Hotel")
    table.add_column("Habitación")
    table.add_column("Salida")
    for booking in bookings:
        room = system.room_for_booking(booking)
        table.add_row(
            booking.id,
            system.hotel_for_room(room.id).name,
            room.name,
            booking.check_out.isoformat(),
        )
    console.print(table)
    booking_id = _ask("Código de reserva")
    system.add_review(
        booking_id,
        email,
        rating=_ask_int("Calificación de 1 a 5", minimum=1),
        comment=_ask("Comentario"),
    )
    console.print("[green]Gracias por compartir su experiencia.[/green]")


def find_hotel(system: BookingSystem) -> None:
    query = _ask("Ciudad o nombre del hotel").casefold()
    hotels = [
        hotel
        for hotel in system.hotels.values()
        if hotel.active
        and (query in hotel.name.casefold() or query in hotel.location.casefold())
    ]
    if not hotels:
        console.print("[yellow]No se encontraron hoteles activos.[/yellow]")
        return
    for index, hotel in enumerate(hotels, start=1):
        console.print(f"{index}. {hotel.name} — {hotel.location}")
    selection = _ask("Número del hotel para ver detalles (0 para volver)")
    if selection.isdigit() and 1 <= int(selection) <= len(hotels):
        _show_hotel_details(system, hotels[int(selection) - 1])


def register_hotel(system: BookingSystem) -> None:
    hotel = system.register_hotel(
        name=_ask("Nombre del hotel"),
        address=_ask("Dirección"),
        phone=_ask("Teléfono"),
        email=_ask("Correo electrónico"),
        location=_ask("Ciudad o ubicación"),
        description=_ask("Descripción"),
        services=_ask_list("Servicios del hotel"),
        photos=_ask_list("Rutas o enlaces de fotos"),
        payment_policy=_ask("Política de pago", "Pago al llegar."),
        cancellation_policy=_ask(
            "Política de cancelación",
            "Cancelación gratuita hasta 3 días antes.",
        ),
        free_cancellation_days=_ask_int(
            "Días mínimos para reembolso completo", minimum=0
        ),
        late_cancellation_fee_percent=_ask_float(
            "Penalidad por cancelación tardía (%)", minimum=0
        ),
    )
    console.print(f"[green]Hotel registrado.[/green] ID: {hotel.id}")
    if _ask("¿Desea agregar una habitación? (s/n)", "s").casefold() == "s":
        register_room(system, hotel.id)


def register_room(system: BookingSystem, hotel_id: str | None = None) -> None:
    if hotel_id is None:
        hotels = [hotel for hotel in system.hotels.values() if hotel.active]
        if not hotels:
            console.print("[yellow]Registre primero un hotel activo.[/yellow]")
            return
        for index, hotel in enumerate(hotels, start=1):
            console.print(f"{index}. {hotel.name} — {hotel.location} ({hotel.id})")
        selection = _ask_int("Número del hotel", minimum=1)
        if selection > len(hotels):
            raise BookingError("La selección no corresponde a un hotel de la lista.")
        hotel_id = hotels[selection - 1].id
    room = system.add_room(
        hotel_id=hotel_id,
        name=_ask("Nombre o número de habitación"),
        room_type=_ask("Tipo de habitación"),
        description=_ask("Descripción"),
        nightly_rate=_ask_float("Precio base por persona y noche", minimum=0.01),
        capacity=_ask_int("Capacidad máxima", minimum=1),
        services=_ask_list("Servicios incluidos"),
        photos=_ask_list("Rutas o enlaces de fotos"),
    )
    console.print(f"[green]Habitación registrada.[/green] ID: {room.id}")


def change_activity(system: BookingSystem) -> None:
    choice = _ask("¿Cambiar estado de (1) hotel o (2) habitación?")
    if choice == "1":
        for hotel in system.hotels.values():
            console.print(
                f"{hotel.id} — {hotel.name} "
                f"({'activo' if hotel.active else 'inactivo'})"
            )
        hotel_id = _ask("ID del hotel")
        hotel = system.hotels.get(hotel_id)
        if hotel is None:
            raise BookingError("No existe el hotel.")
        system.set_hotel_active(hotel_id, not hotel.active)
        console.print("[green]Estado del hotel actualizado.[/green]")
    elif choice == "2":
        for room in system.rooms.values():
            hotel = system.hotel_for_room(room.id)
            console.print(
                f"{room.id} — {hotel.name}, {room.name} "
                f"({'activa' if room.active else 'inactiva'})"
            )
        room_id = _ask("ID de la habitación")
        room = system.rooms.get(room_id)
        if room is None:
            raise BookingError("No existe la habitación.")
        system.set_room_active(room_id, not room.active)
        console.print("[green]Estado de la habitación actualizado.[/green]")
    else:
        raise BookingError("Seleccione 1 para hotel o 2 para habitación.")


def add_pricing_rule(system: BookingSystem) -> None:
    hotels = list(system.hotels.values())
    if not hotels:
        console.print("[yellow]Registre primero un hotel.[/yellow]")
        return
    for hotel in hotels:
        console.print(f"{hotel.id} — {hotel.name}")
    hotel_id = _ask("ID del hotel")
    kind = _ask("¿Agregar temporada (1), promoción (2) o política de cancelación (3)?")
    name = _ask("Nombre")
    if kind == "1":
        start_date = _ask_date("Fecha inicial")
        end_date = _ask_date("Fecha final exclusiva")
        system.add_seasonal_rate(
            hotel_id,
            name,
            start_date,
            end_date,
            _ask_float("Multiplicador de tarifa (por ejemplo 1.2)", minimum=0.01),
        )
        console.print("[green]Temporada registrada.[/green]")
    elif kind == "2":
        start_date = _ask_date("Fecha inicial")
        end_date = _ask_date("Fecha final exclusiva")
        system.add_offer(
            hotel_id,
            name,
            start_date,
            end_date,
            _ask_float("Descuento (%)", minimum=0),
            _ask("Descripción", ""),
        )
        console.print("[green]Promoción registrada.[/green]")
    elif kind == "3":
        room_type = _ask("Tipo de habitación (vacío para todos los tipos)") or None
        start_date = _ask_optional_date("Inicio de vigencia")
        end_date = _ask_optional_date("Fin de vigencia (exclusiva)")
        system.add_cancellation_rule(
            hotel_id,
            name,
            free_cancellation_days=_ask_int(
                "Días mínimos para reembolso completo", minimum=0
            ),
            late_cancellation_fee_percent=_ask_float(
                "Penalidad por cancelación tardía (%)", minimum=0
            ),
            room_type=room_type,
            start_date=start_date,
            end_date=end_date,
        )
        console.print("[green]Política de cancelación registrada.[/green]")
    else:
        raise BookingError("Seleccione 1 para temporada, 2 para promoción o 3 para política.")


def schedule_room_closure(system: BookingSystem) -> None:
    rooms = [room for room in system.rooms.values() if room.active]
    if not rooms:
        console.print("[yellow]No hay habitaciones activas.[/yellow]")
        return
    for room in rooms:
        hotel = system.hotel_for_room(room.id)
        console.print(f"{room.id} — {hotel.name}, {room.name}")
    room_id = _ask("ID de la habitación")
    closure = system.close_room(
        room_id,
        _ask_date("Fecha inicial del cierre"),
        _ask_date("Fecha final exclusiva del cierre"),
        _ask("Motivo (mantenimiento, remodelación, limpieza, etc.)"),
    )
    console.print(
        f"[green]Cierre programado del {closure.start_date} al "
        f"{closure.end_date} (fecha final exclusiva).[/green]"
    )


def _show_menu() -> None:
    console.print("\n[bold cyan]Sistema de reservas hoteleras[/bold cyan]")
    console.print("1. Buscar habitaciones y reservar")
    console.print("2. Consultar o cancelar reservas")
    console.print("3. Calificar una estancia")
    console.print("4. Consultar hoteles y comentarios")
    console.print("5. Registrar hotel")
    console.print("6. Agregar habitación")
    console.print("7. Activar o desactivar hotel/habitación")
    console.print("8. Configurar temporada, oferta o política de cancelación")
    console.print("9. Programar cierre de habitación por fechas")
    console.print("0. Salir")


def main() -> None:
    system = BookingSystem(DATA_FILE)
    actions = {
        "1": search_and_book,
        "2": show_bookings,
        "3": write_review,
        "4": find_hotel,
        "5": register_hotel,
        "6": register_room,
        "7": change_activity,
        "8": add_pricing_rule,
        "9": schedule_room_closure,
    }
    while True:
        _show_menu()
        choice = _ask("Seleccione una opción")
        if choice == "0":
            console.print("¡Gracias por usar el sistema!")
            return
        action = actions.get(choice)
        if action is None:
            console.print("[red]Opción no válida.[/red]")
            continue
        try:
            action(system)
        except (BookingError, ValueError, OSError) as error:
            console.print(f"[red]No se pudo completar la operación: {error}[/red]")


if __name__ == "__main__":
    main()
