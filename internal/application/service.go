package application

import (
	"context"

	"rpm/internal/domain"
)

type Service struct {
	repo domain.Repository
}

func New(repo domain.Repository) *Service {
	return &Service{repo: repo}
}

func (s *Service) Ping(ctx context.Context) error {
	return s.repo.Ping(ctx)
}

func (s *Service) CreateUser(ctx context.Context, user domain.User) (domain.User, error) {
	return s.repo.CreateUser(ctx, user)
}

func (s *Service) ListUsers(ctx context.Context) ([]domain.User, error) {
	return s.repo.ListUsers(ctx)
}

func (s *Service) GetUser(ctx context.Context, id int64) (domain.User, error) {
	return s.repo.GetUser(ctx, id)
}

func (s *Service) UpdateUser(ctx context.Context, id int64, user domain.User) (domain.User, error) {
	return s.repo.UpdateUser(ctx, id, user)
}

func (s *Service) DeleteUser(ctx context.Context, id int64) error {
	return s.repo.DeleteUser(ctx, id)
}

func (s *Service) CreateVenue(ctx context.Context, venue domain.Venue) (domain.Venue, error) {
	return s.repo.CreateVenue(ctx, venue)
}

func (s *Service) ListVenues(ctx context.Context) ([]domain.Venue, error) {
	return s.repo.ListVenues(ctx)
}

func (s *Service) GetVenue(ctx context.Context, id int64) (domain.Venue, error) {
	return s.repo.GetVenue(ctx, id)
}

func (s *Service) UpdateVenue(ctx context.Context, id int64, venue domain.Venue) (domain.Venue, error) {
	return s.repo.UpdateVenue(ctx, id, venue)
}

func (s *Service) DeleteVenue(ctx context.Context, id int64) error {
	return s.repo.DeleteVenue(ctx, id)
}

func (s *Service) CreateEvent(ctx context.Context, event domain.Event) (domain.Event, error) {
	return s.repo.CreateEvent(ctx, event)
}

func (s *Service) ListEvents(ctx context.Context) ([]domain.Event, error) {
	return s.repo.ListEvents(ctx)
}

func (s *Service) GetEvent(ctx context.Context, id int64) (domain.Event, error) {
	return s.repo.GetEvent(ctx, id)
}

func (s *Service) UpdateEvent(ctx context.Context, id int64, event domain.Event) (domain.Event, error) {
	return s.repo.UpdateEvent(ctx, id, event)
}

func (s *Service) DeleteEvent(ctx context.Context, id int64) error {
	return s.repo.DeleteEvent(ctx, id)
}

func (s *Service) CreateCategory(ctx context.Context, category domain.Category) (domain.Category, error) {
	return s.repo.CreateCategory(ctx, category)
}

func (s *Service) ListCategories(ctx context.Context) ([]domain.Category, error) {
	return s.repo.ListCategories(ctx)
}

func (s *Service) GetCategory(ctx context.Context, id int64) (domain.Category, error) {
	return s.repo.GetCategory(ctx, id)
}

func (s *Service) UpdateCategory(ctx context.Context, id int64, category domain.Category) (domain.Category, error) {
	return s.repo.UpdateCategory(ctx, id, category)
}

func (s *Service) DeleteCategory(ctx context.Context, id int64) error {
	return s.repo.DeleteCategory(ctx, id)
}

func (s *Service) AddEventCategory(ctx context.Context, eventID, categoryID int64) error {
	return s.repo.AddEventCategory(ctx, eventID, categoryID)
}

func (s *Service) CreateBooking(ctx context.Context, booking domain.Booking) (domain.Booking, error) {
	return s.repo.CreateBooking(ctx, booking)
}

func (s *Service) ListBookings(ctx context.Context, filter domain.BookingFilter) ([]domain.Booking, error) {
	return s.repo.ListBookings(ctx, filter)
}

func (s *Service) GetBooking(ctx context.Context, id int64) (domain.Booking, error) {
	return s.repo.GetBooking(ctx, id)
}

func (s *Service) UpdateBooking(ctx context.Context, id int64, booking domain.Booking) (domain.Booking, error) {
	return s.repo.UpdateBooking(ctx, id, booking)
}

func (s *Service) DeleteBooking(ctx context.Context, id int64) error {
	return s.repo.DeleteBooking(ctx, id)
}

func (s *Service) UserBookings(ctx context.Context, userID int64) ([]domain.BookingDetails, error) {
	return s.repo.UserBookings(ctx, userID)
}

func (s *Service) EventBookings(ctx context.Context, eventID int64) ([]domain.BookingDetails, error) {
	return s.repo.EventBookings(ctx, eventID)
}

func (s *Service) VenueEvents(ctx context.Context, venueID int64) ([]domain.Event, error) {
	return s.repo.VenueEvents(ctx, venueID)
}

func (s *Service) CategoryEvents(ctx context.Context, categoryID int64) ([]domain.EventSummary, error) {
	return s.repo.CategoryEvents(ctx, categoryID)
}

func (s *Service) EventStats(ctx context.Context, eventID int64) (domain.EventStats, error) {
	return s.repo.EventStats(ctx, eventID)
}
