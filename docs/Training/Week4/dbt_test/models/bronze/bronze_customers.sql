SELECT *
FROM {{ source('raw_shop', 'customers') }}