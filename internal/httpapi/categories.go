package httpapi

import (
	"net/http"

	"rpm/internal/domain"
)

func (a *API) createCategory(w http.ResponseWriter, r *http.Request) {
	var input domain.Category
	if !decode(w, r, &input) {
		return
	}
	category, err := a.service.CreateCategory(r.Context(), input)
	respond(w, category, err, http.StatusCreated)
}

func (a *API) listCategories(w http.ResponseWriter, r *http.Request) {
	categories, err := a.service.ListCategories(r.Context())
	respond(w, categories, err, http.StatusOK)
}

func (a *API) getCategory(w http.ResponseWriter, r *http.Request) {
	category, err := a.service.GetCategory(r.Context(), pathID(r, "id"))
	respond(w, category, err, http.StatusOK)
}

func (a *API) updateCategory(w http.ResponseWriter, r *http.Request) {
	var input domain.Category
	if !decode(w, r, &input) {
		return
	}
	category, err := a.service.UpdateCategory(r.Context(), pathID(r, "id"), input)
	respond(w, category, err, http.StatusOK)
}

func (a *API) deleteCategory(w http.ResponseWriter, r *http.Request) {
	respondNoContent(w, a.service.DeleteCategory(r.Context(), pathID(r, "id")))
}

func (a *API) categoryEvents(w http.ResponseWriter, r *http.Request) {
	items, err := a.service.CategoryEvents(r.Context(), pathID(r, "id"))
	respond(w, items, err, http.StatusOK)
}
