"""Business rules for the extracted delivery service."""


class DeliveryNotFoundError(Exception):
    pass


class OrderNotFoundError(Exception):
    pass


class CourierNotFoundError(Exception):
    pass


class DeliveryConflictError(Exception):
    pass


class DeliveryAccessDeniedError(Exception):
    pass


class DeliveryService:
    def __init__(self, repository):
        self.repository = repository

    def assign_courier(self, order_id: int, courier_id: int):
        order = self.repository.get_order(order_id)
        if not order:
            raise OrderNotFoundError()
        if order.status != "paid":
            raise DeliveryConflictError("Курьера можно назначить только на оплаченный заказ")
        if self.repository.get_by_order(order_id):
            raise DeliveryConflictError("Доставка для заказа уже существует")

        courier = self.repository.get_courier(courier_id)
        if not courier:
            raise CourierNotFoundError()
        if not courier.role or courier.role.name != "courier":
            raise DeliveryConflictError("Пользователь не является курьером")
        if courier.is_blocked:
            raise DeliveryAccessDeniedError("Курьер заблокирован")
        if self.repository.get_active_for_courier(courier_id):
            raise DeliveryConflictError("У курьера уже есть активная доставка")
        return self.repository.create(order_id, courier_id)

    def complete_delivery(self, delivery_id: int, actor_id: int, actor_is_admin: bool):
        delivery = self.repository.get_by_id(delivery_id)
        if not delivery:
            raise DeliveryNotFoundError()
        if not actor_is_admin and delivery.courier_id != actor_id:
            raise DeliveryAccessDeniedError("Access denied")
        if delivery.status == "delivered":
            raise DeliveryConflictError("Доставка уже завершена")
        if delivery.status == "cancelled":
            raise DeliveryConflictError("Отменённую доставку нельзя завершить")
        return self.repository.update_status(delivery, "delivered")

    def get_delivery(self, order_id: int):
        delivery = self.repository.get_by_order(order_id)
        if not delivery:
            raise DeliveryNotFoundError()
        return delivery

    def list_deliveries(self, courier_id: int, include_all: bool):
        return self.repository.list_for_courier(courier_id, include_all)
