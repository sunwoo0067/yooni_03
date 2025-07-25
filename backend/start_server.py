"""
Script to start the backend server with proper error handling
"""
import subprocess
import sys
import time

def start_server():
    """Start the FastAPI backend server"""
    print("=" * 60)
    print("Starting Yooni E-commerce Backend Server")
    print("=" * 60)
    
    try:
        # Change to backend directory and run the server
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=".",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Print output in real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                
            error = process.stderr.readline()
            if error:
                print(f"ERROR: {error.strip()}", file=sys.stderr)
        
        # Get the return code
        rc = process.poll()
        if rc != 0:
            print(f"\nServer exited with code {rc}")
            
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        process.terminate()
        time.sleep(2)
        if process.poll() is None:
            process.kill()
        print("Server stopped.")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_server()