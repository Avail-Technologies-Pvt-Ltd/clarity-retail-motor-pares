# Example: Process numbers, but skip processing for even numbers

numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

print("Starting the loop...")
for number in numbers:
    if number % 2 == 0: # Check if the number is even
        print(f"Skipping even number: {number}")
        continue  # This statement jumps directly to the next iteration of the loop
    
    # This code block will only execute for odd numbers
    print(f"Processing odd number: {number}")
    print(f"  Square of {number}: {number * number}")

print("Loop finished.")


# -----------------------------------------------------------------------------------------------------------------------

# models = ['a','b','c',1,2,3,4,5,6,7,8,9,0]
# for model in models:
# 	print(model)



# -----------------------------------------------------------------------------------------------------------------------


# list_ = []
# list_.append({1:"one"})
# list_.append({2:"2one"})
# list_.append({3:"3one"})
# list_.append({1:"one"})
# list_.append({1:"one"})
# list_.append({1:"one"})
# print(list_)



# -----------------------------------------------------------------------------------------------------------------------

# import random
# import string
# import json

# def generate_large_json_data(num_records=5, num_fields=3, field_length=30):
#   """
#   Generates a large dictionary with the specified number of records and fields.

#   Args:
#       num_records: The number of records to generate.
#       num_fields: The number of fields per record.
#       field_length: The maximum length of each field value.

#   Returns:
#       dict: A dictionary containing the generated data.
#   """
#   data = {}
#   for i in range(num_records):
#     record = {}
#     for j in range(num_fields):
#       field_name = f"field_{j}"
#       field_value = ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(1, field_length)))
#       record[field_name] = field_value
#     data[f"record_{i}"] = record
#   return data

# # Generate the large dictionary
# large_data = generate_large_json_data()

# # Convert the dictionary to JSON string
# json_data = json.dumps(large_data)

# # Print the estimated size (in bytes)
# print(json_data)
# print(f"Estimated size: {len(json_data)} bytes")