select
    order_number,
    shipping_date,
    status,
    days_to_ship
from {{ source('raw_shop', 'orders') }}
