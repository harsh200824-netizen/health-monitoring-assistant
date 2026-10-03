from src.database import *

init_db()

med_id = add_medication("Metformin", "500mg", "09:00")
add_medication("Vitamin D", "1000 IU", "20:00")
log_dose(med_id)
add_metric("blood_pressure", "120/80", "mmHg")
add_metric("weight", 70, "kg")

print("Medications:", get_medications())
print("Dose log:", get_dose_log())
print("Metrics:", get_metrics())