## PSQL Table Design 

So how do I want to set this up? Well for starters let's go ahead and plan out what data I want to store.
- Date
- Type of Expense (Category such as Grocery, Car, Other, etc.)
- Amount

For now that should be fine so I want it structured as such

CREATE TABLE expenses (
ReceiptID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
Date TIMESTAMP,
ToE VARCHAR(255),
Amount INT
);

SELECT * FROM expenses;

sudo docker exec -it (container name) psql -U (db_user) -d (db_name)
