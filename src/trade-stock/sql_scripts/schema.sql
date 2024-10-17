CREATE TYPE trade_state AS ENUM ('submitted', 'pending', 'rejected', 'filled');
CREATE TYPE transaction_type AS ENUM ('buy', 'sell');

CREATE TABLE customer (
    id serial PRIMARY KEY,
    first_name VARCHAR ( 250 ) NOT NULL,
    last_name VARCHAR ( 250 ) NOT NULL,
    created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE TABLE symbol (
    id serial PRIMARY KEY,
    ticker VARCHAR ( 25 ) NOT NULL,
    open numeric NOT NULL CHECK (open > 0),
    high numeric NOT NULL CHECK (high > 0),
    low numeric NOT NULL CHECK (low > 0),
    close numeric NOT NULL CHECK (close > 0),
    volume integer NOT NULL CHECK (volume > 0),
    created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE TABLE activity (
    id serial PRIMARY KEY,
    request_id VARCHAR ( 40 ) UNIQUE NOT NULL,
    customer_id INTEGER REFERENCES customer (id),
    symbol_ticker INTEGER REFERENCES symbol (id),
    type transaction_type NOT NULL,
    current_price numeric NOT NULL CHECK (current_price > 0),
    share_count numeric NOT NULL CHECK (share_count > 0),
    status trade_state NOT NULL,
    created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE  FUNCTION update_updated_on()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_on = now();
    RETURN NEW;
END;
$$ language plpgsql;

CREATE TRIGGER update_symbol_updated_on
    BEFORE UPDATE
    ON
        symbol
    FOR EACH ROW
EXECUTE PROCEDURE update_updated_on();
CREATE TRIGGER update_activity_updated_on
    BEFORE UPDATE
    ON
        activity
    FOR EACH ROW
EXECUTE PROCEDURE update_updated_on();
CREATE TRIGGER update_customer_updated_on
    BEFORE UPDATE
    ON
        customer
    FOR EACH ROW
EXECUTE PROCEDURE update_updated_on();
