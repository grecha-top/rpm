package httpapi

import (
	"net/http"

	"rpm/internal/domain"
)

func (a *API) createEvent(w http.ResponseWriter, r *http.Request) {
	var input domain.Event
	if !decode(w, r, &input) {
		return
	}
	event, err := a.service.CreateEvent(r.Context(), input)
	respond(w, event, err, http.StatusCreated)
}

func (a *API) listEvents(w http.ResponseWriter, r *http.Request) {
	events, err := a.service.ListEvents(r.Context())
	respond(w, events, err, http.StatusOK)
}

func (a *API) getEvent(w http.ResponseWriter, r *http.Request) {
	event, err := a.service.GetEvent(r.Context(), pathID(r, "id"))
	respond(w, event, err, http.StatusOK)
}

func (a *API) updateEvent(w http.ResponseWriter, r *http.Request) {
	var input domain.Event
	if !decode(w, r, &input) {
		return
	}
	event, err := a.service.UpdateEvent(r.Context(), pathID(r, "id"), input)
	respond(w, event, err, http.StatusOK)
}

func (a *API) deleteEvent(w http.ResponseWriter, r *http.Request) {
	respondNoContent(w, a.service.DeleteEvent(r.Context(), pathID(r, "id")))
}

func (a *API) addEventCategory(w http.ResponseWriter, r *http.Request) {
	err := a.service.AddEventCategory(r.Context(), pathID(r, "id"), pathID(r, "categoryID"))
	respond(w, map[string]string{"status": "linked"}, err, http.StatusOK)
}

func (a *API) eventBookings(w http.ResponseWriter, r *http.Request) {
	items, err := a.service.EventBookings(r.Context(), pathID(r, "id"))
	respond(w, items, err, http.StatusOK)
}

func (a *API) eventStats(w http.ResponseWriter, r *http.Request) {
	stats, err := a.service.EventStats(r.Context(), pathID(r, "id"))
	respond(w, stats, err, http.StatusOK)
}
