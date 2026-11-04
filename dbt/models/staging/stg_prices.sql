-- Nettoyage : types, doublons retirés (même crypto + même last_updated => on garde le dernier chargement)
with typed as (
    select
        id,
        upper(symbol) as symbol,
        current_price,
        market_cap,
        total_volume,
        price_change_percentage_24h,
        cast(last_updated as timestamp) as last_updated,
        loaded_at
    from {{ source('raw', 'prices') }}
    where current_price is not null
),

ranked as (
    select
        *,
        row_number() over (partition by id, last_updated order by loaded_at desc) as rn
    from typed
)

select
    id || '|' || cast(last_updated as varchar) as price_key,
    id, symbol, current_price, market_cap, total_volume,
    price_change_percentage_24h, last_updated, loaded_at
from ranked
where rn = 1
