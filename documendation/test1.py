import random
import string
import json

def generate_large_json_data(num_records=5, num_fields=3, field_length=30):
  """
  Generates a large dictionary with the specified number of records and fields.

  Args:
      num_records: The number of records to generate.
      num_fields: The number of fields per record.
      field_length: The maximum length of each field value.

  Returns:
      dict: A dictionary containing the generated data.
  """
  data = {}
  for i in range(num_records):
    record = {}
    for j in range(num_fields):
      field_name = f"field_{j}"
      field_value = ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(1, field_length)))
      record[field_name] = field_value
    data[f"record_{i}"] = record
  return data

# Generate the large dictionary
large_data = generate_large_json_data()

# Convert the dictionary to JSON string
json_data = json.dumps(large_data)

# Print the estimated size (in bytes)
print(json_data)
print(f"Estimated size: {len(json_data)} bytes")