\COPY symbol(ticker,volume,open,close,high,low) 
  FROM '~/seed/stocks.csv' DELIMITER ',' CSV HEADER;
\COPY customer(first_name,last_name) 
  FROM '~/seed/customers.csv' DELIMITER ',' CSV HEADER;
