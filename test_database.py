import database

# Create database tables
database.create_tables()
print("Database created successfully!")

# Add a sample student
email_test = "temp_test@example.com"
result = database.add_student("Test Student", email_test, "BCA", 3)

if result:
    print("Student added successfully!")
    students = database.get_students()
    test_record = students[students["email"] == email_test]
    if not test_record.empty:
        test_id = int(test_record.iloc[0]["id"])
        database.delete_student(test_id)
        print(f"Sample test record (ID: {test_id}) verified and cleaned up successfully.")
else:
    print("Student already exists or operation could not be completed.")

# Display students
print("\nCurrent Enrolled Students:")
print(database.get_students())
