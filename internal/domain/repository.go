package domain

import (
	"context"
	"time"
)

type BookingFilter struct {
	Page     int
	PageSize int
	Status   string
	UserID   int64
	EventID  int64
	From     *time.Time
	To       *time.Time
	Sort     string
}

type Repository interface {
	Ping(ctx context.Context) error

	CreateUser(ctx context.Context, user User) (User, error)
	ListUsers(ctx context.Context) ([]User, error)
	GetUser(ctx context.Context, id int64) (User, error)
	UpdateUser(ctx context.Context, id int64, user User) (User, error)
	DeleteUser(ctx context.Context, id int64) error

	CreateVenue(ctx context.Context, venue Venue) (Venue, error)
	ListVenues(ctx context.Context) ([]Venue, error)
	GetVenue(ctx context.Context, id int64) (Venue, error)
	UpdateVenue(ctx context.Context, id int64, venue Venue) (Venue, error)
	DeleteVenue(ctx context.Context, id int64) error

	CreateEvent(ctx context.Context, event Event) (Event, error)
	ListEvents(ctx context.Context) ([]Event, error)
	GetEvent(ctx context.Context, id int64) (Event, error)
	UpdateEvent(ctx context.Context, id int64, event Event) (Event, error)
	DeleteEvent(ctx context.Context, id int64) error

	CreateCategory(ctx context.Context, category Category) (Category, error)
	ListCategories(ctx context.Context) ([]Category, error)
	GetCategory(ctx context.Context, id int64) (Category, error)
	UpdateCategory(ctx context.Context, id int64, category Category) (Category, error)
	DeleteCategory(ctx context.Context, id int64) error

	AddEventCategory(ctx context.Context, eventID, categoryID int64) error

	CreateBooking(ctx context.Context, booking Booking) (Booking, error)
	ListBookings(ctx context.Context, filter BookingFilter) ([]Booking, error)
	GetBooking(ctx context.Context, id int64) (Booking, error)
	UpdateBooking(ctx context.Context, id int64, booking Booking) (Booking, error)
	DeleteBooking(ctx context.Context, id int64) error

	UserBookings(ctx context.Context, userID int64) ([]BookingDetails, error)
	EventBookings(ctx context.Context, eventID int64) ([]BookingDetails, error)
	VenueEvents(ctx context.Context, venueID int64) ([]Event, error)
	CategoryEvents(ctx context.Context, categoryID int64) ([]EventSummary, error)
	EventStats(ctx context.Context, eventID int64) (EventStats, error)
}
