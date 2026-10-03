from src.parser import parse_message

messages = [
    "Take Metformin 500mg at 9am",
    "Remind me to take Vitamin D 1000 IU at 8pm",
    "add paracetamol 650mg at 21:30",
    "I took Metformin",
    "My BP is 120/80",
    "my sugar is 140",
    "weight 70.5",
    "temperature 99.1",
    "show my medications",
    "show my weight",
    "delete Metformin",
    "help",
    "hello there",
]

for msg in messages:
    print(msg, "->", parse_message(msg))