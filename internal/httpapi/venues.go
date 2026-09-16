package httpapi

import (
	"net/http"

	"rpm/internal/domain"
)

func (a *API) createVenue(w http.ResponseWriter, r *http.Request) {
	var input domain.Venue
	if !decode(w, r, &input) {
		return
	}
	venue, err := a.service.CreateVenue(r.Context(), input)
	respond(w, venue, err, http.StatusCreated)
}

func (a *API) listVenues(w http.ResponseWriter, r *http.Request) {
	venues, err := a.service.ListVenues(r.Context())
	respond(w, venues, err, http.StatusOK)
}

func (a *API) getVenue(w http.ResponseWriter, r *http.Request) {
	venue, err := a.service.GetVenue(r.Context(), pathID(r, "id"))
	respond(w, venue, err, http.StatusOK)
}

func (a *API) updateVenue(w http.ResponseWriter, r *http.Request) {
	var input domain.Venue
	if !decode(w, r, &input) {
		return
	}
	venue, err := a.service.UpdateVenue(r.Context(), pathID(r, "id"), input)
	respond(w, venue, err, http.StatusOK)
}

func (a *API) deleteVenue(w http.ResponseWriter, r *http.Request) {
	respondNoContent(w, a.service.DeleteVenue(r.Context(), pathID(r, "id")))
}

func (a *API) venueEvents(w http.ResponseWriter, r *http.Request) {
	items, err := a.service.VenueEvents(r.Context(), pathID(r, "id"))
	respond(w, items, err, http.StatusOK)
}
