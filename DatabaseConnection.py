import mysql.connector
db=mysql.connector.connect(
    host="localhost",
    user="root",
    password="tomas"
)
print('connected:',db)