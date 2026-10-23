
import struct

# Fixed binary format for one ChronosMatch order.
#
# <  = little-endian byte order
# Q  = unsigned 64-bit Order ID
# q  = signed 64-bit Price
# I  = unsigned 32-bit Quantity
#
# Total size: 8 + 8 + 4 = 20 bytes.

ORDER_FORMAT = "<QqI"
ORDER_SIZE = struct.calcsize(ORDER_FORMAT)


def pack_order(order_id, price, quantity):
    """Convert order fields into a fixed-size bytes object."""

    if not isinstance(order_id, int) or isinstance(order_id, bool):
        raise TypeError("order_id must be an integer")

    if not isinstance(price, int) or isinstance(price, bool):
        raise TypeError("price must be an integer")

    if not isinstance(quantity, int) or isinstance(quantity, bool):
        raise TypeError("quantity must be an integer")

    if not 0 <= order_id <= 18446744073709551615:
        raise ValueError("order_id is outside the uint64 range")

    if not -9223372036854775808 <= price <= 9223372036854775807:
        raise ValueError("price is outside the int64 range")

    if not 0 <= quantity <= 4294967295:
        raise ValueError("quantity is outside the uint32 range")

    return struct.pack(ORDER_FORMAT, order_id, price, quantity)


def unpack_order(data):
    """Convert a fixed-size bytes object back into order fields."""

    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")

    if len(data) != ORDER_SIZE:
        raise ValueError(
            "Expected {} bytes, received {}".format(ORDER_SIZE, len(data))
        )

    order_id, price, quantity = struct.unpack(ORDER_FORMAT, data)

    return order_id, price, quantity


if __name__ == "__main__":
    # Example order: price is stored as an integer number of ticks.
    original_order = (1001, 12550, 10)

    packed = pack_order(*original_order)
    recovered = unpack_order(packed)

    print("Original order:", original_order)
    print("Packed data:", packed)
    print("Packed size:", len(packed), "bytes")
    print("Recovered order:", recovered)
    print("Data matches:", original_order == recovered)
