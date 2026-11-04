-- Une ligne par crypto et par jour : dernier prix, moyenne, min, max
select
    id || '|' || cast(cast(last_updated as date) as varchar) as daily_key,
    id,
    symbol,
    cast(last_updated as date) as price_date,
    arg_max(current_price, last_updated) as close_price,
    avg(current_price) as avg_price,
    min(current_price) as min_price,
    max(current_price) as max_price,
    arg_max(price_change_percentage_24h, last_updated) as change_24h_pct,
    count(*) as nb_observations
from {{ ref('stg_prices') }}
group by id, symbol, cast(last_updated as date)
