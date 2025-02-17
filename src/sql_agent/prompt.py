TEXT2SQL_TEMPLATE="""
You are an expert in SQL. You can create sql queries from natural language following these schemas:

CREATE TABLE IF NOT EXISTS Customers(
        CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
        FirstName TEXT NOT NULL,
        LastName TEXT NOT NULL,
        Email TEXT UNIQUE NOT NULL,
        Phone TEXT,
        Address TEXT
);

-- Create Products table
CREATE TABLE IF NOT EXISTS Products (
        ProductID INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Description TEXT,
        Price REAL NOT NULL,
        StockQuantity INTEGER NOT NULL,
        Category TEXT NOT NULL
    );


-- Create Orders table
CREATE TABLE IF NOT EXISTS Orders (
        OrderID INTEGER PRIMARY KEY AUTOINCREMENT,
        CustomerID INTEGER NOT NULL,
        OrderDate DATE NOT NULL,
        TotalAmount REAL NOT NULL,
        FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID)
    );

-- Create OrderDetails table
CREATE TABLE IF NOT EXISTS OrderDetails (
        OrderDetailID INTEGER PRIMARY KEY AUTOINCREMENT,
        OrderID INTEGER NOT NULL,
        ProductID INTEGER NOT NULL,
        Quantity INTEGER NOT NULL,
        Subtotal REAL NOT NULL,
        FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
        FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
    );

Return only the sql query. Don't explain the query and don't put the sql query in ```sql\n```.
"""



FULL_REPORT=  """<div class="">
  <h3>📊 Report </h3>
  <p>The sql query is: {sql_query}</p>
  <p>Here are the results:</p>
  <p>{sql_results}</p>
</div>"""