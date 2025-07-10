import sqlite3

def create_tables():
    conn = sqlite3.connect("biometric.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS biometric_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aadhaar_voter_hash TEXT UNIQUE,
            photo_hash TEXT UNIQUE,
            fingerprint_hash TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()

def store_hashes(aadhaar_voter_hash, photo_hash, fingerprint_hash):
    conn = sqlite3.connect("biometric.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO biometric_data (aadhaar_voter_hash, photo_hash, fingerprint_hash)
        VALUES (?, ?, ?)
    """, (aadhaar_voter_hash, photo_hash, fingerprint_hash))
    conn.commit()
    conn.close()

def check_duplicate(aadhaar_voter_hash, photo_hash, fingerprint_hash):
    conn = sqlite3.connect("biometric.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM biometric_data
        WHERE aadhaar_voter_hash=? OR photo_hash=? OR fingerprint_hash=?
    """, (aadhaar_voter_hash, photo_hash, fingerprint_hash))
    result = cursor.fetchone()
    conn.close()
    return result is not None
