import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import uvicorn

DB_FILE = "logistics.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Pallets (
            PalletCode TEXT PRIMARY KEY,
            Quantity INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

app = FastAPI(
    title="Logistics Batch Validator API",
    description="Local API for syncing barcode scans with the YOLO Vision System",
    version="1.0"
)

class PalletData(BaseModel):
    PalletCode: str
    Quantity: int

@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url = "/docs")

@app.get("/Pallets", summary = "Lookup a pallet by Pallet Code")
def GetAllPallet():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Pallets")
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "PalletCode": row[0],
            "Quantity": row[1]
        } for row in rows
    ]

@app.get("/Pallets/{PalletCode}", summary = "Lookup a pallet by Pallet Code")
def GetByPalletCode(PalletCode: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT Quantity FROM Pallets WHERE PalletCode = ?", (PalletCode,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code = 404, detail = "Pallet Code not found in database.")

    return {
        "PalletCode": PalletCode,
        "Quantity": row[0]
    }

@app.post("/Pallets", summary = "Add a new pallet to the database")
def CreatePallet(pallet: PalletData):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT OR REPLACE INTO Pallets (PalletCode, Quantity) VALUES (?, ?)",
            (pallet.PalletCode, pallet.Quantity)
        )
        conn.commit()
        conn.close()
        return {"message": f"Successfully logged {pallet.PalletCode} expecting {pallet.Quantity} boxes."}
    except Exception as e:
        raise HTTPException(status_code = 500, detail = str(e))
    
@app.delete("/Pallets/{PalletCode}", summary = "Delete a pallet from the database")
def DeletePallet(PalletCode: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Pallets WHERE PalletCode = ?", (PalletCode,))
    conn.commit()
    conn.close()

    return {"message": f"Successfully deleted pallet {PalletCode}."}

if __name__ == "__main__":
    print("Starting API Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)