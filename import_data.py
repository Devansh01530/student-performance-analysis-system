import sys
import database

# Initialize database schema if not present
database.create_tables()

file_path = "data/students.csv"

# Check if overwrite flag is explicitly provided via command line
overwrite_flag = "--overwrite" in sys.argv

existing_students = database.get_students()
print("Current enrolled students in database:", len(existing_students))

if overwrite_flag:
    print("Action: Overwrite mode enabled. Cleaning up tables in foreign-key order...")
else:
    print("Action: Safe append mode enabled. Existing students and attendance are protected.")

try:
    total = database.import_students_from_csv(file_path, overwrite=overwrite_flag)
    print("CSV data processed successfully!")
    print("Total student rows processed:", total)

    print("\nUpdated Student Registry:")
    print(database.get_students()[["id", "name", "department", "semester"]])

    print("\nCurrent Marks Count:", len(database.get_marks()))

except Exception as e:
    print("Error during data import:", e)
