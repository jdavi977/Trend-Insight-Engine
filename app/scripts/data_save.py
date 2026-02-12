import os
import json
from fastapi import HTTPException

def data_save(data):
    DATA_FOLDER = "data"
    file_name = "manually_change.json"
    file_path = os.path.join(DATA_FOLDER, file_name)
    abs_path = os.path.abspath(file_path)

    try:
        with open(abs_path, "w") as f:
            json.dump(data, f, indent=4)
        print("Saved")
    except IOError as e:
        print(f"Error saving file: {e}")
        raise HTTPException(status_code = 500, detail="Could not save data")
    return {"message": f"Data received and saved as {file_name}"}
