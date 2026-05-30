import os
import time

print("Waiting until 19:00 to start Night Shift...")
while True:
    current_hour = time.localtime().tm_hour
    if current_hour >= 19 or current_hour < 7:
        break
    time.sleep(60)

print("It is now 7:00 PM or later. Transitioning to Night Shift.")

with open("run_autoresearch_loop.py") as f:
    content = f.read()

# Make sure it's fully configured for night shift
content = content.replace(
    "log_filename = f\"sprint_logs/sprint_log_{time.strftime('%Y-%m-%d_%H-%M-%S')}_day_shift.md\"",
    "log_filename = f\"sprint_logs/sprint_log_{time.strftime('%Y-%m-%d_%H-%M-%S')}_night_shift.md\"",
)
content = content.replace(
    "print(f\"--- DAY SHIFT STARTING AT {time.strftime('%H:%M:%S')} ---\")",
    "print(f\"--- NIGHT SHIFT STARTING AT {time.strftime('%H:%M:%S')} ---\")",
)
content = content.replace(
    'print(f"Starting persistent background loop until 7:00 PM...")',
    'print(f"Starting persistent background loop until 7:00 AM...")',
)
content = content.replace(
    "log.write(f\"# Day Shift Sprint - {time.strftime('%Y-%m-%d')}\\n\")",
    "log.write(f\"# Night Shift Sprint - {time.strftime('%Y-%m-%d')}\\n\")",
)
content = content.replace("if current_hour == 19:", "if current_hour == 7:")
content = content.replace(
    'print("7:00 PM reached. Ending Day Shift sprint.")',
    'print("7:00 AM reached. Ending Night Shift sprint.")',
)
content = content.replace(
    'log.write(f"\\n## Sprint Completed at 7:00 PM\\n")',
    'log.write(f"\\n## Sprint Completed at 7:00 AM\\n")',
)
content = content.replace(
    "f.write(f\"\\n\\n--- DAY SHIFT CYCLE {i}: {tweak['name']} ---\\n\")",
    "f.write(f\"\\n\\n--- NIGHT SHIFT CYCLE {i}: {tweak['name']} ---\\n\")",
)
content = content.replace(
    'os.system(f\'git add . && git commit -m "Day Shift: {tweak["name"]} improved model"\')',
    'os.system(f\'git add . && git commit -m "Night Shift: {tweak["name"]} improved model"\')',
)

with open("run_autoresearch_loop.py", "w") as f:
    f.write(content)

os.system(
    'git add run_autoresearch_loop.py && git commit -m "Configure research loop for Night Shift (7 PM - 7 AM)" && git push origin main'
)

# Kill any existing loops
os.system("pkill -f run_autoresearch_loop.py")
os.system("pkill -f train.py")
time.sleep(2)

# Start the Night Shift loop
os.system("uv run python run_autoresearch_loop.py &")
