actual_status = 200
expected_status = "200" 
print(actual_status == expected_status) 
print(actual_status == int(expected_status))

raw_input_from_csv = "45"
expected_item_count = int(raw_input_from_csv)
# str()
print(expected_item_count)

# Numbers
max_retries = 3              # int
temperature = 0.7            # float (you'll see this in every LLM config)
confidence_threshold = 0.85  # float