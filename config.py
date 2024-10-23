from dotenv import load_dotenv
load_dotenv()
import os, sys

BOT_TOKEN= os.getenv("BOT_TOKEN_TEST") if "-test" in sys.argv else os.getenv("BOT_TOKEN") 
DB_NAME="DISTRIB"
BOT_ID = 7893820846 if "-test" in sys.argv else 7030989354 

admin_id = [448582837, 1020207657]
SEND_DELAY = 3
SEND_DELAY_FILE = "delay.txt"
