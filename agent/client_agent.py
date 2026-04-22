import time
import requests
import socket
import json
import logging
from agent.scan_engine import run_full_scan

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SERVER_URL = "http://localhost:8000"
CHECKIN_INTERVAL = 60  # seconds

def get_hostname():
    return socket.gethostname()

def run_agent():
    hostname = get_hostname()
    logging.info(f"Agent started for hostname: {hostname}")

    while True:
        try:
            # 1. Check in with the server
            checkin_url = f"{SERVER_URL}/assets/agent/checkin/{hostname}/"
            response = requests.get(checkin_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                action = data.get("action")
                
                if action == "scan":
                    logging.info("Server requested a scan. Executing...")
                    
                    try:
                        # 2. Run the scan
                        scan_results = run_full_scan()
                        
                        # 3. Upload the format
                        upload_url = f"{SERVER_URL}/assets/agent/upload/"
                        upload_response = requests.post(
                            upload_url, 
                            json=scan_results, 
                            timeout=30
                        )
                        
                        if upload_response.status_code == 200:
                            logging.info("Successfully uploaded scan results.")
                        else:
                            logging.error(f"Failed to upload. Server responded: {upload_response.status_code}")
                            
                    except Exception as e:
                        logging.error(f"Failed during scan or upload: {e}")
                else:
                    logging.debug("Checked in successfully. No tasks pending.")
            else:
                logging.warning(f"Checkin failed with status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logging.warning(f"Server is unreachable or offline. Will retry in {CHECKIN_INTERVAL}s. ({e})")
            
        # Sleep until the next cycle
        time.sleep(CHECKIN_INTERVAL)

if __name__ == "__main__":
    run_agent()
