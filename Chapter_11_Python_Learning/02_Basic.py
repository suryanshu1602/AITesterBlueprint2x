name = "Pramod"
name = "Dutta"
name = 123
print("Hi ",name)

# identifier - Identifier basically means the name of the variable. 
# literal - Variable value is called the variable literal. 
# = -> Nothing but an operator 

test_name = "Login should succeed"
print(type(test_name)) # str - String 

retry_count = 3
print(type(retry_count)) # int

response_time = 0.847  # float - decimal seconds
is_passing = True      # bool - True / False
error_message = None   # None - "nothing here yet"


base_url = "https://api.thetestingacademy.com"
endpoint = "/v1/login"
expected_status = 200
timeout_seconds = 30


print(f"I will hit this {base_url}{endpoint}, and I am expecting that it will be {expected_status} Ok!")