package domain

import "time"

type User struct {
	ID        int64     `json:"id"`
	Email     string    `json:"email"`
	FullName  string    `json:"full_name"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type Venue struct {
	ID        int64     `json:"id"`
	Name      string    `json:"name"`
	City      string    `json:"city"`
	Address   string    `json:"address"`
	Capacity  int       `json:"capacity"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type Event struct {
	ID        int64     `json:"id"`
	VenueID   int64     `json:"venue_id"`
	Title     string    `json:"title"`
	Status    string    `json:"status"`
	StartsAt  time.Time `json:"starts_at"`
	BasePrice int64     `json:"base_price"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type Category struct {
	ID        int64     `json:"id"`
	Name      string    `json:"name"`
	CreatedAt time.Time `json:"created_at"`
}

type Booking struct {
	ID        int64     `json:"id"`
	UserID    int64     `json:"user_id"`
	EventID   int64     `json:"event_id"`
	Status    string    `json:"status"`
	Seats     int       `json:"seats"`
	Total     int64     `json:"total"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type BookingDetails struct {
	Booking
	UserEmail  string    `json:"user_email"`
	EventTitle string    `json:"event_title"`
	VenueName  string    `json:"venue_name"`
	VenueCity  string    `json:"venue_city"`
	StartsAt   time.Time `json:"starts_at"`
}

type EventSummary struct {
	Event
	VenueName     string   `json:"venue_name"`
	VenueCity     string   `json:"venue_city"`
	Categories    []string `json:"categories"`
	BookingsCount int64    `json:"bookings_count"`
}

type EventStats struct {
	EventID      int64   `json:"event_id"`
	Bookings     int64   `json:"bookings"`
	Seats        int64   `json:"seats"`
	Revenue      int64   `json:"revenue"`
	AverageTotal float64 `json:"average_total"`
}
