select
    nullif(trim(order_number), '') as order_number,
    shipping_date,
    nullif(upper(trim(status)), '') as status,
    days_to_ship
from {{ ref('stg_orders') }}

-- `NULLIF(..., '')` converts empty strings to NULL