"""Domain services for the hotel reservation system."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from math import isfinite
from pathlib import Path
from typing import Any
from uuid import uuid4


class BookingError(ValueError):
    """Raised when a requested hotel operation violates a business rule."""


@dataclass
class Hotel:
    id: str
    name: str
    address: str
    phone: str
    email: str
    location: str
    description: str
    services: list[str] = field(default_factory=list)
    photos: list[str] = field(default_factory=list)
    active: bool = True
    payment_policy: str = "Pago al llegar."
    cancellation_policy: str = "Cancelación gratuita hasta 3 días antes."
    free_cancellation_days: int = 3
    late_cancellation_fee_percent: float = 50.0


@dataclass
class Room:
    id: str
    hotel_id: str
    name: str
    room_type: str
    description: str
    nightly_rate: float
    capacity: int
    services: list[str] = field(default_factory=list)
    photos: list[str] = field(default_factory=list)
    active: bool = True


@dataclass
class Customer:
    id: str
    full_name: str
    phone: str
    email: str
    address: str


@dataclass
class SeasonalRate:
    id: str
    hotel_id: str
    name: str
    start_date: date
    end_date: date
    multiplier: float


@dataclass
class Offer:
    id: str
    hotel_id: str
    name: str
    start_date: date
    end_date: date
    discount_percent: float
    description: str = ""


@dataclass
class CancellationRule:
    id: str
    hotel_id: str
    name: str
    room_type: str | None
    start_date: date | None
    end_date: date | None
    free_cancellation_days: int
    late_cancellation_fee_percent: float


@dataclass
class Booking:
    id: str
    customer_id: str
    room_id: str
    check_in: date
    check_out: date
    guests: int
    total_price: float
    status: str = "confirmed"
    refund_amount: float | None = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class RoomClosure:
    id: str
    room_id: str
    start_date: date
    end_date: date
    reason: str


@dataclass
class Review:
    id: str
    booking_id: str
    hotel_id: str
    room_id: str
    customer_id: str
    rating: int
    comment: str
    created_at: datetime = field(default_factory=datetime.now)


class BookingSystem:
    """Manage hotel inventory, guests, reservations, and reviews."""

    def __init__(self, data_path: str | Path | None = None, seed: bool = True):
        self.data_path = Path(data_path) if data_path is not None else None
        self.hotels: dict[str, Hotel] = {}
        self.rooms: dict[str, Room] = {}
        self.customers: dict[str, Customer] = {}
        self.seasonal_rates: dict[str, SeasonalRate] = {}
        self.offers: dict[str, Offer] = {}
        self.cancellation_rules: dict[str, CancellationRule] = {}
        self.room_closures: dict[str, RoomClosure] = {}
        self.bookings: dict[str, Booking] = {}
        self.reviews: dict[str, Review] = {}

        if self.data_path is not None and self.data_path.exists():
            self._load()
        elif seed:
            self._seed_demo_data()
            self._save()

    def register_hotel(
        self,
        name: str,
        address: str,
        phone: str,
        email: str,
        location: str,
        description: str,
        services: list[str] | None = None,
        photos: list[str] | None = None,
        payment_policy: str = "Pago al llegar.",
        cancellation_policy: str = "Cancelación gratuita hasta 3 días antes.",
        free_cancellation_days: int = 3,
        late_cancellation_fee_percent: float = 50.0,
    ) -> Hotel:
        self._require_text(name, "El nombre del hotel")
        self._require_text(location, "La ubicación")
        if free_cancellation_days < 0:
            raise BookingError("Los días de cancelación gratuita no pueden ser negativos.")
        if not 0 <= late_cancellation_fee_percent <= 100:
            raise BookingError("La penalidad debe estar entre 0 y 100 por ciento.")

        hotel = Hotel(
            id=self._new_id(),
            name=name.strip(),
            address=address.strip(),
            phone=phone.strip(),
            email=email.strip().lower(),
            location=location.strip(),
            description=description.strip(),
            services=self._clean_list(services),
            photos=self._clean_list(photos),
            payment_policy=payment_policy.strip(),
            cancellation_policy=cancellation_policy.strip(),
            free_cancellation_days=free_cancellation_days,
            late_cancellation_fee_percent=late_cancellation_fee_percent,
        )
        self.hotels[hotel.id] = hotel
        self._save()
        return hotel

    def add_room(
        self,
        hotel_id: str,
        name: str,
        room_type: str,
        description: str,
        nightly_rate: float,
        capacity: int,
        services: list[str] | None = None,
        photos: list[str] | None = None,
    ) -> Room:
        hotel = self._get(self.hotels, hotel_id, "No existe el hotel.")
        self._require_text(name, "El nombre de la habitación")
        if not isfinite(nightly_rate) or nightly_rate <= 0:
            raise BookingError("La tarifa por noche debe ser mayor que cero.")
        if capacity < 1:
            raise BookingError("La capacidad debe ser al menos una persona.")

        room = Room(
            id=self._new_id(),
            hotel_id=hotel.id,
            name=name.strip(),
            room_type=room_type.strip(),
            description=description.strip(),
            nightly_rate=round(float(nightly_rate), 2),
            capacity=capacity,
            services=self._clean_list(services),
            photos=self._clean_list(photos),
        )
        self.rooms[room.id] = room
        self._save()
        return room

    def register_customer(
        self, full_name: str, phone: str, email: str, address: str
    ) -> Customer:
        self._require_text(full_name, "El nombre del cliente")
        self._require_text(email, "El correo electrónico")
        normalized_email = email.strip().lower()
        existing = next(
            (
                customer
                for customer in self.customers.values()
                if customer.email == normalized_email
            ),
            None,
        )
        if existing is not None:
            existing.full_name = full_name.strip()
            existing.phone = phone.strip()
            existing.address = address.strip()
            self._save()
            return existing

        customer = Customer(
            id=self._new_id(),
            full_name=full_name.strip(),
            phone=phone.strip(),
            email=normalized_email,
            address=address.strip(),
        )
        self.customers[customer.id] = customer
        self._save()
        return customer

    def set_hotel_active(self, hotel_id: str, active: bool) -> None:
        hotel = self._get(self.hotels, hotel_id, "No existe el hotel.")
        hotel.active = active
        self._save()

    def set_room_active(self, room_id: str, active: bool) -> None:
        room = self._get(self.rooms, room_id, "No existe la habitación.")
        room.active = active
        self._save()

    def close_room(
        self, room_id: str, start_date: date, end_date: date, reason: str
    ) -> RoomClosure:
        room = self._get(self.rooms, room_id, "No existe la habitación.")
        self._validate_date_range(start_date, end_date)
        self._require_text(reason, "El motivo del cierre")
        if any(
            booking.room_id == room.id
            and booking.status == "confirmed"
            and self._overlaps(
                start_date, end_date, booking.check_in, booking.check_out
            )
            for booking in self.bookings.values()
        ):
            raise BookingError(
                "No se puede cerrar la habitación durante una reserva confirmada."
            )
        closure = RoomClosure(
            id=self._new_id(),
            room_id=room.id,
            start_date=start_date,
            end_date=end_date,
            reason=reason.strip(),
        )
        self.room_closures[closure.id] = closure
        self._save()
        return closure

    def add_seasonal_rate(
        self,
        hotel_id: str,
        name: str,
        start_date: date,
        end_date: date,
        multiplier: float,
    ) -> SeasonalRate:
        hotel = self._get(self.hotels, hotel_id, "No existe el hotel.")
        self._validate_date_range(start_date, end_date)
        if not isfinite(multiplier) or multiplier <= 0:
            raise BookingError("El factor de temporada debe ser mayor que cero.")
        for season in self.seasonal_rates.values():
            if season.hotel_id == hotel.id and self._overlaps(
                start_date, end_date, season.start_date, season.end_date
            ):
                raise BookingError("Las temporadas de un hotel no pueden superponerse.")

        season = SeasonalRate(
            id=self._new_id(),
            hotel_id=hotel.id,
            name=name.strip(),
            start_date=start_date,
            end_date=end_date,
            multiplier=float(multiplier),
        )
        self.seasonal_rates[season.id] = season
        self._save()
        return season

    def add_offer(
        self,
        hotel_id: str,
        name: str,
        start_date: date,
        end_date: date,
        discount_percent: float,
        description: str = "",
    ) -> Offer:
        hotel = self._get(self.hotels, hotel_id, "No existe el hotel.")
        self._validate_date_range(start_date, end_date)
        if not isfinite(discount_percent) or not 0 <= discount_percent <= 100:
            raise BookingError("El descuento debe estar entre 0 y 100 por ciento.")
        offer = Offer(
            id=self._new_id(),
            hotel_id=hotel.id,
            name=name.strip(),
            start_date=start_date,
            end_date=end_date,
            discount_percent=float(discount_percent),
            description=description.strip(),
        )
        self.offers[offer.id] = offer
        self._save()
        return offer

    def add_cancellation_rule(
        self,
        hotel_id: str,
        name: str,
        free_cancellation_days: int,
        late_cancellation_fee_percent: float,
        room_type: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> CancellationRule:
        hotel = self._get(self.hotels, hotel_id, "No existe el hotel.")
        self._require_text(name, "El nombre de la política")
        if (start_date is None) != (end_date is None):
            raise BookingError(
                "Debe indicar ambas fechas de vigencia o dejar ambas vacías."
            )
        if start_date is not None and end_date is not None:
            self._validate_date_range(start_date, end_date)
        if free_cancellation_days < 0:
            raise BookingError("Los días de cancelación gratuita no pueden ser negativos.")
        if (
            not isfinite(late_cancellation_fee_percent)
            or not 0 <= late_cancellation_fee_percent <= 100
        ):
            raise BookingError("La penalidad debe estar entre 0 y 100 por ciento.")

        normalized_room_type = room_type.strip().casefold() if room_type else None
        if not normalized_room_type:
            normalized_room_type = None
        for existing in self.cancellation_rules.values():
            if (
                existing.hotel_id == hotel.id
                and (existing.room_type or None) == normalized_room_type
                and (existing.start_date is None) == (start_date is None)
                and self._date_ranges_overlap(
                    start_date,
                    end_date,
                    existing.start_date,
                    existing.end_date,
                )
            ):
                raise BookingError(
                    "Ya existe una política equivalente con fechas superpuestas."
                )
        rule = CancellationRule(
            id=self._new_id(),
            hotel_id=hotel.id,
            name=name.strip(),
            room_type=normalized_room_type,
            start_date=start_date,
            end_date=end_date,
            free_cancellation_days=free_cancellation_days,
            late_cancellation_fee_percent=late_cancellation_fee_percent,
        )
        self.cancellation_rules[rule.id] = rule
        self._save()
        return rule

    def search_rooms(
        self,
        check_in: date,
        check_out: date,
        guests: int,
        location: str = "",
        minimum_rating: float = 0,
        maximum_nightly_rate: float | None = None,
    ) -> list[dict[str, Any]]:
        self._validate_stay(check_in, check_out, guests)
        if not isfinite(minimum_rating) or not 0 <= minimum_rating <= 5:
            raise BookingError("La calificación mínima debe estar entre 0 y 5.")
        if maximum_nightly_rate is not None and (
            not isfinite(maximum_nightly_rate) or maximum_nightly_rate < 0
        ):
            raise BookingError("El precio máximo debe ser un número válido no negativo.")
        search_location = location.strip().casefold()
        matches = []
        for room in self.rooms.values():
            hotel = self.hotels.get(room.hotel_id)
            if (
                not room.active
                or room.capacity < guests
                or hotel is None
                or not hotel.active
                or (
                    search_location
                    and search_location not in hotel.location.casefold()
                    and search_location not in hotel.name.casefold()
                )
                or self._hotel_rating(hotel.id) < minimum_rating
                or not self._is_available(room.id, check_in, check_out)
            ):
                continue
            if (
                maximum_nightly_rate is not None
                and max(
                    self._nightly_price(
                        room, check_in + timedelta(days=offset)
                    )
                    * guests
                    for offset in range((check_out - check_in).days)
                )
                > maximum_nightly_rate
            ):
                continue
            nightly = self._nightly_price(room, check_in)
            matches.append(
                {
                    "hotel": hotel,
                    "room": room,
                    "nightly_rate": nightly,
                    "total_price": self.quote(room.id, check_in, check_out, guests),
                    "hotel_rating": self._hotel_rating(hotel.id),
                    "room_rating": self._room_rating(room.id),
                }
            )
        return sorted(matches, key=lambda match: match["total_price"])

    def quote(
        self, room_id: str, check_in: date, check_out: date, guests: int
    ) -> float:
        room = self._get(self.rooms, room_id, "No existe la habitación.")
        self._validate_stay(check_in, check_out, guests)
        if guests > room.capacity:
            raise BookingError("La cantidad de huéspedes supera la capacidad.")
        total = sum(
            self._nightly_price(room, check_in + timedelta(days=offset)) * guests
            for offset in range((check_out - check_in).days)
        )
        return round(total, 2)

    def create_booking(
        self,
        customer_id: str,
        room_id: str,
        check_in: date,
        check_out: date,
        guests: int,
    ) -> Booking:
        customer = self._get(
            self.customers, customer_id, "No existe el cliente registrado."
        )
        room = self._get(self.rooms, room_id, "No existe la habitación.")
        hotel = self._get(self.hotels, room.hotel_id, "No existe el hotel.")
        self._validate_stay(check_in, check_out, guests)
        if not hotel.active:
            raise BookingError("El hotel está inactivo y no acepta reservas.")
        if not room.active:
            raise BookingError("La habitación está inactiva y no acepta reservas.")
        if guests > room.capacity:
            raise BookingError("La cantidad de huéspedes supera la capacidad.")
        if not self._is_available(room.id, check_in, check_out):
            raise BookingError("La habitación no está disponible en esas fechas.")

        booking = Booking(
            id=self._new_id(),
            customer_id=customer.id,
            room_id=room.id,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            total_price=self.quote(room.id, check_in, check_out, guests),
        )
        self.bookings[booking.id] = booking
        self._save()
        return booking

    def cancel_booking(
        self, booking_id: str, customer_email: str, today: date | None = None
    ) -> Booking:
        booking = self._get(self.bookings, booking_id, "No existe la reserva.")
        customer = self._get(
            self.customers, booking.customer_id, "No existe el cliente de la reserva."
        )
        if customer.email != customer_email.strip().lower():
            raise BookingError("El correo no corresponde al titular de la reserva.")
        if booking.status != "confirmed":
            raise BookingError("La reserva ya fue cancelada.")

        hotel = self.hotels[self.rooms[booking.room_id].hotel_id]
        cancellation_date = today or date.today()
        if cancellation_date >= booking.check_in:
            raise BookingError("No se puede cancelar una estancia que ya comenzó.")
        remaining_days = (booking.check_in - cancellation_date).days
        room = self.rooms[booking.room_id]
        cancellation_rule = self._cancellation_rule_for(room, booking.check_in)
        free_days = (
            cancellation_rule.free_cancellation_days
            if cancellation_rule is not None
            else hotel.free_cancellation_days
        )
        fee_percent = (
            cancellation_rule.late_cancellation_fee_percent
            if cancellation_rule is not None
            else hotel.late_cancellation_fee_percent
        )
        if remaining_days >= free_days:
            fee_percent = 0
        booking.status = "cancelled"
        booking.refund_amount = round(
            booking.total_price * (1 - fee_percent / 100), 2
        )
        self._save()
        return booking

    def add_review(
        self,
        booking_id: str,
        customer_email: str,
        rating: int,
        comment: str,
        today: date | None = None,
    ) -> Review:
        booking = self._get(self.bookings, booking_id, "No existe la reserva.")
        customer = self._get(
            self.customers, booking.customer_id, "No existe el cliente de la reserva."
        )
        if customer.email != customer_email.strip().lower():
            raise BookingError("El correo no corresponde al titular de la reserva.")
        if booking.status != "confirmed":
            raise BookingError("Solo se pueden reseñar reservas completadas.")
        if booking.check_out > (today or date.today()):
            raise BookingError("La reseña se habilita después de la salida.")
        if not 1 <= rating <= 5:
            raise BookingError("La calificación debe estar entre 1 y 5.")
        if not comment.strip():
            raise BookingError("El comentario no puede estar vacío.")
        if any(review.booking_id == booking.id for review in self.reviews.values()):
            raise BookingError("Esta reserva ya tiene una reseña.")

        room = self.rooms[booking.room_id]
        review = Review(
            id=self._new_id(),
            booking_id=booking.id,
            hotel_id=room.hotel_id,
            room_id=room.id,
            customer_id=customer.id,
            rating=rating,
            comment=comment.strip(),
        )
        self.reviews[review.id] = review
        self._save()
        return review

    def hotel_reviews(self, hotel_id: str) -> list[Review]:
        self._get(self.hotels, hotel_id, "No existe el hotel.")
        return [
            review for review in self.reviews.values() if review.hotel_id == hotel_id
        ]

    def room_reviews(self, room_id: str) -> list[Review]:
        self._get(self.rooms, room_id, "No existe la habitación.")
        return [review for review in self.reviews.values() if review.room_id == room_id]

    def bookings_for_customer(self, email: str) -> list[Booking]:
        normalized_email = email.strip().lower()
        customer = next(
            (
                customer
                for customer in self.customers.values()
                if customer.email == normalized_email
            ),
            None,
        )
        if customer is None:
            return []
        return sorted(
            (
                booking
                for booking in self.bookings.values()
                if booking.customer_id == customer.id
            ),
            key=lambda booking: booking.check_in,
        )

    def hotel_rating(self, hotel_id: str) -> float:
        self._get(self.hotels, hotel_id, "No existe el hotel.")
        return self._hotel_rating(hotel_id)

    def room_rating(self, room_id: str) -> float:
        self._get(self.rooms, room_id, "No existe la habitación.")
        return self._room_rating(room_id)

    def customer(self, customer_id: str) -> Customer:
        return self._get(self.customers, customer_id, "No existe el cliente.")

    def find_customer_by_email(self, email: str) -> Customer | None:
        normalized_email = email.strip().lower()
        return next(
            (
                customer
                for customer in self.customers.values()
                if customer.email == normalized_email
            ),
            None,
        )

    def hotel_for_room(self, room_id: str) -> Hotel:
        room = self._get(self.rooms, room_id, "No existe la habitación.")
        return self._get(self.hotels, room.hotel_id, "No existe el hotel.")

    def room_for_booking(self, booking: Booking) -> Room:
        return self._get(self.rooms, booking.room_id, "No existe la habitación.")

    def _is_available(self, room_id: str, check_in: date, check_out: date) -> bool:
        has_booking = any(
            booking.room_id == room_id
            and booking.status == "confirmed"
            and self._overlaps(check_in, check_out, booking.check_in, booking.check_out)
            for booking in self.bookings.values()
        )
        has_closure = any(
            closure.room_id == room_id
            and self._overlaps(
                check_in, check_out, closure.start_date, closure.end_date
            )
            for closure in self.room_closures.values()
        )
        return not has_booking and not has_closure

    def _cancellation_rule_for(
        self, room: Room, check_in: date
    ) -> CancellationRule | None:
        matching = [
            rule
            for rule in self.cancellation_rules.values()
            if rule.hotel_id == room.hotel_id
            and (rule.room_type is None or rule.room_type == room.room_type.casefold())
            and (
                rule.start_date is None
                or (
                    rule.end_date is not None
                    and rule.start_date <= check_in < rule.end_date
                )
            )
        ]
        return max(
            matching,
            key=lambda rule: (
                rule.room_type is not None,
                rule.start_date is not None,
            ),
            default=None,
        )

    def _nightly_price(self, room: Room, day: date) -> float:
        hotel = self.hotels[room.hotel_id]
        multiplier = next(
            (
                season.multiplier
                for season in self.seasonal_rates.values()
                if season.hotel_id == hotel.id
                and season.start_date <= day < season.end_date
            ),
            1.0,
        )
        discount = max(
            (
                offer.discount_percent
                for offer in self.offers.values()
                if offer.hotel_id == hotel.id
                and offer.start_date <= day < offer.end_date
            ),
            default=0.0,
        )
        return round(room.nightly_rate * multiplier * (1 - discount / 100), 2)

    def _hotel_rating(self, hotel_id: str) -> float:
        ratings = [
            review.rating
            for review in self.reviews.values()
            if review.hotel_id == hotel_id
        ]
        return round(sum(ratings) / len(ratings), 1) if ratings else 0.0

    def _room_rating(self, room_id: str) -> float:
        ratings = [
            review.rating
            for review in self.reviews.values()
            if review.room_id == room_id
        ]
        return round(sum(ratings) / len(ratings), 1) if ratings else 0.0

    def _seed_demo_data(self) -> None:
        hotel = self.register_hotel(
            name="Hotel Central",
            address="Calle 10 # 5-20",
            phone="555-0100",
            email="reservas@hotelcentral.example",
            location="Bogotá",
            description="Hotel de ejemplo para explorar y probar el sistema.",
            services=["restaurante", "wifi", "gimnasio"],
            payment_policy="Pago al llegar o anticipado.",
            cancellation_policy="Reembolso completo con al menos 3 días de anticipación.",
        )
        self.add_room(
            hotel.id,
            "Habitación 101",
            "Doble",
            "Habitación para dos huéspedes con baño privado.",
            180_000,
            2,
            ["wifi", "desayuno"],
        )
        self.add_room(
            hotel.id,
            "Habitación 201",
            "Familiar",
            "Habitación amplia para familias.",
            280_000,
            4,
            ["wifi", "desayuno", "minibar"],
        )

    def _save(self) -> None:
        if self.data_path is None:
            return
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "hotels": self.hotels,
            "rooms": self.rooms,
            "customers": self.customers,
            "seasonal_rates": self.seasonal_rates,
            "offers": self.offers,
            "cancellation_rules": self.cancellation_rules,
            "room_closures": self.room_closures,
            "bookings": self.bookings,
            "reviews": self.reviews,
        }
        encoded = json.dumps(
            data,
            default=self._json_default,
            ensure_ascii=False,
            indent=2,
        )
        temporary_path = self.data_path.with_suffix(self.data_path.suffix + ".tmp")
        temporary_path.write_text(encoded, encoding="utf-8")
        temporary_path.replace(self.data_path)

    def _load(self) -> None:
        if self.data_path is None:
            return
        data = json.loads(self.data_path.read_text(encoding="utf-8"))
        self.hotels = {
            key: Hotel(**value) for key, value in data.get("hotels", {}).items()
        }
        self.rooms = {key: Room(**value) for key, value in data.get("rooms", {}).items()}
        self.customers = {
            key: Customer(**value) for key, value in data.get("customers", {}).items()
        }
        self.seasonal_rates = {
            key: SeasonalRate(
                **{**value, "start_date": date.fromisoformat(value["start_date"]),
                   "end_date": date.fromisoformat(value["end_date"])}
            )
            for key, value in data.get("seasonal_rates", {}).items()
        }
        self.offers = {
            key: Offer(
                **{**value, "start_date": date.fromisoformat(value["start_date"]),
                   "end_date": date.fromisoformat(value["end_date"])}
            )
            for key, value in data.get("offers", {}).items()
        }
        self.cancellation_rules = {
            key: CancellationRule(
                **{
                    **value,
                    "start_date": (
                        date.fromisoformat(value["start_date"])
                        if value["start_date"]
                        else None
                    ),
                    "end_date": (
                        date.fromisoformat(value["end_date"])
                        if value["end_date"]
                        else None
                    ),
                }
            )
            for key, value in data.get("cancellation_rules", {}).items()
        }
        self.room_closures = {
            key: RoomClosure(
                **{**value, "start_date": date.fromisoformat(value["start_date"]),
                   "end_date": date.fromisoformat(value["end_date"])}
            )
            for key, value in data.get("room_closures", {}).items()
        }
        self.bookings = {
            key: Booking(
                **{
                    **value,
                    "check_in": date.fromisoformat(value["check_in"]),
                    "check_out": date.fromisoformat(value["check_out"]),
                    "created_at": datetime.fromisoformat(value["created_at"]),
                }
            )
            for key, value in data.get("bookings", {}).items()
        }
        self.reviews = {
            key: Review(
                **{**value, "created_at": datetime.fromisoformat(value["created_at"])}
            )
            for key, value in data.get("reviews", {}).items()
        }

    @staticmethod
    def _json_default(value: Any) -> Any:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if hasattr(value, "__dataclass_fields__"):
            return asdict(value)
        raise TypeError(f"No se puede guardar un valor de tipo {type(value).__name__}.")

    @staticmethod
    def _new_id() -> str:
        return uuid4().hex[:12]

    @staticmethod
    def _clean_list(values: list[str] | None) -> list[str]:
        return [value.strip() for value in values or [] if value.strip()]

    @staticmethod
    def _require_text(value: str, label: str) -> None:
        if not value or not value.strip():
            raise BookingError(f"{label} es obligatorio.")

    @staticmethod
    def _get(items: dict[str, Any], item_id: str, message: str) -> Any:
        try:
            return items[item_id]
        except KeyError as error:
            raise BookingError(message) from error

    @staticmethod
    def _validate_date_range(start_date: date, end_date: date) -> None:
        if end_date <= start_date:
            raise BookingError("La fecha final debe ser posterior a la fecha inicial.")

    @classmethod
    def _validate_stay(cls, check_in: date, check_out: date, guests: int) -> None:
        cls._validate_date_range(check_in, check_out)
        if guests < 1:
            raise BookingError("La reserva debe incluir al menos un huésped.")

    @staticmethod
    def _overlaps(start_a: date, end_a: date, start_b: date, end_b: date) -> bool:
        return start_a < end_b and start_b < end_a

    @staticmethod
    def _date_ranges_overlap(
        start_a: date | None,
        end_a: date | None,
        start_b: date | None,
        end_b: date | None,
    ) -> bool:
        if (
            start_a is None
            or end_a is None
            or start_b is None
            or end_b is None
        ):
            return True
        return BookingSystem._overlaps(start_a, end_a, start_b, end_b)
