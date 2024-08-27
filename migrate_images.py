import os
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
MEDIA_ROOT = "J:\\blackdiamondlodge\\BlackDiamondHub\\media"

conn = psycopg2.connect(database=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'), host='postgresql.mi', port='5432')
cur = conn.cursor()
cur.execute("SELECT id, picture FROM items")

for record in cur.fetchall():
    item_id, image_data = record
    if image_data:
        # Construct the relative file path
        relative_file_path = os.path.join('items', f'image_{item_id}.jpg')
        absolute_file_path = os.path.join(MEDIA_ROOT, relative_file_path)

        # Write the image data to the file system
        with open(absolute_file_path, 'wb') as f:
            f.write(image_data)
        
        # Update the database with the relative path
        cur.execute("UPDATE inventory_item SET picture = %s WHERE id = %s", (relative_file_path, item_id))

conn.commit()
cur.close()
conn.close()
