package httpapi

import (
	"net/http"

	"rpm/internal/domain"
)

func (a *API) createUser(w http.ResponseWriter, r *http.Request) {
	var input domain.User
	if !decode(w, r, &input) {
		return
	}
	user, err := a.service.CreateUser(r.Context(), input)
	respond(w, user, err, http.StatusCreated)
}

func (a *API) listUsers(w http.ResponseWriter, r *http.Request) {
	users, err := a.service.ListUsers(r.Context())
	respond(w, users, err, http.StatusOK)
}

func (a *API) getUser(w http.ResponseWriter, r *http.Request) {
	user, err := a.service.GetUser(r.Context(), pathID(r, "id"))
	respond(w, user, err, http.StatusOK)
}

func (a *API) updateUser(w http.ResponseWriter, r *http.Request) {
	var input domain.User
	if !decode(w, r, &input) {
		return
	}
	user, err := a.service.UpdateUser(r.Context(), pathID(r, "id"), input)
	respond(w, user, err, http.StatusOK)
}

func (a *API) deleteUser(w http.ResponseWriter, r *http.Request) {
	respondNoContent(w, a.service.DeleteUser(r.Context(), pathID(r, "id")))
}

func (a *API) userBookings(w http.ResponseWriter, r *http.Request) {
	items, err := a.service.UserBookings(r.Context(), pathID(r, "id"))
	respond(w, items, err, http.StatusOK)
}
