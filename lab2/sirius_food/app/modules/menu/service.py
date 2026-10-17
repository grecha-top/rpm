"""Menu use cases. Cache details stay inside MenuRepository."""
from typing import Optional, Protocol


class MenuRepositoryProtocol(Protocol):
    def get_all(self):
        ...

    def get_by_id(self, item_id: int):
        ...

    def get_by_name(self, name: str):
        ...

    def get_by_category(self, category_id: int):
        ...

    def save(self, item):
        ...

    def create_item(self, name: str, price: float, category_id: Optional[int] = None):
        ...

    def invalidate_cache(self, category_id: Optional[int] = None) -> None:
        ...


class MenuItemNameExistsError(Exception):
    pass


class MenuItemNotFoundError(Exception):
    pass


class MenuService:
    def __init__(self, repository: MenuRepositoryProtocol):
        self.repository = repository

    def get_items(self):
        return self.repository.get_all()

    def get_category(self, category_id: int):
        return self.repository.get_by_category(category_id)

    def create_item(self, name: str, price: float, category_id: Optional[int] = None):
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
        if len(name.strip()) < 2:
            raise ValueError("Название блюда слишком короткое")
        if self.repository.get_by_name(name):
            raise MenuItemNameExistsError()

        saved = self.repository.create_item(name, price, category_id)
        self.repository.invalidate_cache(category_id)
        return saved

    def update_item(
        self,
        item_id: int,
        name: Optional[str],
        price: Optional[float],
        is_available: Optional[bool],
        category_id: Optional[int],
    ):
        item = self.repository.get_by_id(item_id)
        if not item:
            raise MenuItemNotFoundError()
        old_category_id = item.category_id
        if price is not None and price <= 0:
            raise ValueError("Цена должна быть положительной")
        if name is not None:
            item.name = name
        if price is not None:
            item.price = price
        if is_available is not None:
            item.is_available = is_available
        if category_id is not None:
            item.category_id = category_id
        saved = self.repository.save(item)
        self.repository.invalidate_cache(old_category_id)
        if category_id is not None and category_id != old_category_id:
            self.repository.invalidate_cache(category_id)
        return saved
