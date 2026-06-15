DO $$
BEGIN

    -- 1. STABILITY SCORE
    CREATE TABLE IF NOT EXISTS analytics_stability_score (
        restaurant VARCHAR,
        restaurant_category VARCHAR,
        price_change_events INT,
        cv_pct NUMERIC,
        avg_price NUMERIC,
        pvs_normalized NUMERIC
    );

    CREATE TABLE stability_score_staging AS
    SELECT
        base.restaurant,
        base.restaurant_category,
        COUNT(chg.item_name)::INT AS price_change_events,
        COALESCE(ROUND(STDDEV(chg.pct_change)::NUMERIC, 4), 0.0) AS cv_pct,
        COALESCE(ROUND(AVG(chg.new_price)::NUMERIC, 2), 0.0) AS avg_price,
        ROUND(
    (COUNT(chg.item_name)::NUMERIC /
    NULLIF(MAX(COUNT(chg.item_name)::NUMERIC) OVER (), 0)) * 100, 2
)::NUMERIC AS pvs_normalized
    FROM (SELECT DISTINCT restaurant, restaurant_category FROM v_analysis_base) base
    LEFT JOIN v_price_changes chg
        ON base.restaurant = chg.restaurant
        AND base.restaurant_category = chg.restaurant_category
    GROUP BY base.restaurant, base.restaurant_category;

    -- 2. RAIN PREMIUM INDEX
    CREATE TABLE IF NOT EXISTS analytics_rain_premium (
        restaurant VARCHAR,
        category VARCHAR,
        rainy_records INT,
        clear_records INT,
        avg_change_rain NUMERIC,
        avg_change_clear NUMERIC,
        rpi NUMERIC,
        significant BOOLEAN,
        verdict VARCHAR
    );

    CREATE TABLE rain_premium_staging AS
    SELECT
        base.restaurant,
        base.restaurant_category AS category,
        COUNT(CASE WHEN chg.is_rainy = TRUE THEN 1 END)::INT AS rainy_records,
        COUNT(CASE WHEN chg.is_rainy = FALSE THEN 1 END)::INT AS clear_records,
        COALESCE(ROUND(AVG(CASE WHEN chg.is_rainy = TRUE THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS avg_change_rain,
        COALESCE(ROUND(AVG(CASE WHEN chg.is_rainy = FALSE THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS avg_change_clear,
        COALESCE(ROUND(AVG(CASE WHEN chg.is_rainy = TRUE THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS rpi,
        (COUNT(CASE WHEN chg.is_rainy = TRUE THEN 1 END) >= 5)::BOOLEAN AS significant,
        CASE
            WHEN COUNT(CASE WHEN chg.is_rainy = TRUE THEN 1 END) >= 5
                AND COALESCE(AVG(CASE WHEN chg.is_rainy = TRUE THEN chg.pct_change END), 0) > 0
                THEN 'Surge confirmed'
            WHEN COUNT(CASE WHEN chg.is_rainy = TRUE THEN 1 END) >= 5
                AND COALESCE(AVG(CASE WHEN chg.is_rainy = TRUE THEN chg.pct_change END), 0) < 0
                THEN 'Drop during rain'
            ELSE 'No significant change'
        END::VARCHAR AS verdict
    FROM (SELECT DISTINCT restaurant, restaurant_category FROM v_analysis_base) base
    LEFT JOIN v_price_changes chg
        ON base.restaurant = chg.restaurant
        AND base.restaurant_category = chg.restaurant_category
    GROUP BY base.restaurant, base.restaurant_category;

    -- 3. WEEKEND PREMIUM INDEX
    CREATE TABLE IF NOT EXISTS analytics_weekend_premium (
        restaurant VARCHAR,
        category VARCHAR,
        weekend_records INT,
        weekday_records INT,
        avg_change_weekend NUMERIC,
        avg_change_weekday NUMERIC,
        wpi NUMERIC,
        significant BOOLEAN,
        verdict VARCHAR
    );

    CREATE TABLE weekend_premium_staging AS
    SELECT
        base.restaurant,
        base.restaurant_category AS category,
        COUNT(CASE WHEN chg.is_weekend = TRUE THEN 1 END)::INT AS weekend_records,
        COUNT(CASE WHEN chg.is_weekend = FALSE THEN 1 END)::INT AS weekday_records,
        COALESCE(ROUND(AVG(CASE WHEN chg.is_weekend = TRUE THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS avg_change_weekend,
        COALESCE(ROUND(AVG(CASE WHEN chg.is_weekend = FALSE THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS avg_change_weekday,
        COALESCE(ROUND(AVG(CASE WHEN chg.is_weekend = TRUE THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS wpi,
        (COUNT(CASE WHEN chg.is_weekend = TRUE THEN 1 END) >= 3)::BOOLEAN AS significant,
        CASE
            WHEN COUNT(CASE WHEN chg.is_weekend = TRUE THEN 1 END) >= 3
                AND COALESCE(AVG(CASE WHEN chg.is_weekend = TRUE THEN chg.pct_change END), 0) > 0
                THEN 'Weekend premium confirmed'
            WHEN COUNT(CASE WHEN chg.is_weekend = TRUE THEN 1 END) >= 3
                AND COALESCE(AVG(CASE WHEN chg.is_weekend = TRUE THEN chg.pct_change END), 0) < 0
                THEN 'Cheaper on weekends'
            ELSE 'No significant change'
        END::VARCHAR AS verdict
    FROM (SELECT DISTINCT restaurant, restaurant_category FROM v_analysis_base) base
    LEFT JOIN v_price_changes chg
        ON base.restaurant = chg.restaurant
        AND base.restaurant_category = chg.restaurant_category
    GROUP BY base.restaurant, base.restaurant_category;

    -- 4. TEMPERATURE EFFECT
    CREATE TABLE IF NOT EXISTS analytics_temperature_effect (
        restaurant VARCHAR,
        category VARCHAR,
        cool_records INT,
        normal_records INT,
        hot_records INT,
        avg_price_hot NUMERIC,
        avg_price_normal NUMERIC,
        temp_effect_score NUMERIC,
        significant BOOLEAN,
        verdict VARCHAR
    );

    CREATE TABLE temperature_effect_staging AS
    SELECT
        base.restaurant,
        base.restaurant_category AS category,
        COUNT(CASE WHEN chg.temperature_band = 'Cool' THEN 1 END)::INT AS cool_records,
        COUNT(CASE WHEN chg.temperature_band = 'Normal' THEN 1 END)::INT AS normal_records,
        COUNT(CASE WHEN chg.temperature_band = 'Hot' THEN 1 END)::INT AS hot_records,
        COALESCE(ROUND(AVG(CASE WHEN chg.temperature_band = 'Hot' THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS avg_price_hot,
        COALESCE(ROUND(AVG(CASE WHEN chg.temperature_band = 'Normal' THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS avg_price_normal,
        COALESCE(ROUND(AVG(CASE WHEN chg.temperature_band = 'Hot' THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS temp_effect_score,
        ((COUNT(CASE WHEN chg.temperature_band = 'Hot' THEN 1 END) + COUNT(CASE WHEN chg.temperature_band = 'Cool' THEN 1 END)) >= 3)::BOOLEAN AS significant,
        CASE
            WHEN (COUNT(CASE WHEN chg.temperature_band = 'Hot' THEN 1 END) + COUNT(CASE WHEN chg.temperature_band = 'Cool' THEN 1 END)) >= 3
                AND COALESCE(AVG(CASE WHEN chg.temperature_band = 'Hot' THEN chg.pct_change END), 0) > 0
                THEN 'Price rises in heat'
            WHEN (COUNT(CASE WHEN chg.temperature_band = 'Hot' THEN 1 END) + COUNT(CASE WHEN chg.temperature_band = 'Cool' THEN 1 END)) >= 3
                AND COALESCE(AVG(CASE WHEN chg.temperature_band = 'Hot' THEN chg.pct_change END), 0) < 0
                THEN 'Price drops in heat'
            ELSE 'No significant change'
        END::VARCHAR AS verdict
    FROM (SELECT DISTINCT restaurant, restaurant_category FROM v_analysis_base) base
    LEFT JOIN v_price_changes chg
        ON base.restaurant = chg.restaurant
        AND base.restaurant_category = chg.restaurant_category
    GROUP BY base.restaurant, base.restaurant_category;

    -- 5. CATEGORY SENSITIVITY
    CREATE TABLE IF NOT EXISTS analytics_category_sensitivity (
        dish_type VARCHAR,
        total_change_events INT,
        rpi NUMERIC,
        wpi NUMERIC,
        sensitivity_score NUMERIC
    );

    CREATE TABLE category_sensitivity_staging AS
    SELECT
        base.dish_type,
        COUNT(chg.item_name)::INT AS total_change_events,
        COALESCE(ROUND(AVG(CASE WHEN chg.is_rainy = TRUE THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS rpi,
        COALESCE(ROUND(AVG(CASE WHEN chg.is_weekend = TRUE THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS wpi,
        COALESCE(ROUND(AVG(chg.pct_change)::NUMERIC, 2), 0.0) AS sensitivity_score
    FROM (SELECT DISTINCT dish_type FROM v_analysis_base WHERE dish_type != 'Other') base
    LEFT JOIN v_price_changes chg ON base.dish_type = chg.dish_type
    GROUP BY base.dish_type;

    -- 6. HOURLY OVERALL
    CREATE TABLE IF NOT EXISTS analytics_hourly_overall (
        hour_of_day INT,
        total_change_events INT,
        avg_price_change_pct NUMERIC
    );

    CREATE TABLE hourly_overall_staging AS
    SELECT
        hours.hour_of_day::INT,
        COUNT(chg.item_name)::INT AS total_change_events,
        COALESCE(ROUND(AVG(chg.pct_change)::NUMERIC, 2), 0.0) AS avg_price_change_pct
    FROM (SELECT DISTINCT hour_of_day FROM v_analysis_base) hours
    LEFT JOIN v_price_changes chg ON hours.hour_of_day = chg.hour_of_day
    GROUP BY hours.hour_of_day;

    -- 6b. HOURLY PER RESTAURANT
    CREATE TABLE IF NOT EXISTS analytics_hourly_per_restaurant (
        restaurant VARCHAR,
        restaurant_category VARCHAR,
        hour_of_day INT,
        total_change_events INT,
        avg_price_change_pct NUMERIC
    );

    CREATE TABLE hourly_per_restaurant_staging AS
    SELECT
        base.restaurant,
        base.restaurant_category,
        hours.hour_of_day::INT,
        COUNT(chg.item_name)::INT AS total_change_events,
        COALESCE(ROUND(AVG(chg.pct_change)::NUMERIC, 2), 0.0) AS avg_price_change_pct
    FROM (SELECT DISTINCT restaurant, restaurant_category FROM v_analysis_base) base
    CROSS JOIN (SELECT DISTINCT hour_of_day FROM v_analysis_base) hours
    LEFT JOIN v_price_changes chg
        ON base.restaurant = chg.restaurant
        AND base.restaurant_category = chg.restaurant_category
        AND hours.hour_of_day = chg.hour_of_day
    GROUP BY base.restaurant, base.restaurant_category, hours.hour_of_day;

    -- 6c. HOURLY PEAK PER RESTAURANT
    CREATE TABLE IF NOT EXISTS analytics_hourly_peak_restaurant (
        restaurant VARCHAR,
        restaurant_category VARCHAR,
        peak_hour INT,
        peak_change_pct NUMERIC
    );

    CREATE TABLE hourly_peak_restaurant_staging AS
    SELECT DISTINCT ON (restaurant, restaurant_category)
        restaurant,
        restaurant_category,
        hour_of_day AS peak_hour,
        avg_price_change_pct AS peak_change_pct
    FROM hourly_per_restaurant_staging
    ORDER BY restaurant, restaurant_category, avg_price_change_pct DESC;

    -- 7. PEAK / OFF-PEAK WINDOWS
    CREATE TABLE IF NOT EXISTS analytics_peak_offpeak (
        restaurant VARCHAR,
        restaurant_category VARCHAR,
        time_window VARCHAR,
        total_change_events INT,
        avg_price_change_pct NUMERIC
    );

    CREATE TABLE peak_offpeak_staging AS
    SELECT
        base.restaurant,
        base.restaurant_category,
        CASE
            WHEN hours.hour_of_day IN (12, 13)             THEN '2-Lunch Peak'
            WHEN hours.hour_of_day IN (19, 20)             THEN '4-Dinner Peak'
            WHEN hours.hour_of_day IN (10, 11)             THEN '1-Morning Off-Peak'
            WHEN hours.hour_of_day IN (14, 15, 16, 17, 18) THEN '3-Afternoon Off-Peak'
            WHEN hours.hour_of_day IN (21, 22)             THEN '5-Late Night Off-Peak'
            ELSE 'Other'
        END::VARCHAR AS time_window,
        COUNT(chg.item_name)::INT AS total_change_events,
        COALESCE(ROUND(AVG(chg.pct_change)::NUMERIC, 2), 0.0) AS avg_price_change_pct
    FROM (SELECT DISTINCT restaurant, restaurant_category FROM v_analysis_base) base
    CROSS JOIN (SELECT DISTINCT hour_of_day FROM v_analysis_base) hours
    LEFT JOIN v_price_changes chg
        ON base.restaurant = chg.restaurant
        AND base.restaurant_category = chg.restaurant_category
        AND hours.hour_of_day = chg.hour_of_day
    GROUP BY base.restaurant, base.restaurant_category, time_window;

    -- 8. SYNCHRONIZED PRICING SHELLS (written by Python engine in run_all.py)
    CREATE TABLE IF NOT EXISTS analytics_sync_pairs_all (
        restaurant_a VARCHAR,
        restaurant_b VARCHAR,
        correlation NUMERIC,
        strength VARCHAR
    );

    CREATE TABLE IF NOT EXISTS analytics_sync_pairs_rain (
        restaurant_a VARCHAR,
        restaurant_b VARCHAR,
        correlation NUMERIC,
        strength VARCHAR
    );

    -- 9. DYNAMIC PRICING INDEX
    CREATE TABLE IF NOT EXISTS analytics_dynamic_pricing_index (
        restaurant VARCHAR,
        category VARCHAR,
        rpi NUMERIC,
        wpi NUMERIC,
        temp_effect NUMERIC,
        pvs_normalized NUMERIC,
        dpi NUMERIC,
        dpi_rank INT,
        pricing_behavior VARCHAR
    );

    CREATE TABLE dynamic_pricing_index_staging AS
    WITH base AS (
        SELECT
            r.restaurant,
            r.category,
            r.rpi,
            w.wpi,
            t.temp_effect_score,
            s.pvs_normalized
        FROM rain_premium_staging r
        JOIN weekend_premium_staging w
            ON r.restaurant = w.restaurant
            AND r.category = w.category
        JOIN temperature_effect_staging t
            ON r.restaurant = t.restaurant
            AND r.category = t.category
        JOIN stability_score_staging s
            ON r.restaurant = s.restaurant
            AND r.category = s.restaurant_category
    ),
    normed AS (
    SELECT
        *,
        GREATEST(0, LEAST(100, GREATEST(rpi, 0) / 20.0 * 100)) AS rpi_norm,
        GREATEST(0, LEAST(100, GREATEST(wpi, 0) / 20.0 * 100)) AS wpi_norm,
        GREATEST(0, LEAST(100, GREATEST(temp_effect_score, 0) / 15.0 * 100)) AS temp_norm
    FROM base
),
    calculated AS (
    SELECT
        restaurant,
        category,
        rpi,
        wpi,
        temp_effect_score AS temp_effect,
        pvs_normalized,
        ROUND(
    (rpi_norm * 0.20 + wpi_norm * 0.20 + temp_norm * 0.10 + pvs_normalized * 0.50)::NUMERIC,
2) AS dpi
        FROM normed
    )
    SELECT
        restaurant,
        category,
        rpi,
        wpi,
        temp_effect,
        pvs_normalized,
        dpi,
        RANK() OVER (ORDER BY dpi DESC)::INT AS dpi_rank,
        CASE
            WHEN dpi < 25 THEN 'Static Pricer'
            WHEN dpi < 50 THEN 'Low Dynamic'
            WHEN dpi < 75 THEN 'Moderate Dynamic'
            ELSE 'Aggressive Dynamic'
        END::VARCHAR AS pricing_behavior
    FROM calculated;

    -- 10. ATOMIC SWAP
    DROP TABLE IF EXISTS analytics_stability_score CASCADE;
    ALTER TABLE stability_score_staging RENAME TO analytics_stability_score;

    DROP TABLE IF EXISTS analytics_rain_premium CASCADE;
    ALTER TABLE rain_premium_staging RENAME TO analytics_rain_premium;

    DROP TABLE IF EXISTS analytics_weekend_premium CASCADE;
    ALTER TABLE weekend_premium_staging RENAME TO analytics_weekend_premium;

    DROP TABLE IF EXISTS analytics_temperature_effect CASCADE;
    ALTER TABLE temperature_effect_staging RENAME TO analytics_temperature_effect;

    DROP TABLE IF EXISTS analytics_category_sensitivity CASCADE;
    ALTER TABLE category_sensitivity_staging RENAME TO analytics_category_sensitivity;

    DROP TABLE IF EXISTS analytics_hourly_overall CASCADE;
    ALTER TABLE hourly_overall_staging RENAME TO analytics_hourly_overall;

    DROP TABLE IF EXISTS analytics_hourly_per_restaurant CASCADE;
    ALTER TABLE hourly_per_restaurant_staging RENAME TO analytics_hourly_per_restaurant;

    DROP TABLE IF EXISTS analytics_hourly_peak_restaurant CASCADE;
    ALTER TABLE hourly_peak_restaurant_staging RENAME TO analytics_hourly_peak_restaurant;

    DROP TABLE IF EXISTS analytics_peak_offpeak CASCADE;
    ALTER TABLE peak_offpeak_staging RENAME TO analytics_peak_offpeak;

    DROP TABLE IF EXISTS analytics_dynamic_pricing_index CASCADE;
    ALTER TABLE dynamic_pricing_index_staging RENAME TO analytics_dynamic_pricing_index;

    -- analytics_sync_pairs_all and analytics_sync_pairs_rain are managed
    -- by the Python engine in run_all.py — not swapped here.
    DROP TABLE IF EXISTS analytics_category_hour_heatmap;
-- ============================================
    -- Table 15: analytics_category_hour_heatmap
    -- ============================================
CREATE TABLE analytics_category_hour_heatmap AS
SELECT 
    category,   
    EXTRACT(HOUR FROM scraped_at)::integer AS hour_of_day,
    ROUND(AVG(price), 0) AS avg_price,
    COUNT(*) AS observation_count
FROM prices
WHERE EXTRACT(HOUR FROM scraped_at) BETWEEN 10 AND 22
GROUP BY category, EXTRACT(HOUR FROM scraped_at)
ORDER BY category, hour_of_day;

-- ============================================
    -- Table 13: analytics_restaurant_weather_price
    -- ============================================
    DROP TABLE IF EXISTS analytics_restaurant_weather_price_staging;
    
    CREATE TABLE analytics_restaurant_weather_price_staging AS
    SELECT 
        p.restaurant,
        CASE WHEN w.is_rainy THEN 'Rain' ELSE 'Dry' END AS weather_condition,
        ROUND(AVG(p.price), 0) AS avg_price,
        COUNT(*) AS observation_count
    FROM prices p
    JOIN weather w ON p.scrape_session_id = w.scrape_session_id
    GROUP BY p.restaurant, CASE WHEN w.is_rainy THEN 'Rain' ELSE 'Dry' END;
    
    DROP TABLE IF EXISTS analytics_restaurant_weather_price;
    ALTER TABLE analytics_restaurant_weather_price_staging 
        RENAME TO analytics_restaurant_weather_price;

    -- ============================================
    -- Table 14: analytics_market_weather_price
    -- ============================================
    DROP TABLE IF EXISTS analytics_market_weather_price_staging;
    
    CREATE TABLE analytics_market_weather_price_staging AS
    SELECT 
        CASE WHEN w.is_rainy THEN 'Rain' ELSE 'Dry' END AS weather_condition,
        ROUND(AVG(p.price), 0) AS avg_price,
        COUNT(*) AS observation_count
    FROM prices p
    JOIN weather w ON p.scrape_session_id = w.scrape_session_id
    GROUP BY CASE WHEN w.is_rainy THEN 'Rain' ELSE 'Dry' END;
    
    DROP TABLE IF EXISTS analytics_market_weather_price;
    ALTER TABLE analytics_market_weather_price_staging 
        RENAME TO analytics_market_weather_price;
END $$;