import sqlite3
import os
import sys

def main():
    # Path to the database file
    db_path = "OrientalMedDic/hanjadic.db"
    
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        sys.exit(1)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables found: {tables}")
        
        search_term = "졸중"
        print(f"\nSearching for '{search_term}' in relevant tables...\n")
        
        # 1. Check disease table
        if "disease" in tables:
            cursor.execute("SELECT name_hanja, name_korean, symptoms FROM disease WHERE name_korean LIKE ?", (f"%{search_term}%",))
            results = cursor.fetchall()
            if results:
                print("Found in 'disease' table:")
                for row in results:
                    print(f"  Hanja: {row[0]}, Korean: {row[1]}, Symptoms: {row[2]}")
            else:
                print("Not found in 'disease' table.")
                
        # 2. Check symptom_formula table
        if "symptom_formula" in tables:
            cursor.execute("SELECT symptom_hanja, symptom_korean, category FROM symptom_formula WHERE symptom_korean LIKE ?", (f"%{search_term}%",))
            results = cursor.fetchall()
            if results:
                print("Found in 'symptom_formula' table:")
                for row in results:
                    print(f"  Hanja: {row[0]}, Korean: {row[1]}, Category: {row[2]}")
            else:
                print("Not found in 'symptom_formula' table.")
                
        # 3. Check hanja_word table
        if "hanja_word" in tables:
            cursor.execute("SELECT hanja, reading, meaning FROM hanja_word WHERE hanja LIKE ? OR reading LIKE ?", (f"%{search_term}%", f"%{search_term}%",))
            results = cursor.fetchall()
            if results:
                print("Found in 'hanja_word' table:")
                for row in results:
                    print(f"  Hanja: {row[0]}, Reading: {row[1]}, Meaning: {row[2]}")
            else:
                print("Not found in 'hanja_word' table.")
                
        # 4. Check herbal table
        if "herbal" in tables:
            cursor.execute("SELECT name_hanja, name_korean FROM herbal WHERE name_korean LIKE ?", (f"%{search_term}%",))
            results = cursor.fetchall()
            if results:
                print("Found in 'herbal' table:")
                for row in results:
                    print(f"  Hanja: {row[0]}, Korean: {row[1]}")
            else:
                print("Not found in 'herbal' table.")
                
        # 5. Check formula table
        if "formula" in tables:
            cursor.execute("SELECT name_hanja, name_korean FROM formula WHERE name_korean LIKE ?", (f"%{search_term}%",))
            results = cursor.fetchall()
            if results:
                print("Found in 'formula' table:")
                for row in results:
                    print(f"  Hanja: {row[0]}, Korean: {row[1]}")
            else:
                print("Not found in 'formula' table.")
                
        # 6. Check acupuncture table
        if "acupuncture" in tables:
            cursor.execute("SELECT name_hanja, name_korean FROM acupuncture WHERE name_korean LIKE ?", (f"%{search_term}%",))
            results = cursor.fetchall()
            if results:
                print("Found in 'acupuncture' table:")
                for row in results:
                    print(f"  Hanja: {row[0]}, Korean: {row[1]}")
            else:
                print("Not found in 'acupuncture' table.")
                
        # 7. Check hanja table
        if "hanja" in tables:
            cursor.execute("SELECT character, hangul_reading, korean_reading FROM hanja WHERE hangul_reading LIKE ? OR korean_reading LIKE ?", (f"%{search_term}%", f"%{search_term}%",))
            results = cursor.fetchall()
            if results:
                print("Found in 'hanja' table:")
                for row in results:
                    print(f"  Character: {row[0]}, Hangul: {row[1]}, Korean: {row[2]}")
            else:
                print("Not found in 'hanja' table.")
                
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
