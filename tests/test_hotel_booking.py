import tempfile
import unittest
from datetime import date
from pathlib import Path

from hotel_booking import BookingError, BookingSystem


class BookingSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.system = BookingSystem(seed=False)
        self.hotel = self.system.register_hotel(
            name="Hotel Prueba",
            address="Calle 1",
            phone="555",
            email="hotel@example.com",
            location="Bogotá",
            description="Hotel para pruebas.",
            free_cancellation_days=3,
            late_cancellation_fee_percent=40,
        )
        self.room = self.system.add_room(
            self.hotel.id,
            "101",
            "Doble",
            "Habitación de prueba.",
            100,
            2,
        )
        self.customer = self.system.register_customer(
            "Ana Pérez", "300123", "ana@example.com", "Calle 2"
        )

    def test_booking_reserves_room_until_checkout(self) -> None:
        first = self.system.create_booking(
            self.customer.id,
            self.room.id,
            date(2027, 1, 10),
            date(2027, 1, 12),
            2,
        )
        self.assertEqual(first.total_price, 400)
        self.assertEqual(
            self.system.search_rooms(
                date(2027, 1, 11), date(2027, 1, 13), 1, "bogotá"
            ),
            [],
        )
        next_stay = self.system.create_booking(
            self.customer.id,
            self.room.id,
            date(2027, 1, 12),
            date(2027, 1, 13),
            1,
        )
        self.assertEqual(next_stay.total_price, 100)

    def test_rejects_invalid_stay_and_over_capacity(self) -> None:
        with self.assertRaises(BookingError):
            self.system.create_booking(
                self.customer.id,
                self.room.id,
                date(2027, 1, 12),
                date(2027, 1, 12),
                1,
            )
        with self.assertRaises(BookingError):
            self.system.create_booking(
                self.customer.id,
                self.room.id,
                date(2027, 1, 12),
                date(2027, 1, 13),
                3,
            )
        with self.assertRaises(BookingError):
            self.system.add_room(
                self.hotel.id,
                "102",
                "Doble",
                "Tarifa inválida.",
                float("nan"),
                2,
            )

    def test_search_price_limit_is_per_night_for_all_guests(self) -> None:
        dates = (date(2027, 1, 10), date(2027, 1, 11))
        self.assertEqual(
            self.system.search_rooms(*dates, 2, maximum_nightly_rate=199), []
        )
        self.assertEqual(
            len(self.system.search_rooms(*dates, 2, maximum_nightly_rate=200)), 1
        )
        self.system.add_seasonal_rate(
            self.hotel.id,
            "Temporada alta",
            date(2027, 1, 11),
            date(2027, 1, 12),
            2,
        )
        self.assertEqual(
            self.system.search_rooms(
                date(2027, 1, 10),
                date(2027, 1, 12),
                2,
                maximum_nightly_rate=300,
            ),
            [],
        )

    def test_inactive_hotel_and_room_are_not_searchable(self) -> None:
        check_in, check_out = date(2027, 1, 10), date(2027, 1, 11)
        self.assertEqual(len(self.system.search_rooms(check_in, check_out, 1)), 1)
        self.system.set_room_active(self.room.id, False)
        self.assertEqual(self.system.search_rooms(check_in, check_out, 1), [])
        self.system.set_room_active(self.room.id, True)
        self.system.set_hotel_active(self.hotel.id, False)
        self.assertEqual(self.system.search_rooms(check_in, check_out, 1), [])

    def test_room_closure_blocks_only_overlapping_dates(self) -> None:
        self.system.close_room(
            self.room.id,
            date(2027, 1, 10),
            date(2027, 1, 12),
            "Mantenimiento",
        )
        self.assertEqual(
            self.system.search_rooms(
                date(2027, 1, 11), date(2027, 1, 13), 1
            ),
            [],
        )
        self.assertEqual(
            len(
                self.system.search_rooms(
                    date(2027, 1, 12), date(2027, 1, 13), 1
                )
            ),
            1,
        )
        with self.assertRaises(BookingError):
            self.system.close_room(
                self.room.id,
                date(2027, 1, 12),
                date(2027, 1, 12),
                "Fechas inválidas",
            )

    def test_season_and_offer_are_applied_per_night(self) -> None:
        self.system.add_seasonal_rate(
            self.hotel.id,
            "Temporada alta",
            date(2027, 4, 2),
            date(2027, 4, 4),
            2,
        )
        self.system.add_offer(
            self.hotel.id,
            "Oferta de primavera",
            date(2027, 4, 3),
            date(2027, 4, 5),
            25,
        )
        total = self.system.quote(
            self.room.id, date(2027, 4, 1), date(2027, 4, 4), 2
        )
        self.assertEqual(total, 900)
        with self.assertRaises(BookingError):
            self.system.add_seasonal_rate(
                self.hotel.id,
                "Temporada superpuesta",
                date(2027, 4, 3),
                date(2027, 4, 6),
                1.5,
            )

    def test_cancellation_refund_obeys_hotel_policy(self) -> None:
        booking = self.system.create_booking(
            self.customer.id,
            self.room.id,
            date(2027, 1, 10),
            date(2027, 1, 12),
            1,
        )
        cancelled = self.system.cancel_booking(
            booking.id, self.customer.email, today=date(2027, 1, 8)
        )
        self.assertEqual(cancelled.refund_amount, 120)
        with self.assertRaises(BookingError):
            self.system.cancel_booking(
                booking.id, self.customer.email, today=date(2027, 1, 8)
            )
        with self.assertRaises(BookingError):
            self.system.cancel_booking(
                booking.id, "otra@example.com", today=date(2027, 1, 8)
            )

    def test_started_stay_cannot_be_cancelled(self) -> None:
        booking = self.system.create_booking(
            self.customer.id,
            self.room.id,
            date(2027, 1, 10),
            date(2027, 1, 12),
            1,
        )
        with self.assertRaises(BookingError):
            self.system.cancel_booking(
                booking.id, self.customer.email, today=date(2027, 1, 10)
            )

    def test_cancellation_rule_can_vary_by_room_type_and_season(self) -> None:
        self.system.add_cancellation_rule(
            self.hotel.id,
            "Política general doble",
            free_cancellation_days=7,
            late_cancellation_fee_percent=90,
            room_type="Doble",
        )
        self.system.add_cancellation_rule(
            self.hotel.id,
            "Temporada especial doble",
            free_cancellation_days=2,
            late_cancellation_fee_percent=40,
            room_type="Doble",
            start_date=date(2027, 1, 10),
            end_date=date(2027, 1, 20),
        )
        booking = self.system.create_booking(
            self.customer.id,
            self.room.id,
            date(2027, 1, 15),
            date(2027, 1, 16),
            1,
        )
        cancelled = self.system.cancel_booking(
            booking.id, self.customer.email, today=date(2027, 1, 14)
        )
        self.assertEqual(cancelled.refund_amount, 60)

    def test_review_is_only_allowed_after_completed_stay(self) -> None:
        booking = self.system.create_booking(
            self.customer.id,
            self.room.id,
            date(2027, 1, 10),
            date(2027, 1, 12),
            1,
        )
        with self.assertRaises(BookingError):
            self.system.add_review(
                booking.id,
                self.customer.email,
                5,
                "Excelente.",
                today=date(2027, 1, 11),
            )
        review = self.system.add_review(
            booking.id,
            self.customer.email,
            5,
            "Excelente.",
            today=date(2027, 1, 12),
        )
        self.assertEqual(review.rating, 5)
        self.assertEqual(self.system.hotel_rating(self.hotel.id), 5)
        self.assertEqual(self.system.room_rating(self.room.id), 5)
        with self.assertRaises(BookingError):
            self.system.add_review(
                booking.id,
                self.customer.email,
                4,
                "Otra reseña.",
                today=date(2027, 1, 12),
            )

    def test_data_persists_between_system_instances(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_path = Path(directory) / "data" / "reservas.json"
            system = BookingSystem(data_path, seed=False)
            hotel = system.register_hotel(
                "Hotel Guardado",
                "Calle 3",
                "555",
                "guardado@example.com",
                "Cali",
                "Prueba de persistencia.",
            )
            room = system.add_room(
                hotel.id, "201", "Suite", "Suite guardada.", 250, 3
            )
            customer = system.register_customer(
                "Luis Gómez", "555", "luis@example.com", "Calle 4"
            )
            system.add_cancellation_rule(
                hotel.id,
                "Política para suites",
                free_cancellation_days=2,
                late_cancellation_fee_percent=25,
                room_type="Suite",
            )
            system.close_room(
                room.id,
                date(2027, 2, 5),
                date(2027, 2, 7),
                "Mantenimiento",
            )
            booking = system.create_booking(
                customer.id,
                room.id,
                date(2027, 2, 1),
                date(2027, 2, 3),
                2,
            )

            loaded = BookingSystem(data_path, seed=False)
            self.assertEqual(loaded.bookings[booking.id].total_price, 1000)
            self.assertEqual(loaded.hotels[hotel.id].name, "Hotel Guardado")
            self.assertEqual(loaded.customers[customer.id].email, "luis@example.com")
            self.assertEqual(len(loaded.cancellation_rules), 1)
            self.assertEqual(len(loaded.room_closures), 1)


if __name__ == "__main__":
    unittest.main()
