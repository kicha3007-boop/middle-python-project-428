import "@typespec/http";
import "@typespec/openapi";

using TypeSpec.Http;
using TypeSpec.OpenAPI;

/** API сервиса бронирования авиабилетов. Фронтенд и API отвечают на одном порту, API — под /api. */
@service(#{ title: "Flight Booking API" })
@info(#{ version: "1.0.0" })
@server("http://localhost:8080", "Локальный запуск: фронтенд и API на одном порту")
namespace FlightBookingApi;

// ---------- Модели ----------

/** Город (аэропорт) из справочника. */
model City {
  /** IATA-подобный код: MOW, LED. */
  code: string;

  /** Название на русском. */
  name: string;

  country?: string;
}

/** Денежная сумма в целых рублях. */
model Money {
  amount: int32;
  currency: string = "RUB";
}

/** Авиакомпания. */
model Airline {
  code: string;
  name: string;
}

/** Рейс: результат поиска и предмет бронирования. */
model Flight {
  /** Идентификатор рейса; попадает в адрес /booking/{id}, поэтому без пробелов и слешей. */
  id: string;

  flightNumber: string;
  airline: Airline;
  origin: City;
  destination: City;

  /** Время вылета в UTC, ISO 8601 с Z. */
  departureAt: utcDateTime;

  /** Время прилёта в UTC, ISO 8601 с Z. */
  arrivalAt: utcDateTime;

  durationMinutes: int32;

  /** Цена за одного пассажира. */
  price: Money;

  seatsAvailable: int32;
}

/** Пассажир брони. */
model Passenger {
  firstName: string;
  lastName: string;
  dateOfBirth: plainDate;
  documentNumber: string;
}

/** Контакт заказчика брони. */
model Contact {
  email: string;
  phone: string;
}

/** Статус брони. */
enum BookingStatus {
  confirmed,
  cancelled,
}

/** Бронь. */
model Booking {
  /** Код брони: ровно 6 символов из A-Z и 0-9. */
  @pattern("^[A-Z0-9]{6}$")
  code: string;

  status: BookingStatus;
  flight: Flight;
  passengers: Passenger[];
  contact: Contact;

  /** Итоговая стоимость: цена рейса × число пассажиров. Считает сервер. */
  totalPrice: Money;

  createdAt: utcDateTime;
}

/** Тело запроса на создание брони. */
model CreateBookingRequest {
  flightId: string;
  contact: Contact;

  /** Минимум один пассажир. */
  @minItems(1)
  passengers: Passenger[];
}

/** Второй фактор доступа к брони при отмене. */
model LastNameBody {
  /** Фамилия любого пассажира брони. Отсутствующая или неверная даёт 404, а не 400. */
  lastName?: string;
}

/** Ответ хелсчека. */
model Health {
  status: "ok";
}

/** Некорректные параметры запроса или тело. */
@error
model BadRequestError {
  @statusCode statusCode: 400;
  code: "validation_error";
  message: string;
}

/** Ресурс не найден. */
@error
model NotFoundError {
  @statusCode statusCode: 404;
  code: "not_found";
  message: string;
}

// ---------- Эндпоинты ----------

@route("/api/health")
@tag("Reference")
interface HealthCheck {
  /** Хелсчек: 200, пока приложение отвечает. База не проверяется. */
  @get check(): Health;
}

@route("/api/cities")
@tag("Reference")
interface Cities {
  /** Справочник городов. Москва и Санкт-Петербург идут первыми. */
  @get list(): City[];
}

@route("/api/flights")
@tag("Flights")
interface Flights {
  /** Поиск рейсов по городам, дате вылета и числу свободных мест. Пустой результат — 200 и []. */
  @get search(
    @query origin: string,
    @query destination: string,
    @query date: plainDate,
    @query passengers?: int32 = 1,
  ): Flight[] | BadRequestError;

  /** Рейс по идентификатору — в том же виде, что в поиске. */
  @get
  @route("/{id}")
  getById(@path id: string): Flight | NotFoundError;
}

@route("/api/bookings")
@tag("Bookings")
interface Bookings {
  /** Создать бронь. Пустой список пассажиров, пустое поле, неизвестный flightId — 400. */
  @post create(@body body: CreateBookingRequest): {
    @statusCode statusCode: 201;
    @body booking: Booking;
  } | BadRequestError;

  /**
   * Просмотр брони по коду и фамилии любого пассажира (без учёта регистра и внешних пробелов).
   * Неверный код, неверная или отсутствующая фамилия — одинаковый 404.
   */
  @get
  @route("/{code}")
  getByCode(@path code: string, @query lastName?: string): Booking | NotFoundError;

  /** Отмена брони: бронь не удаляется, status становится cancelled. Повторная отмена допустима. */
  @post
  @route("/{code}/cancel")
  cancel(@path code: string, @body body?: LastNameBody): Booking | NotFoundError;
}
