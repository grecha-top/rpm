package httpapi

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"time"

	"rpm/internal/application"
	"rpm/internal/domain"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

type API struct {
	service *application.Service
}

func NewRouter(service *application.Service) http.Handler {
	api := &API{service: service}
	r := chi.NewRouter()
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	r.Get("/health", api.health)
	r.Get("/openapi.json", api.openapi)

	r.Route("/api", func(r chi.Router) {
		r.Get("/users", api.listUsers)
		r.Post("/users", api.createUser)
		r.Get("/users/{id}", api.getUser)
		r.Put("/users/{id}", api.updateUser)
		r.Delete("/users/{id}", api.deleteUser)
		r.Get("/users/{id}/bookings", api.userBookings)

		r.Get("/venues", api.listVenues)
		r.Post("/venues", api.createVenue)
		r.Get("/venues/{id}", api.getVenue)
		r.Put("/venues/{id}", api.updateVenue)
		r.Delete("/venues/{id}", api.deleteVenue)
		r.Get("/venues/{id}/events", api.venueEvents)

		r.Get("/events", api.listEvents)
		r.Post("/events", api.createEvent)
		r.Get("/events/{id}", api.getEvent)
		r.Put("/events/{id}", api.updateEvent)
		r.Delete("/events/{id}", api.deleteEvent)
		r.Get("/events/{id}/bookings", api.eventBookings)
		r.Get("/events/{id}/stats", api.eventStats)
		r.Post("/events/{id}/categories/{categoryID}", api.addEventCategory)

		r.Get("/categories", api.listCategories)
		r.Post("/categories", api.createCategory)
		r.Get("/categories/{id}", api.getCategory)
		r.Put("/categories/{id}", api.updateCategory)
		r.Delete("/categories/{id}", api.deleteCategory)
		r.Get("/categories/{id}/events", api.categoryEvents)

		r.Get("/bookings", api.listBookings)
		r.Post("/bookings", api.createBooking)
		r.Get("/bookings/{id}", api.getBooking)
		r.Put("/bookings/{id}", api.updateBooking)
		r.Delete("/bookings/{id}", api.deleteBooking)
	})

	return r
}

func (a *API) health(w http.ResponseWriter, r *http.Request) {
	if err := a.service.Ping(r.Context()); err != nil {
		writeError(w, http.StatusServiceUnavailable, "database is unavailable")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *API) openapi(w http.ResponseWriter, r *http.Request) {
	http.ServeFile(w, r, "docs/openapi.json")
}

func decode(w http.ResponseWriter, r *http.Request, dst any) bool {
	defer r.Body.Close()
	if err := json.NewDecoder(r.Body).Decode(dst); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return false
	}
	return true
}

func respond(w http.ResponseWriter, data any, err error, status int) {
	if err != nil {
		if errors.Is(err, domain.ErrNotFound) {
			writeError(w, http.StatusNotFound, "not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, status, data)
}

func respondNoContent(w http.ResponseWriter, err error) {
	if err != nil {
		if errors.Is(err, domain.ErrNotFound) {
			writeError(w, http.StatusNotFound, "not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func writeJSON(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func pathID(r *http.Request, key string) int64 {
	id, _ := strconv.ParseInt(chi.URLParam(r, key), 10, 64)
	return id
}

func queryInt(r *http.Request, key string, fallback int) int {
	value, err := strconv.Atoi(r.URL.Query().Get(key))
	if err != nil {
		return fallback
	}
	return value
}

func queryInt64(r *http.Request, key string, fallback int64) int64 {
	value, err := strconv.ParseInt(r.URL.Query().Get(key), 10, 64)
	if err != nil {
		return fallback
	}
	return value
}

func queryTime(r *http.Request, key string) *time.Time {
	raw := r.URL.Query().Get(key)
	if raw == "" {
		return nil
	}
	t, err := time.Parse(time.DateOnly, raw)
	if err != nil {
		return nil
	}
	return &t
}
