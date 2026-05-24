model = "claude-sonnet-4-20250514"
model2 = "gpt-5.4"
model3 = "gemini-2.5-flash"

print(model)
print(model2)
print(model3)

print(type(model))
print(type(model2))
print(type(model3))

task = "summarize bug reports"
print(task)
print(type(task))

# Template literal | Format strings 
prompt = f"You are {model}. Your task is to {task}."
print(prompt)