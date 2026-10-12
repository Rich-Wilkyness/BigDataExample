select
    status,
    COUNT(*) as order_count,
    AVG(days_to_ship) as avg_days_to_ship
from {{ ref('silver_orders') }}
group by status