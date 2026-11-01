
def generate_orders(count, start_id=1001):
    """
    Generate orders one at a time.

    Each order contains:
    (order_id, price, quantity)
    """

    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError("count must be an integer")

    if not isinstance(start_id, int) or isinstance(start_id, bool):
        raise ValueError("start_id must be an integer")

    if count < 0:
        raise ValueError("count cannot be negative")

    if start_id < 0:
        raise ValueError("start_id cannot be negative")

    for i in range(count):
        order_id = start_id + i
        price = 12500 + (i % 1000) * 10
        quantity = (i % 10) + 1

        yield (order_id, price, quantity)
