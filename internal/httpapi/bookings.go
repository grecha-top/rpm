package httpapi

import (
	"net/http"

	"rpm/internal/domain"
)

func (a *API) createBooking(w http.ResponseWriter, r *http.Request) {
	var input domain.Booking
	if !decode(w, r, &input) {
		return
	}
	booking, err := a.service.CreateBooking(r.Context(), input)
	respond(w, booking, err, http.StatusCreated)
}

func (a *API) listBookings(w http.ResponseWriter, r *http.Request) {
	filter := domain.BookingFilter{
		Page:     queryInt(r, "page", 1),
		PageSize: queryInt(r, "pageSize", 20),
		Status:   r.URL.Query().Get("status"),
		UserID:   queryInt64(r, "user_id", 0),
		EventID:  queryInt64(r, "event_id", 0),
		Sort:     r.URL.Query().Get("sort"),
	}
	filter.From = queryTime(r, "from")
	filter.To = queryTime(r, "to")
	if filter.Page < 1 {
		filter.Page = 1
	}
	if filter.PageSize < 1 || filter.PageSize > 200 {
		filter.PageSize = 20
	}
	bookings, err := a.service.ListBookings(r.Context(), filter)
	respond(w, bookings, err, http.StatusOK)
}

func (a *API) getBooking(w http.ResponseWriter, r *http.Request) {
	booking, err := a.service.GetBooking(r.Context(), pathID(r, "id"))
	respond(w, booking, err, http.StatusOK)
}

func (a *API) updateBooking(w http.ResponseWriter, r *http.Request) {
	var input domain.Booking
	if !decode(w, r, &input) {
		return
	}
	booking, err := a.service.UpdateBooking(r.Context(), pathID(r, "id"), input)
	respond(w, booking, err, http.StatusOK)
}

func (a *API) deleteBooking(w http.ResponseWriter, r *http.Request) {
	respondNoContent(w, a.service.DeleteBooking(r.Context(), pathID(r, "id")))
}
